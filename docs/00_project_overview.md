# Project Overview

A scenario-based trade study that evaluates ISR drone deployment policies under coverage, persistence, cost, and dynamic-tasking constraints. The goal is decision support, not a single optimal solution.

## What the project does

- Simulates static, random-patrol, greedy, and task-aware patrol policies on configurable scenarios.
- Scores each policy on coverage, weighted coverage, persistence, redundancy, task service, and response time.
- Produces reproducible analyst briefs, stable showcase figures, and a static HTML dashboard per run.
- Persists every run in CSV, Parquet, and DuckDB so the same outputs feed BI tools, notebooks, or future ML evaluation.

## How it is structured

| Layer | Purpose |
| --- | --- |
| `configs/` | Scenario, sweep, and policy-comparison YAMLs. |
| `src/isr_trade_study/sim/` | Scenario types and the Monte Carlo runner. |
| `src/isr_trade_study/io/` | YAML config loading. |
| `src/isr_trade_study/analytics/` | DuckDB + Parquet persistence. |
| `src/isr_trade_study/dashboard/` | Per-run dashboard and live-demo HTML generation. |
| `src/isr_trade_study/viz/` | Matplotlib helpers shared by all reports. |
| `scripts/` | One-command entrypoints (`run_demo.py`, `run_policy_comparison.py`, etc.). |
| `docs/` | Problem statement, assumptions, experiments plan, results, walkthroughs. |
| `docs/live_demo/` | Generated live demo (auto-built via `make live-demo`). |

## Scope

- 2D grid scenarios with priority zones and dynamic tasks.
- Homogeneous or heterogeneous fleets defined declaratively in YAML.
- Configurable mission length, sensor radius, endurance, and patrol policy parameters.
- Deterministic seeding so every run is reproducible.

## What this project is **not**

- Not a real-time C2 system.
- Not an ML model or training pipeline (see [AeroTrack](https://github.com/joshleh/aerotrack) for that).
- Not a sensor-fusion math library (see [FusionTrack](https://github.com/joshleh/fusiontrack)).

This repo is the analytical layer that sits next to those: scenarios, KPIs, sweeps, and analyst-style reporting on top of a small Monte Carlo simulation.
