from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from anduril_ops.sim.scenario import DynamicTask, PlatformSpec, PriorityZone, Scenario


def strategy_display_name(strategy: str) -> str:
    labels = {
        "static": "Static coverage plan",
        "patrol": "Random patrol",
        "greedy_patrol": "Assignment planner",
        "assignment_patrol": "Assignment planner",
        "priority_patrol": "Task-aware planner",
    }
    return labels.get(strategy, strategy.replace("_", " ").title())


@dataclass(frozen=True)
class MissionAsset:
    label: str
    platform_name: str
    role: str
    sensor_radius: int
    endurance_steps: int
    cruise_step_size: int
    cost_per_step: float
    summary: str


@dataclass(frozen=True)
class MissionZone:
    name: str
    weight: float
    centroid_x: int
    centroid_y: int
    area_cells: int
    purpose: str


@dataclass(frozen=True)
class MissionTask:
    name: str
    priority: float
    start_step: int
    end_step: int
    duration_steps: int
    purpose: str
    suggested_owner_role: str


@dataclass(frozen=True)
class AllocationRecommendation:
    phase: str
    asset_group: str
    target_name: str
    target_kind: str
    reason: str


@dataclass(frozen=True)
class MissionOverview:
    scenario_name: str
    preferred_policy: str
    plain_english_summary: str
    assets: tuple[MissionAsset, ...]
    zones: tuple[MissionZone, ...]
    tasks: tuple[MissionTask, ...]
    allocation_playbook: tuple[AllocationRecommendation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "preferred_policy": self.preferred_policy,
            "plain_english_summary": self.plain_english_summary,
            "assets": [asdict(asset) for asset in self.assets],
            "zones": [asdict(zone) for zone in self.zones],
            "tasks": [asdict(task) for task in self.tasks],
            "allocation_playbook": [asdict(rec) for rec in self.allocation_playbook],
        }


def _asset_role(platform_name: str) -> str:
    lower = platform_name.lower()
    if "sentinel" in lower:
        return "anchor"
    if "scout" in lower:
        return "respond"
    return "general"


def _asset_summary(platform: PlatformSpec) -> str:
    role = _asset_role(platform.name)
    role_text = {
        "anchor": "stays over high-value areas and keeps persistent watch",
        "respond": "moves quickly toward new incidents and unserved space",
        "general": "balances coverage and response as a general-purpose asset",
    }[role]
    return (
        f"{platform.name.title()} platform with sensor radius {platform.sensor_radius}, "
        f"endurance {platform.endurance_steps} steps, and cruise step size {platform.cruise_step_size}; "
        f"typically {role_text}."
    )


def _zone_purpose(zone: PriorityZone) -> str:
    lower = zone.name.lower()
    if "border" in lower:
        return "Keeps persistent watch on the border approach."
    if "crossing" in lower:
        return "Monitors the likely transit lane where activity can spike quickly."
    if "logistics" in lower or "hub" in lower:
        return "Protects the logistics hub where missed coverage is most costly."
    return f"Maintains awareness over the {zone.name.replace('_', ' ')} area."


def _task_purpose(task: DynamicTask) -> str:
    lower = task.name.lower()
    if "convoy" in lower:
        return "Track a moving convoy-like event through the middle corridor."
    if "hub" in lower or "anomaly" in lower:
        return "Investigate suspicious activity near the logistics hub."
    if "crossing" in lower or "spike" in lower:
        return "Respond to a sudden surveillance spike near a crossing route."
    if "retask" in lower or "southern" in lower:
        return "Shift surveillance attention to the southern edge later in the mission."
    return f"Respond to the {task.name.replace('_', ' ')} event."


def _zone_centroid(zone: PriorityZone) -> tuple[int, int]:
    return ((zone.x_min + zone.x_max) // 2, (zone.y_min + zone.y_max) // 2)


def _zone_area(zone: PriorityZone) -> int:
    return (abs(zone.x_max - zone.x_min) + 1) * (abs(zone.y_max - zone.y_min) + 1)


def _build_assets(scenario: Scenario) -> tuple[MissionAsset, ...]:
    assets: list[MissionAsset] = []
    if scenario.fleet.platforms:
        for platform in scenario.fleet.platforms:
            for idx in range(platform.count):
                assets.append(
                    MissionAsset(
                        label=f"{platform.name}-{idx + 1}",
                        platform_name=platform.name,
                        role=_asset_role(platform.name),
                        sensor_radius=platform.sensor_radius,
                        endurance_steps=platform.endurance_steps,
                        cruise_step_size=platform.cruise_step_size,
                        cost_per_step=platform.cost_per_step,
                        summary=_asset_summary(platform),
                    )
                )
    else:
        for idx in range(scenario.fleet.num_drones):
            assets.append(
                MissionAsset(
                    label=f"drone-{idx + 1}",
                    platform_name="homogeneous",
                    role="general",
                    sensor_radius=scenario.fleet.sensor_radius,
                    endurance_steps=scenario.fleet.endurance_steps,
                    cruise_step_size=1,
                    cost_per_step=scenario.fleet.cost_per_step,
                    summary=(
                        f"General-purpose drone with sensor radius {scenario.fleet.sensor_radius} "
                        f"and endurance {scenario.fleet.endurance_steps} steps."
                    ),
                )
            )
    return tuple(assets)


def _build_zones(scenario: Scenario) -> tuple[MissionZone, ...]:
    zones: list[MissionZone] = []
    for zone in scenario.priority_zones:
        cx, cy = _zone_centroid(zone)
        zones.append(
            MissionZone(
                name=zone.name,
                weight=zone.weight,
                centroid_x=cx,
                centroid_y=cy,
                area_cells=_zone_area(zone),
                purpose=_zone_purpose(zone),
            )
        )
    return tuple(sorted(zones, key=lambda item: item.weight, reverse=True))


def _build_tasks(scenario: Scenario) -> tuple[MissionTask, ...]:
    tasks: list[MissionTask] = []
    for task in scenario.dynamic_tasks:
        suggested_owner_role = "respond" if task.priority >= 3.0 else "general"
        tasks.append(
            MissionTask(
                name=task.name,
                priority=task.priority,
                start_step=task.start_step,
                end_step=task.end_step,
                duration_steps=max(0, task.end_step - task.start_step),
                purpose=_task_purpose(task),
                suggested_owner_role=suggested_owner_role,
            )
        )
    return tuple(sorted(tasks, key=lambda item: (item.start_step, -item.priority)))


def _build_playbook(
    assets: tuple[MissionAsset, ...],
    zones: tuple[MissionZone, ...],
    tasks: tuple[MissionTask, ...],
    preferred_policy: str,
) -> tuple[AllocationRecommendation, ...]:
    recommendations: list[AllocationRecommendation] = []
    anchor_assets = [asset for asset in assets if asset.role == "anchor"]
    responder_assets = [asset for asset in assets if asset.role == "respond"]
    general_assets = [asset for asset in assets if asset.role == "general"]

    if anchor_assets and zones:
        recommendations.append(
            AllocationRecommendation(
                phase="Baseline watch",
                asset_group=f"{len(anchor_assets)} anchor asset(s)",
                target_name=zones[0].name,
                target_kind="priority zone",
                reason="Keep the highest-value area under persistent observation before demand spikes appear.",
            )
        )
        if len(zones) > 1:
            recommendations.append(
                AllocationRecommendation(
                    phase="Baseline watch",
                    asset_group=f"{max(1, len(anchor_assets) - 1)} anchor reserve",
                    target_name=zones[1].name,
                    target_kind="priority zone",
                    reason="Split long-endurance coverage across the next-most-important corridor so the planner does not overfocus on one area.",
                )
            )

    if responder_assets and tasks:
        top_task = max(tasks, key=lambda item: item.priority)
        recommendations.append(
            AllocationRecommendation(
                phase="Dynamic response",
                asset_group=f"{len(responder_assets)} response asset(s)",
                target_name=top_task.name,
                target_kind="mission task",
                reason="Fast assets should move first toward live incidents because missed early service is expensive and visible in the metrics.",
            )
        )

    if tasks:
        first_task = min(tasks, key=lambda item: item.start_step)
        recommendations.append(
            AllocationRecommendation(
                phase="Retasking logic",
                asset_group="task-aware planner"
                if preferred_policy == "priority_patrol"
                else strategy_display_name(preferred_policy),
                target_name=first_task.name,
                target_kind="mission task",
                reason="When the first time-varying event appears, the planner should reallocate scouts without abandoning the permanent watch areas.",
            )
        )

    recommendations.append(
        AllocationRecommendation(
            phase="Fallback behavior",
            asset_group=f"{len(responder_assets) or len(general_assets) or len(assets)} mobile asset(s)",
            target_name="unseen cells",
            target_kind="coverage gap",
            reason="If no urgent task is active, the mobile element should expand coverage instead of repeatedly revisiting the same already-seen cells.",
        )
    )

    return tuple(recommendations)


def build_mission_overview(scenario: Scenario, preferred_policy: str) -> MissionOverview:
    assets = _build_assets(scenario)
    zones = _build_zones(scenario)
    tasks = _build_tasks(scenario)
    playbook = _build_playbook(assets, zones, tasks, preferred_policy)

    summary = (
        f"A finite ISR fleet must keep watch over {len(zones)} important area(s) while reacting to "
        f"{len(tasks)} time-varying task(s). The preferred control logic is {strategy_display_name(preferred_policy).lower()}, "
        "which balances standing coverage with rapid retasking."
    )

    return MissionOverview(
        scenario_name=scenario.name,
        preferred_policy=preferred_policy,
        plain_english_summary=summary,
        assets=assets,
        zones=zones,
        tasks=tasks,
        allocation_playbook=playbook,
    )
