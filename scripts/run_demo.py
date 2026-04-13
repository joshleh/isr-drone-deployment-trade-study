from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from _bootstrap import bootstrap_src_path

bootstrap_src_path()

from anduril_ops.io.config import build_objects_from_cfg, load_yaml, override_factors
from anduril_ops.sim.monte_carlo import run_simulation
from anduril_ops.utils.seed import make_rng
from anduril_ops.viz.plots import (
    plot_coverage_heatmap,
    plot_priority_vs_global_coverage,
    plot_redundancy_vs_coverage,
    plot_timeseries_comparison,
)


def compute_mission_fit_score(agg: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    scored = agg.copy()
    max_efficiency = float(scored["coverage_efficiency"].max()) if not scored.empty else 0.0
    normalized_efficiency = (
        scored["coverage_efficiency"] / max_efficiency if max_efficiency > 0 else 0.0
    )

    scored["mission_fit_score"] = (
        float(weights.get("weighted_coverage", 0.45)) * scored["final_weighted_coverage"]
        + float(weights.get("priority_persistence", 0.30)) * scored["pct_priority_revisits_within_threshold"]
        + float(weights.get("efficiency", 0.15)) * normalized_efficiency
        + float(weights.get("low_redundancy", 0.10)) * (1.0 - scored["redundancy_ratio"])
    )
    return scored


def rerun_timeseries(
    base_cfg: dict,
    strategy_type: str,
    fleet_size: int,
    sensor_radius: int,
    seed: int,
) -> pd.DataFrame:
    cfg_point = override_factors(
        base_cfg,
        fleet_size=fleet_size,
        sensor_radius=sensor_radius,
        strategy_type=strategy_type,
    )
    cfg_point["run"]["seed"] = int(seed)

    scenario, strategy, seed_used, _ = build_objects_from_cfg(cfg_point)
    metrics = run_simulation(scenario, strategy, make_rng(seed_used))

    return pd.DataFrame(
        {
            "t": list(range(scenario.time.steps)),
            "coverage": metrics.coverage_over_time,
            "weighted_coverage": metrics.weighted_coverage_over_time,
            "task_service": metrics.task_service_over_time,
        }
    )


def format_top_configs(df: pd.DataFrame) -> str:
    columns = [
        "strategy",
        "num_drones",
        "sensor_radius",
        "mission_fit_score",
        "final_weighted_coverage",
        "priority_cell_coverage",
        "pct_priority_revisits_within_threshold",
        "redundancy_ratio",
    ]
    header = (
        "| strategy | drones | radius | mission_fit | weighted_cov | "
        "priority_cov | priority_persist | redundancy |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    )
    rows: list[str] = []
    for _, row in df[columns].iterrows():
        rows.append(
            "| "
            f"{row['strategy']} | {int(row['num_drones'])} | {int(row['sensor_radius'])} | "
            f"{row['mission_fit_score']:.3f} | {row['final_weighted_coverage']:.3f} | "
            f"{row['priority_cell_coverage']:.3f} | {row['pct_priority_revisits_within_threshold']:.3f} | "
            f"{row['redundancy_ratio']:.3f} |"
        )
    return header + "\n".join(rows)


def write_demo_report(
    report_path: Path,
    narrative: str,
    agg: pd.DataFrame,
    best_static: pd.Series,
    best_patrol: pd.Series,
) -> None:
    top_configs = agg.sort_values("mission_fit_score", ascending=False).head(5)
    report = f"""# Demo Trade Study Brief

## Scenario

{narrative}

## Best-Scoring Configurations

{format_top_configs(top_configs)}

## Strategy Takeaways

- Best static config: `n={int(best_static['num_drones'])}`, `r={int(best_static['sensor_radius'])}` with mission-fit score `{best_static['mission_fit_score']:.3f}`.
- Best patrol config: `n={int(best_patrol['num_drones'])}`, `r={int(best_patrol['sensor_radius'])}` with mission-fit score `{best_patrol['mission_fit_score']:.3f}`.
- Static tends to hold stronger persistence over priority cells, while patrol trades some revisit discipline for broader weighted coverage.
- Redundancy is now explicit in the outputs, which makes it easier to explain when adding platforms increases overlap more than mission value.

## How To Use This Demo

1. Review the weighted-coverage heatmaps for static vs patrol.
2. Compare global coverage against priority-cell coverage.
3. Use the timeseries plot to explain when patrol starts outperforming static on mission-weighted reach.
4. Treat `mission_fit_score` as a demo-only ranking aid, not an objective truth.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the portfolio demo scenario and export demo artifacts.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/sweeps/demo_priority_trade_study.yaml",
        help="Path to demo sweep YAML config",
    )
    parser.add_argument(
        "--docs_figures",
        type=str,
        default="docs/figures",
        help="Output directory for stable demo figures",
    )
    args = parser.parse_args()

    sweep_cfg = load_yaml(args.config)
    base_cfg = load_yaml(sweep_cfg["base_config"])

    sweep_name = str(sweep_cfg["sweep"]["name"])
    runs_per_point = int(sweep_cfg["sweep"]["num_runs_per_point"])
    fleet_sizes = list(sweep_cfg["sweep"]["factors"]["fleet_sizes"])
    sensor_radii = list(sweep_cfg["sweep"]["factors"]["sensor_radii"])
    strategy_types = [str(s) for s in sweep_cfg["sweep"]["strategy_types"]]

    demo_cfg = sweep_cfg.get("demo", {})
    narrative = str(
        demo_cfg.get(
            "narrative",
            "Priority-weighted ISR deployment trade study.",
        )
    )
    score_weights = dict(demo_cfg.get("mission_fit_weights", {}))

    base_cfg["run"] = dict(base_cfg.get("run", {}))
    base_cfg["run"]["seed"] = int(sweep_cfg["run"]["seed"])
    base_cfg["run"]["output_dir"] = str(sweep_cfg["run"]["output_dir"])

    ts = time.strftime("%Y%m%d_%H%M%S")
    demo_dir = Path(base_cfg["run"]["output_dir"]) / f"{sweep_name}_{ts}"
    demo_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    total_jobs = len(strategy_types) * len(fleet_sizes) * len(sensor_radii) * runs_per_point
    job_idx = 0

    for strategy_type in strategy_types:
        for fleet_size in fleet_sizes:
            for sensor_radius in sensor_radii:
                for run_index in range(runs_per_point):
                    job_idx += 1
                    strategy_offset = sum(ord(ch) for ch in strategy_type)
                    seed = (
                        int(base_cfg["run"]["seed"])
                        + strategy_offset
                        + (fleet_size * 10000)
                        + (sensor_radius * 100)
                        + run_index
                    )
                    cfg_point = override_factors(
                        base_cfg,
                        fleet_size=fleet_size,
                        sensor_radius=sensor_radius,
                        strategy_type=strategy_type,
                    )
                    cfg_point["run"]["seed"] = seed

                    scenario, strategy, seed_used, _ = build_objects_from_cfg(cfg_point)
                    metrics = run_simulation(scenario, strategy, make_rng(seed_used))
                    rec = metrics.to_dict()
                    rec.update(
                        {
                            "sweep": sweep_name,
                            "scenario": scenario.name,
                            "strategy": strategy.type,
                            "seed": seed_used,
                            "steps": scenario.time.steps,
                            "grid_w": scenario.grid.width,
                            "grid_h": scenario.grid.height,
                            "num_drones": scenario.fleet.total_drones,
                            "sensor_radius": scenario.fleet.sensor_radius,
                            "run_index": run_index,
                        }
                    )
                    rows.append(rec)

                    if job_idx % 10 == 0 or job_idx == total_jobs:
                        print(
                            f"[{job_idx}/{total_jobs}] strategy={strategy.type}, "
                            f"n={fleet_size}, r={sensor_radius} -> weighted_cov={rec['final_weighted_coverage']:.3f}"
                        )

    raw = pd.DataFrame(rows)
    raw_path = demo_dir / "demo_results_raw.csv"
    raw.to_csv(raw_path, index=False)

    agg = (
        raw.groupby(["num_drones", "sensor_radius", "strategy"], as_index=False)
        .agg(
            {
                "seed": "min",
                "steps": "mean",
                "grid_w": "mean",
                "grid_h": "mean",
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
                "total_cost": "mean",
                "utilization": "mean",
                "redundancy_ratio": "mean",
                "coverage_efficiency": "mean",
            }
        )
        .sort_values(["strategy", "num_drones", "sensor_radius"])
    )
    agg = compute_mission_fit_score(agg, score_weights)
    agg_path = demo_dir / "demo_results_agg.csv"
    agg.to_csv(agg_path, index=False)

    best_static = agg[agg["strategy"] == "static"].sort_values("mission_fit_score", ascending=False).iloc[0]
    best_patrol = agg[agg["strategy"] == "patrol"].sort_values("mission_fit_score", ascending=False).iloc[0]

    static_timeseries = rerun_timeseries(
        base_cfg,
        strategy_type="static",
        fleet_size=int(best_static["num_drones"]),
        sensor_radius=int(best_static["sensor_radius"]),
        seed=int(best_static["seed"]),
    )
    patrol_timeseries = rerun_timeseries(
        base_cfg,
        strategy_type="patrol",
        fleet_size=int(best_patrol["num_drones"]),
        sensor_radius=int(best_patrol["sensor_radius"]),
        seed=int(best_patrol["seed"]),
    )
    static_timeseries.to_csv(demo_dir / "best_static_timeseries.csv", index=False)
    patrol_timeseries.to_csv(demo_dir / "best_patrol_timeseries.csv", index=False)

    docs_figures = Path(args.docs_figures)
    plot_coverage_heatmap(
        agg,
        out_path=docs_figures / "demo_priority_static_heatmap.png",
        strategy="static",
        value_col="final_weighted_coverage",
        title="Static Weighted Coverage Heatmap",
    )
    plot_coverage_heatmap(
        agg,
        out_path=docs_figures / "demo_priority_patrol_heatmap.png",
        strategy="patrol",
        value_col="final_weighted_coverage",
        title="Patrol Weighted Coverage Heatmap",
    )
    plot_priority_vs_global_coverage(
        agg,
        out_path=docs_figures / "demo_priority_priority_vs_global.png",
    )
    plot_redundancy_vs_coverage(
        agg,
        out_path=docs_figures / "demo_priority_redundancy_vs_coverage.png",
    )
    plot_timeseries_comparison(
        static_timeseries,
        patrol_timeseries,
        out_path=docs_figures / "demo_priority_best_timeseries.png",
        static_label=f"static n={int(best_static['num_drones'])}, r={int(best_static['sensor_radius'])}",
        patrol_label=f"patrol n={int(best_patrol['num_drones'])}, r={int(best_patrol['sensor_radius'])}",
    )

    report_path = demo_dir / "demo_report.md"
    write_demo_report(report_path, narrative, agg, best_static, best_patrol)

    print(f"Saved demo outputs to: {demo_dir.resolve()}")
    print(f"Saved demo figures to: {docs_figures.resolve()}")
    print(f"Saved demo report to: {report_path.resolve()}")


if __name__ == "__main__":
    main()
