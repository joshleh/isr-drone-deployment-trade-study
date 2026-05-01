# Results Summary

This document captures the qualitative findings of the trade study. Concrete numbers depend on the latest run and live in `results/` and on the live-demo viewer; the patterns described below are stable across reasonable parameter choices.

## Static vs patrol (priority-weighted demo)

- **Static** strategies hold near-perfect persistence over the cells they cover, but their weighted coverage caps out at the union of the loiter footprints.
- **Patrol** strategies trade tighter revisit behavior for substantially higher cumulative weighted coverage; the gap widens as sensor radius grows.
- **Sensor footprint** drives more marginal weighted coverage than fleet size in this setup. Doubling the sensor radius beats adding two more drones in most configurations.
- **Diminishing returns** show up clearly at higher resource levels and are made visible by the redundancy ratio.

## Dynamic policy comparison (heterogeneous fleet, dynamic tasks)

- **Static** keeps perfect persistence over the loiter cells but underserves dynamic tasks the moment demand shifts away from those cells.
- **Random patrol** broadens reach, but it is undisciplined about response: tasks are eventually observed but mean response time is high.
- **`greedy_patrol`** improves response and task service materially over random patrol because it explicitly assigns drones to the highest-utility candidate every step.
- **`priority_patrol`** adds target commitment and platform-aware fit (scouts chase tasks; sentinels anchor priority zones). It usually wins on the composite mission-fit score and on task completion, while staying competitive on weighted coverage.

The exact ordering can shift with the weight vector inside `mission_fit_weights`; that is intentional. The point of the comparison is to make the tradeoff explicit, not to declare a single winning policy.

## Persistence and revisit behavior

- Persistence was evaluated using revisit gaps between consecutive observations of the same cell.
- Static deployments push the mean and 90th-percentile revisit gap close to one timestep on the cells they hold.
- Patrol-based policies have longer revisit gaps but cover far more cells, so per-cell persistence loses some of its meaning.
- Restricting the persistence metric to *priority* cells gives a fairer cross-policy comparison, which is why `pct_priority_revisits_within_threshold` is one of the headline metrics on the live demo.

## Cost and utilization

- Under the baseline endurance assumptions, fleet utilization stays at or near 100% across every configuration. That confirms the observed tradeoffs are policy-driven, not availability-driven.
- Total operational cost scales linearly with fleet size and is independent of strategy.
- Coverage efficiency (`weighted coverage / cost`) is therefore a reasonable, simple way to compare strategies that happen to use different fleet sizes.

## Operational takeaways

- Static deployments suit missions that are dominated by holding a small, stable set of high-value cells.
- Patrol-based policies suit missions that need broad situational awareness or that face shifting demand.
- The choice between greedy and task-aware planning depends on how much you value committing to a target vs reacting to the current best candidate; the harness lets you tune that explicitly.
- Sensor capability improvements often outperform fleet expansion at fixed budget — a useful observation when planning future procurements.

## Limitations and next steps

- The current sensor model is binary; a probabilistic detection model would change which policy looks best in dense scenarios.
- Patrol behavior is random walk; structured sweeps and lawnmower patterns are an obvious next baseline.
- Adversary action and platform attrition are not modeled; adding them would change the value of redundancy.
- The next strong layer is an optimization-backed router or a learned policy plugged into the same scoring harness, with the same outputs.
