# Demo Walkthrough

This repository now includes a one-command demo scenario that is intentionally different from the `aerotrack` project. Instead of serving an ML API, the demo behaves like a compact decision-support artifact: it runs a priority-weighted trade study, exports comparison figures, and writes a short analyst brief.

## Command

```bash
python3 scripts/run_demo.py
```

Use a Python `3.10+` interpreter. If your default `python3` is older, point the command at a newer environment.

## What The Demo Shows

- A border corridor that matters, but not as much as the downstream ingress lane
- A logistics hub with the highest mission weight
- Static and patrol strategies evaluated across the same fleet-size and sensor-radius sweep
- Weighted coverage, priority-cell coverage, revisit behavior, and redundancy

For the expanded project version, the separate `run_policy_comparison.py` workflow adds dynamic tasks, heterogeneous fleets, DuckDB persistence, and a dashboard.

## Outputs

- Stable demo figures are written to `docs/figures/`
- Timestamped CSVs and the generated brief are written to `results/demo/`

## Why This Demo Is Better Than The Original Baseline

- It avoids flat utilization-driven visuals by emphasizing weighted coverage and redundancy
- It frames the study around mission priorities instead of coverage on a blank grid
- It makes strategy tradeoffs easier to narrate in an interview or portfolio walkthrough
