# Anduril Role Alignment

This project is still strongest for operations analysis, but it also maps cleanly to several adjacent roles when framed correctly.

## Operations Analyst

- Scenario design under explicit assumptions
- Tradeoff analysis across cost, coverage, persistence, and redundancy
- Decision-focused reporting instead of pure model benchmarking

## Data Scientist

- KPI design for mission effectiveness, not just model accuracy
- Simulation-backed hypothesis testing across controlled parameter sweeps
- Priority-weighted metrics that reflect operational objectives instead of generic averages

## Data Engineer

- Reproducible experiment configuration and result generation
- Clean separation between configs, simulation logic, exported artifacts, and reporting
- Straightforward path to scaling runs, storing sweep outputs, and productionizing experiment pipelines
- DuckDB and Parquet outputs that make the project feel closer to a compact analytics platform than a one-off notebook exercise

## Adjacent MLE / Autonomy Analytics Relevance

- Evaluation logic for surveillance-task allocation can become the offline scoring layer for autonomy systems
- Priority zones, revisit thresholds, and redundancy metrics are the kinds of operational metrics that matter once learned policies or planners exist
- The new dynamic-task policy comparison already creates the harness for comparing heuristic patrol policies against learned or optimized routing policies
- The project now also reads more cleanly as a mission-tasking layer because it exposes assets, zones, tasks, and assignment behavior rather than only aggregate sweep metrics

## Best Framing

The strongest pitch is not "this is an MLE project." The better pitch is:

> This is a reproducible simulation and mission-tasking evaluation project for ISR resource allocation, with a clear path toward optimization, autonomy evaluation, and experiment pipelines.
