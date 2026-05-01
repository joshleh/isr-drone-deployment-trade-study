from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from isr_trade_study.sim.placements import resolve_static_points
from isr_trade_study.sim.scenario import (
    DynamicTask,
    FleetSpec,
    GridSpec,
    PlatformSpec,
    PriorityZone,
    Scenario,
    StrategySpec,
    TimeSpec,
)


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _build_priority_zones(cfg: dict) -> Tuple[PriorityZone, ...]:
    return tuple(
        PriorityZone(
            name=str(zone["name"]),
            x_min=int(zone["x_min"]),
            x_max=int(zone["x_max"]),
            y_min=int(zone["y_min"]),
            y_max=int(zone["y_max"]),
            weight=float(zone.get("weight", 1.0)),
        )
        for zone in cfg.get("priority_zones", [])
    )


def _build_dynamic_tasks(cfg: dict) -> Tuple[DynamicTask, ...]:
    return tuple(
        DynamicTask(
            name=str(task["name"]),
            start_step=int(task["start_step"]),
            end_step=int(task["end_step"]),
            x_min=int(task["x_min"]),
            x_max=int(task["x_max"]),
            y_min=int(task["y_min"]),
            y_max=int(task["y_max"]),
            priority=float(task.get("priority", 1.0)),
        )
        for task in cfg.get("dynamic_tasks", [])
    )


def _build_fleet_spec(cfg: dict) -> FleetSpec:
    platforms = tuple(
        PlatformSpec(
            name=str(platform["name"]),
            count=int(platform["count"]),
            sensor_radius=int(platform["sensor_radius"]),
            endurance_steps=int(platform["endurance_steps"]),
            cost_per_step=float(platform["cost_per_step"]),
            cruise_step_size=int(platform.get("cruise_step_size", 1)),
        )
        for platform in cfg.get("platforms", [])
    )
    return FleetSpec(
        num_drones=int(cfg.get("num_drones", 0)),
        sensor_radius=int(cfg.get("sensor_radius", 0)),
        endurance_steps=int(cfg.get("endurance_steps", 0)),
        cost_per_step=float(cfg.get("cost_per_step", 0.0)),
        platforms=platforms,
    )


def build_objects_from_cfg(cfg: dict) -> Tuple[Scenario, StrategySpec, int, str]:
    seed = int(cfg["run"]["seed"])
    out_root = str(cfg["run"]["output_dir"])

    sc = cfg["scenario"]
    fl = cfg["fleet"]
    st = cfg["strategy"]

    scenario = Scenario(
        name=str(sc["name"]),
        grid=GridSpec(width=int(sc["grid"]["width"]), height=int(sc["grid"]["height"])),
        time=TimeSpec(steps=int(sc["time"]["steps"])),
        fleet=_build_fleet_spec(fl),
        priority_zones=_build_priority_zones(sc),
        dynamic_tasks=_build_dynamic_tasks(sc),
    )

    if st["type"] == "static":
        static_cfg = st["static"]
        pts = [tuple(map(int, p)) for p in static_cfg.get("points", [])]
        strategy = StrategySpec(
            type="static",
            static_points=resolve_static_points(
                width=scenario.grid.width,
                height=scenario.grid.height,
                num_drones=scenario.fleet.total_drones,
                explicit_points=pts,
                point_mode=str(static_cfg.get("point_mode", "explicit")),
            ),
        )
    elif st["type"] in {"patrol", "priority_patrol", "greedy_patrol"}:
        patrol_cfg = st["patrol"]
        strategy = StrategySpec(
            type=str(st["type"]),
            patrol_step_size=int(patrol_cfg.get("step_size", 1)),
            patrol_turn_prob=float(patrol_cfg.get("turn_prob", 0.25)),
            task_priority_bias=float(patrol_cfg.get("task_priority_bias", 2.5)),
            priority_zone_bias=float(patrol_cfg.get("priority_zone_bias", 1.5)),
            exploration_bias=float(patrol_cfg.get("exploration_bias", 0.35)),
            target_commitment_steps=int(patrol_cfg.get("target_commitment_steps", 4)),
            congestion_penalty=float(patrol_cfg.get("congestion_penalty", 0.35)),
        )
    else:
        raise ValueError(f"Unknown strategy.type: {st['type']}")

    return scenario, strategy, seed, out_root


def override_factors(base_cfg: dict, fleet_size: int, sensor_radius: int, strategy_type: str | None) -> dict:
    cfg: Dict[str, Any] = dict(base_cfg)
    cfg["fleet"] = dict(base_cfg["fleet"])
    cfg["strategy"] = dict(base_cfg["strategy"])

    cfg["fleet"]["num_drones"] = int(fleet_size)
    cfg["fleet"]["sensor_radius"] = int(sensor_radius)

    if "platforms" in cfg["fleet"]:
        del cfg["fleet"]["platforms"]

    if strategy_type is not None:
        cfg["strategy"]["type"] = strategy_type

    if cfg["strategy"]["type"] == "static":
        cfg["strategy"]["static"] = dict(base_cfg["strategy"]["static"])
        pts = [tuple(p) for p in cfg["strategy"]["static"].get("points", [])]
        if not pts and str(cfg["strategy"]["static"].get("point_mode", "explicit")) != "auto_grid":
            raise ValueError("Static strategy requires at least 1 loiter point or point_mode=auto_grid.")
        cfg["strategy"]["static"]["points"] = [list(p) for p in pts]

    return cfg
