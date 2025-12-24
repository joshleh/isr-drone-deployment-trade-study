from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
import yaml

from anduril_ops.utils.seed import make_rng
from anduril_ops.sim.scenario import Scenario, GridSpec, TimeSpec, FleetSpec, StrategySpec
from anduril_ops.sim.monte_carlo import run_simulation


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_objects_from_cfg(cfg: dict) -> Tuple[Scenario, StrategySpec, int, str]:
    """Same idea as run_pipeline.py, but kept local so sweep is self-contained."""
    seed = int(cfg["run"]["seed"])
    out_root = str(cfg["run"]["output_dir"])

    sc = cfg["scenario"]
    fl = cfg["fleet"]
    st = cfg["strategy"]

    scenario = Scenario(
        name=str(sc["name"]),
        grid=GridSpec(width=int(sc["grid"]["width"]), height=int(sc["grid"]["height"])),
        time=TimeSpec(steps=int(sc["time"]["steps"])),
        fleet=FleetSpec(
            num_drones=int(fl["num_drones"]),
            sensor_radius=int(fl["sensor_radius"]),
            endurance_steps=int(fl["endurance_steps"]),
            cost_per_step=float(fl["cost_per_step"]),
        ),
    )

    if st["type"] == "static":
        pts = [tuple(map(int, p)) for p in st["static"]["points"]]
        strategy = StrategySpec(type="static", static_points=pts)
    elif st["type"] == "patrol":
        strategy = StrategySpec(
            type="patrol",
            patrol_step_size=int(st["patrol"]["step_size"]),
            patrol_turn_prob=float(st["patrol"]["turn_prob"]),
        )
    else:
        raise ValueError(f"Unknown strategy.type: {st['type']}")

    return scenario, strategy, seed, out_root


def override_factors(base_cfg: dict, fleet_size: int, sensor_radius: int, strategy_type: str | None) -> dict:
    cfg = dict(base_cfg)  # shallow copy is ok; we overwrite nested keys below carefully

    # Ensure nested dicts exist
    cfg["fleet"] = dict(base_cfg["fleet"])
    cfg["strategy"] = dict(base_cfg["strategy"])

    cfg["fleet"]["num_drones"] = int(fleet_size)
    cfg["fleet"]["sensor_radius"] = int(sensor_radius)

    if strategy_type is not None:
        cfg["strategy"]["type"] = strategy_type

    # If static strategy is used and points are fewer than num_drones, repeat points (cyclic).
    # This keeps sweep from failing due to config mismatch.
    if cfg["strategy"]["type"] == "static":
        cfg["strategy"]["static"] = dict(base_cfg["strategy"]["static"])
        pts = [tuple(p) for p in cfg["strategy"]["static"]["points"]]
        if len(pts) == 0:
            raise ValueError("Static strategy requires at least 1 loiter point.")
        if len(pts) < fleet_size:
            # repeat points cyclically
            repeated = [pts[i % len(pts)] for i in range(fleet_size)]
            cfg["strategy"]["static"]["points"] = [list(p) for p in repeated]
        else:
            cfg["strategy"]["static"]["points"] = [list(p) for p in pts]

    return cfg


def main() -> None:
    sweep_cfg = load_yaml("configs/sweeps/sweep_01.yaml")
    base_cfg_path = sweep_cfg["base_config"]
    base_cfg = load_yaml(base_cfg_path)

    sweep_name = str(sweep_cfg["sweep"]["name"])
    runs_per_point = int(sweep_cfg["sweep"]["num_runs_per_point"])

    fleet_sizes = list(sweep_cfg["sweep"]["factors"]["fleet_sizes"])
    sensor_radii = list(sweep_cfg["sweep"]["factors"]["sensor_radii"])

    strategy_override = sweep_cfg["sweep"].get("strategy_type", None)

    # Use base run settings as default, but allow sweep to override output directory/seed
    base_cfg["run"] = dict(base_cfg.get("run", {}))
    base_cfg["run"]["seed"] = int(sweep_cfg["run"]["seed"])
    base_cfg["run"]["output_dir"] = str(sweep_cfg["run"]["output_dir"])

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_root = Path(base_cfg["run"]["output_dir"])
    sweep_dir = out_root / f"{sweep_name}_{ts}"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    rows: list[Dict[str, Any]] = []

    total_jobs = len(fleet_sizes) * len(sensor_radii) * runs_per_point
    job_idx = 0

    for n in fleet_sizes:
        for r in sensor_radii:
            for k in range(runs_per_point):
                job_idx += 1
                seed = int(base_cfg["run"]["seed"]) + (n * 10000) + (r * 100) + k
                cfg_point = override_factors(base_cfg, fleet_size=n, sensor_radius=r, strategy_type=strategy_override)
                cfg_point["run"]["seed"] = seed

                scenario, strategy, seed_used, _ = build_objects_from_cfg(cfg_point)
                rng = make_rng(seed_used)

                metrics = run_simulation(scenario, strategy, rng)
                rec = metrics.to_dict()

                rec.update({
                    "sweep": sweep_name,
                    "scenario": scenario.name,
                    "strategy": strategy.type,
                    "seed": seed_used,
                    "steps": scenario.time.steps,
                    "grid_w": scenario.grid.width,
                    "grid_h": scenario.grid.height,
                    "num_drones": scenario.fleet.num_drones,
                    "sensor_radius": scenario.fleet.sensor_radius,
                    "endurance_steps": scenario.fleet.endurance_steps,
                    "cost_per_step": scenario.fleet.cost_per_step,
                    "run_index": k,
                })

                rows.append(rec)

                if job_idx % 10 == 0 or job_idx == total_jobs:
                    print(f"[{job_idx}/{total_jobs}] n={n}, r={r}, run={k} -> avg_cov={rec['avg_coverage']:.3f}")

    df = pd.DataFrame(rows)

    # Save raw sweep results
    raw_path = sweep_dir / "sweep_results_raw.csv"
    df.to_csv(raw_path, index=False)

    # Save aggregated table (mean across runs per (n,r,strategy))
    group_cols = ["num_drones", "sensor_radius", "strategy"]
    agg = (
        df.groupby(group_cols, as_index=False)
          .agg({
              "avg_coverage": "mean",
              "revisit_time_mean": "mean",
              "revisit_time_p90": "mean",
              "total_cost": "mean",
              "utilization": "mean",
          })
          .sort_values(group_cols)
    )
    agg_path = sweep_dir / "sweep_results_agg.csv"
    agg.to_csv(agg_path, index=False)

    print(f"\nSaved sweep outputs to:\n- {raw_path}\n- {agg_path}\n")


if __name__ == "__main__":
    main()