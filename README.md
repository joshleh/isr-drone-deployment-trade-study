# ISR Drone Deployment Trade Study

Scenario-based operations analysis of ISR drone fleet deployment under cost, coverage, and persistence constraints.

This project evaluates tradeoffs between alternative ISR drone deployment strategies using simulation, parameter sweeps, and decision-relevant metrics. The analysis is structured as a formal trade study, emphasizing transparency, reproducibility, and operational insight rather than model complexity.

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
3. Evaluate performance using standardized metrics  
4. Compare outcomes across fleet sizes and sensor footprints  
5. Identify tradeoffs and decision-relevant insights  

The baseline implementation is developed in Python for clarity and reproducibility, with a clear path toward optimization and C++ acceleration.

---

## Key Metrics

Deployment strategies are evaluated using the following metrics:

- **Coverage**: Fraction of the operational area observed at least once during the mission  
- **Persistence**: Distribution of revisit gaps between consecutive observations of the same location  
- **Cost**: Total operational cost based on drone activity time  
- **Utilization**: Fraction of available drone capacity used  
- **Persistence Threshold Score**: Percentage of revisits occurring within a fixed timestep threshold  

---

## Key Findings

- **Static deployments** provide strong persistence over fixed areas but are limited in spatial reach.  
- **Patrol deployments** achieve substantially higher cumulative coverage by sweeping the operational area over time, at the cost of looser revisit behavior.  
- Improvements in **sensor footprint** often yield larger marginal coverage gains than increasing fleet size.  
- Coverage gains exhibit diminishing returns at higher resource levels, suggesting inefficiencies beyond certain fleet sizes.  
- Persistence and cumulative coverage represent competing mission objectives rather than simultaneously optimizable outcomes.

Detailed results, plots, and interpretation are provided in `docs/04_results_summary.md`.

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

1. Install dependencies  
   python -m pip install -e .

2. Run a single baseline simulation  
   python scripts/run_pipeline.py

3. Run a parameter sweep  
   python scripts/run_sweep.py --config configs/sweeps/sweep_01.yaml  

   Additional sweep configurations (e.g., patrol vs. static) are located in `configs/sweeps/`.

4. Export figures  
   python scripts/export_results.py  

   Exported figures are saved to `docs/figures/`.

---

## Documentation

Detailed project documentation is provided in the `docs/` directory:

- `00_project_overview.md` — Executive overview  
- `01_problem_statement.md` — Formal problem definition  
- `02_modeling_assumptions.md` — Explicit modeling assumptions  
- `03_experiments_plan.md` — Experimental design and methodology  
- `04_results_summary.md` — Results, insights, and tradeoffs  

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