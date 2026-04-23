from __future__ import annotations

import csv
import html
import os
from pathlib import Path
from typing import Any

from anduril_ops.io.config import build_objects_from_cfg, load_yaml
from anduril_ops.mission.briefing import MissionOverview, build_mission_overview, strategy_display_name


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


def _rel(base: Path, target: Path) -> str:
    return os.path.relpath(target, start=base)


def _fmt(value: float, digits: int = 3) -> str:
    if value != value:
        return "n/a"
    if value == float("inf"):
        return "inf"
    return f"{value:.{digits}f}"


def _build_demo_snapshot(results_root: Path) -> dict[str, Any]:
    latest_demo = _latest(results_root, "demo/demo_priority_trade_study_*/demo_results_agg.csv")
    if latest_demo is None:
        return {"top_configs": [], "best_static": None, "best_patrol": None}

    rows = _read_rows(latest_demo)
    rows.sort(key=lambda row: _as_float(row, "mission_fit_score"), reverse=True)
    return {
        "top_configs": rows[:4],
        "best_static": next((row for row in rows if row.get("strategy") == "static"), None),
        "best_patrol": next((row for row in rows if row.get("strategy") == "patrol"), None),
    }


def _build_policy_snapshot(results_root: Path) -> dict[str, Any]:
    latest_policy = _latest(results_root, "policy/policy_comparison_dynamic_heterogeneous_*/policy_results_agg.csv")
    if latest_policy is None:
        return {"ranking": [], "best": None}

    rows = _read_rows(latest_policy)
    rows.sort(key=lambda row: _as_float(row, "mission_fit_score"), reverse=True)
    return {"ranking": rows, "best": rows[0] if rows else None}


def _load_mission_overview(repo_root: Path, preferred_policy: str) -> MissionOverview:
    base_cfg = load_yaml(repo_root / "configs" / "advanced_ops_base.yaml")
    scenario, _, _, _ = build_objects_from_cfg(base_cfg)
    return build_mission_overview(scenario, preferred_policy=preferred_policy)


def _group_assets(overview: MissionOverview) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int, int], dict[str, Any]] = {}
    for asset in overview.assets:
        key = (
            asset.platform_name,
            asset.role,
            asset.sensor_radius,
            asset.endurance_steps,
            asset.cruise_step_size,
        )
        group = grouped.setdefault(
            key,
            {
                "platform_name": asset.platform_name,
                "role": asset.role,
                "sensor_radius": asset.sensor_radius,
                "endurance_steps": asset.endurance_steps,
                "cruise_step_size": asset.cruise_step_size,
                "cost_per_step": asset.cost_per_step,
                "count": 0,
                "summary": asset.summary,
            },
        )
        group["count"] += 1
    return sorted(grouped.values(), key=lambda row: (row["role"], row["platform_name"]))


def _policy_explanation(strategy: str) -> str:
    mapping = {
        "static": "Holds fixed positions the whole mission. Best when you care most about staying over one place.",
        "patrol": "Sweeps around randomly. Good for reach, but weaker at disciplined response.",
        "greedy_patrol": "Assigns each drone to the most valuable target each step.",
        "assignment_patrol": "Assigns each drone to the most valuable target each step.",
        "priority_patrol": "Keeps long-endurance assets on key zones while fast assets react to live tasks.",
    }
    return mapping.get(strategy, "Alternative planning logic.")


def _glossary_items() -> list[tuple[str, str]]:
    return [
        ("Coverage", "How much of the map gets seen at least once during the mission."),
        ("Weighted coverage", "Coverage that counts important places more heavily than low-value areas."),
        ("Persistence", "How often the same place gets revisited instead of being seen once and forgotten."),
        ("Task service", "How much of the currently active incident area is being watched right now."),
        ("Response time", "How long it takes to get any surveillance on a newly appearing task."),
        ("Redundancy", "How much effort is spent re-watching places that were already covered."),
    ]


def _figure_specs(repo_root: Path) -> list[dict[str, str]]:
    figures_root = repo_root / "docs" / "figures"
    return [
        {
            "path": str(figures_root / "demo_priority_priority_vs_global.png"),
            "title": "Priority zones versus total map coverage",
            "caption": "This shows the tradeoff between watching the whole map and staying focused on the places that matter most.",
        },
        {
            "path": str(figures_root / "demo_priority_best_timeseries.png"),
            "title": "How coverage changes over time",
            "caption": "This is the easiest chart for non-technical viewers: it shows when patrol starts to outperform static coverage over the course of the mission.",
        },
        {
            "path": str(figures_root / "demo_priority_redundancy_vs_coverage.png"),
            "title": "When adding assets stops helping",
            "caption": "Higher redundancy means the team is spending more time re-covering old space instead of creating new mission value.",
        },
        {
            "path": str(figures_root / "policy_dynamic_strategy_bars.png"),
            "title": "Overall planner scorecard",
            "caption": "This summarizes which policy did best across mission fit, task service, completion, and efficiency.",
        },
        {
            "path": str(figures_root / "policy_dynamic_task_service_vs_response.png"),
            "title": "Task service versus speed of response",
            "caption": "Better planners both react quickly and keep more of the active task area under watch.",
        },
        {
            "path": str(figures_root / "policy_dynamic_timeseries.png"),
            "title": "How each planner behaves through the mission",
            "caption": "This makes the difference between random patrol, assignment planning, and task-aware planning visible over time.",
        },
    ]


def _policy_table_html(policy_snapshot: dict[str, Any]) -> str:
    rows = policy_snapshot["ranking"]
    if not rows:
        return "<p class='empty'>Run the policy comparison workflow to populate this section.</p>"

    body_rows: list[str] = []
    for idx, row in enumerate(rows):
        cls = " class='is-best'" if idx == 0 else ""
        body_rows.append(
            "<tr"
            f"{cls}>"
            f"<td>{html.escape(strategy_display_name(str(row['strategy'])))}</td>"
            f"<td>{_fmt(_as_float(row, 'mission_fit_score'))}</td>"
            f"<td>{_fmt(_as_float(row, 'avg_task_service_rate'))}</td>"
            f"<td>{_fmt(_as_float(row, 'task_completion_rate'))}</td>"
            f"<td>{_fmt(_as_float(row, 'mean_task_response_time'), digits=2)}</td>"
            f"<td>{html.escape(_policy_explanation(str(row['strategy'])))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Policy</th><th>Mission fit</th><th>Task service</th><th>Completion</th><th>Response time</th><th>What it does</th>"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def _demo_table_html(demo_snapshot: dict[str, Any]) -> str:
    rows = demo_snapshot["top_configs"]
    if not rows:
        return "<p class='empty'>Run the priority demo workflow to populate this section.</p>"

    body_rows: list[str] = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(strategy_display_name(str(row['strategy'])))}</td>"
            f"<td>{_as_int(row, 'num_drones')}</td>"
            f"<td>{_as_int(row, 'sensor_radius')}</td>"
            f"<td>{_fmt(_as_float(row, 'mission_fit_score'))}</td>"
            f"<td>{_fmt(_as_float(row, 'final_weighted_coverage'))}</td>"
            f"<td>{_fmt(_as_float(row, 'pct_priority_revisits_within_threshold'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Strategy</th><th>Drones</th><th>Sensor radius</th><th>Mission fit</th><th>Weighted coverage</th><th>Priority persistence</th>"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def build_live_demo_site(repo_root: Path, site_path: Path) -> None:
    results_root = repo_root / "results"
    docs_root = repo_root / "docs"
    live_demo_root = site_path.parent

    policy_snapshot = _build_policy_snapshot(results_root)
    best_policy = str(policy_snapshot["best"]["strategy"]) if policy_snapshot["best"] is not None else "priority_patrol"
    mission_overview = _load_mission_overview(repo_root, preferred_policy=best_policy)
    demo_snapshot = _build_demo_snapshot(results_root)

    asset_cards = []
    for group in _group_assets(mission_overview):
        role_text = {
            "anchor": "Anchor assets",
            "respond": "Response assets",
            "general": "General-purpose assets",
        }[str(group["role"])]
        asset_cards.append(
            "<article class='info-card'>"
            f"<div class='eyebrow-small'>{html.escape(role_text)}</div>"
            f"<h3>{html.escape(group['platform_name'].title())} x{group['count']}</h3>"
            f"<p>{html.escape(group['summary'])}</p>"
            "<ul class='mini-list'>"
            f"<li>Sensor radius: {group['sensor_radius']}</li>"
            f"<li>Endurance: {group['endurance_steps']} steps</li>"
            f"<li>Cruise step size: {group['cruise_step_size']}</li>"
            "</ul>"
            "</article>"
        )

    zone_cards = []
    for zone in mission_overview.zones:
        zone_cards.append(
            "<article class='info-card'>"
            "<div class='eyebrow-small'>Priority zone</div>"
            f"<h3>{html.escape(zone.name.replace('_', ' ').title())}</h3>"
            f"<p>{html.escape(zone.purpose)}</p>"
            "<ul class='mini-list'>"
            f"<li>Weight: {_fmt(zone.weight, digits=1)}</li>"
            f"<li>Centroid: ({zone.centroid_x}, {zone.centroid_y})</li>"
            f"<li>Area: {zone.area_cells} cells</li>"
            "</ul>"
            "</article>"
        )

    task_cards = []
    for task in mission_overview.tasks:
        owner = "Fast response assets" if task.suggested_owner_role == "respond" else "Any available asset"
        task_cards.append(
            "<article class='info-card'>"
            "<div class='eyebrow-small'>Dynamic task</div>"
            f"<h3>{html.escape(task.name.replace('_', ' ').title())}</h3>"
            f"<p>{html.escape(task.purpose)}</p>"
            "<ul class='mini-list'>"
            f"<li>Priority: {_fmt(task.priority, digits=1)}</li>"
            f"<li>Window: step {task.start_step} to {task.end_step}</li>"
            f"<li>Best owner: {html.escape(owner)}</li>"
            "</ul>"
            "</article>"
        )

    playbook_rows = []
    for rec in mission_overview.allocation_playbook:
        playbook_rows.append(
            "<tr>"
            f"<td>{html.escape(rec.phase)}</td>"
            f"<td>{html.escape(rec.asset_group)}</td>"
            f"<td>{html.escape(rec.target_name.replace('_', ' ').title())}</td>"
            f"<td>{html.escape(rec.target_kind)}</td>"
            f"<td>{html.escape(rec.reason)}</td>"
            "</tr>"
        )

    glossary_cards = []
    for title, text in _glossary_items():
        glossary_cards.append(
            "<article class='glossary-card'>"
            f"<h3>{html.escape(title)}</h3>"
            f"<p>{html.escape(text)}</p>"
            "</article>"
        )

    figures = []
    for spec in _figure_specs(repo_root):
        rel = _rel(live_demo_root, Path(spec["path"]))
        figures.append(
            "<figure class='evidence'>"
            f"<img src='{html.escape(rel)}' alt='{html.escape(spec['title'])}'>"
            f"<figcaption><strong>{html.escape(spec['title'])}</strong><span>{html.escape(spec['caption'])}</span></figcaption>"
            "</figure>"
        )

    summary_lines = [
        mission_overview.plain_english_summary,
        "The site is now static and self-contained, so it can be hosted on GitHub Pages without a backend.",
    ]
    if policy_snapshot["best"] is not None:
        best = policy_snapshot["best"]
        summary_lines.append(
            f"The current top policy is {strategy_display_name(str(best['strategy']))}, with task completion {_fmt(_as_float(best, 'task_completion_rate'))}."
        )

    html_out = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ISR Mission Tasking Demo</title>
  <style>
    :root {{
      --bg: #f2ece1;
      --ink: #122631;
      --muted: #5b696e;
      --panel: rgba(255, 251, 245, 0.92);
      --line: rgba(18, 38, 49, 0.12);
      --accent: #bf5d18;
      --accent-soft: rgba(191, 93, 24, 0.12);
      --hero: linear-gradient(145deg, rgba(12, 23, 30, 0.98), rgba(27, 46, 57, 0.9));
      --shadow: 0 18px 44px rgba(18, 38, 49, 0.12);
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
        radial-gradient(circle at top left, rgba(239, 186, 122, 0.18), transparent 34%),
        linear-gradient(180deg, #f8f3ea 0%, var(--bg) 44%, #ede4d6 100%);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
    }}
    .hero {{
      min-height: 100svh;
      padding: 28px 24px 42px;
      color: #f7efe2;
      background: var(--hero);
      position: relative;
      overflow: hidden;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.045) 36%, transparent 62%),
        radial-gradient(circle at 80% 28%, rgba(255, 205, 138, 0.2), transparent 22%);
      pointer-events: none;
    }}
    .hero-inner,
    main {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    .hero-inner {{
      position: relative;
      z-index: 1;
      min-height: calc(100svh - 70px);
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
      gap: 40px;
      align-items: end;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.2em;
      font-size: 0.78rem;
      color: rgba(247, 239, 226, 0.72);
      margin-bottom: 18px;
    }}
    .eyebrow-small {{
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.74rem;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    h1, h2, h3 {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      margin: 0;
      line-height: 0.97;
    }}
    h1 {{
      font-size: clamp(3rem, 7vw, 6.2rem);
      max-width: 7ch;
      letter-spacing: -0.04em;
    }}
    h2 {{
      font-size: clamp(2rem, 4vw, 3rem);
      letter-spacing: -0.03em;
    }}
    h3 {{
      font-size: 1.35rem;
      line-height: 1.15;
    }}
    .hero-copy p,
    .section-head p,
    .lede {{
      line-height: 1.7;
      font-size: 1.04rem;
    }}
    .hero-copy p {{
      color: rgba(247, 239, 226, 0.84);
      max-width: 40rem;
      margin-top: 20px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 26px;
    }}
    .action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 12px 18px;
      text-decoration: none;
      color: #f7efe2;
      border: 1px solid rgba(247, 239, 226, 0.2);
      transition: transform 180ms ease, background 180ms ease;
    }}
    .action:hover {{
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.06);
    }}
    .action-primary {{
      background: linear-gradient(135deg, #ef9b4d, #bf5d18);
      color: #1c130d;
      border-color: transparent;
      font-weight: 700;
    }}
    .hero-panel {{
      background: rgba(255, 248, 238, 0.08);
      border: 1px solid rgba(247, 239, 226, 0.12);
      border-radius: 28px;
      padding: 22px;
      backdrop-filter: blur(8px);
    }}
    .summary-list,
    .mini-list {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
    }}
    .summary-list li + li,
    .mini-list li + li {{
      margin-top: 8px;
    }}
    main {{
      padding: 34px 24px 80px;
    }}
    .section {{
      margin-top: 40px;
    }}
    .section-head {{
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: 24px;
      align-items: start;
      margin-bottom: 20px;
    }}
    .section-head p {{
      margin: 0;
      color: var(--muted);
    }}
    .grid-3,
    .glossary-grid,
    .figure-grid {{
      display: grid;
      gap: 18px;
    }}
    .grid-3 {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .glossary-grid {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .figure-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .info-card,
    .glossary-card,
    .table-panel,
    .evidence {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: var(--shadow);
    }}
    .info-card,
    .glossary-card,
    .table-panel {{
      padding: 20px;
    }}
    .info-card p,
    .glossary-card p {{
      color: var(--muted);
      line-height: 1.65;
    }}
    .table-panel table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    .table-panel th,
    .table-panel td {{
      border-bottom: 1px solid var(--line);
      padding: 11px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .table-panel th {{
      color: var(--muted);
      font-weight: 600;
    }}
    tr.is-best td:first-child {{
      color: var(--accent);
      font-weight: 700;
    }}
    .evidence {{
      overflow: hidden;
      margin: 0;
    }}
    .evidence img {{
      display: block;
      width: 100%;
      height: auto;
      background: #fff;
    }}
    .evidence figcaption {{
      display: grid;
      gap: 8px;
      padding: 16px 18px 20px;
      color: var(--muted);
      line-height: 1.6;
    }}
    .evidence figcaption strong {{
      color: var(--ink);
    }}
    .callout {{
      padding: 18px 20px;
      border-radius: 22px;
      background: var(--accent-soft);
      border: 1px solid rgba(191, 93, 24, 0.18);
      line-height: 1.65;
      color: #5d3011;
    }}
    .hosting-note {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .empty {{
      color: var(--muted);
      line-height: 1.6;
    }}
    @media (max-width: 980px) {{
      .hero-inner,
      .section-head,
      .grid-3,
      .glossary-grid,
      .figure-grid,
      .hosting-note {{
        grid-template-columns: 1fr;
      }}
      .hero {{
        min-height: auto;
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
        <div class="eyebrow">ISR Mission Tasking And Evaluation</div>
        <h1>Plain-English demo of the mission-decision layer.</h1>
        <p>This project is not about detecting objects in imagery. It is about deciding where a limited drone fleet should watch, when it should move, and how to judge whether a planning policy is actually helping the mission.</p>
        <div class="actions">
          <a class="action action-primary" href="#mission">See the mission setup</a>
          <a class="action" href="#results">See the policy results</a>
          <a class="action" href="#hosting">Hosting notes</a>
        </div>
      </div>
      <aside class="hero-panel">
        <div class="eyebrow-small">If you only read one thing</div>
        <ul class="summary-list">
          {"".join(f"<li>{html.escape(line)}</li>" for line in summary_lines)}
        </ul>
      </aside>
    </div>
  </section>

  <main>
    <section class="section">
      <div class="section-head">
        <div>
          <h2>What this project does</h2>
        </div>
        <p class="lede">In plain English: a handful of drones cannot watch everything all the time. This project tests different ways of assigning those drones to important areas and new incidents, then measures which policy creates the best mission outcome.</p>
      </div>
      <div class="callout">
        The key shift in this repo is from a simple trade study to a mission-tasking layer: explicit assets, explicit zones, explicit tasks, and explicit planner behavior under changing demand.
      </div>
    </section>

    <section class="section" id="mission">
      <div class="section-head">
        <div>
          <h2>Mission setup</h2>
        </div>
        <p>{html.escape(mission_overview.plain_english_summary)}</p>
      </div>
      <div class="grid-3">
        {"".join(asset_cards)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Important areas</h2>
        </div>
        <p>The planner is not treating the map as equally important everywhere. Some zones matter more, so missing them should hurt the score more.</p>
      </div>
      <div class="grid-3">
        {"".join(zone_cards)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Dynamic tasks</h2>
        </div>
        <p>These are the time-varying incidents that appear after the mission starts. A good planner has to react to them without abandoning the persistent-watch areas completely.</p>
      </div>
      <div class="grid-3">
        {"".join(task_cards)}
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>What the planner is deciding</h2>
        </div>
        <p>This is the concrete decision logic the repo is evaluating. It is much easier for non-technical viewers to understand the project through this playbook than through raw code or equations.</p>
      </div>
      <article class="table-panel">
        <table>
          <thead>
            <tr>
              <th>Phase</th>
              <th>Who moves</th>
              <th>Toward what</th>
              <th>Type</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {"".join(playbook_rows)}
          </tbody>
        </table>
      </article>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>How to read the metrics</h2>
        </div>
        <p>The site now explains the score terms directly so a reviewer does not need a simulation background to understand what a “good” policy means.</p>
      </div>
      <div class="glossary-grid">
        {"".join(glossary_cards)}
      </div>
    </section>

    <section class="section" id="results">
      <div class="section-head">
        <div>
          <h2>Latest result snapshot</h2>
        </div>
        <p>The comparison below uses the current saved outputs. The labels are intentionally human-readable so the site feels like a mission brief instead of a notebook dump.</p>
      </div>
      <div class="grid-3" style="grid-template-columns: 1fr 1fr;">
        <article class="table-panel">
          <h3>Priority demo sweep</h3>
          {_demo_table_html(demo_snapshot)}
        </article>
        <article class="table-panel">
          <h3>Dynamic policy comparison</h3>
          {_policy_table_html(policy_snapshot)}
        </article>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>What the charts are showing</h2>
        </div>
        <p>The figures below are the stable assets committed in the repo, so this site stays portable and can be hosted statically without any backend compute.</p>
      </div>
      <div class="figure-grid">
        {"".join(figures)}
      </div>
    </section>

    <section class="section" id="hosting">
      <div class="section-head">
        <div>
          <h2>Hosting</h2>
        </div>
        <p>This site is static HTML plus committed figures. That means GitHub Pages is enough for the current showcase. You only need Render later if you add uploads, a backend API, or live reruns in the browser.</p>
      </div>
      <div class="hosting-note">
        <article class="info-card">
          <div class="eyebrow-small">Use GitHub Pages now</div>
          <p>Best choice for the current repo because the site is static. Point Pages at the <code>docs/</code> folder after you merge the branch.</p>
        </article>
        <article class="info-card">
          <div class="eyebrow-small">Use Render later</div>
          <p>Only worth it if you want an interactive product surface, such as file upload, a policy-run API, or server-side simulation execution.</p>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
"""

    site_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.write_text(html_out, encoding="utf-8")

    docs_index = repo_root / "docs" / "index.html"
    redirect_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=live_demo/index.html">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ISR Mission Tasking Demo</title>
</head>
<body>
  <p>Redirecting to <a href="live_demo/index.html">the showcase site</a>...</p>
</body>
</html>
"""
    docs_index.write_text(redirect_html, encoding="utf-8")
