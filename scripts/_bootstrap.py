from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_src_path() -> Path:
    """Make `src/` importable for direct script execution from a fresh clone."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    return repo_root
