from __future__ import annotations

import unittest

from anduril_ops.sim.monte_carlo import run_simulation
from anduril_ops.sim.placements import resolve_static_points
from anduril_ops.sim.scenario import (
    DynamicTask,
    FleetSpec,
    GridSpec,
    PlatformSpec,
    Scenario,
    StrategySpec,
    TimeSpec,
)
from anduril_ops.utils.seed import make_rng


class SimulationTests(unittest.TestCase):
    def test_same_timestep_overlap_does_not_create_zero_gap(self) -> None:
        scenario = Scenario(
            name="overlap_gap_check",
            grid=GridSpec(width=9, height=9),
            time=TimeSpec(steps=3),
            fleet=FleetSpec(
                num_drones=2,
                sensor_radius=0,
                endurance_steps=3,
                cost_per_step=1.0,
            ),
        )
        strategy = StrategySpec(type="static", static_points=[(4, 4), (4, 4)])

        metrics = run_simulation(scenario, strategy, make_rng(7))

        self.assertEqual(metrics.revisit_gap_mean, 1.0)
        self.assertEqual(metrics.revisit_gap_p90, 1.0)

    def test_static_point_resolution_adds_unique_positions(self) -> None:
        points = resolve_static_points(
            width=30,
            height=20,
            num_drones=6,
            explicit_points=[(2, 2), (27, 17)],
            point_mode="explicit",
        )

        self.assertEqual(len(points), 6)
        self.assertEqual(len(set(points)), 6)

    def test_heterogeneous_fleet_costs_accumulate_correctly(self) -> None:
        scenario = Scenario(
            name="heterogeneous_cost_check",
            grid=GridSpec(width=10, height=10),
            time=TimeSpec(steps=2),
            fleet=FleetSpec(
                num_drones=0,
                sensor_radius=0,
                endurance_steps=0,
                cost_per_step=0.0,
                platforms=(
                    PlatformSpec(name="sentinel", count=1, sensor_radius=0, endurance_steps=2, cost_per_step=2.0),
                    PlatformSpec(name="scout", count=2, sensor_radius=0, endurance_steps=2, cost_per_step=1.0),
                ),
            ),
        )
        strategy = StrategySpec(type="static", static_points=[(1, 1), (5, 5), (8, 8)])

        metrics = run_simulation(scenario, strategy, make_rng(3))

        self.assertEqual(scenario.fleet.total_drones, 3)
        self.assertAlmostEqual(metrics.total_cost, 8.0)
        self.assertAlmostEqual(metrics.utilization, 1.0)

    def test_dynamic_task_metrics_capture_immediate_service(self) -> None:
        scenario = Scenario(
            name="task_service_check",
            grid=GridSpec(width=7, height=7),
            time=TimeSpec(steps=3),
            fleet=FleetSpec(
                num_drones=1,
                sensor_radius=0,
                endurance_steps=3,
                cost_per_step=1.0,
            ),
            dynamic_tasks=(
                DynamicTask(
                    name="watch_cell",
                    start_step=0,
                    end_step=3,
                    x_min=3,
                    x_max=3,
                    y_min=3,
                    y_max=3,
                    priority=2.0,
                ),
            ),
        )
        strategy = StrategySpec(type="static", static_points=[(3, 3)])

        metrics = run_simulation(scenario, strategy, make_rng(4))

        self.assertAlmostEqual(metrics.avg_task_service_rate, 1.0)
        self.assertAlmostEqual(metrics.task_completion_rate, 1.0)
        self.assertAlmostEqual(metrics.mean_task_response_time, 0.0)

    def test_priority_patrol_responds_to_task(self) -> None:
        scenario = Scenario(
            name="priority_patrol_check",
            grid=GridSpec(width=12, height=12),
            time=TimeSpec(steps=18),
            fleet=FleetSpec(
                num_drones=1,
                sensor_radius=0,
                endurance_steps=18,
                cost_per_step=1.0,
            ),
            dynamic_tasks=(
                DynamicTask(
                    name="late_spike",
                    start_step=1,
                    end_step=18,
                    x_min=10,
                    x_max=10,
                    y_min=10,
                    y_max=10,
                    priority=5.0,
                ),
            ),
        )
        strategy = StrategySpec(
            type="priority_patrol",
            patrol_step_size=1,
            patrol_turn_prob=0.0,
            task_priority_bias=3.0,
        )

        metrics = run_simulation(scenario, strategy, make_rng(9))

        self.assertGreater(metrics.task_completion_rate, 0.0)
        self.assertLess(metrics.mean_task_response_time, float("inf"))

    def test_greedy_patrol_responds_to_task(self) -> None:
        scenario = Scenario(
            name="greedy_patrol_check",
            grid=GridSpec(width=12, height=12),
            time=TimeSpec(steps=18),
            fleet=FleetSpec(
                num_drones=1,
                sensor_radius=0,
                endurance_steps=18,
                cost_per_step=1.0,
            ),
            dynamic_tasks=(
                DynamicTask(
                    name="late_spike",
                    start_step=1,
                    end_step=18,
                    x_min=10,
                    x_max=10,
                    y_min=10,
                    y_max=10,
                    priority=5.0,
                ),
            ),
        )
        strategy = StrategySpec(
            type="greedy_patrol",
            patrol_step_size=1,
            patrol_turn_prob=0.0,
            task_priority_bias=3.0,
        )

        metrics = run_simulation(scenario, strategy, make_rng(9))

        self.assertGreater(metrics.task_completion_rate, 0.0)
        self.assertLess(metrics.mean_task_response_time, float("inf"))


if __name__ == "__main__":
    unittest.main()
