"""Matplotlib helpers for sweep and policy outputs.

A muted, defense-tech-flavored style is applied globally so figures match
the dark dashboard aesthetic when embedded in the live demo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


_PALETTE = ["#5fb6c0", "#d99a3d", "#9aa8b3", "#7d8c83", "#cf6659", "#7984c7"]

_BASE_STYLE = {
    "figure.facecolor": "#0f1418",
    "axes.facecolor": "#141a1f",
    "axes.edgecolor": "#3a4651",
    "axes.labelcolor": "#d6dce2",
    "axes.titlecolor": "#f1f4f7",
    "axes.titlesize": 12,
    "axes.titleweight": "600",
    "axes.labelsize": 10,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#1f2730",
    "grid.linestyle": "-",
    "grid.linewidth": 0.8,
    "xtick.color": "#aab3bb",
    "ytick.color": "#aab3bb",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.facecolor": "#141a1f",
    "legend.edgecolor": "#3a4651",
    "legend.labelcolor": "#d6dce2",
    "legend.fontsize": 9,
    "legend.frameon": True,
    "text.color": "#d6dce2",
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Segoe UI", "DejaVu Sans", "Arial"],
    "font.size": 10,
    "savefig.facecolor": "#0f1418",
    "savefig.edgecolor": "#0f1418",
    "axes.prop_cycle": plt.cycler(color=_PALETTE),
}

plt.rcParams.update(_BASE_STYLE)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_fig(fig: plt.Figure, out_path: Path, dpi: int = 200) -> None:
    ensure_dir(out_path.parent)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def _filter_strategy(df: pd.DataFrame, strategy: Optional[str]) -> pd.DataFrame:
    filtered = df.copy()
    if strategy is not None and "strategy" in filtered.columns:
        filtered = filtered[filtered["strategy"] == strategy]
    return filtered


def _scatter_by_strategy(ax: plt.Axes, df: pd.DataFrame, x: str, y: str) -> None:
    strategies = list(df["strategy"].unique()) if "strategy" in df.columns else [None]
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for idx, strategy in enumerate(strategies):
        subset = df if strategy is None else df[df["strategy"] == strategy]
        label = "all" if strategy is None else str(strategy)
        ax.scatter(
            subset[x],
            subset[y],
            label=label,
            alpha=0.85,
            s=52,
            edgecolor="#0f1418",
            linewidth=0.6,
            color=colors[idx % len(colors)],
        )


def plot_coverage_heatmap(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
    value_col: str = "final_coverage",
    title: str = "Final Coverage Heatmap",
) -> None:
    df = _filter_strategy(agg, strategy)

    pivot = (
        df.pivot_table(
            index="num_drones",
            columns="sensor_radius",
            values=value_col,
            aggfunc="mean",
        )
        .sort_index()
        .sort_index(axis=1)
    )

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    im = ax.imshow(
        pivot.values,
        aspect="auto",
        cmap="cividis",
        vmin=0.0,
        vmax=max(1.0, float(np.nanmax(pivot.values))),
    )

    ax.set_title(title)
    ax.set_xlabel("Sensor Radius (cells)")
    ax.set_ylabel("Fleet Size (num_drones)")

    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels([str(c) for c in pivot.columns])
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels([str(i) for i in pivot.index])

    cbar = fig.colorbar(im, ax=ax, label=value_col)
    cbar.outline.set_edgecolor("#3a4651")

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.18, subtitle, transform=ax.transAxes, ha="center", va="top", color="#aab3bb")

    save_fig(fig, out_path)


def plot_cost_vs_coverage(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    df = _filter_strategy(agg, strategy)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    _scatter_by_strategy(ax, df, "total_cost", "final_weighted_coverage")

    ax.set_title("Cost vs Weighted Coverage")
    ax.set_xlabel("Total Cost")
    ax.set_ylabel("Final Weighted Coverage")

    for _, row in df.iterrows():
        ax.annotate(
            f"n={int(row['num_drones'])}, r={int(row['sensor_radius'])}",
            (row["total_cost"], row["final_weighted_coverage"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
            color="#aab3bb",
        )

    if "strategy" in df.columns and strategy is None:
        ax.legend(title="Strategy")

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.16, subtitle, transform=ax.transAxes, ha="center", va="top", color="#aab3bb")

    save_fig(fig, out_path)


def plot_coverage_efficiency_by_fleet(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    df = _filter_strategy(agg, strategy)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))

    for r in sorted(df["sensor_radius"].unique()):
        sub = df[df["sensor_radius"] == r].sort_values("num_drones")
        ax.plot(sub["num_drones"], sub["coverage_efficiency"], marker="o", label=f"r={int(r)}")

    ax.set_title("Coverage Efficiency vs Fleet Size")
    ax.set_xlabel("Fleet Size (num_drones)")
    ax.set_ylabel("Final Weighted Coverage / Total Cost")

    ax.legend(title="Sensor Radius")

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.16, subtitle, transform=ax.transAxes, ha="center", va="top", color="#aab3bb")

    save_fig(fig, out_path)


def plot_redundancy_vs_coverage(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    df = _filter_strategy(agg, strategy)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    _scatter_by_strategy(ax, df, "redundancy_ratio", "final_weighted_coverage")

    ax.set_title("Redundancy vs Weighted Coverage")
    ax.set_xlabel("Redundancy Ratio")
    ax.set_ylabel("Final Weighted Coverage")

    if "strategy" in df.columns and strategy is None:
        ax.legend(title="Strategy")

    save_fig(fig, out_path)


def plot_priority_vs_global_coverage(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    df = _filter_strategy(agg, strategy)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    _scatter_by_strategy(ax, df, "final_coverage", "priority_cell_coverage")

    ax.set_title("Priority Coverage vs Global Coverage")
    ax.set_xlabel("Final Global Coverage")
    ax.set_ylabel("Priority-Cell Coverage")

    if "strategy" in df.columns and strategy is None:
        ax.legend(title="Strategy")

    save_fig(fig, out_path)


def plot_task_service_vs_response(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    df = _filter_strategy(agg, strategy)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["mean_task_response_time"])

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    _scatter_by_strategy(ax, df, "avg_task_service_rate", "mean_task_response_time")

    ax.set_title("Task Service vs Response Time")
    ax.set_xlabel("Average Task Service Rate")
    ax.set_ylabel("Mean Task Response Time (steps)")

    if "strategy" in df.columns and strategy is None:
        ax.legend(title="Strategy")

    save_fig(fig, out_path)


def plot_strategy_metric_bars(
    agg: pd.DataFrame,
    out_path: Path,
    metrics: list[str],
    title: str,
) -> None:
    if "strategy" not in agg.columns:
        raise ValueError("plot_strategy_metric_bars requires a strategy column.")

    summary = agg.groupby("strategy", as_index=False)[metrics].mean(numeric_only=True)
    strategies = list(summary["strategy"])
    x = np.arange(len(strategies))
    width = 0.8 / max(len(metrics), 1)

    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, metric in enumerate(metrics):
        ax.bar(x + idx * width, summary[metric], width=width, label=metric)

    ax.set_xticks(x + width * (len(metrics) - 1) / 2)
    ax.set_xticklabels(strategies)
    ax.set_title(title)
    ax.legend()

    save_fig(fig, out_path)


def plot_timeseries_comparison(
    static_timeseries: pd.DataFrame,
    patrol_timeseries: pd.DataFrame,
    out_path: Path,
    static_label: str,
    patrol_label: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)

    axes[0].plot(static_timeseries["t"], static_timeseries["coverage"], label=static_label)
    axes[0].plot(patrol_timeseries["t"], patrol_timeseries["coverage"], label=patrol_label)
    axes[0].set_title("Global Coverage Over Time")
    axes[0].set_xlabel("Timestep")
    axes[0].set_ylabel("Coverage")
    axes[0].legend()

    axes[1].plot(static_timeseries["t"], static_timeseries["weighted_coverage"], label=static_label)
    axes[1].plot(patrol_timeseries["t"], patrol_timeseries["weighted_coverage"], label=patrol_label)
    axes[1].set_title("Weighted Coverage Over Time")
    axes[1].set_xlabel("Timestep")
    axes[1].set_ylabel("Weighted Coverage")
    axes[1].legend()

    save_fig(fig, out_path)


def plot_policy_timeseries(
    timeseries_by_label: dict[str, pd.DataFrame],
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharex=True)

    for label, df in timeseries_by_label.items():
        axes[0].plot(df["t"], df["coverage"], label=label)
        axes[1].plot(df["t"], df["weighted_coverage"], label=label)
        axes[2].plot(df["t"], df["task_service"], label=label)

    axes[0].set_title("Global Coverage")
    axes[1].set_title("Weighted Coverage")
    axes[2].set_title("Task Service")
    for ax in axes:
        ax.set_xlabel("Timestep")
        ax.legend()
    axes[0].set_ylabel("Rate")

    save_fig(fig, out_path)
