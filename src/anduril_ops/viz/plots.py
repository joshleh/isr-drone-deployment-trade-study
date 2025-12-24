from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_fig(fig: plt.Figure, out_path: Path, dpi: int = 200) -> None:
    ensure_dir(out_path.parent)
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def plot_coverage_heatmap(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    """
    Heatmap: avg_coverage vs (num_drones x sensor_radius)
    """
    df = agg.copy()
    if strategy is not None and "strategy" in df.columns:
        df = df[df["strategy"] == strategy]

    pivot = df.pivot_table(
        index="num_drones",
        columns="sensor_radius",
        values="avg_coverage",
        aggfunc="mean",
    ).sort_index().sort_index(axis=1)

    fig, ax = plt.subplots()
    im = ax.imshow(pivot.values, aspect="auto")  # default colormap

    ax.set_title("Average Coverage Heatmap")
    ax.set_xlabel("Sensor Radius (cells)")
    ax.set_ylabel("Fleet Size (num_drones)")

    ax.set_xticks(np.arange(pivot.shape[1]))
    ax.set_xticklabels([str(c) for c in pivot.columns])
    ax.set_yticks(np.arange(pivot.shape[0]))
    ax.set_yticklabels([str(i) for i in pivot.index])

    # colorbar is informative and standard
    fig.colorbar(im, ax=ax, label="avg_coverage")

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.12, subtitle, transform=ax.transAxes, ha="center", va="top")

    save_fig(fig, out_path)


def plot_cost_vs_coverage(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    """
    Scatter: total_cost vs avg_coverage. Annotate with (num_drones, sensor_radius).
    """
    df = agg.copy()
    if strategy is not None and "strategy" in df.columns:
        df = df[df["strategy"] == strategy]

    fig, ax = plt.subplots()
    ax.plot(df["total_cost"], df["avg_coverage"], marker="o", linestyle="")

    ax.set_title("Cost vs Coverage Tradeoff")
    ax.set_xlabel("Total Cost")
    ax.set_ylabel("Average Coverage")

    # light annotations (kept small so plot isn't unreadable)
    for _, row in df.iterrows():
        ax.annotate(
            f"n={int(row['num_drones'])}, r={int(row['sensor_radius'])}",
            (row["total_cost"], row["avg_coverage"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
        )

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.12, subtitle, transform=ax.transAxes, ha="center", va="top")

    save_fig(fig, out_path)


def plot_utilization_by_fleet(
    agg: pd.DataFrame,
    out_path: Path,
    strategy: Optional[str] = None,
) -> None:
    """
    Line plot: utilization vs fleet size, with separate lines per sensor_radius.
    """
    df = agg.copy()
    if strategy is not None and "strategy" in df.columns:
        df = df[df["strategy"] == strategy]

    fig, ax = plt.subplots()

    for r in sorted(df["sensor_radius"].unique()):
        sub = df[df["sensor_radius"] == r].sort_values("num_drones")
        ax.plot(sub["num_drones"], sub["utilization"], marker="o", label=f"r={int(r)}")

    ax.set_title("Utilization vs Fleet Size")
    ax.set_xlabel("Fleet Size (num_drones)")
    ax.set_ylabel("Utilization (active_steps / (T * N))")

    ax.legend(title="Sensor Radius")

    subtitle = f"strategy={strategy}" if strategy else "all strategies"
    ax.text(0.5, -0.12, subtitle, transform=ax.transAxes, ha="center", va="top")

    save_fig(fig, out_path)