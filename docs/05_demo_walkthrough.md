# Demo Walkthrough

The repository ships with a one-command priority-weighted trade-study demo. Instead of serving an ML API, the demo behaves like a compact decision-support artifact: it runs a sweep, exports comparison figures, writes a short analyst brief, and feeds the live-demo viewer.

## Command

```bash
python scripts/run_demo.py
```

Use Python 3.10+. The Makefile target `make demo` is the equivalent invocation.

## What the demo shows

- A border corridor that matters but takes second priority to a downstream ingress lane.
- A logistics hub that carries the highest mission weight.
- Static and patrol strategies evaluated across the same fleet-size and sensor-radius sweep.
- Weighted coverage, priority-cell coverage, revisit behavior, and redundancy alongside a `mission_fit_score` ranking.

For the heterogeneous fleet, dynamic-task version of the analysis, see [07_dynamic_policy_comparison.md](07_dynamic_policy_comparison.md).

## Outputs

- Stable showcase figures land in `docs/figures/` (these back the live-demo gallery and the README).
- Timestamped CSVs and the generated brief land in `results/demo/<run-id>/`.
- The latest run is automatically picked up by the live-demo viewer (`make live-demo`).

## Reading the brief

The generated `demo_report.md` contains:

- The narrative for the run (configurable in `configs/sweeps/demo_priority_trade_study.yaml`).
- A top-5 configuration table ranked by `mission_fit_score`.
- A short take on the static-vs-patrol tradeoff for the chosen scenario.

`mission_fit_score` is intentionally a demo-grade ranking aid, not a normative metric — its weights are configurable and live alongside the run.
