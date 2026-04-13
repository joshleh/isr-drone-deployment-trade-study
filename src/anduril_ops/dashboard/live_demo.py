from __future__ import annotations

import csv
import html
import os
from pathlib import Path
from typing import Any


def _latest(pattern_root: Path, pattern: str) -> Path | None:
    matches = sorted(pattern_root.glob(pattern))
    if not matches:
        return None
    return matches[-1]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def _as_int(row: dict[str, str], key: str) -> int:
    return int(round(_as_float(row, key)))


def _rel(base: Path, target: Path | None) -> str | None:
    if target is None:
        return None
    return os.path.relpath(target, start=base)


def _fmt(value: float, digits: int = 3) -> str:
    if value != value:
        return "n/a"
    if value == float("inf"):
        return "inf"
    return f"{value:.{digits}f}"


def _build_demo_snapshot(results_root: Path, live_demo_root: Path) -> dict[str, Any]:
    latest_demo = _latest(results_root, "demo/demo_priority_trade_study_*/demo_results_agg.csv")
    if latest_demo is None:
        return {
            "best_static": None,
            "best_patrol": None,
            "top_configs": [],
            "report_link": None,
            "run_label": "No demo run found yet",
        }

    rows = _read_rows(latest_demo)
    rows.sort(key=lambda row: _as_float(row, "mission_fit_score"), reverse=True)
    static_rows = [row for row in rows if row.get("strategy") == "static"]
    patrol_rows = [row for row in rows if row.get("strategy") == "patrol"]
    demo_dir = latest_demo.parent

    return {
        "best_static": static_rows[0] if static_rows else None,
        "best_patrol": patrol_rows[0] if patrol_rows else None,
        "top_configs": rows[:4],
        "report_link": _rel(live_demo_root, demo_dir / "demo_report.md"),
        "run_label": demo_dir.name,
    }


def _build_policy_snapshot(results_root: Path, live_demo_root: Path) -> dict[str, Any]:
    latest_policy = _latest(results_root, "policy/policy_comparison_dynamic_heterogeneous_*/policy_results_agg.csv")
    if latest_policy is None:
        return {
            "best": None,
            "ranking": [],
            "dashboard_link": None,
            "report_link": None,
            "response_gain_vs_static": None,
            "run_label": "No policy comparison found yet",
        }

    rows = _read_rows(latest_policy)
    rows.sort(key=lambda row: _as_float(row, "mission_fit_score"), reverse=True)
    policy_dir = latest_policy.parent
    best = rows[0] if rows else None
    static_row = next((row for row in rows if row.get("strategy") == "static"), None)
    completion_lift = None
    weighted_lift = None
    if best is not None and static_row is not None:
        static_completion = _as_float(static_row, "task_completion_rate")
        best_completion = _as_float(best, "task_completion_rate")
        static_weighted_cov = _as_float(static_row, "final_weighted_coverage")
        best_weighted_cov = _as_float(best, "final_weighted_coverage")
        if static_completion == static_completion and best_completion == best_completion:
            completion_lift = best_completion - static_completion
        if static_weighted_cov == static_weighted_cov and best_weighted_cov == best_weighted_cov:
            weighted_lift = best_weighted_cov - static_weighted_cov

    return {
        "best": best,
        "ranking": rows,
        "dashboard_link": _rel(live_demo_root, policy_dir / "dashboard.html"),
        "report_link": _rel(live_demo_root, policy_dir / "policy_report.md"),
        "task_completion_lift_vs_static": completion_lift,
        "weighted_coverage_lift_vs_static": weighted_lift,
        "run_label": policy_dir.name,
    }


def _summary_lines(demo: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    best_policy = policy.get("best")
    if best_policy is not None:
        lines.append(
            f"Best dynamic policy: {best_policy['strategy']} at mission-fit {_fmt(_as_float(best_policy, 'mission_fit_score'))}."
        )

    completion_lift = policy.get("task_completion_lift_vs_static")
    if completion_lift is not None:
        lines.append(f"Task-completion lift vs static: {_fmt(float(completion_lift), digits=3)}.")

    weighted_lift = policy.get("weighted_coverage_lift_vs_static")
    if weighted_lift is not None:
        lines.append(f"Weighted-coverage lift vs static: {_fmt(float(weighted_lift), digits=3)}.")

    best_static = demo.get("best_static")
    best_patrol = demo.get("best_patrol")
    if best_static is not None and best_patrol is not None:
        lines.append(
            "Priority demo contrast: "
            f"static weighted coverage {_fmt(_as_float(best_static, 'final_weighted_coverage'))} vs "
            f"patrol {_fmt(_as_float(best_patrol, 'final_weighted_coverage'))}."
        )

    return lines


def _table_html(headers: list[str], rows: list[list[str]], highlight_first: bool = False) -> str:
    if not rows:
        return "<p class='empty'>Run the demo workflows to populate this section.</p>"

    thead = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_rows: list[str] = []
    for idx, row in enumerate(rows):
        cls = " class='is-best'" if highlight_first and idx == 0 else ""
        tds = "".join(f"<td>{cell}</td>" for cell in row)
        body_rows.append(f"<tr{cls}>{tds}</tr>")
    tbody = "".join(body_rows)
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def build_live_demo_site(
    repo_root: Path,
    site_path: Path,
) -> None:
    results_root = repo_root / "results"
    docs_root = repo_root / "docs"
    figures_root = docs_root / "figures"
    live_demo_root = site_path.parent

    demo = _build_demo_snapshot(results_root, live_demo_root)
    policy = _build_policy_snapshot(results_root, live_demo_root)

    stable_figure_paths = [
        figures_root / "demo_priority_priority_vs_global.png",
        figures_root / "demo_priority_best_timeseries.png",
        figures_root / "demo_priority_redundancy_vs_coverage.png",
        figures_root / "policy_dynamic_strategy_bars.png",
        figures_root / "policy_dynamic_task_service_vs_response.png",
        figures_root / "policy_dynamic_timeseries.png",
    ]

    figure_sections = []
    for path in stable_figure_paths:
        rel = _rel(live_demo_root, path)
        if rel is None:
            continue
        caption = path.stem.replace("_", " ")
        figure_sections.append(
            "<figure class='evidence'>"
            f"<img src='{html.escape(rel)}' alt='{html.escape(caption)}'>"
            f"<figcaption>{html.escape(caption)}</figcaption>"
            "</figure>"
        )

    demo_rows: list[list[str]] = []
    for row in demo["top_configs"]:
        demo_rows.append(
            [
                html.escape(str(row["strategy"])),
                str(_as_int(row, "num_drones")),
                str(_as_int(row, "sensor_radius")),
                _fmt(_as_float(row, "mission_fit_score")),
                _fmt(_as_float(row, "final_weighted_coverage")),
                _fmt(_as_float(row, "pct_priority_revisits_within_threshold")),
            ]
        )

    policy_rows: list[list[str]] = []
    for row in policy["ranking"]:
        policy_rows.append(
            [
                html.escape(str(row["strategy"])),
                _fmt(_as_float(row, "mission_fit_score")),
                _fmt(_as_float(row, "final_weighted_coverage")),
                _fmt(_as_float(row, "avg_task_service_rate")),
                _fmt(_as_float(row, "task_completion_rate")),
                _fmt(_as_float(row, "mean_task_response_time"), digits=2),
            ]
        )

    demo_table = _table_html(
        headers=["Strategy", "Drones", "Radius", "Mission Fit", "Weighted Cov", "Priority Persist"],
        rows=demo_rows,
    )
    policy_table = _table_html(
        headers=["Strategy", "Mission Fit", "Weighted Cov", "Task Service", "Completion", "Mean Response"],
        rows=policy_rows,
        highlight_first=True,
    )

    policy_dashboard_link = policy.get("dashboard_link")
    policy_report_link = policy.get("report_link")
    demo_report_link = demo.get("report_link")

    action_links = []
    if policy_dashboard_link is not None:
        action_links.append(
            f"<a class='action action-primary' href='{html.escape(policy_dashboard_link)}'>Open policy dashboard</a>"
        )
    if policy_report_link is not None:
        action_links.append(
            f"<a class='action' href='{html.escape(policy_report_link)}'>Open policy brief</a>"
        )
    if demo_report_link is not None:
        action_links.append(
            f"<a class='action' href='{html.escape(demo_report_link)}'>Open demo brief</a>"
        )

    summary_items = "".join(
        f"<li>{html.escape(line)}</li>"
        for line in _summary_lines(demo, policy)
    )

    html_out = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ISR Demo Viewer</title>
  <style>
    :root {{
      --bg: #f1ece2;
      --bg-deep: #13242d;
      --panel: rgba(255, 249, 240, 0.9);
      --ink: #11222b;
      --muted: #55646b;
      --line: rgba(17, 34, 43, 0.14);
      --accent: #b85a11;
      --accent-soft: rgba(184, 90, 17, 0.12);
      --shadow: 0 18px 50px rgba(17, 34, 43, 0.12);
    }}
    * {{
      box-sizing: border-box;
    }}
    html {{
      scroll-behavior: smooth;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(245, 197, 133, 0.22), transparent 38%),
        linear-gradient(180deg, #f7f2e8 0%, var(--bg) 44%, #efe7da 100%);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(17, 34, 43, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(17, 34, 43, 0.035) 1px, transparent 1px);
      background-size: 56px 56px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.55), transparent 80%);
    }}
    .hero {{
      position: relative;
      min-height: 100svh;
      padding: 28px 24px 48px;
      overflow: hidden;
      background:
        radial-gradient(circle at right top, rgba(255, 196, 111, 0.35), transparent 28%),
        linear-gradient(135deg, rgba(10, 23, 31, 0.96), rgba(25, 45, 56, 0.88));
      color: #f5efe5;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.04) 35%, transparent 62%),
        radial-gradient(circle at 78% 34%, rgba(255, 219, 165, 0.22), transparent 24%);
      mix-blend-mode: screen;
    }}
    .hero-inner {{
      position: relative;
      z-index: 1;
      max-width: 1220px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
      gap: 48px;
      align-items: end;
      min-height: calc(100svh - 76px);
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.22em;
      font-size: 0.78rem;
      color: rgba(245, 239, 229, 0.72);
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      font-weight: 600;
      line-height: 0.96;
      margin: 0;
    }}
    h1 {{
      font-size: clamp(3.2rem, 7vw, 6.4rem);
      max-width: 7ch;
      letter-spacing: -0.04em;
    }}
    .hero-copy p {{
      max-width: 40rem;
      margin: 20px 0 0;
      font-size: 1.04rem;
      line-height: 1.6;
      color: rgba(245, 239, 229, 0.8);
    }}
    .hero-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 28px;
    }}
    .action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 18px;
      border-radius: 999px;
      border: 1px solid rgba(245, 239, 229, 0.22);
      color: #f5efe5;
      text-decoration: none;
      transition: transform 220ms ease, background 220ms ease, border-color 220ms ease;
      backdrop-filter: blur(8px);
    }}
    .action:hover {{
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.06);
      border-color: rgba(245, 239, 229, 0.42);
    }}
    .action-primary {{
      background: linear-gradient(135deg, #f1a04d, #b85a11);
      border-color: transparent;
      color: #1a130f;
      font-weight: 700;
    }}
    .hero-board {{
      padding: 24px 0 0;
      border-top: 1px solid rgba(245, 239, 229, 0.16);
      align-self: stretch;
      display: grid;
      align-content: end;
    }}
    .board-label {{
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 0.72rem;
      color: rgba(245, 239, 229, 0.62);
      margin-bottom: 12px;
    }}
    .board-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 12px;
    }}
    .board-list li {{
      padding: 14px 0;
      border-bottom: 1px solid rgba(245, 239, 229, 0.12);
      font-size: 0.96rem;
      line-height: 1.45;
    }}
    main {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 28px 24px 80px;
    }}
    .section {{
      opacity: 0;
      transform: translateY(26px);
      transition: opacity 520ms ease, transform 520ms ease;
      margin-top: 42px;
    }}
    .section.is-visible {{
      opacity: 1;
      transform: translateY(0);
    }}
    .section-head {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
      gap: 24px;
      align-items: start;
      margin-bottom: 22px;
    }}
    .section-head p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      max-width: 40rem;
    }}
    h2 {{
      font-size: clamp(2rem, 4vw, 3rem);
      letter-spacing: -0.03em;
    }}
    .ops-rail {{
      display: grid;
      gap: 14px;
      padding-top: 8px;
    }}
    .ops-rail div {{
      padding: 14px 0;
      border-top: 1px solid var(--line);
      color: var(--muted);
      line-height: 1.5;
    }}
    .tables {{
      display: grid;
      grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
      gap: 20px;
    }}
    .table-panel, .command-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 22px 22px 18px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }}
    .table-panel h3, .command-panel h3 {{
      font-size: 1.35rem;
      margin-bottom: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 12px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    tr.is-best td:first-child {{
      color: var(--accent);
      font-weight: 700;
    }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }}
    .evidence {{
      margin: 0;
      background: rgba(255, 251, 245, 0.9);
      border: 1px solid var(--line);
      border-radius: 28px;
      overflow: hidden;
      box-shadow: var(--shadow);
      transition: transform 260ms ease, box-shadow 260ms ease;
    }}
    .evidence:hover {{
      transform: translateY(-4px);
      box-shadow: 0 24px 52px rgba(17, 34, 43, 0.16);
    }}
    .evidence img {{
      display: block;
      width: 100%;
      height: auto;
      background: #fff;
    }}
    .evidence figcaption {{
      padding: 14px 16px 18px;
      color: var(--muted);
      text-transform: capitalize;
    }}
    .command-panel pre {{
      margin: 0;
      padding: 18px 20px;
      overflow-x: auto;
      border-radius: 20px;
      background: #111b21;
      color: #f5efe5;
      line-height: 1.6;
    }}
    .command-panel code {{
      font-family: "SFMono-Regular", "Consolas", monospace;
      font-size: 0.94rem;
    }}
    .artifact-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }}
    .artifact-links a {{
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px solid rgba(17, 34, 43, 0.18);
      padding-bottom: 2px;
    }}
    .artifact-links a:hover {{
      color: var(--accent);
      border-bottom-color: rgba(184, 90, 17, 0.5);
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }}
    .meta .table-panel {{
      min-height: 100%;
    }}
    .small {{
      color: var(--muted);
      font-size: 0.94rem;
      line-height: 1.6;
    }}
    .run-tag {{
      display: inline-flex;
      margin-top: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.86rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .empty {{
      color: var(--muted);
      line-height: 1.6;
    }}
    @media (max-width: 980px) {{
      .hero-inner,
      .section-head,
      .tables,
      .meta {{
        grid-template-columns: 1fr;
      }}
      .gallery {{
        grid-template-columns: 1fr;
      }}
      .hero {{
        min-height: auto;
        padding-bottom: 36px;
      }}
      .hero-inner {{
        min-height: auto;
      }}
    }}
  </style>
</head>
<body>
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-copy">
        <div class="eyebrow">ISR Drone Deployment Trade Study</div>
        <h1>Live demo for the operations-side story.</h1>
        <p>This viewer turns the repo into a showable artifact: a mission brief, the strongest comparison outputs, and direct links into the local dashboard and analyst writeups.</p>
        <div class="hero-actions">
          {"".join(action_links)}
        </div>
      </div>
      <aside class="hero-board">
        <div class="board-label">Why this reads differently than Aerotrack</div>
        <ul class="board-list">
          <li>Simulation and trade-study first, not an ML product shell.</li>
          <li>Dynamic tasking, heterogeneous fleets, and policy evaluation instead of API-driven inference.</li>
          <li>Closer to operations analysis, data science, autonomy evaluation, and data engineering workstreams.</li>
          <li>Built around explainable mission tradeoffs you can walk through in an interview.</li>
        </ul>
      </aside>
    </div>
  </section>

  <main>
    <section class="section">
      <div class="section-head">
        <div>
          <h2>Mission snapshot</h2>
        </div>
        <p>The strongest current story is not that the heuristic always wins. It is that the project now supports honest policy comparison under changing demand, with outputs that are stable enough to review like analyst material.</p>
      </div>
      <div class="meta">
        <article class="table-panel">
          <h3>Current readout</h3>
          <ul class="board-list">{summary_items}</ul>
        </article>
        <article class="table-panel">
          <h3>Latest local runs</h3>
          <p class="small">Priority demo: <span class="run-tag">{html.escape(str(demo['run_label']))}</span></p>
          <p class="small">Policy comparison: <span class="run-tag">{html.escape(str(policy['run_label']))}</span></p>
          <p class="small">These links point at your local generated artifacts, so the page stays tied to the freshest run instead of a hand-written summary.</p>
        </article>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Two demo layers</h2>
        </div>
        <div class="ops-rail">
          <div>The priority-weighted trade study shows static versus patrol tradeoffs without the flat-graph problem from the original blank-grid setup.</div>
          <div>The dynamic policy workflow adds tasks, fleet heterogeneity, DuckDB persistence, and a real policy ranking surface.</div>
        </div>
      </div>
      <div class="tables">
        <article class="table-panel">
          <h3>Priority-weighted trade study</h3>
          {demo_table}
        </article>
        <article class="table-panel">
          <h3>Dynamic policy ranking</h3>
          {policy_table}
        </article>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Evidence wall</h2>
        </div>
        <p>These are the stable figures committed in the repo, so the demo is viewable without digging through timestamped result folders.</p>
      </div>
      <div class="gallery">
        {"".join(figure_sections)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Open it locally</h2>
        </div>
        <p>This is intended to be a lightweight local showcase. Build or refresh the site, then serve the repo root and visit the live-demo page in your browser.</p>
      </div>
      <div class="tables">
        <article class="command-panel">
          <h3>Commands</h3>
          <pre><code>make live-demo
make serve-demo

# then open
http://127.0.0.1:8010/docs/live_demo/index.html</code></pre>
        </article>
        <article class="command-panel">
          <h3>Role alignment</h3>
          <div class="artifact-links">
            <a href="../06_anduril_role_alignment.md">Anduril role framing</a>
            <a href="../05_demo_walkthrough.md">Demo walkthrough</a>
            <a href="../07_dynamic_policy_comparison.md">Dynamic policy writeup</a>
            <a href="../04_results_summary.md">Results summary</a>
          </div>
          <p class="small">Best fit: operations analyst, data scientist, data engineer, or autonomy-evaluation-adjacent work. Least natural fit: pure MLE, unless you frame this as the offline evaluation harness for routing or autonomy policies.</p>
        </article>
      </div>
    </section>
  </main>

  <script>
    const observer = new IntersectionObserver((entries) => {{
      for (const entry of entries) {{
        if (entry.isIntersecting) {{
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }}
      }}
    }}, {{ threshold: 0.18 }});
    document.querySelectorAll('.section').forEach((section) => observer.observe(section));
  </script>
</body>
</html>
"""

    site_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.write_text(html_out, encoding="utf-8")
