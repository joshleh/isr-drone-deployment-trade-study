from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .metrics import RunMetrics, summarize_response_times, summarize_revisit_gaps
from .scenario import DynamicTask, Scenario, StrategySpec


@dataclass
class DroneState:
    x: int
    y: int
    sensor_radius: int
    endurance_steps: int
    cost_per_step: float
    step_size: int
    platform_name: str
    heading_x: int = 1
    heading_y: int = 0
    active: bool = True
    target_key: Optional[str] = None
    target_lock_remaining: int = 0


@dataclass(frozen=True)
class CandidateTarget:
    key: str
    kind: str
    centroid: tuple[int, int]
    utility: float
    capacity: int = 1


def _clip(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _sign(v: int) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _random_direction(rng: np.random.Generator) -> tuple[int, int]:
    while True:
        dx = int(rng.choice([-1, 0, 1]))
        dy = int(rng.choice([-1, 0, 1]))
        if dx != 0 or dy != 0:
            return dx, dy


def _disk_offsets(r: int) -> List[Tuple[int, int]]:
    offsets: List[Tuple[int, int]] = []
    r2 = r * r
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r2:
                offsets.append((dx, dy))
    return offsets


def _make_rect_mask(
    width: int,
    height: int,
    x_min: int,
    x_max: int,
    y_min: int,
    y_max: int,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    xs = slice(_clip(min(x_min, x_max), 0, width - 1), _clip(max(x_min, x_max), 0, width - 1) + 1)
    ys = slice(_clip(min(y_min, y_max), 0, height - 1), _clip(max(y_min, y_max), 0, height - 1) + 1)
    mask[ys, xs] = True
    return mask


def _mask_centroid(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    if xs.size == 0:
        return 0, 0
    return int(round(np.mean(xs))), int(round(np.mean(ys)))


def _mean_mask_age(mask: np.ndarray, last_seen: np.ndarray, t: int) -> float:
    seen_steps = last_seen[mask]
    if seen_steps.size == 0:
        return float(t + 1)
    ages = np.where(seen_steps < 0, t + 1, t - seen_steps)
    return float(np.mean(ages))


def _move_toward(
    drone: DroneState,
    target_x: int,
    target_y: int,
    width: int,
    height: int,
) -> None:
    dx = _sign(target_x - drone.x)
    dy = _sign(target_y - drone.y)
    if dx == 0 and dy == 0:
        return
    drone.heading_x = dx
    drone.heading_y = dy
    drone.x = _clip(drone.x + dx * drone.step_size, 0, width - 1)
    drone.y = _clip(drone.y + dy * drone.step_size, 0, height - 1)


def _expand_fleet(scenario: Scenario, strategy: StrategySpec, rng: np.random.Generator) -> list[DroneState]:
    width, height = scenario.grid.width, scenario.grid.height
    drones: list[DroneState] = []
    default_step = max(1, int(strategy.patrol_step_size))

    if scenario.fleet.platforms:
        for platform in scenario.fleet.platforms:
            for _ in range(platform.count):
                heading_x, heading_y = _random_direction(rng)
                drones.append(
                    DroneState(
                        x=0,
                        y=0,
                        sensor_radius=platform.sensor_radius,
                        endurance_steps=platform.endurance_steps,
                        cost_per_step=platform.cost_per_step,
                        step_size=max(default_step, int(platform.cruise_step_size)),
                        platform_name=platform.name,
                        heading_x=heading_x,
                        heading_y=heading_y,
                    )
                )
    else:
        for _ in range(scenario.fleet.num_drones):
            heading_x, heading_y = _random_direction(rng)
            drones.append(
                DroneState(
                    x=0,
                    y=0,
                    sensor_radius=scenario.fleet.sensor_radius,
                    endurance_steps=scenario.fleet.endurance_steps,
                    cost_per_step=scenario.fleet.cost_per_step,
                    step_size=default_step,
                    platform_name="homogeneous",
                    heading_x=heading_x,
                    heading_y=heading_y,
                )
            )

    if strategy.type == "static":
        if not strategy.static_points or len(strategy.static_points) < len(drones):
            raise ValueError("Static strategy requires >= total drone count points.")
        for drone, (x, y) in zip(drones, strategy.static_points):
            drone.x = _clip(x, 0, width - 1)
            drone.y = _clip(y, 0, height - 1)
    else:
        for drone in drones:
            drone.x = int(rng.integers(0, width))
            drone.y = int(rng.integers(0, height))

    return drones


def _build_priority_targets(scenario: Scenario) -> list[tuple[np.ndarray, tuple[int, int], float]]:
    targets: list[tuple[np.ndarray, tuple[int, int], float]] = []
    for zone in scenario.priority_zones:
        mask = _make_rect_mask(
            scenario.grid.width,
            scenario.grid.height,
            zone.x_min,
            zone.x_max,
            zone.y_min,
            zone.y_max,
        )
        targets.append((mask, _mask_centroid(mask), float(zone.weight)))
    return targets


def _build_task_records(scenario: Scenario) -> list[dict]:
    records: list[dict] = []
    for task in scenario.dynamic_tasks:
        mask = _make_rect_mask(
            scenario.grid.width,
            scenario.grid.height,
            task.x_min,
            task.x_max,
            task.y_min,
            task.y_max,
        )
        records.append(
            {
                "task": task,
                "mask": mask,
                "centroid": _mask_centroid(mask),
                "response_time": None,
            }
        )
    return records


def _step_patrol(drone: DroneState, turn_prob: float, width: int, height: int, rng: np.random.Generator) -> None:
    if rng.random() < turn_prob:
        drone.heading_x, drone.heading_y = _random_direction(rng)
    drone.x = _clip(drone.x + drone.heading_x * drone.step_size, 0, width - 1)
    drone.y = _clip(drone.y + drone.heading_y * drone.step_size, 0, height - 1)


def _candidate_score(
    drone: DroneState,
    candidate: CandidateTarget,
    strategy: StrategySpec,
) -> float:
    cx, cy = candidate.centroid
    dist = abs(cx - drone.x) + abs(cy - drone.y)
    platform_fit = 1.0 + 0.08 * drone.sensor_radius + 0.04 * drone.step_size

    if candidate.kind == "task":
        kind_bias = strategy.task_priority_bias
    elif candidate.kind == "priority_zone":
        kind_bias = strategy.priority_zone_bias
    else:
        kind_bias = strategy.exploration_bias

    if strategy.type == "priority_patrol":
        if candidate.kind == "task":
            if drone.platform_name == "scout":
                platform_fit *= 1.42
            elif drone.platform_name == "sentinel":
                platform_fit *= 0.72
        elif candidate.kind == "priority_zone":
            if drone.platform_name == "sentinel":
                platform_fit *= 1.48
            elif drone.platform_name == "scout":
                platform_fit *= 0.74
        elif candidate.kind == "explore" and drone.platform_name == "scout":
            platform_fit *= 1.08

    return kind_bias * candidate.utility * platform_fit / (1.0 + dist)


def _build_candidate_targets(
    task_records: Sequence[dict],
    priority_targets: Sequence[tuple[np.ndarray, tuple[int, int], float]],
    ever_seen: np.ndarray,
    last_seen: np.ndarray,
    t: int,
    strategy: StrategySpec,
    rng: np.random.Generator,
) -> list[CandidateTarget]:
    candidates: list[CandidateTarget] = []

    for record in task_records:
        task: DynamicTask = record["task"]
        if not (task.start_step <= t < task.end_step):
            continue
        task_seen_ratio = float(np.mean(ever_seen[record["mask"]]))
        age_factor = min(1.0, _mean_mask_age(record["mask"], last_seen, t) / max(1, t + 1))
        urgency_boost = 1.55 if record["response_time"] is None else 1.0
        cx, cy = record["centroid"]
        utility = (
            task.priority
            * urgency_boost
            * (0.8 + 0.9 * age_factor)
            * max(0.25, 1.0 - 0.4 * task_seen_ratio)
        )
        capacity = 2 if task.priority >= 4.0 else 1
        candidates.append(
            CandidateTarget(
                key=f"task:{task.name}",
                kind="task",
                centroid=(cx, cy),
                utility=utility,
                capacity=capacity,
            )
        )

    for idx, (mask, centroid, weight) in enumerate(priority_targets):
        seen_ratio = float(np.mean(ever_seen[mask]))
        age_factor = min(1.0, _mean_mask_age(mask, last_seen, t) / max(1, t + 1))
        candidates.append(
            CandidateTarget(
                key=f"zone:{idx}",
                kind="priority_zone",
                centroid=centroid,
                utility=weight * max(0.18, (0.35 * (1.0 - seen_ratio)) + (0.65 * age_factor)),
                capacity=2 if weight >= 3.0 else 1,
            )
        )

    unseen = np.argwhere(~ever_seen)
    if unseen.size > 0:
        sample_size = min(len(unseen), 48)
        sample_indices = rng.choice(len(unseen), size=sample_size, replace=False)
        for seq, idx in enumerate(sample_indices):
            y, x = unseen[int(idx)]
            candidates.append(
                CandidateTarget(
                    key=f"explore:{seq}",
                    kind="explore",
                    centroid=(int(x), int(y)),
                    utility=1.0,
                    capacity=1,
                )
            )

    return candidates


def _assign_targets(
    drones: Sequence[DroneState],
    candidates: Sequence[CandidateTarget],
    strategy: StrategySpec,
    mode: str,
) -> dict[int, CandidateTarget]:
    assignments: dict[int, CandidateTarget] = {}
    candidate_map = {candidate.key: candidate for candidate in candidates}
    used_capacity = {candidate.key: 0 for candidate in candidates}
    active_task_exists = any(candidate.kind == "task" for candidate in candidates)

    if mode == "priority_patrol":
        for idx, drone in enumerate(drones):
            if drone.target_key is None or drone.target_lock_remaining <= 0:
                continue
            candidate = candidate_map.get(drone.target_key)
            if candidate is None:
                continue
            if candidate.kind == "explore":
                continue
            if active_task_exists and candidate.kind != "task":
                if not (candidate.kind == "priority_zone" and drone.platform_name == "sentinel"):
                    continue
            if candidate.kind == "priority_zone" and drone.platform_name not in {"sentinel", "homogeneous"}:
                continue
            if used_capacity[candidate.key] >= candidate.capacity:
                continue
            assignments[idx] = candidate
            used_capacity[candidate.key] += 1

    pending = [idx for idx in range(len(drones)) if idx not in assignments]
    proposals: list[tuple[float, int, str]] = []
    for idx in pending:
        drone = drones[idx]
        for candidate in candidates:
            score = _candidate_score(drone, candidate, strategy)
            if mode == "priority_patrol":
                if active_task_exists and drone.platform_name == "sentinel" and candidate.kind == "task":
                    score *= 0.72
                if active_task_exists and drone.platform_name == "scout" and candidate.kind == "priority_zone":
                    score *= 0.78
            if mode == "priority_patrol" and candidate.key == drone.target_key:
                score *= 1.2
            proposals.append((score, idx, candidate.key))

    proposals.sort(reverse=True, key=lambda item: item[0])

    for score, idx, candidate_key in proposals:
        if idx in assignments:
            continue
        candidate = candidate_map[candidate_key]
        occupancy = used_capacity[candidate_key]
        if occupancy >= candidate.capacity:
            continue
        adjusted_score = score * ((1.0 - strategy.congestion_penalty) ** occupancy)
        if adjusted_score <= 0:
            continue
        assignments[idx] = candidate
        used_capacity[candidate_key] += 1

    return assignments


def run_simulation(
    scenario: Scenario,
    strategy: StrategySpec,
    rng: np.random.Generator,
) -> RunMetrics:
    """Single Monte Carlo execution of a scenario under a strategy."""
    width, height = scenario.grid.width, scenario.grid.height
    steps = scenario.time.steps

    ever_seen = np.zeros((height, width), dtype=bool)
    last_seen = np.full((height, width), -1, dtype=int)
    coverage_over_time = np.zeros(steps, dtype=float)
    weighted_coverage_over_time = np.zeros(steps, dtype=float)
    task_service_over_time = np.zeros(steps, dtype=float)

    priority_weights = np.ones((height, width), dtype=float)
    priority_mask = np.zeros((height, width), dtype=bool)
    for zone in scenario.priority_zones:
        mask = _make_rect_mask(width, height, zone.x_min, zone.x_max, zone.y_min, zone.y_max)
        priority_weights[mask] = np.maximum(priority_weights[mask], float(zone.weight))
        priority_mask[mask] = True
    total_priority_weight = float(np.sum(priority_weights))

    revisit_gaps: list[int] = []
    priority_revisit_gaps: list[int] = []
    persistence_threshold_steps = 10

    drones = _expand_fleet(scenario, strategy, rng)
    max_available_steps = float(sum(min(steps, drone.endurance_steps) for drone in drones))
    offset_cache = {drone.sensor_radius: _disk_offsets(drone.sensor_radius) for drone in drones}
    priority_targets = _build_priority_targets(scenario)
    task_records = _build_task_records(scenario)

    active_steps_total = 0.0
    total_cost = 0.0
    total_sensor_observations = 0
    newly_covered_observations = 0
    weighted_task_service_numerator = 0.0
    weighted_task_service_denominator = 0.0

    for t in range(steps):
        seen_this_step = np.zeros((height, width), dtype=bool)

        for drone in drones:
            drone.active = t < drone.endurance_steps

        if strategy.type == "patrol":
            for drone in drones:
                if drone.active:
                    _step_patrol(drone, float(strategy.patrol_turn_prob), width, height, rng)
        elif strategy.type in {"priority_patrol", "greedy_patrol"}:
            active_drone_indices = [idx for idx, drone in enumerate(drones) if drone.active]
            active_drones = [drones[idx] for idx in active_drone_indices]
            candidates = _build_candidate_targets(
                task_records=task_records,
                priority_targets=priority_targets,
                ever_seen=ever_seen,
                last_seen=last_seen,
                t=t,
                strategy=strategy,
                rng=rng,
            )
            assignments = _assign_targets(
                drones=active_drones,
                candidates=candidates,
                strategy=strategy,
                mode=strategy.type,
            )

            for local_idx, drone in enumerate(active_drones):
                candidate = assignments.get(local_idx)
                if candidate is None:
                    _step_patrol(drone, float(strategy.patrol_turn_prob), width, height, rng)
                    drone.target_key = None
                    drone.target_lock_remaining = 0
                    continue

                _move_toward(drone, candidate.centroid[0], candidate.centroid[1], width, height)
                if strategy.type == "priority_patrol":
                    drone.target_key = candidate.key
                    drone.target_lock_remaining = max(0, int(strategy.target_commitment_steps))
                else:
                    drone.target_key = None
                    drone.target_lock_remaining = 0

            if strategy.type == "priority_patrol":
                for drone in drones:
                    if drone.active and drone.target_lock_remaining > 0:
                        drone.target_lock_remaining -= 1

        for drone in drones:
            if not drone.active:
                continue
            active_steps_total += 1.0
            total_cost += float(drone.cost_per_step)
            cx, cy = drone.x, drone.y
            for dx, dy in offset_cache[drone.sensor_radius]:
                x = cx + dx
                y = cy + dy
                if 0 <= x < width and 0 <= y < height:
                    seen_this_step[y, x] = True
                    total_sensor_observations += 1
                    if not ever_seen[y, x]:
                        newly_covered_observations += 1

                    prev = last_seen[y, x]
                    if 0 <= prev < t:
                        gap = t - prev
                        revisit_gaps.append(gap)
                        if priority_mask[y, x]:
                            priority_revisit_gaps.append(gap)

                    ever_seen[y, x] = True
                    last_seen[y, x] = t

        coverage_over_time[t] = float(np.mean(ever_seen))
        weighted_coverage_over_time[t] = float(np.sum(priority_weights * ever_seen) / total_priority_weight)

        active_task_weight = 0.0
        weighted_task_service = 0.0
        for record in task_records:
            task: DynamicTask = record["task"]
            if not (task.start_step <= t < task.end_step):
                continue
            service_fraction = float(np.mean(seen_this_step[record["mask"]]))
            weighted_task_service += task.priority * service_fraction
            active_task_weight += task.priority
            if service_fraction > 0.0 and record["response_time"] is None:
                record["response_time"] = t - task.start_step

        if active_task_weight > 0:
            task_service_over_time[t] = weighted_task_service / active_task_weight
            weighted_task_service_numerator += weighted_task_service
            weighted_task_service_denominator += active_task_weight

    avg_coverage = float(np.mean(coverage_over_time))
    final_coverage = float(coverage_over_time[-1]) if steps else 0.0
    avg_weighted_coverage = float(np.mean(weighted_coverage_over_time))
    final_weighted_coverage = float(weighted_coverage_over_time[-1]) if steps else 0.0
    priority_cell_coverage = float(np.mean(ever_seen[priority_mask])) if np.any(priority_mask) else final_coverage

    gaps = np.array(revisit_gaps, dtype=int)
    priority_gaps = np.array(priority_revisit_gaps, dtype=int)
    gap_mean, gap_p90, pct_within = summarize_revisit_gaps(gaps, persistence_threshold_steps)
    priority_gap_mean, priority_gap_p90, priority_pct_within = summarize_revisit_gaps(
        priority_gaps,
        persistence_threshold_steps,
    )

    response_times = np.array(
        [record["response_time"] for record in task_records if record["response_time"] is not None],
        dtype=float,
    )
    mean_response_time, p90_response_time, pct_tasks_within = summarize_response_times(
        response_times,
        persistence_threshold_steps,
    )
    avg_task_service_rate = (
        float(weighted_task_service_numerator / weighted_task_service_denominator)
        if weighted_task_service_denominator > 0
        else 0.0
    )
    task_completion_rate = (
        float(len(response_times) / len(task_records))
        if task_records
        else 0.0
    )

    utilization = float(active_steps_total / max_available_steps) if max_available_steps > 0 else 0.0
    redundancy_ratio = (
        float(1.0 - (newly_covered_observations / total_sensor_observations))
        if total_sensor_observations
        else 0.0
    )
    coverage_efficiency = float(final_weighted_coverage / total_cost) if total_cost > 0 else 0.0

    return RunMetrics(
        coverage_over_time=coverage_over_time,
        avg_coverage=avg_coverage,
        final_coverage=final_coverage,
        weighted_coverage_over_time=weighted_coverage_over_time,
        avg_weighted_coverage=avg_weighted_coverage,
        final_weighted_coverage=final_weighted_coverage,
        priority_cell_coverage=priority_cell_coverage,
        revisit_gap_mean=gap_mean,
        revisit_gap_p90=gap_p90,
        pct_revisits_within_threshold=pct_within,
        priority_revisit_gap_mean=priority_gap_mean,
        priority_revisit_gap_p90=priority_gap_p90,
        pct_priority_revisits_within_threshold=priority_pct_within,
        task_service_over_time=task_service_over_time,
        avg_task_service_rate=avg_task_service_rate,
        task_completion_rate=task_completion_rate,
        mean_task_response_time=mean_response_time,
        p90_task_response_time=p90_response_time,
        pct_tasks_responded_within_threshold=pct_tasks_within,
        total_cost=total_cost,
        utilization=utilization,
        redundancy_ratio=redundancy_ratio,
        coverage_efficiency=coverage_efficiency,
    )
