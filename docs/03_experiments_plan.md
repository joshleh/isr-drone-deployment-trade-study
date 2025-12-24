# ISR Drone Deployment Trade Study  
## Experiments Plan

### 1. Objective

The objective of this experiments plan is to define a structured approach for evaluating ISR drone deployment strategies under varying operational conditions. The experiments are designed to quantify tradeoffs between coverage, persistence, cost, utilization, and operational behavior across multiple scenarios.

This document distinguishes between experiments that have been executed and analyzed, and extensions that are planned for future work.

---

## Part I — Executed Experiments

### 2. Baseline Scenario

The baseline scenario serves as the reference point for all executed experiments.

**Baseline characteristics:**
- Fixed two-dimensional operational area
- Homogeneous ISR drone fleet
- Fixed mission duration
- Static and patrol-based deployment strategies
- Linear operational cost model
- Full fleet availability over the mission horizon

All executed experiments are compared against this baseline configuration.

---

### 3. Experimental Factors (Executed)

The following factors were varied systematically in executed experiments:

#### 3.1 Fleet Size
- Number of available ISR drones
- Evaluated across low to high fleet sizes

#### 3.2 Sensor Footprint
- Sensor coverage radius
- Represents alternative sensor capabilities or operating altitudes

#### 3.3 Deployment Strategy
- Static loiter deployments
- Patrol-based deployments using a predefined stochastic movement policy

Each factor was varied in a controlled manner to isolate its impact on performance metrics.

---

### 4. Executed Scenarios

Executed experiments include:
- Static deployment sweeps across fleet size and sensor footprint
- Patrol deployment sweeps across the same parameter space
- Direct comparison of static versus patrol strategies under identical resource constraints

Each scenario was defined using configuration files to ensure reproducibility.

---

### 5. Simulation Runs

For each executed scenario:
- Multiple simulation runs were performed to account for stochastic variability
- Controlled random seeds were used to ensure fair comparisons
- Results were aggregated across runs for reporting and analysis

---

### 6. Performance Metrics (Executed)

The following metrics were computed for executed experiments:

- Cumulative coverage over the mission horizon
- Revisit gap statistics (mean and tail behavior)
- Persistence threshold score (percentage of revisits within a fixed timestep threshold)
- Total operational cost
- Fleet utilization

Metrics were evaluated at the mission level and aggregated across runs.

---

### 7. Comparison Methodology

Executed results were analyzed using:
- Parameter sweep comparison tables
- Coverage–cost tradeoff plots
- Strategy-level comparisons highlighting persistence versus spatial reach
- Sensitivity observation across fleet size and sensor footprint

The analysis emphasizes tradeoffs rather than optimization toward a single objective.

---

## Part II — Planned Extensions

### 8. Additional Experimental Factors (Planned)

Future experiments may introduce:
- Mission duration as an explicit experimental factor
- Alternative operational area sizes and shapes
- Region-weighted coverage priorities

---

### 9. Alternative Deployment Policies (Planned)

Planned extensions include evaluation of alternative patrol policies, such as:
- Structured sweep or sector-based patrols
- Persistence-aware patrol policies
- Hybrid static–patrol deployments

These policies will be evaluated relative to the executed baseline strategies.

---

### 10. Optimization-Based Experiments (Planned)

Future work may incorporate:
- Optimization-based deployment strategies
- Pareto frontier identification across coverage, persistence, and cost
- Constraint-driven strategy selection based on mission priorities

---

### 11. Performance and Scalability Extensions (Planned)

To support larger scenario sweeps, planned work includes:
- Profiling and identification of simulation bottlenecks
- Selective C++ acceleration of performance-critical components
- Evaluation of scalability across larger grids and longer missions

---

### 12. Experiment Traceability

All experiments, executed and planned, are designed to maintain:
- Explicit configuration files
- Traceability from results to assumptions
- Reproducibility across code versions

---

### 13. Success Criteria

The experimental program is considered successful if it:
- Clearly illustrates tradeoffs between competing mission objectives
- Distinguishes operational strengths and limitations of deployment strategies
- Produces decision-relevant insights rather than purely technical metrics
- Supports future extension toward optimization and performance scaling
