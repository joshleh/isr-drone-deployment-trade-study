from __future__ import annotations
import time
from pathlib import Path
import pandas as pd

from _bootstrap import bootstrap_src_path

bootstrap_src_path()

from isr_trade_study.io.config import build_objects_from_cfg, load_yaml
from isr_trade_study.utils.seed import make_rng
from isr_trade_study.sim.monte_carlo import run_simulation

def main() -> None:
    cfg = load_yaml("configs/base.yaml")
    scenario, strategy, seed, out_root = build_objects_from_cfg(cfg)

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
        "num_drones": scenario.fleet.total_drones,
        "sensor_radius": scenario.fleet.sensor_radius,
        "fleet_mix": "mixed" if scenario.fleet.is_heterogeneous else "homogeneous",
    })

    pd.DataFrame([summary]).to_csv(run_dir / "metrics_summary.csv", index=False)

    # Save timeseries
    pd.DataFrame({
        "t": list(range(scenario.time.steps)),
        "coverage": metrics.coverage_over_time,
        "weighted_coverage": metrics.weighted_coverage_over_time,
        "task_service": metrics.task_service_over_time,
    }).to_csv(run_dir / "coverage_timeseries.csv", index=False)

    print(f"Saved results to: {run_dir}")

if __name__ == "__main__":
    main()
