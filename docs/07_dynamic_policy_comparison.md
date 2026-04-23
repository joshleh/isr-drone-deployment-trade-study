# Dynamic Policy Comparison

This project now includes an expanded workflow that moves beyond static trade studies into dynamic, policy-aware evaluation.

## Command

```bash
python3 scripts/run_policy_comparison.py
```

Use a Python `3.10+` environment. Do not change the machine's global default Python just for this project.

## What It Adds

- A heterogeneous fleet with long-endurance `sentinel` drones and faster `scout` drones
- Time-varying surveillance tasks that appear and expire during the mission
- A stronger `assignment_patrol` baseline that assigns drones to targets each step
- A `priority_patrol` policy that reacts to active tasks and priority zones
- A lightweight `Makefile` so the main workflows can be run with `make test`, `make demo`, and `make policy` while still pointing `PYTHON` at a 3.10+ interpreter when needed
- Policy scoring that can favor dynamic response rather than only global reach
- Persisted results in CSV, Parquet, and DuckDB
- A static HTML dashboard suitable for portfolio review

## Output Artifacts

Running the command writes a timestamped directory under `results/policy/` containing:

- `policy_results_raw.csv`
- `policy_results_agg.csv`
- `analysis.duckdb`
- corresponding Parquet tables
- `dashboard.html`
- `policy_report.md`

Stable figures are also written to `docs/figures/`.

## Why This Matters

This workflow makes the project more relevant to:

- operations analysis, because it compares policy behavior under mission shifts
- data science, because it formalizes dynamic-response KPIs and composite policy scoring
- data engineering, because it persists experiment outputs into analytics-friendly storage instead of leaving them as ad hoc CSVs
- autonomy evaluation, because it creates a harness that could later compare heuristic, optimized, or learned policies
