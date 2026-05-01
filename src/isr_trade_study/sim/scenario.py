from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class GridSpec:
    width: int
    height: int


@dataclass(frozen=True)
class TimeSpec:
    steps: int


@dataclass(frozen=True)
class PlatformSpec:
    name: str
    count: int
    sensor_radius: int
    endurance_steps: int
    cost_per_step: float
    cruise_step_size: int = 1


@dataclass(frozen=True)
class FleetSpec:
    num_drones: int
    sensor_radius: int
    endurance_steps: int
    cost_per_step: float
    platforms: Tuple[PlatformSpec, ...] = ()

    @property
    def total_drones(self) -> int:
        if self.platforms:
            return sum(platform.count for platform in self.platforms)
        return self.num_drones

    @property
    def is_heterogeneous(self) -> bool:
        return bool(self.platforms)


@dataclass(frozen=True)
class PriorityZone:
    name: str
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    weight: float


@dataclass(frozen=True)
class DynamicTask:
    name: str
    start_step: int
    end_step: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    priority: float = 1.0


@dataclass(frozen=True)
class Scenario:
    name: str
    grid: GridSpec
    time: TimeSpec
    fleet: FleetSpec
    priority_zones: Tuple[PriorityZone, ...] = ()
    dynamic_tasks: Tuple[DynamicTask, ...] = ()


@dataclass(frozen=True)
class StrategySpec:
    """Configuration for a deployment policy.

    `type` is one of:
      - "static"          : drones loiter on fixed points
      - "patrol"          : random-walk patrol
      - "greedy_patrol"   : assign drones to highest-utility candidate each step
      - "priority_patrol" : task-aware planner with target commitment
    """

    type: str
    static_points: Optional[List[Tuple[int, int]]] = None
    patrol_step_size: int = 1
    patrol_turn_prob: float = 0.25
    task_priority_bias: float = 2.5
    priority_zone_bias: float = 1.5
    exploration_bias: float = 0.35
    target_commitment_steps: int = 4
    congestion_penalty: float = 0.35
