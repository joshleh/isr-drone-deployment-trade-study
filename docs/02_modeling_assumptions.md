# Modeling Assumptions

These assumptions intentionally simplify the operational environment while preserving the drivers of the static-vs-patrol-vs-task-aware tradeoff. Each section lists what is modeled and what is deferred.

## Operational environment

- The operational area is a 2D grid with fixed boundaries.
- The environment is static within each run; weather, terrain, and adversary dynamics are not simulated.
- All cells are equally observable unless they sit inside a declared priority zone (which only changes their *weight*, not their visibility).

## Drone platforms

Each drone has:

- A fixed sensor footprint (disk of integer radius).
- A fixed endurance budget in timesteps.
- A fixed cost per active timestep.
- A fixed cruise step size.

Heterogeneous fleets are supported: each platform type sets its own sensor radius, endurance, cost, and step size. The dynamic-policy workflow uses this to model a long-endurance `sentinel` plus a faster `scout`.

## Sensor and coverage model

- Within the sensor footprint, coverage is binary: a cell is either observed or not on a given step.
- Sensor performance does not degrade with distance, time, or environmental conditions.
- Overlapping coverage produces no extra benefit, but it *is* tracked through the redundancy ratio so the cost of overlap is visible.

## Time and movement

- Time is discretized; one observation pass per drone per step.
- Drones operate continuously up to their endurance limit, then go inactive.
- Patrol policies use random walk with a configurable turn probability.
- Greedy and task-aware planners pick a target each step from a candidate set built from active tasks, priority zones, and unseen cells.
- Launch, recovery, transit, and deconfliction are handled outside the model.

## Cost model

- Operational cost is linear in active drone-steps.
- Acquisition, maintenance, and logistics are not split out — they are folded into `cost_per_step`.
- This focuses the trade study on marginal operational decisions.

## Risk representation

- Risk is captured indirectly through proxy metrics: revisit gaps, redundancy ratio, response time, and uncovered weighted area.
- Adversary action, attrition, and platform failures are not simulated.

## Constraints enforced

- Total drones available.
- Per-drone endurance.
- Operational area boundaries.
- Mission time horizon.
- Priority and task definitions from the YAML config.

## Known limitations

- Simplified geometry and binary sensor model.
- No adversarial behavior or attrition.
- Linear cost structure.
- Probabilistic patrol uses random walk; structured sweeps are not yet modeled.

## Planned extensions

- Probabilistic sensor performance (range or angle dependent).
- Structured sweep / sector-based patrol policies.
- Optimization-backed routing benchmark sharing the same harness.
- Dynamic adversary behaviors and attrition for risk-explicit scoring.
