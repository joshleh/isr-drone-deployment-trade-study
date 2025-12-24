from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

from .scenario import Scenario, StrategySpec
from .metrics import RunMetrics, compute_revisit_stats

@dataclass
class DroneState:
    x: int
    y: int
    active: bool = True

def _clip(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))

def _disk_offsets(r: int) -> List[Tuple[int, int]]:
    # Precompute integer offsets within a radius r (inclusive).
    offsets: List[Tuple[int, int]] = []
    r2 = r * r
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r2:
                offsets.append((dx, dy))
    return offsets

def run_simulation(
    scenario: Scenario,
    strategy: StrategySpec,
    rng: np.random.Generator,
) -> RunMetrics:
    W, H = scenario.grid.width, scenario.grid.height
    T = scenario.time.steps
    N = scenario.fleet.num_drones
    r = scenario.fleet.sensor_radius

    # coverage bookkeeping
    ever_seen = np.zeros((H, W), dtype=bool)
    last_seen = np.full((H, W), -1, dtype=int)
    coverage_over_time = np.zeros(T, dtype=float)

    # initialize drone states
    drones: List[DroneState] = []
    if strategy.type == "static":
        if not strategy.static_points or len(strategy.static_points) < N:
            raise ValueError("Static strategy requires >= num_drones points.")
        for i in range(N):
            x, y = strategy.static_points[i]
            drones.append(DroneState(_clip(x, 0, W - 1), _clip(y, 0, H - 1), True))
    elif strategy.type == "patrol":
        # start positions random
        for _ in range(N):
            drones.append(DroneState(int(rng.integers(0, W)), int(rng.integers(0, H)), True))
    else:
        raise ValueError(f"Unknown strategy type: {strategy.type}")

    offsets = _disk_offsets(r)

    active_steps_total = 0
    for t in range(T):
        # update active status by endurance
        for d in drones:
            d.active = (t < scenario.fleet.endurance_steps)

        # move drones if patrol
        if strategy.type == "patrol":
            step = max(1, int(strategy.patrol_step_size))
            turn_prob = float(strategy.patrol_turn_prob)

            # Random-walk with occasional direction change
            # store per-drone direction implicitly each step
            for d in drones:
                if not d.active:
                    continue
                # choose a random direction; more likely to keep going "straight" is not modeled yet
                if rng.random() < turn_prob:
                    dx, dy = rng.choice([-1, 0, 1]), rng.choice([-1, 0, 1])
                    if dx == 0 and dy == 0:
                        dx = 1
                else:
                    dx, dy = rng.choice([-1, 0, 1]), rng.choice([-1, 0, 1])
                    if dx == 0 and dy == 0:
                        dy = 1

                d.x = _clip(d.x + dx * step, 0, W - 1)
                d.y = _clip(d.y + dy * step, 0, H - 1)

        # apply sensing
        for d in drones:
            if not d.active:
                continue
            active_steps_total += 1
            cx, cy = d.x, d.y
            for dx, dy in offsets:
                x = cx + dx
                y = cy + dy
                if 0 <= x < W and 0 <= y < H:
                    ever_seen[y, x] = True
                    last_seen[y, x] = t

        # coverage fraction at time t (ever-seen up to t)
        coverage_over_time[t] = float(np.mean(ever_seen))

    avg_coverage = float(np.mean(coverage_over_time))
    revisit_mean, revisit_p90 = compute_revisit_stats(last_seen, T)

    total_cost = float(active_steps_total * scenario.fleet.cost_per_step)
    utilization = float(active_steps_total / (T * N))

    return RunMetrics(
        coverage_over_time=coverage_over_time,
        avg_coverage=avg_coverage,
        revisit_time_mean=revisit_mean,
        revisit_time_p90=revisit_p90,
        total_cost=total_cost,
        utilization=utilization,
    )