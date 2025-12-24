from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass(frozen=True)
class GridSpec:
    width: int
    height: int

@dataclass(frozen=True)
class TimeSpec:
    steps: int

@dataclass(frozen=True)
class FleetSpec:
    num_drones: int
    sensor_radius: int
    endurance_steps: int
    cost_per_step: float

@dataclass(frozen=True)
class Scenario:
    name: str
    grid: GridSpec
    time: TimeSpec
    fleet: FleetSpec

@dataclass(frozen=True)
class StrategySpec:
    type: str  # "static" or "patrol"
    static_points: Optional[List[Tuple[int, int]]] = None
    patrol_step_size: int = 1
    patrol_turn_prob: float = 0.25