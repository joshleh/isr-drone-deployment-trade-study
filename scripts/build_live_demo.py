from __future__ import annotations

import argparse
from pathlib import Path

from _bootstrap import bootstrap_src_path

repo_root = bootstrap_src_path()

from anduril_ops.dashboard.live_demo import build_live_demo_site


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local live-demo site from the latest generated artifacts.")
    parser.add_argument(
        "--site",
        type=str,
        default="docs/live_demo/index.html",
        help="Path to the generated live-demo HTML file",
    )
    args = parser.parse_args()

    site_path = (repo_root / args.site).resolve()
    build_live_demo_site(repo_root=repo_root, site_path=site_path)
    print(f"Saved live demo to: {site_path}")


if __name__ == "__main__":
    main()
