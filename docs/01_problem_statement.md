# Problem Statement

## Background

ISR missions increasingly rely on unmanned aerial systems for persistent situational awareness across large operational areas. Compared to manned platforms, ISR drones offer lower cost, lower personnel risk, and flexible deployment, but limited fleet size, finite endurance, sensor constraints, and operational cost introduce tradeoffs that are non-obvious by inspection.

This project develops a scenario-based analytical framework to evaluate and compare alternative ISR deployment strategies through simulation, metric engineering, and structured trade studies.

## Question

> How should a finite ISR drone fleet be deployed to balance coverage, persistence, task response, and cost under realistic operational constraints?

## Decision variables

The trade study sweeps over:

- Number of drones in the fleet (or fleet composition for heterogeneous mixes).
- Sensor footprint (effective radius).
- Deployment policy (`static`, `patrol`, `greedy_patrol`, `priority_patrol`).
- Strategy parameters: patrol step size, turn probability, target commitment, congestion penalty, and policy bias terms.

## Key performance metrics

Each scenario is evaluated on:

- **Coverage** — fraction of the operational area observed at least once.
- **Weighted coverage** — coverage weighted by per-cell mission priority.
- **Priority cell coverage** — coverage restricted to declared priority zones.
- **Persistence** — distribution of revisit gaps; fraction of revisits within a configurable threshold.
- **Task service** — time-weighted fraction of active dynamic tasks observed during their window.
- **Task completion** — fraction of tasks observed at least once.
- **Mean / p90 response time** — steps from task spawn to first observation.
- **Cost** — total drone activity cost.
- **Utilization** — fraction of available drone-steps used.
- **Redundancy ratio** — fraction of observations that re-cover already-seen cells.
- **Coverage efficiency** — weighted coverage per unit cost.
- **Mission-fit score** — configurable weighted blend of the above (defined per workflow).

## Analytical approach

1. Define the scenario, fleet, and strategy in YAML.
2. Run the Monte Carlo simulation across the requested seed count and factor grid.
3. Aggregate per-strategy results, compute the composite mission-fit score, and write CSV / Parquet / DuckDB outputs.
4. Render the analyst brief, the showcase figures, and the per-run dashboard.
5. Compare policies and configurations using the resulting tables and plots.

The implementation prioritizes interpretability and reproducibility. Performance-critical paths are kept in NumPy and structured so a future C++ kernel could replace the inner loop without changing the report layer.
