from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np


@dataclass
class RunMetrics:
    """Per-run summary metrics emitted by `run_simulation`."""

    coverage_over_time: np.ndarray
    avg_coverage: float
    final_coverage: float

    weighted_coverage_over_time: np.ndarray
    avg_weighted_coverage: float
    final_weighted_coverage: float
    priority_cell_coverage: float

    revisit_gap_mean: float
    revisit_gap_p90: float
    pct_revisits_within_threshold: float
    priority_revisit_gap_mean: float
    priority_revisit_gap_p90: float
    pct_priority_revisits_within_threshold: float

    task_service_over_time: np.ndarray
    avg_task_service_rate: float
    task_completion_rate: float
    mean_task_response_time: float
    p90_task_response_time: float
    pct_tasks_responded_within_threshold: float

    total_cost: float
    utilization: float
    redundancy_ratio: float
    coverage_efficiency: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_coverage": float(self.avg_coverage),
            "final_coverage": float(self.final_coverage),
            "avg_weighted_coverage": float(self.avg_weighted_coverage),
            "final_weighted_coverage": float(self.final_weighted_coverage),
            "priority_cell_coverage": float(self.priority_cell_coverage),
            "revisit_gap_mean": float(self.revisit_gap_mean),
            "revisit_gap_p90": float(self.revisit_gap_p90),
            "pct_revisits_within_threshold": float(self.pct_revisits_within_threshold),
            "priority_revisit_gap_mean": float(self.priority_revisit_gap_mean),
            "priority_revisit_gap_p90": float(self.priority_revisit_gap_p90),
            "pct_priority_revisits_within_threshold": float(self.pct_priority_revisits_within_threshold),
            "avg_task_service_rate": float(self.avg_task_service_rate),
            "task_completion_rate": float(self.task_completion_rate),
            "mean_task_response_time": float(self.mean_task_response_time),
            "p90_task_response_time": float(self.p90_task_response_time),
            "pct_tasks_responded_within_threshold": float(self.pct_tasks_responded_within_threshold),
            "total_cost": float(self.total_cost),
            "utilization": float(self.utilization),
            "redundancy_ratio": float(self.redundancy_ratio),
            "coverage_efficiency": float(self.coverage_efficiency),
        }


def summarize_revisit_gaps(gaps: np.ndarray, threshold_steps: int) -> tuple[float, float, float]:
    """Mean / 90th-percentile / fraction-within-threshold for revisit gaps."""
    if gaps.size == 0:
        return float("inf"), float("inf"), 0.0

    mean_gap = float(np.mean(gaps))
    p90_gap = float(np.percentile(gaps, 90))
    pct_within = float(np.mean(gaps <= threshold_steps))
    return mean_gap, p90_gap, pct_within


def summarize_response_times(times: np.ndarray, threshold_steps: int) -> tuple[float, float, float]:
    """Mean / 90th-percentile / fraction-within-threshold for task response times."""
    if times.size == 0:
        return float("inf"), float("inf"), 0.0

    mean_time = float(np.mean(times))
    p90_time = float(np.percentile(times, 90))
    pct_within = float(np.mean(times <= threshold_steps))
    return mean_time, p90_time, pct_within
