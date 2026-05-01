# Dynamic Policy Comparison

The dynamic policy workflow extends the static trade study into a four-policy comparison on a heterogeneous fleet under time-varying surveillance demand.

## Command

```bash
python scripts/run_policy_comparison.py
```

Or `make policy`. Use Python 3.10+.

## What it adds over the static demo

- A heterogeneous fleet with long-endurance `sentinel` drones and faster `scout` drones (`configs/advanced_ops_base.yaml`).
- Time-varying surveillance tasks that appear and expire during the mission.
- Four policies compared head-to-head:
  - `static` — fixed loiter points.
  - `patrol` — random-walk patrol.
  - `greedy_patrol` — assigns each drone to the highest-utility candidate every step.
  - `priority_patrol` — task-aware planner with target commitment and platform-aware fit.
- Composite scoring that weights task service, response time, and weighted coverage.
- Persistence of every run in CSV, Parquet, and DuckDB.
- A static HTML dashboard generated next to the run.

## Output artifacts

Every run drops a timestamped folder under `results/policy/`:

| File | Purpose |
| --- | --- |
| `policy_results_raw.csv` | One row per individual run (all seeds). |
| `policy_results_agg.csv` | Mean across runs, grouped by strategy and fleet mix. |
| `analysis.duckdb` | DuckDB database holding the same tables. |
| `*.parquet` | Parquet copies for downstream BI/notebooks. |
| `dashboard.html` | Static dashboard sharing the live-demo theme. |
| `policy_report.md` | Markdown brief for the run. |

Stable plots land in `docs/figures/policy_dynamic_*` and back the live-demo gallery.

## Why this layer matters

- Operations analysis: compares policy behavior under mission shifts, not just static geometry.
- Data science: formalizes dynamic-response KPIs and a composite scoring surface.
- Data engineering: persists experiment outputs in analytics-friendly storage instead of ad hoc CSVs.
- Autonomy evaluation: provides a harness that can later score optimization-based or learned routing policies against the same heuristics.
