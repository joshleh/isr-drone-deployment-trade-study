from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np

@dataclass
class RunMetrics:
    coverage_over_time: np.ndarray  # shape (T,)
    avg_coverage: float

    # NEW: persistence metrics based on revisit gaps
    revisit_gap_mean: float
    revisit_gap_p90: float
    pct_revisits_within_threshold: float

    total_cost: float
    utilization: float  # proxy: active_steps / (T * num_drones)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_coverage": float(self.avg_coverage),
            "revisit_gap_mean": float(self.revisit_gap_mean),
            "revisit_gap_p90": float(self.revisit_gap_p90),
            "pct_revisits_within_threshold": float(self.pct_revisits_within_threshold),
            "total_cost": float(self.total_cost),
            "utilization": float(self.utilization),
        }

def summarize_revisit_gaps(gaps: np.ndarray, threshold_steps: int) -> tuple[float, float, float]:
    """
    gaps: array of revisit gaps (positive integers). Each sample corresponds to a cell being revisited.
    threshold_steps: count revisits within this many steps as "good persistence".
    """
    if gaps.size == 0:
        # No revisits occurred (e.g., extremely sparse coverage)
        return float("inf"), float("inf"), 0.0

    mean_gap = float(np.mean(gaps))
    p90_gap = float(np.percentile(gaps, 90))
    pct_within = float(np.mean(gaps <= threshold_steps))

    return mean_gap, p90_gap, pct_within