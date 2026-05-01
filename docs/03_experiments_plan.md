# Experiments Plan

The experimental program is structured as a small set of reproducible workflows. Each one is configured by a YAML file under `configs/` and produces stable showcase figures plus per-run artifacts under `results/`.

## Workflows

| Workflow | Entrypoint | Configs | Purpose |
| --- | --- | --- | --- |
| Baseline single run | `scripts/run_pipeline.py` | `configs/base.yaml` | Smoke run for development. |
| Parameter sweep | `scripts/run_sweep.py` | `configs/sweeps/sweep_01.yaml` | Sweep fleet size and sensor radius for both static and patrol strategies side by side. |
| Priority-weighted demo | `scripts/run_demo.py` | `configs/sweeps/demo_priority_trade_study.yaml` | Static vs patrol on a priority-weighted scenario; emits the analyst brief and the live-demo demo block. |
| Dynamic policy comparison | `scripts/run_policy_comparison.py` | `configs/policy_comparison_heterogeneous.yaml` | Static / random / greedy / task-aware patrol on a heterogeneous fleet under dynamic tasks. |
| Live demo build | `scripts/build_live_demo.py` | reads `results/` | Renders the static `docs/live_demo/index.html` from the latest local artifacts. |

## Experimental factors

- **Fleet size** — typically 2 / 4 / 6 / 8 / 10 in the parameter sweeps, 3 / 6 / 9 in the priority demo.
- **Sensor radius** — 2 / 4 / 6 / 8 in the sweeps, 3 / 5 / 7 in the priority demo.
- **Strategy** — `static`, `patrol`, `greedy_patrol`, `priority_patrol`.
- **Fleet composition** — homogeneous in the sweeps and priority demo; heterogeneous (`sentinel` + `scout`) in the policy comparison.
- **Mission length** — 240–300 timesteps depending on scenario.
- **Number of seeds per cell** — 3–5 in the sweeps, 4 in the priority demo, 5 in the policy comparison. All seeds are derived deterministically from the strategy name and grid coordinates.

## Metrics

Every workflow records the metrics defined in `RunMetrics` (`src/isr_trade_study/sim/metrics.py`):

- Coverage timeseries, average, and final.
- Weighted coverage timeseries, average, and final.
- Priority cell coverage.
- Revisit-gap mean / p90 / fraction-within-threshold (global and priority-restricted).
- Task service rate, task completion rate, response-time mean / p90 / fraction-within-threshold.
- Total cost, utilization, redundancy ratio, coverage efficiency.

Each workflow then layers a composite `mission_fit_score` on top of those raw metrics, with weights configurable in the workflow YAML.

## Reporting

For each workflow:

- Raw and aggregated CSVs land under `results/{workflow}/<run-id>/`.
- The dynamic policy comparison also persists Parquet + DuckDB and renders a per-run dashboard.
- A markdown brief is written next to the data so the analyst-style narrative is reviewable without running anything.
- Stable showcase figures land under `docs/figures/` so the README and the live demo can reference them across runs.

## Success criteria

The program is considered effective if it:

- Surfaces operational tradeoffs (coverage vs persistence, response vs reach) clearly.
- Distinguishes the strengths and limitations of each policy under controlled changes.
- Produces decision-relevant outputs (ranked policies, briefs, dashboards) rather than only technical metrics.
- Stays open to plugging in optimization-based or learned policies without changing the metric or report layer.
