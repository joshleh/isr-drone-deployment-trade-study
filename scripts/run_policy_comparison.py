from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from _bootstrap import bootstrap_src_path

bootstrap_src_path()

from isr_trade_study.analytics.storage import persist_tables_to_duckdb
from isr_trade_study.dashboard.html import build_static_dashboard
from isr_trade_study.io.config import build_objects_from_cfg, load_yaml
from isr_trade_study.sim.monte_carlo import run_simulation
from isr_trade_study.utils.seed import make_rng
from isr_trade_study.viz.plots import (
    plot_policy_timeseries,
    plot_redundancy_vs_coverage,
    plot_strategy_metric_bars,
    plot_task_service_vs_response,
)


def _strategy_seed(base_seed: int, strategy: str, run_index: int) -> int:
    return int(base_seed) + sum(ord(ch) for ch in strategy) + run_index


def add_policy_scores(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    scored = df.copy()

    max_efficiency = float(scored["coverage_efficiency"].max()) if not scored.empty else 0.0
    efficiency_component = (
        scored["coverage_efficiency"] / max_efficiency if max_efficiency > 0 else 0.0
    )

    finite_response = scored.loc[np.isfinite(scored["mean_task_response_time"]), "mean_task_response_time"]
    if not finite_response.empty:
        worst_response = float(finite_response.max())
        response_filled = scored["mean_task_response_time"].replace([math.inf, -math.inf], worst_response * 1.25)
        response_component = 1.0 - (response_filled / max(worst_response * 1.25, 1.0)).clip(lower=0.0, upper=1.0)
    else:
        response_component = 0.0

    scored["mission_fit_score"] = (
        float(weights.get("weighted_coverage", 0.28)) * scored["final_weighted_coverage"]
        + float(weights.get("task_service", 0.24)) * scored["avg_task_service_rate"]
        + float(weights.get("task_completion", 0.20)) * scored["task_completion_rate"]
        + float(weights.get("response_speed", 0.12)) * response_component
        + float(weights.get("persistence", 0.08)) * scored["pct_priority_revisits_within_threshold"]
        + float(weights.get("efficiency", 0.08)) * efficiency_component
    )
    return scored


def rerun_timeseries(base_cfg: dict, strategy_type: str, seed: int) -> pd.DataFrame:
    cfg = dict(base_cfg)
    cfg["run"] = dict(base_cfg["run"])
    cfg["strategy"] = dict(base_cfg["strategy"])
    cfg["run"]["seed"] = int(seed)
    cfg["strategy"]["type"] = strategy_type

    scenario, strategy, seed_used, _ = build_objects_from_cfg(cfg)
    metrics = run_simulation(scenario, strategy, make_rng(seed_used))
    return pd.DataFrame(
        {
            "t": list(range(scenario.time.steps)),
            "coverage": metrics.coverage_over_time,
            "weighted_coverage": metrics.weighted_coverage_over_time,
            "task_service": metrics.task_service_over_time,
        }
    )


def build_dashboard_tables(agg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    best = agg.sort_values("mission_fit_score", ascending=False).iloc[0]
    baseline = agg[agg["strategy"] == "static"].iloc[0] if "static" in set(agg["strategy"]) else best
    response_gain = baseline["mean_task_response_time"] - best["mean_task_response_time"]
    response_gain_value = f"{response_gain:.2f}" if math.isfinite(float(response_gain)) else "n/a"
    summary = pd.DataFrame(
        [
            {"metric": "Best Policy", "value": str(best["strategy"])},
            {"metric": "Mission-Fit Score", "value": f"{best['mission_fit_score']:.3f}"},
            {"metric": "Task Completion", "value": f"{best['task_completion_rate']:.3f}"},
            {"metric": "Avg Task Service", "value": f"{best['avg_task_service_rate']:.3f}"},
            {
                "metric": "Response Time Gain vs Static",
                "value": response_gain_value,
            },
        ]
    )
    top = agg[
        [
            "strategy",
            "mission_fit_score",
            "final_weighted_coverage",
            "avg_task_service_rate",
            "task_completion_rate",
            "mean_task_response_time",
            "coverage_efficiency",
        ]
    ].sort_values("mission_fit_score", ascending=False)
    return summary, top


def format_markdown_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(df.columns) + " |\n"
    divider = "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
    rows: list[str] = []
    for row in df.itertuples(index=False):
        rendered: list[str] = []
        for value in row:
            if isinstance(value, float):
                rendered.append(f"{value:.3f}")
            else:
                rendered.append(str(value))
        rows.append("| " + " | ".join(rendered) + " |")
    return header + divider + "\n".join(rows)


def write_report(report_path: Path, narrative: str, agg: pd.DataFrame) -> None:
    ranked = agg.sort_values("mission_fit_score", ascending=False).reset_index(drop=True)
    best = ranked.iloc[0]
    static_row = ranked[ranked["strategy"] == "static"].iloc[0] if "static" in set(ranked["strategy"]) else best
    patrol_row = ranked[ranked["strategy"] == "patrol"].iloc[0] if "patrol" in set(ranked["strategy"]) else best
    greedy_row = ranked[ranked["strategy"] == "greedy_patrol"].iloc[0] if "greedy_patrol" in set(ranked["strategy"]) else best
    priority_row = ranked[ranked["strategy"] == "priority_patrol"].iloc[0] if "priority_patrol" in set(ranked["strategy"]) else best
    if priority_row["avg_task_service_rate"] >= greedy_row["avg_task_service_rate"]:
        priority_vs_greedy = (
            f"`priority_patrol` improves average task service from `{greedy_row['avg_task_service_rate']:.3f}` "
            f"to `{priority_row['avg_task_service_rate']:.3f}` relative to the greedy planner."
        )
    else:
        priority_vs_greedy = (
            f"`priority_patrol` stays below the greedy planner on pure task service "
            f"(`{priority_row['avg_task_service_rate']:.3f}` vs `{greedy_row['avg_task_service_rate']:.3f}`), "
            "but it remains much stronger than random patrol while preserving a more interpretable anchor-and-respond behavior."
        )

    report = f"""# Dynamic Policy Comparison Brief

## Scenario

{narrative}

## Ranking

{format_markdown_table(ranked[['strategy', 'mission_fit_score', 'final_weighted_coverage', 'avg_task_service_rate', 'task_completion_rate', 'mean_task_response_time', 'coverage_efficiency']])}

## Key Takeaways

- Best overall policy: `{best['strategy']}` with mission-fit score `{best['mission_fit_score']:.3f}`.
- Static basing keeps perfect persistence over what it already watches, but it under-serves dynamic tasks once demand shifts.
- Random patrol broadens reach, but it is less disciplined about task response than the planner-style baselines.
- `greedy_patrol` provides the stronger non-random baseline by explicitly assigning drones to targets each step.
- `priority_patrol` improves average task service from `{patrol_row['avg_task_service_rate']:.3f}` to `{priority_row['avg_task_service_rate']:.3f}` relative to random patrol.
- {priority_vs_greedy}
- The heterogeneous fleet matters: slower long-endurance sentinels anchor persistent regions while faster scouts absorb the time-varying task spikes.

## Why This Helps The Portfolio

- It moves the project beyond a static trade study into dynamic decision support.
- It shows role relevance for operations analysis, data science, and data engineering at the same time.
- It creates an offline evaluation harness that could later compare optimization or learned routing policies.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run heterogeneous policy comparison and build persisted analytics artifacts.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/policy_comparison_heterogeneous.yaml",
        help="Path to comparison YAML config",
    )
    parser.add_argument(
        "--docs_figures",
        type=str,
        default="docs/figures",
        help="Directory for stable figure exports",
    )
    args = parser.parse_args()

    cfg = load_yaml(args.config)
    base_cfg = load_yaml(cfg["base_config"])
    base_cfg["run"] = dict(base_cfg["run"])
    base_cfg["run"]["seed"] = int(cfg["run"]["seed"])
    base_cfg["run"]["output_dir"] = str(cfg["run"]["output_dir"])

    comparison_cfg = cfg["comparison"]
    report_cfg = cfg.get("report", {})
    dashboard_cfg = cfg.get("dashboard", {})

    comparison_name = str(comparison_cfg["name"])
    runs_per_strategy = int(comparison_cfg["num_runs_per_strategy"])
    strategies = [str(strategy) for strategy in comparison_cfg["strategies"]]
    narrative = str(report_cfg.get("narrative", "Dynamic heterogeneous policy comparison."))
    weights = dict(report_cfg.get("mission_fit_weights", {}))

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(base_cfg["run"]["output_dir"]) / f"{comparison_name}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    total_jobs = len(strategies) * runs_per_strategy
    job_idx = 0

    for strategy_type in strategies:
        for run_index in range(runs_per_strategy):
            job_idx += 1
            run_cfg = dict(base_cfg)
            run_cfg["run"] = dict(base_cfg["run"])
            run_cfg["strategy"] = dict(base_cfg["strategy"])
            run_cfg["strategy"]["type"] = strategy_type
            run_cfg["run"]["seed"] = _strategy_seed(base_cfg["run"]["seed"], strategy_type, run_index)

            scenario, strategy, seed_used, _ = build_objects_from_cfg(run_cfg)
            metrics = run_simulation(scenario, strategy, make_rng(seed_used))
            row = metrics.to_dict()
            row.update(
                {
                    "comparison": comparison_name,
                    "scenario": scenario.name,
                    "strategy": strategy.type,
                    "seed": seed_used,
                    "num_drones": scenario.fleet.total_drones,
                    "fleet_mix": ",".join(
                        f"{platform.name}:{platform.count}" for platform in scenario.fleet.platforms
                    )
                    if scenario.fleet.is_heterogeneous
                    else "homogeneous",
                    "run_index": run_index,
                }
            )
            rows.append(row)

            print(
                f"[{job_idx}/{total_jobs}] strategy={strategy.type} "
                f"task_service={row['avg_task_service_rate']:.3f} response={row['mean_task_response_time']:.2f}"
            )

    raw = pd.DataFrame(rows)
    raw = add_policy_scores(raw, weights)
    raw_path = out_dir / "policy_results_raw.csv"
    raw.to_csv(raw_path, index=False)

    agg = (
        raw.groupby(["strategy", "num_drones", "fleet_mix"], as_index=False)
        .agg(
            {
                "seed": "min",
                "final_coverage": "mean",
                "final_weighted_coverage": "mean",
                "priority_cell_coverage": "mean",
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
                "mission_fit_score": "mean",
            }
        )
        .sort_values("mission_fit_score", ascending=False)
    )
    agg_path = out_dir / "policy_results_agg.csv"
    agg.to_csv(agg_path, index=False)

    docs_figures = Path(args.docs_figures)
    strategy_figure = docs_figures / "policy_dynamic_strategy_bars.png"
    response_figure = docs_figures / "policy_dynamic_task_service_vs_response.png"
    redundancy_figure = docs_figures / "policy_dynamic_redundancy_vs_coverage.png"
    timeseries_figure = docs_figures / "policy_dynamic_timeseries.png"

    plot_strategy_metric_bars(
        agg,
        out_path=strategy_figure,
        metrics=[
            "mission_fit_score",
            "avg_task_service_rate",
            "task_completion_rate",
            "coverage_efficiency",
        ],
        title="Policy Comparison Summary",
    )
    plot_task_service_vs_response(agg, out_path=response_figure)
    plot_redundancy_vs_coverage(agg, out_path=redundancy_figure)

    timeseries_by_label: dict[str, pd.DataFrame] = {}
    for strategy_type in strategies:
        best_row = raw[raw["strategy"] == strategy_type].sort_values("mission_fit_score", ascending=False).iloc[0]
        label = f"{strategy_type} (seed {int(best_row['seed'])})"
        series = rerun_timeseries(base_cfg, strategy_type, int(best_row["seed"]))
        timeseries_by_label[label] = series
        series.to_csv(out_dir / f"{strategy_type}_best_timeseries.csv", index=False)
    plot_policy_timeseries(timeseries_by_label, out_path=timeseries_figure)

    dashboard_summary, dashboard_top = build_dashboard_tables(agg)
    persist_tables_to_duckdb(
        output_dir=out_dir,
        duckdb_path=out_dir / "analysis.duckdb",
        tables={
            "policy_results_raw": raw,
            "policy_results_agg": agg,
            "dashboard_summary": dashboard_summary,
            "dashboard_top_policies": dashboard_top,
        },
    )

    dashboard_path = out_dir / "dashboard.html"
    build_static_dashboard(
        duckdb_path=out_dir / "analysis.duckdb",
        html_path=dashboard_path,
        summary_table="SELECT * FROM dashboard_summary",
        top_table="SELECT * FROM dashboard_top_policies",
        title=str(dashboard_cfg.get("title", "Policy Comparison Dashboard")),
        subtitle=str(dashboard_cfg.get("subtitle", narrative)),
        figure_paths=[strategy_figure, response_figure, redundancy_figure, timeseries_figure],
    )

    report_path = out_dir / "policy_report.md"
    write_report(report_path, narrative, agg)

    print(f"Saved raw results to: {raw_path.resolve()}")
    print(f"Saved aggregated results to: {agg_path.resolve()}")
    print(f"Saved dashboard to: {dashboard_path.resolve()}")
    print(f"Saved report to: {report_path.resolve()}")


if __name__ == "__main__":
    main()
