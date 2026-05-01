# Role Alignment

This project sits at the intersection of operations analysis, data science, and lightweight data engineering. Below are the workstreams it touches and how to frame them in a conversation.

## Operations analyst

- Scenario design under explicit assumptions and decision variables.
- Tradeoff analysis across cost, coverage, persistence, redundancy, and task response.
- Decision-focused reporting (mission-fit score, ranked policy table, analyst brief) instead of single-metric benchmarks.

## Data scientist

- KPI design tied to mission effectiveness rather than model accuracy.
- Simulation-backed hypothesis testing across controlled parameter sweeps.
- Composite scoring that blends coverage, response time, and persistence under explicit weights.

## Data engineer

- Reproducible experiment configs (`configs/`) and a single Python entrypoint per workflow (`scripts/`).
- DuckDB + Parquet outputs side-by-side with CSVs, so each run is structured like a small analytics warehouse instead of a folder of CSVs.
- Static HTML dashboards generated from the same DuckDB tables, ready to be wired into a BI tool or notebook.

## Autonomy / planner evaluation

- The dynamic-policy harness (`run_policy_comparison.py`) compares static, random, greedy, and task-aware patrol policies under the same scenario.
- The same harness can score an optimization-based or learned routing policy without changing the metrics or the report shape.
- Priority zones, revisit thresholds, and task-response metrics are the kinds of operational scores that matter when comparing autonomy stacks.

## How to pitch it

> A reproducible simulation and decision-analysis project for ISR resource allocation, with a clear path toward optimization-backed routing and policy evaluation on top of the same harness.
