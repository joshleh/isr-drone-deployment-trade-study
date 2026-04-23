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
        badge = "<span class='table-chip'>Top policy</span>" if idx == 0 else ""
        body_rows.append(
            "<tr"
            f"{cls}>"
            f"<td><strong>{html.escape(strategy_display_name(str(row['strategy'])))}</strong>{badge}</td>"
            f"<td>{_fmt(_as_float(row, 'mission_fit_score'))}</td>"
            f"<td>{_fmt(_as_float(row, 'avg_task_service_rate'))}</td>"
            f"<td>{_fmt(_as_float(row, 'task_completion_rate'))}</td>"
            f"<td>{_fmt(_as_float(row, 'mean_task_response_time'), digits=2)}</td>"
            f"<td>{html.escape(_policy_explanation(str(row['strategy'])))}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th scope='col'>Policy</th><th scope='col'>Mission fit</th><th scope='col'>Task service</th><th scope='col'>Completion</th><th scope='col'>Response time</th><th scope='col'>What it does</th>"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def _demo_table_html(demo_snapshot: dict[str, Any]) -> str:
    rows = demo_snapshot["top_configs"]
    if not rows:
        return "<p class='empty'>Run the priority demo workflow to populate this section.</p>"

    body_rows: list[str] = []
    for idx, row in enumerate(rows):
        badge = "<span class='table-chip'>Best sweep row</span>" if idx == 0 else ""
        body_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(strategy_display_name(str(row['strategy'])))}</strong>{badge}</td>"
            f"<td>{_as_int(row, 'num_drones')}</td>"
            f"<td>{_as_int(row, 'sensor_radius')}</td>"
            f"<td>{_fmt(_as_float(row, 'mission_fit_score'))}</td>"
            f"<td>{_fmt(_as_float(row, 'final_weighted_coverage'))}</td>"
            f"<td>{_fmt(_as_float(row, 'pct_priority_revisits_within_threshold'))}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th scope='col'>Strategy</th><th scope='col'>Drones</th><th scope='col'>Sensor radius</th><th scope='col'>Mission fit</th><th scope='col'>Weighted coverage</th><th scope='col'>Priority persistence</th>"
        "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def build_live_demo_site(repo_root: Path, site_path: Path) -> None:
    results_root = repo_root / "results"
    docs_root = repo_root / "docs"
    live_demo_root = site_path.parent

    policy_snapshot = _build_policy_snapshot(results_root)
    best_policy = str(policy_snapshot["best"]["strategy"]) if policy_snapshot["best"] is not None else "priority_patrol"
    mission_overview = _load_mission_overview(repo_root, preferred_policy=best_policy)
    demo_snapshot = _build_demo_snapshot(results_root)

    hero_meta_cards = []
    for label, value in [
        ("Fleet", f"{len(mission_overview.assets)} assets"),
        ("Priority areas", f"{len(mission_overview.zones)} zones"),
        ("Dynamic tasks", f"{len(mission_overview.tasks)} live tasks"),
        ("Publishing", "GitHub Pages ready"),
    ]:
        hero_meta_cards.append(
            "<div class='stat-pill'>"
            f"<span class='stat-label'>{html.escape(label)}</span>"
            f"<strong>{html.escape(value)}</strong>"
            "</div>"
        )

    result_cards: list[str] = []
    if policy_snapshot["best"] is not None:
        best = policy_snapshot["best"]
        ranking = policy_snapshot["ranking"]
        runner_up = ranking[1] if len(ranking) > 1 else None
        result_cards.append(
            "<article class='result-card'>"
            "<div class='eyebrow-small'>Best current planner</div>"
            f"<h3>{html.escape(strategy_display_name(str(best['strategy'])))}</h3>"
            f"<p>{html.escape(_policy_explanation(str(best['strategy'])))}</p>"
            "<ul class='mini-list'>"
            f"<li><span>Mission fit</span><strong>{_fmt(_as_float(best, 'mission_fit_score'))}</strong></li>"
            f"<li><span>Task completion</span><strong>{_fmt(_as_float(best, 'task_completion_rate'))}</strong></li>"
            "</ul>"
            "</article>"
        )
        if runner_up is not None:
            delta = _as_float(best, "mission_fit_score") - _as_float(runner_up, "mission_fit_score")
            result_cards.append(
                "<article class='result-card'>"
                "<div class='eyebrow-small'>Lead over runner-up</div>"
                f"<h3>{_fmt(delta)}</h3>"
                f"<p>{html.escape(strategy_display_name(str(best['strategy'])))} currently leads {html.escape(strategy_display_name(str(runner_up['strategy'])))} on the overall mission-fit score.</p>"
                "<ul class='mini-list'>"
                f"<li><span>Runner-up</span><strong>{html.escape(strategy_display_name(str(runner_up['strategy'])))}</strong></li>"
                f"<li><span>Response time</span><strong>{_fmt(_as_float(best, 'mean_task_response_time'), digits=2)} steps</strong></li>"
                "</ul>"
                "</article>"
            )
        result_cards.append(
            "<article class='result-card'>"
            "<div class='eyebrow-small'>How to read the win</div>"
            "<h3>Balance, not just reach</h3>"
            "<p>The strongest planner is not the one that visits the most cells. It is the one that keeps persistent watch on high-value zones while still reacting quickly to late-arriving tasks.</p>"
            "<ul class='mini-list'>"
            f"<li><span>Task service</span><strong>{_fmt(_as_float(best, 'avg_task_service_rate'))}</strong></li>"
            f"<li><span>Why it stands out</span><strong>Anchors plus responders</strong></li>"
            "</ul>"
            "</article>"
        )

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
            f"<li><span>Sensor radius</span><strong>{group['sensor_radius']}</strong></li>"
            f"<li><span>Endurance</span><strong>{group['endurance_steps']} steps</strong></li>"
            f"<li><span>Cruise step size</span><strong>{group['cruise_step_size']}</strong></li>"
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
            f"<li><span>Weight</span><strong>{_fmt(zone.weight, digits=1)}</strong></li>"
            f"<li><span>Centroid</span><strong>({zone.centroid_x}, {zone.centroid_y})</strong></li>"
            f"<li><span>Area</span><strong>{zone.area_cells} cells</strong></li>"
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
            f"<li><span>Priority</span><strong>{_fmt(task.priority, digits=1)}</strong></li>"
            f"<li><span>Window</span><strong>step {task.start_step} to {task.end_step}</strong></li>"
            f"<li><span>Best owner</span><strong>{html.escape(owner)}</strong></li>"
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
            f"<img src='{html.escape(rel)}' alt='{html.escape(spec['title'])}' loading='lazy'>"
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
  <meta name="theme-color" content="#112430">
  <meta name="color-scheme" content="light">
  <title>ISR Mission Tasking Demo</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23112430'/%3E%3Cpath d='M16 45V19h6v26zm13 0V25h6v20zm13 0V13h6v32z' fill='%23f7efe2'/%3E%3C/svg%3E">
  <style>
    :root {{
      --bg: #f2ecdf;
      --bg-deep: #e9dfd0;
      --ink: #10222d;
      --muted: #495b65;
      --panel: rgba(255, 250, 244, 0.9);
      --panel-strong: rgba(255, 252, 247, 0.98);
      --line: rgba(16, 34, 45, 0.12);
      --accent: #7d4c0d;
      --accent-strong: #5f3707;
      --accent-soft: rgba(125, 76, 13, 0.11);
      --hero: linear-gradient(145deg, #0d1c25 0%, #153140 54%, #0f2431 100%);
      --hero-line: rgba(247, 239, 226, 0.12);
      --hero-text: #f7efe2;
      --hero-muted: rgba(247, 239, 226, 0.78);
      --focus: #0e5f74;
      --shadow: 0 18px 46px rgba(16, 34, 45, 0.09);
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
        radial-gradient(circle at top left, rgba(205, 161, 94, 0.14), transparent 32%),
        linear-gradient(180deg, #f8f4eb 0%, var(--bg) 48%, var(--bg-deep) 100%);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      text-rendering: optimizeLegibility;
    }}
    a {{
      color: var(--accent-strong);
      text-decoration-thickness: 1.5px;
      text-underline-offset: 3px;
    }}
    a:focus-visible,
    button:focus-visible {{
      outline: 3px solid var(--focus);
      outline-offset: 3px;
      border-radius: 6px;
    }}
    .skip-link {{
      position: absolute;
      left: 20px;
      top: -48px;
      z-index: 50;
      background: var(--panel-strong);
      color: var(--ink);
      padding: 10px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      text-decoration: none;
    }}
    .skip-link:focus {{
      top: 18px;
    }}
    .hero {{
      min-height: 88svh;
      padding: 40px 28px 54px;
      color: var(--hero-text);
      background: var(--hero);
      position: relative;
      overflow: hidden;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(to right, transparent 0, transparent calc(100% - 1px), rgba(247, 239, 226, 0.04) calc(100% - 1px)),
        linear-gradient(to bottom, transparent 0, transparent calc(100% - 1px), rgba(247, 239, 226, 0.04) calc(100% - 1px));
      background-size: 88px 88px;
      opacity: 0.35;
      pointer-events: none;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 78% 24%, rgba(234, 172, 93, 0.22), transparent 20%),
        linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.045) 38%, transparent 63%);
      pointer-events: none;
    }}
    .hero-inner,
    main {{
      max-width: 1120px;
      margin: 0 auto;
    }}
    .hero-inner {{
      position: relative;
      z-index: 1;
      min-height: calc(88svh - 94px);
      display: grid;
      grid-template-columns: minmax(0, 1.06fr) minmax(320px, 0.94fr);
      gap: 48px;
      align-items: center;
    }}
    .hero-copy {{
      padding: 24px 0;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.22em;
      font-size: 0.75rem;
      color: rgba(247, 239, 226, 0.74);
      margin-bottom: 18px;
    }}
    .eyebrow-small {{
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.72rem;
      color: var(--accent-strong);
      margin-bottom: 10px;
      font-weight: 700;
    }}
    h1, h2, h3 {{
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      margin: 0;
    }}
    h1 {{
      font-size: clamp(2.9rem, 6vw, 5.15rem);
      max-width: 8ch;
      letter-spacing: -0.045em;
      line-height: 0.95;
    }}
    h2 {{
      font-size: clamp(2rem, 3.7vw, 2.8rem);
      line-height: 1;
      letter-spacing: -0.03em;
    }}
    h3 {{
      font-size: 1.34rem;
      line-height: 1.15;
    }}
    .hero-copy p,
    .section-head p,
    .lede,
    .info-card p,
    .glossary-card p,
    .result-card p {{
      line-height: 1.7;
      font-size: 1.02rem;
    }}
    .hero-copy p {{
      color: var(--hero-muted);
      max-width: 33rem;
      margin: 20px 0 0;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 28px;
    }}
    .action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 46px;
      border-radius: 999px;
      padding: 12px 18px;
      text-decoration: none;
      color: var(--hero-text);
      border: 1px solid rgba(247, 239, 226, 0.24);
      transition: transform 180ms ease, background 180ms ease, border-color 180ms ease;
    }}
    .action:hover {{
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(247, 239, 226, 0.4);
    }}
    .action-primary {{
      background: linear-gradient(135deg, #f0ba7b, #b86a1e);
      color: #1b130d;
      border-color: transparent;
      font-weight: 700;
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 30px;
      max-width: 52rem;
    }}
    .stat-pill {{
      padding: 14px 14px 12px;
      border-radius: 18px;
      background: rgba(255, 249, 241, 0.08);
      border: 1px solid var(--hero-line);
      display: grid;
      gap: 6px;
    }}
    .stat-label {{
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: rgba(247, 239, 226, 0.68);
    }}
    .stat-pill strong {{
      font-size: 1rem;
      line-height: 1.25;
      color: var(--hero-text);
    }}
    .hero-panel {{
      background: rgba(255, 248, 238, 0.08);
      border: 1px solid rgba(247, 239, 226, 0.12);
      border-radius: 30px;
      padding: 26px 24px 24px;
      backdrop-filter: blur(10px);
      box-shadow: 0 16px 40px rgba(3, 8, 12, 0.24);
    }}
    .summary-list,
    .mini-list {{
      margin: 0;
      line-height: 1.65;
    }}
    .summary-list {{
      padding-left: 18px;
    }}
    .summary-list li + li {{
      margin-top: 10px;
    }}
    .mini-list {{
      list-style: none;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .mini-list li {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .mini-list li strong {{
      color: var(--ink);
      text-align: right;
      font-weight: 700;
    }}
    main {{
      padding: 44px 28px 96px;
    }}
    .section {{
      margin-top: 70px;
      padding-top: 28px;
      border-top: 1px solid var(--line);
    }}
    .section:first-of-type {{
      margin-top: 18px;
    }}
    .section[id] {{
      scroll-margin-top: 28px;
    }}
    .section-head {{
      display: grid;
      grid-template-columns: minmax(0, 0.82fr) minmax(0, 1fr);
      gap: 28px;
      align-items: start;
      margin-bottom: 24px;
    }}
    .section-head p {{
      margin: 0;
      color: var(--muted);
      max-width: 42rem;
    }}
    .asset-grid,
    .zone-grid,
    .task-grid,
    .glossary-grid,
    .figure-grid,
    .results-grid,
    .table-grid,
    .hosting-note {{
      display: grid;
      gap: 18px;
    }}
    .asset-grid {{
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .zone-grid {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .task-grid {{
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }}
    .glossary-grid {{
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    }}
    .figure-grid,
    .table-grid,
    .hosting-note {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .results-grid {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-bottom: 18px;
    }}
    .info-card,
    .glossary-card,
    .table-panel,
    .result-card,
    .evidence {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .info-card,
    .glossary-card,
    .table-panel,
    .result-card {{
      padding: 22px;
    }}
    .info-card,
    .glossary-card,
    .result-card {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 100%;
    }}
    .info-card p,
    .glossary-card p,
    .result-card p {{
      color: var(--muted);
      margin: 0;
    }}
    .table-panel h3 {{
      margin-bottom: 14px;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    .table-panel table {{
      width: 100%;
      min-width: 640px;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    .table-panel th,
    .table-panel td {{
      border-bottom: 1px solid var(--line);
      padding: 12px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .table-panel th {{
      color: var(--muted);
      font-weight: 700;
      white-space: nowrap;
    }}
    .table-panel td strong {{
      display: inline-block;
      color: var(--ink);
      font-weight: 700;
    }}
    .table-chip {{
      display: inline-flex;
      align-items: center;
      margin-left: 10px;
      padding: 3px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent-strong);
      font-size: 0.73rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      font-weight: 700;
      vertical-align: middle;
    }}
    tr.is-best td:first-child strong {{
      color: var(--accent-strong);
    }}
    .evidence {{
      overflow: hidden;
      margin: 0;
      background: var(--panel-strong);
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
      max-width: 50rem;
      padding: 20px 22px 20px 24px;
      border-radius: 22px;
      background: var(--accent-soft);
      border: 1px solid rgba(125, 76, 13, 0.18);
      border-left: 5px solid var(--accent);
      line-height: 1.7;
      color: var(--accent-strong);
    }}
    .empty {{
      color: var(--muted);
      line-height: 1.65;
    }}
    @media (max-width: 1040px) {{
      .hero-inner,
      .section-head,
      .results-grid,
      .table-grid,
      .figure-grid,
      .hosting-note {{
        grid-template-columns: 1fr;
      }}
      .hero-meta {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .hero {{
        min-height: auto;
      }}
      .hero-inner {{
        min-height: auto;
      }}
    }}
    @media (max-width: 720px) {{
      .hero,
      main {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      .hero {{
        padding-top: 30px;
        padding-bottom: 40px;
      }}
      .hero-meta {{
        grid-template-columns: 1fr;
      }}
      .actions {{
        flex-direction: column;
        align-items: stretch;
      }}
      .action {{
        width: 100%;
      }}
      .table-panel {{
        padding: 18px;
      }}
      .table-panel table {{
        min-width: 560px;
      }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
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
        <div class="hero-meta">
          {"".join(hero_meta_cards)}
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

  <main id="main">
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
      <div class="asset-grid">
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
      <div class="zone-grid">
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
      <div class="task-grid">
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
        <p>The comparison below uses the current saved outputs. The labels are intentionally human-readable so the site feels like a mission brief instead of a notebook dump, and the important states are called out with text badges instead of color alone.</p>
      </div>
      <div class="results-grid">
        {"".join(result_cards)}
      </div>
      <div class="table-grid">
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
        <p>The figures below are the stable assets committed in the repo, so this site stays portable and can be hosted statically without any backend compute. The updated chart palette also uses colorblind-safe colors plus distinct line styles, markers, and labels.</p>
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
