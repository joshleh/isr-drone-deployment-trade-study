from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from anduril_ops.viz.plots import (
    plot_coverage_heatmap,
    plot_cost_vs_coverage,
    plot_utilization_by_fleet,
)


def find_latest_sweep_agg(results_root: Path, prefix: str = "sweep_") -> Path:
    """
    Find the most recent sweep folder containing sweep_results_agg.csv.
    Assumes folders are timestamped (lexicographically sortable).
    """
    candidates = []
    if not results_root.exists():
        raise FileNotFoundError(f"Results root not found: {results_root}")

    for p in results_root.iterdir():
        if p.is_dir() and p.name.startswith(prefix):
            agg = p / "sweep_results_agg.csv"
            if agg.exists():
                candidates.append(agg)

    if not candidates:
        raise FileNotFoundError(f"No sweep_results_agg.csv found under: {results_root}")

    return sorted(candidates)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export trade study figures to docs/figures.")
    parser.add_argument("--agg_csv", type=str, default=None, help="Path to sweep_results_agg.csv")
    parser.add_argument("--results_root", type=str, default="results/runs", help="Root results directory")
    parser.add_argument("--docs_figures", type=str, default="docs/figures", help="Output directory for figures")
    parser.add_argument("--strategy", type=str, default=None, help="Optional strategy filter, e.g. static or patrol")
    args = parser.parse_args()

    docs_figures = Path(args.docs_figures)
    results_root = Path(args.results_root)

    if args.agg_csv is not None:
        agg_path = Path(args.agg_csv)
    else:
        agg_path = find_latest_sweep_agg(results_root)

    agg = pd.read_csv(agg_path)

    # Name figures based on sweep folder
    sweep_folder = agg_path.parent.name
    suffix = f"_{args.strategy}" if args.strategy else ""
    base = f"{sweep_folder}{suffix}"

    plot_coverage_heatmap(
        agg,
        out_path=docs_figures / f"{base}_coverage_heatmap.png",
        strategy=args.strategy,
    )

    plot_cost_vs_coverage(
        agg,
        out_path=docs_figures / f"{base}_cost_vs_coverage.png",
        strategy=args.strategy,
    )

    plot_utilization_by_fleet(
        agg,
        out_path=docs_figures / f"{base}_utilization_vs_fleet.png",
        strategy=args.strategy,
    )

    print("Exported figures to:", docs_figures.resolve())
    print("Used agg CSV:", agg_path.resolve())


if __name__ == "__main__":
    main()