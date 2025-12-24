from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np

@dataclass
class RunMetrics:
    coverage_over_time: np.ndarray  # shape (T,)
    avg_coverage: float
    revisit_time_mean: float
    revisit_time_p90: float
    total_cost: float
    utilization: float  # proxy: active_steps / (T * num_drones)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_coverage": float(self.avg_coverage),
            "revisit_time_mean": float(self.revisit_time_mean),
            "revisit_time_p90": float(self.revisit_time_p90),
            "total_cost": float(self.total_cost),
            "utilization": float(self.utilization),
        }

def compute_revisit_stats(last_seen: np.ndarray, T: int) -> tuple[float, float]:
    """
    last_seen: int array (H,W) of last time index each cell was observed; -1 if never.
    We'll compute revisit times using gaps for cells that were ever seen.
    Baseline: approximate by treating 'time since last seen at end' as one sample.
    """
    seen_mask = last_seen >= 0
    if not np.any(seen_mask):
        return float("inf"), float("inf")

    # time since last seen at end of simulation
    gaps = (T - 1) - last_seen[seen_mask]
    return float(np.mean(gaps)), float(np.percentile(gaps, 90))
