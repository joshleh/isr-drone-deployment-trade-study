# ISR Drone Deployment Trade Study  
## Modeling Assumptions

### 1. Purpose of Assumptions

The purpose of this document is to clearly state the modeling assumptions used in the ISR drone deployment trade study. These assumptions are intended to simplify the operational environment while preserving the key drivers of tradeoffs between coverage, persistence, cost, and risk.

Explicit documentation of assumptions improves transparency, supports reproducibility, and enables future extensions or sensitivity analysis.

---

### 2. Operational Environment

- The operational area is modeled as a two-dimensional region with fixed boundaries.
- The environment is assumed to be static over the duration of each simulation run.
- Terrain, weather, and adversary dynamics are not explicitly modeled in the baseline analysis.
- All regions within the operational area are assumed to be equally observable unless otherwise specified.

---

### 3. Drone Platform Assumptions

Each ISR drone in the fleet is assumed to have homogeneous capabilities:

- Fixed cruise speed and operating altitude
- Fixed sensor footprint with circular or rectangular coverage area
- Fixed endurance (maximum mission time per sortie)
- Fixed operational cost per unit time
- Identical reliability and availability across the fleet

Heterogeneous drone fleets may be considered in future extensions.

---

### 4. Sensor and Coverage Model

- A drone provides full coverage within its sensor footprint.
- Sensor performance does not degrade with distance or time.
- Coverage is binary at the baseline level (covered vs. not covered).
- Overlapping sensor coverage does not provide additional benefit unless explicitly modeled.

This simplified sensor model enables clear interpretation of coverage and persistence metrics.

---

### 5. Temporal Modeling

- Time is discretized into fixed-length steps.
- Drone movement, coverage, and metric updates occur at each time step.
- Mission duration is finite and defined per scenario.
- Drones are assumed to operate continuously until endurance limits are reached.

---

### 6. Deployment and Movement

- Drone deployment strategies are predefined per scenario.
- Drones follow predefined movement or patrol policies, which may include stochastic behavior.
- Collision avoidance and deconfliction are assumed to be handled externally.
- Launch, recovery, and transit delays are not explicitly modeled.

---

### 7. Cost Modeling

- Operational cost is modeled as a linear function of drone operating time.
- Acquisition and sunk costs are excluded from the baseline analysis.
- Maintenance and logistics costs are aggregated into the operational cost term.

This approach focuses the trade study on marginal operational decisions.

---

### 8. Risk Representation

- Risk is represented using proxy metrics rather than explicit threat modeling.
- Examples of risk proxies include:
  - Low revisit rates over critical regions
  - High utilization with limited redundancy
  - Large uncovered areas over time
- Adversary action, attrition, and failure modes are not explicitly simulated.

---

### 9. Constraints

The baseline model enforces the following constraints:

- Maximum number of available drones
- Drone endurance limits
- Operational area boundaries
- Mission time horizon

Additional constraints may be introduced in later scenarios.

---

### 10. Limitations

The following limitations are acknowledged:

- Simplified geometry and sensor models
- Absence of adversarial behavior
- Homogeneous fleet assumption
- Linear cost structure

These limitations are intentional and will be revisited as the model evolves.

---

### 11. Path to Model Extension

Future extensions may include:

- Heterogeneous drone fleets
- Probabilistic sensor performance
- Dynamic tasking and replanning
- Adversarial and environmental effects
- Nonlinear cost and risk functions

Each extension will be evaluated against the baseline to assess incremental value and complexity.