# Interview Notes — ISR Drone Deployment Trade Study

Personal study notes for technical interviews about this project. Not part of
the canonical `00–07` documentation series; intentionally informal.

These are organized roughly in the order an interviewer is likely to push:
context → modeling → policies → metrics → engineering → "what would you do
next." Each section gives the short answer first, then the detail you would
escalate to if the interviewer keeps asking.

---

## 1. The 60-second pitch

> "It's a reproducible simulation harness for ISR drone deployment. You declare
> a scenario, a fleet, and a policy in YAML, run a Monte Carlo over the
> resulting grid of seeds, and get back a ranked policy comparison with
> coverage, persistence, task-response, and cost metrics — plus a static HTML
> dashboard and a live demo. Four policies are built in: static loiter, random
> patrol, greedy assignment, and a task-aware patrol that does target
> commitment and platform-aware fit. The point is not to pick a single 'best'
> policy — it's to make the tradeoff explicit and to give a harness where you
> can drop in an optimization-based or learned router later and score it the
> same way."

What this signals: domain framing, modeling discipline, KPI engineering,
data engineering, evaluation methodology, and a path to the next thing.

---

## 2. Domain framing (ISR)

- **ISR** = Intelligence, Surveillance, Reconnaissance. Persistent observation
  of an operational area to detect, track, and characterize activity.
- **Why drones matter operationally**: lower cost per flight hour, lower
  personnel risk, higher geographic flexibility than manned platforms.
- **Why a trade study matters**: fleets are finite, endurance is finite,
  sensors are finite, and the cost of "covering everything everywhere" is
  prohibitive. So the operational question isn't "do we have drones?", it's
  *"given a budget and a mission, where and how do we fly them?"*
- **Where this project sits**: it's the *evaluation and decision-support*
  layer that wraps an autonomy stack. AeroTrack and FusionTrack are the
  perception/tracking inside the drone; this project is the
  operations-analysis loop on the outside that says "given perception of
  quality X, here's how to deploy the fleet."

If asked "is this real ISR data?": no — it's a synthetic but structurally
honest scenario. The grid, priority zones, and dynamic tasks are abstracted
versions of what an analyst would model in practice (border corridor,
crossing lane, logistics hub, time-bounded surveillance spikes).

---

## 3. Problem definition — decision variables, constraints, KPIs

### Decision variables (what we sweep)

- Fleet size and fleet **composition** (homogeneous or `sentinel` + `scout`).
- Sensor radius (effective footprint).
- Deployment policy (`static`, `patrol`, `greedy_patrol`, `priority_patrol`).
- Strategy hyperparameters: turn probability, target commitment steps,
  task-priority bias, priority-zone bias, exploration bias, congestion
  penalty.

### Constraints

- Total drones available.
- Per-drone endurance (timesteps before the platform goes inactive).
- Per-drone cost-per-step.
- Operational area boundaries (2D grid).
- Mission time horizon.
- Priority zone and dynamic task definitions (from YAML).

### KPIs (and *why* each one)

| KPI | What it captures | Why it matters |
| --- | --- | --- |
| Coverage / weighted coverage | Fraction (or weight-fraction) of the area observed at least once. | Reach. |
| Priority cell coverage | Same, restricted to declared priority zones. | Did we cover what *mattered*? |
| Revisit-gap mean / **p90** / pct-within-threshold | Distribution of time between consecutive observations of the same cell. | Persistence — were observations fresh? p90 catches the worst-case, mean hides it. |
| Task service rate | Time-weighted fraction of active tasks observed during their window. | Are we *holding* eyes on the task once it appears? |
| Task completion rate | Fraction of tasks observed at least once. | Did we ever even spot it? |
| Mean / **p90 response time** | Steps from task spawn to first observation. | How fast does the fleet react? p90 is the operational worst-case. |
| Total cost, utilization | Drone-step accounting. | Resource use. |
| Redundancy ratio | Fraction of observations that re-cover already-seen cells. | Surfaces "wasted" overlap. |
| Coverage efficiency | Weighted coverage per unit cost. | Lets you compare configs that use different fleet sizes. |
| `mission_fit_score` | Configurable weighted blend of the above. | Single ranking number for the report. |

**The argument for percentiles**: ISR is risk-driven. A mean response time of
5 steps that hides a p90 of 60 steps is operationally unacceptable —
decision-makers care about the bad cases. Use p90 (or p95) alongside the
mean; never present the mean alone.

**The argument for weighted coverage over coverage**: not every cell is equal.
Border corridors, ingress lanes, and logistics hubs carry mission weight; the
policy that "covers more grid cells" but ignores the high-weight zones is the
wrong policy.

**The argument for `mission_fit_score`**: you need a single ranking number to
sort a table. But because the right weighting depends on the mission posture,
the weights live in `configs/policy_comparison_heterogeneous.yaml` and the
docs explicitly note that the ordering can shift with the weight vector.
That's a feature: the harness makes the value tradeoff *visible and editable*
instead of burying it in a constant.

---

## 4. Policies — what they do, when each wins

### `static`

- Fixed loiter points; drones hold position for the run.
- **Wins** when the mission is dominated by holding a small, stable set of
  high-value cells (a checkpoint, a fixed asset).
- **Loses** the moment demand shifts away from the loiter set — task service
  collapses.

### `patrol` (random walk)

- Each drone walks the grid with a configurable turn probability.
- **Wins** when demand is roughly uniform and the goal is cumulative weighted
  coverage.
- **Loses** on response time — random walks are undisciplined about urgency.

### `greedy_patrol`

- Each step, build a candidate set (active tasks, priority zones, unseen
  cells), score every drone × candidate pair, and assign the highest-scoring
  pair first (`mode = greedy`).
- **Wins** the response-time argument over random patrol because the
  assignment is *explicitly* utility-driven each step.
- **Loses** because it has no commitment — a drone may abandon a task it was
  approaching the moment a slightly higher-scoring task appears, which can
  thrash. That's exactly what `priority_patrol` fixes.

### `priority_patrol` (the intended default)

- Same candidate construction as greedy, plus:
  - **Target commitment**: a drone holds its target for `target_commitment_steps`
    unless the lock expires or the task ends.
  - **Platform-aware fit**: scouts (faster, smaller sensor) get bonus utility
    on tasks; sentinels (slower, larger sensor, longer endurance) get bonus
    utility on priority zones. The intuition: the right platform on the
    right job.
  - **Congestion penalty** discourages multiple drones from converging on the
    same target unless capacity allows it.
- **Wins** the composite score and task completion under shifting mission
  demand. Stays competitive on weighted coverage because sentinels still
  blanket the priority zones.

> **Common interview question**: "Why not RL?" — Because (a) the action space
> is small and the structure is interpretable, so a hand-designed planner is a
> strong, debuggable, *defensible* baseline; (b) any RL or optimization-based
> policy plugged in later gets scored on the *same* metrics, which means the
> harness is the deliverable, not the policy itself. The next step would be
> to drop in an MILP or a Q-learning agent and let the report show whether it
> beats `priority_patrol` on the same scoring weights.

---

## 5. Simulation methodology

### Monte Carlo, deterministically seeded

- Each `(strategy, fleet config)` cell runs `num_runs_per_strategy` seeds.
- Seeds are derived deterministically from `(strategy_name, grid_indices)`,
  not random — so the run is reproducible bit-for-bit. (See
  `src/isr_trade_study/utils/seed.py`.)
- The aggregation collapses seeds with a `mean` per metric per cell;
  this is what lands in `*_results_agg.csv`.

If asked **"why Monte Carlo at all?"**: the patrol policies are stochastic
(turn probability, exploration sampling, candidate sub-sampling). A single
seed doesn't tell you whether a result is the policy or the luck. The mean
across `N` seeds gives you a defensible point estimate per cell; the spread
across seeds is available in the raw CSVs if you want intervals.

### Discrete-time grid model

- Time and space are both discretized. One observation pass per drone per
  step, integer coordinates on a `width × height` grid.
- **Trade-off**: trivial to implement and reason about, but the binary
  sensor model and integer movement under-represent the real system.
- **Defense of the choice**: this is an analytical harness, not a flight
  simulator. The grid model preserves the structure that matters (coverage,
  revisit, response, cost) without dragging in geometry, kinematics, or
  weather. The harness deliberately keeps the inner loop in NumPy so a future
  C++ kernel could replace it without changing the report layer.

### Binary sensor model and what it misses

- Inside the disk: cell is observed.
- Outside: cell is not.
- Misses: range-dependent SNR, look-angle, weather, occlusion, false
  positives. Documented in `02_modeling_assumptions.md` and explicitly
  flagged as a near-term extension. The right answer in an interview is to
  acknowledge the limitation and explain how the harness would extend (swap
  the disk function for a probability-of-detection function; metrics already
  accept floats).

---

## 6. Engineering / data choices

### Why DuckDB + Parquet + CSV all at once

- **CSV** is the lowest-common-denominator: opens in Excel, in pandas, in
  any notebook. Required for analyst hand-off.
- **Parquet** is columnar and typed: 5–20× smaller, faster scans for BI and
  notebooks. Required if anyone downstream cares about performance.
- **DuckDB** is the embedded analytical query engine: lets a non-engineer
  open `analysis.duckdb` and run SQL across runs without spinning up a
  warehouse. Same data, three access patterns.

> The point in an interview: each run has the *shape* of a small analytics
> warehouse, not a folder of CSVs. That makes downstream consumption (BI,
> sweep aggregation, hand-off) the same shape as a real analytics pipeline,
> just locally and reproducibly.

### Configs as code

- Every scenario, sweep, and policy comparison is a YAML file under
  `configs/`. Run identity = config + seed. That's reproducibility without
  any infrastructure.

### Repo layout (`src/` style)

- `src/isr_trade_study/` keeps the package out of the repo root. Editable
  install (`pip install -e .`) is what tests and scripts use; this prevents
  the classic "import works locally but fails for everyone else" problem.

### CI / Pages

- `.github/workflows/pages.yml` runs unit tests, regenerates the demo and
  policy comparison artifacts, rebuilds the live demo, and deploys it to
  GitHub Pages on every push to `main`.
- `actions/configure-pages` with `enablement: true` provisions Pages
  on the first run so a fresh fork "just works."

---

## 7. Trade-study methodology (the operations-analysis lens)

- **Factor sweep**, not optimization. The harness sweeps fleet size,
  sensor radius, and strategy across a grid; you read the surface and
  pick the operating point. This is intentional — it gives the
  decision-maker the *shape* of the tradeoff, not just the optimum point
  (which is fragile to weight changes).
- **Sensitivity to weights** is documented in `04_results_summary.md`:
  the ordering of policies can shift if `mission_fit_weights` shifts. That's
  not a bug; it's the analyst's job to expose it.
- **Coverage vs persistence vs cost vs response** is a four-way tradeoff.
  The headline takeaway is that you can't dominate all four with a fixed
  budget — `static` wins persistence, `patrol` wins reach, `greedy_patrol`
  wins response, `priority_patrol` wins the composite. The harness exists
  to make this concrete.
- **Sensor capability vs fleet expansion**: under the baseline assumptions,
  doubling sensor radius beats adding two more drones in most configs.
  That's a concrete, defensible operations-analysis observation that maps
  directly to procurement decisions.

---

## 8. Likely interview questions and short answers

| Question | One-line answer |
| --- | --- |
| Why a 2D grid instead of continuous geometry? | Analytical harness, not a flight sim. The grid preserves the tradeoffs that drive policy choice without dragging in kinematics. Documented limitation. |
| Why not RL? | Action space is small and the structure is interpretable. A hand-designed planner is a defensible baseline; the harness is built so any RL or optimization-based policy slots in and gets scored on the same metrics. |
| How would you scale this to a real operational area? | Replace the binary disk with a probability-of-detection function, replace integer movement with a continuous kinematic step, swap the inner loop to a vectorized or compiled kernel. The metric and report layer stays the same. |
| How would you validate against real data? | The metrics layer already consumes timeseries; you'd need ground-truth coverage maps and task logs from a real operational run. The same `RunMetrics` would compute on real data. The harder part is permission, not code. |
| Why p90 and not just mean? | ISR cares about the worst case. A mean response time that hides a long p90 is operationally unacceptable; a decision-maker can't stake reputation on an average. |
| Why DuckDB and Parquet on top of CSV? | Three access patterns: CSV for hand-off, Parquet for performance, DuckDB for ad-hoc SQL across runs. Same data; lets each consumer pick their tool. |
| What's the next thing you'd build? | Either (a) plug in an MILP-based router and let the report show whether it beats `priority_patrol`, or (b) replace the binary sensor with a probabilistic detection model and re-run the comparison. Both extend the harness without changing the report layer. |
| How does this differ from AeroTrack/FusionTrack? | AeroTrack/FusionTrack are the perception and tracking *inside* the drone (detection, MOT, sensor fusion). This project is the operations-analysis loop *around* the fleet — given perception of some quality, where and how do you fly. They are complementary, not redundant. |
| What's the biggest weakness of the project? | Honest answer: the planner is hand-designed and not benchmarked against a true optimization solver. That's the deliberate next step — drop an MILP or RL agent into the same harness and compare. |

---

## 9. Things to know cold (no looking them up)

- The four policies and their one-line "when they win."
- The metric list and **why p90** matters operationally.
- "Why DuckDB + Parquet + CSV" in three lines.
- Why this is an analytical harness, not a flight simulator (and what
  that lets you defer).
- The two next-step extensions (probabilistic sensor; optimization-based
  router) and why they slot in without rewriting the report layer.
- The sister-project framing: AeroTrack / FusionTrack are perception
  and tracking; this is the ops-analysis loop around them.

---

## 10. Things to *not* over-claim

- Not a flight simulator. No kinematics, no geometry, no weather.
- Not adversarial — there is no opposing force, no attrition, no jamming.
- The patrol policies are random-walk + bias terms, not lawnmower or
  optimal sweep.
- `mission_fit_score` is a ranking aid, not a normative metric — its
  weights live in YAML and are explicitly editable.
- The scenarios are structurally honest but synthetic. They are not
  derived from any real ISR mission.

If an interviewer pushes on any of these, the right answer is "yes,
that's deliberately deferred — here's how the harness would absorb it,"
not "yes but actually we kind of model that." Honest scoping is the
strongest operations-analysis signal.
