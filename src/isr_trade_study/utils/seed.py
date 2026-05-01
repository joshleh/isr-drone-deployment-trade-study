from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Build a numpy random Generator from an integer seed."""
    return np.random.default_rng(seed)
