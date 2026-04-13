from __future__ import annotations

import time
import argparse
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from _bootstrap import bootstrap_src_path

bootstrap_src_path()

from anduril_ops.analytics.storage import persist_tables_to_duckdb
from anduril_ops.io.config import build_objects_from_cfg, load_yaml, override_factors
from anduril_ops.utils.seed import make_rng
from anduril_ops.sim.monte_carlo import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run parameter sweep for ISR trade study.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/sweeps/sweep_01.yaml",
        help="Path to sweep YAML config",
    )
    args = parser.parse_args()

    sweep_cfg = load_yaml(args.config)
    base_cfg_path = sweep_cfg["base_config"]
    base_cfg = load_yaml(base_cfg_path)

    sweep_name = str(sweep_cfg["sweep"]["name"])
    runs_per_point = int(sweep_cfg["sweep"]["num_runs_per_point"])

    fleet_sizes = list(sweep_cfg["sweep"]["factors"]["fleet_sizes"])
    sensor_radii = list(sweep_cfg["sweep"]["factors"]["sensor_radii"])

    strategy_types = sweep_cfg["sweep"].get("strategy_types")
    if strategy_types is None:
        strategy_override = sweep_cfg["sweep"].get("strategy_type", None)
        strategy_types = [strategy_override]
    else:
        strategy_types = [None if s is None else str(s) for s in strategy_types]

    # Use base run settings as default, but allow sweep to override output directory/seed
    base_cfg["run"] = dict(base_cfg.get("run", {}))
    base_cfg["run"]["seed"] = int(sweep_cfg["run"]["seed"])
    base_cfg["run"]["output_dir"] = str(sweep_cfg["run"]["output_dir"])

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_root = Path(base_cfg["run"]["output_dir"])
    sweep_dir = out_root / f"{sweep_name}_{ts}"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    rows: list[Dict[str, Any]] = []

    total_jobs = len(strategy_types) * len(fleet_sizes) * len(sensor_radii) * runs_per_point
    job_idx = 0

    for strategy_override in strategy_types:
        for n in fleet_sizes:
            for r in sensor_radii:
                for k in range(runs_per_point):
                    job_idx += 1
                    strategy_offset = sum(ord(ch) for ch in (strategy_override or "base"))
                    seed = int(base_cfg["run"]["seed"]) + strategy_offset + (n * 10000) + (r * 100) + k
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
                        "num_drones": scenario.fleet.total_drones,
                        "sensor_radius": scenario.fleet.sensor_radius,
                        "endurance_steps": scenario.fleet.endurance_steps,
                        "cost_per_step": scenario.fleet.cost_per_step,
                        "fleet_mix": "mixed" if scenario.fleet.is_heterogeneous else "homogeneous",
                        "run_index": k,
                    })

                    rows.append(rec)

                    if job_idx % 10 == 0 or job_idx == total_jobs:
                        print(
                            f"[{job_idx}/{total_jobs}] strategy={strategy.type}, "
                            f"n={n}, r={r}, run={k} -> final_cov={rec['final_coverage']:.3f}"
                        )

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
                "final_coverage": "mean",
                "avg_weighted_coverage": "mean",
                "final_weighted_coverage": "mean",
                "priority_cell_coverage": "mean",
                "revisit_gap_mean": "mean",
                "revisit_gap_p90": "mean",
                "pct_revisits_within_threshold": "mean",
                "priority_revisit_gap_mean": "mean",
                "priority_revisit_gap_p90": "mean",
                "pct_priority_revisits_within_threshold": "mean",
                "avg_task_service_rate": "mean",
                "task_completion_rate": "mean",
                "mean_task_response_time": "mean",
                "p90_task_response_time": "mean",
                "pct_tasks_responded_within_threshold": "mean",
                "total_cost": "mean",
                "utilization": "mean",
                "redundancy_ratio": "mean",
                "coverage_efficiency": "mean",
            })
          .sort_values(group_cols)
    )
    agg_path = sweep_dir / "sweep_results_agg.csv"
    agg.to_csv(agg_path, index=False)
    persist_tables_to_duckdb(
        output_dir=sweep_dir,
        duckdb_path=sweep_dir / "analysis.duckdb",
        tables={
            "sweep_results_raw": df,
            "sweep_results_agg": agg,
        },
    )

    print(f"\nSaved sweep outputs to:\n- {raw_path}\n- {agg_path}\n")


if __name__ == "__main__":
    main()
