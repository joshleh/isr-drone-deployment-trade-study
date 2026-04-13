# ISR Drone Deployment Trade Study

Scenario-based operations analysis of ISR drone fleet deployment under cost, coverage, persistence, and mission-priority constraints.

This project evaluates tradeoffs between alternative ISR drone deployment strategies using simulation, parameter sweeps, and decision-relevant metrics. The analysis is structured as a formal trade study, emphasizing transparency, reproducibility, and operational insight rather than model complexity.

This repository is intentionally positioned as a simulation and decision-support project: scenario design, KPI engineering, sweep analysis, and analyst-style reporting.

The project now also includes:

- dynamic task arrivals instead of only fixed-area monitoring
- heterogeneous fleets with mixed endurance, cost, and sensor footprints
- planner-style and task-aware patrol policy comparison against static basing and random patrol
- DuckDB and Parquet persistence plus a lightweight static dashboard

---

## Problem Overview

ISR missions must balance competing objectives such as spatial coverage, persistence over critical areas, and operational cost. Given a finite fleet of unmanned ISR drones with limited endurance and sensor capability, deployment decisions can significantly affect mission effectiveness.

This trade study addresses the following question:

**How should a finite ISR drone fleet be deployed to balance coverage, persistence, and cost under realistic operational constraints?**

---

## Analytical Approach

The study follows a structured MS&A-style workflow:

1. Define scenarios, assumptions, and decision variables  
2. Simulate ISR drone deployments under static and patrol strategies  
3. Evaluate performance using standardized and mission-priority-aware metrics  
4. Compare outcomes across fleet sizes, sensor footprints, and strategy types  
5. Identify tradeoffs, redundancy, and decision-relevant insights  

The baseline implementation is developed in Python for clarity and reproducibility, with a clear path toward optimization and C++ acceleration.

---

## Key Metrics

Deployment strategies are evaluated using the following metrics:

- **Coverage**: Fraction of the operational area observed at least once during the mission  
- **Weighted Coverage**: Coverage adjusted for mission-priority zones such as ingress corridors or logistics hubs  
- **Persistence**: Distribution of revisit gaps between consecutive observations of the same location  
- **Cost**: Total operational cost based on drone activity time  
- **Utilization**: Fraction of available drone capacity used  
- **Persistence Threshold Score**: Percentage of revisits occurring within a fixed timestep threshold  
- **Redundancy Ratio**: Share of observations spent re-covering already observed cells rather than extending reach  

---

## Key Findings

- **Static deployments** provide strong persistence over fixed areas but are limited in spatial reach.  
- **Patrol deployments** achieve substantially higher cumulative coverage by sweeping the operational area over time, at the cost of looser revisit behavior.  
- Improvements in **sensor footprint** often yield larger marginal coverage gains than increasing fleet size.  
- Coverage gains exhibit diminishing returns at higher resource levels, and redundancy now makes that inefficiency visible.  
- Persistence and cumulative coverage represent competing mission objectives rather than simultaneously optimizable outcomes.

Detailed results, plots, and interpretation are provided in `docs/04_results_summary.md`.

---

## Demo

The fastest way to understand the project is to run the priority-weighted demo:

```bash
python3 scripts/run_demo.py
```

The demo runs a compact trade study over both `static` and `patrol` strategies, exports stable figures to `docs/figures/`, and writes a timestamped analyst brief to `results/demo/`.

This demo is intentionally more portfolio-friendly than the original blank-grid baseline because it introduces:

- priority zones with different mission value
- weighted coverage and redundancy metrics
- a ranking-oriented demo brief that reads like analyst support material

For the more advanced version of the project, run:

```bash
python3 scripts/run_policy_comparison.py
```

That workflow compares `static`, `patrol`, and `priority_patrol` policies on a heterogeneous fleet with dynamic surveillance tasks, then writes:

It now includes a stronger `greedy_patrol` baseline as well, so the project compares:

- `static`
- `patrol`
- `greedy_patrol`
- `priority_patrol`

- raw and aggregated CSV outputs
- Parquet tables
- a DuckDB database
- a static HTML dashboard
- a report summarizing which policy best matches the mission objective

---

## Repository Structure

docs/       Problem statement, assumptions, experiments plan, results summary  
configs/    Scenario and sweep configuration files  
src/        Simulation, metrics, and visualization code  
scripts/    Pipeline, sweep, and export entrypoints  
results/    Generated outputs (ignored by default)

---

## How to Run

The commands below reproduce the baseline analysis and trade study results described in the documentation.

Use a Python `3.10+` interpreter for all commands below. If your default `python3` is older, run the commands with a newer virtualenv or Conda interpreter instead.

Do not change the machine-wide default Python just for this repo. A project-specific environment is the safer choice.

1. Install dependencies  
   `python3 -m pip install -e .`

2. Run a single baseline simulation  
   `python3 scripts/run_pipeline.py`

3. Run a parameter sweep  
   `python3 scripts/run_sweep.py --config configs/sweeps/sweep_01.yaml`

   Additional sweep configurations (e.g., patrol vs. static) are located in `configs/sweeps/`.

4. Export figures  
   `python3 scripts/export_results.py`

   Exported figures are saved to `docs/figures/`.

5. Run the portfolio demo  
   `python3 scripts/run_demo.py`

6. Run the advanced heterogeneous policy comparison  
   `python3 scripts/run_policy_comparison.py`

7. Use the lightweight project entrypoints
   `make test`
   `make demo PYTHON=/path/to/python3.10+`
   `make policy PYTHON=/path/to/python3.10+`
   `make live-demo PYTHON=/path/to/python3.10+`
   `make serve-demo PYTHON=/path/to/python3.10+`

8. Open the local demo viewer
   After `make live-demo`, start `make serve-demo` and visit `http://127.0.0.1:8010/docs/live_demo/index.html`

---

## Documentation

Detailed project documentation is provided in the `docs/` directory:

- `00_project_overview.md` — Executive overview  
- `01_problem_statement.md` — Formal problem definition  
- `02_modeling_assumptions.md` — Explicit modeling assumptions  
- `03_experiments_plan.md` — Experimental design and methodology  
- `04_results_summary.md` — Results, insights, and tradeoffs  
- `05_demo_walkthrough.md` — Demo scenario and outputs  
- `06_anduril_role_alignment.md` — How to frame the project for Anduril-adjacent roles  
- `07_dynamic_policy_comparison.md` — Heterogeneous fleet, dynamic tasks, and dashboard workflow
- `live_demo/index.html` — Local showcase page that pulls together the strongest artifacts

---

## Anduril Relevance

This project fits most naturally for:

- **Operations Analyst**: scenario design, trade studies, KPI definition, mission tradeoff interpretation
- **Data Scientist**: experiment design, metric engineering, simulation-backed analysis, priority-weighted evaluation, policy scoring
- **Data Engineer**: reproducible configs, sweep pipelines, DuckDB and Parquet persistence, dashboard-oriented result generation

It is less of a direct **MLE** repo and more of an evaluation layer for planners, routing policies, and autonomy systems.

The new `priority_patrol` comparison makes that framing much stronger because the repo now evaluates alternative policies under dynamic demand rather than only measuring static geometry.
The added `greedy_patrol` baseline also makes the comparison feel more serious and less like a hand-picked heuristic demo.

---

## How To Expand It

Strong next steps that would deepen the project while keeping it focused on simulation and decision support:

- add structured patrol policies instead of only stochastic patrol
- introduce heterogeneous fleets with different endurance, cost, and sensor quality
- model dynamic tasking or incident arrivals rather than a static grid alone
- compare heuristics against optimization or learned routing policies
- persist sweep outputs to a small warehouse-style schema and build analyst dashboards on top

Those extensions are now partially implemented. The next strong layer would be optimization-backed routing or a learned policy benchmark on top of the new evaluation harness.

---

## Disclaimer

This project is an independent analytical study for educational and portfolio purposes. It does not represent operational systems, real-world ISR deployments, or proprietary methodologies.

---

## Next Steps

Planned extensions include:
- Alternative patrol policies  
- Additional persistence-focused metrics  
- Optimization-based deployment strategies  
- Heterogeneous drone fleets  
- Performance-critical C++ acceleration  
