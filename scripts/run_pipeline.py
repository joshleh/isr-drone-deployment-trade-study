from __future__ import annotations
import os
import time
from pathlib import Path
import yaml
import pandas as pd

from anduril_ops.utils.seed import make_rng
from anduril_ops.sim.scenario import Scenario, GridSpec, TimeSpec, FleetSpec, StrategySpec
from anduril_ops.sim.monte_carlo import run_simulation

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_objects(cfg: dict) -> tuple[Scenario, StrategySpec, int, str]:
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

def main() -> None:
    cfg = load_config("configs/base.yaml")
    scenario, strategy, seed, out_root = build_objects(cfg)

    rng = make_rng(seed)
    metrics = run_simulation(scenario, strategy, rng)

    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(out_root) / f"{scenario.name}_{strategy.type}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save summary metrics
    summary = metrics.to_dict()
    summary.update({
        "scenario": scenario.name,
        "strategy": strategy.type,
        "seed": seed,
        "steps": scenario.time.steps,
        "grid_w": scenario.grid.width,
        "grid_h": scenario.grid.height,
        "num_drones": scenario.fleet.num_drones,
        "sensor_radius": scenario.fleet.sensor_radius,
    })

    pd.DataFrame([summary]).to_csv(run_dir / "metrics_summary.csv", index=False)

    # Save timeseries
    pd.DataFrame({
        "t": list(range(scenario.time.steps)),
        "coverage": metrics.coverage_over_time,
    }).to_csv(run_dir / "coverage_timeseries.csv", index=False)

    print(f"Saved results to: {run_dir}")

if __name__ == "__main__":
    main()
