"""Build the local / GitHub Pages live-demo site.

The site stitches together:
  * a hero block describing the study
  * key metric cards from the latest demo + policy runs
  * the priority-weighted demo ranking and dynamic policy ranking
  * stable showcase figures committed under ``docs/figures``
  * deep links into the per-run reports + dashboards

Designed to render even when no runs are present: every section
fails over to a friendly empty-state instead of crashing.
"""

from __future__ import annotations

import csv
import html
import math
from pathlib import Path
from typing import Any, Sequence

from .theme import (
    relative_to,
    render_figure,
    render_metric_card,
    render_page,
    render_table,
)


_STABLE_FIGURES: tuple[tuple[str, str], ...] = (
    ("demo_priority_priority_vs_global.png", "Priority vs global coverage"),
    ("demo_priority_best_timeseries.png", "Best static vs patrol timeseries"),
    ("demo_priority_redundancy_vs_coverage.png", "Redundancy vs weighted coverage"),
    ("policy_dynamic_strategy_bars.png", "Policy comparison summary"),
    ("policy_dynamic_task_service_vs_response.png", "Task service vs response time"),
    ("policy_dynamic_timeseries.png", "Policy timeseries: coverage and task service"),
)


def _latest(pattern_root: Path, pattern: str) -> Path | None:
    matches = sorted(pattern_root.glob(pattern))
    return matches[-1] if matches else None


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def _as_int(row: dict[str, str], key: str) -> int:
    value = _as_float(row, key)
    return int(round(value)) if math.isfinite(value) else 0


def _fmt(value: float, digits: int = 3) -> str:
    if not math.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def _build_demo_snapshot(results_root: Path, live_demo_root: Path) -> dict[str, Any]:
    latest_demo = _latest(results_root, "demo/demo_priority_trade_study_*/demo_results_agg.csv")
    if latest_demo is None:
        return {
            "best_static": None,
            "best_patrol": None,
            "top_configs": [],
            "report_link": None,
            "run_label": None,
        }

    rows = _read_rows(latest_demo)
    rows.sort(key=lambda row: _as_float(row, "mission_fit_score"), reverse=True)
    static_rows = [row for row in rows if row.get("strategy") == "static"]
    patrol_rows = [row for row in rows if row.get("strategy") == "patrol"]
    demo_dir = latest_demo.parent

    return {
        "best_static": static_rows[0] if static_rows else None,
        "best_patrol": patrol_rows[0] if patrol_rows else None,
        "top_configs": rows[:5],
        "report_link": relative_to(live_demo_root, demo_dir / "demo_report.md"),
        "run_label": demo_dir.name,
    }


def _build_policy_snapshot(results_root: Path, live_demo_root: Path) -> dict[str, Any]:
    latest_policy = _latest(
        results_root,
        "policy/policy_comparison_dynamic_heterogeneous_*/policy_results_agg.csv",
    )
    if latest_policy is None:
        return {
            "best": None,
            "static_baseline": None,
            "ranking": [],
            "dashboard_link": None,
            "report_link": None,
            "task_completion_lift_vs_static": None,
            "weighted_coverage_lift_vs_static": None,
            "run_label": None,
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
        static_weighted = _as_float(static_row, "final_weighted_coverage")
        best_weighted = _as_float(best, "final_weighted_coverage")
        if math.isfinite(static_completion) and math.isfinite(best_completion):
            completion_lift = best_completion - static_completion
        if math.isfinite(static_weighted) and math.isfinite(best_weighted):
            weighted_lift = best_weighted - static_weighted

    return {
        "best": best,
        "static_baseline": static_row,
        "ranking": rows,
        "dashboard_link": relative_to(live_demo_root, policy_dir / "dashboard.html"),
        "report_link": relative_to(live_demo_root, policy_dir / "policy_report.md"),
        "task_completion_lift_vs_static": completion_lift,
        "weighted_coverage_lift_vs_static": weighted_lift,
        "run_label": policy_dir.name,
    }


def _action(label: str, href: str | None, *, primary: bool = False) -> str:
    classes = ["action"]
    if primary:
        classes.append("action-primary")
    cls = " ".join(classes)
    if not href:
        return f'<a class="{cls}" aria-disabled="true" href="#">{html.escape(label)}</a>'
    return f'<a class="{cls}" href="{html.escape(href)}">{html.escape(label)}</a>'


def _hero_brief_items(demo: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    items: list[str] = []

    best_policy = policy.get("best")
    if best_policy is not None:
        items.append(
            f"Best dynamic policy: <strong>{html.escape(str(best_policy['strategy']))}</strong> "
            f"at mission-fit <strong>{_fmt(_as_float(best_policy, 'mission_fit_score'))}</strong>."
        )

    completion_lift = policy.get("task_completion_lift_vs_static")
    if completion_lift is not None:
        items.append(
            f"Task-completion lift vs static baseline: <strong>{_fmt(float(completion_lift))}</strong>."
        )

    weighted_lift = policy.get("weighted_coverage_lift_vs_static")
    if weighted_lift is not None:
        items.append(
            f"Weighted-coverage lift vs static baseline: <strong>{_fmt(float(weighted_lift))}</strong>."
        )

    best_static = demo.get("best_static")
    best_patrol = demo.get("best_patrol")
    if best_static is not None and best_patrol is not None:
        items.append(
            "Priority demo: static reaches "
            f"<strong>{_fmt(_as_float(best_static, 'final_weighted_coverage'))}</strong> "
            "weighted coverage, patrol reaches "
            f"<strong>{_fmt(_as_float(best_patrol, 'final_weighted_coverage'))}</strong>."
        )

    if not items:
        items.append("Run <code>make demo</code> and <code>make policy</code> to populate this brief.")

    return items


def _hero_block(demo: dict[str, Any], policy: dict[str, Any]) -> str:
    primary = _action("Open policy dashboard", policy.get("dashboard_link"), primary=True)
    secondary = _action("Open policy brief", policy.get("report_link"))
    tertiary = _action("Open demo brief", demo.get("report_link"))
    items = "".join(f"<li>{line}</li>" for line in _hero_brief_items(demo, policy))

    return f"""
<section class="hero">
  <div class="hero-copy">
    <span class="eyebrow">Operations analysis</span>
    <h1>ISR drone deployment, scored under realistic mission demand.</h1>
    <p>A reproducible simulation harness that compares static, random, greedy, and task-aware patrol policies on a heterogeneous ISR fleet under priority zones and time-varying surveillance tasks.</p>
    <div class="actions">
      {primary}
      {secondary}
      {tertiary}
    </div>
  </div>
  <aside class="brief">
    <span class="brief-title">Mission readout</span>
    <ul class="brief-list">{items}</ul>
  </aside>
</section>
"""


def _metric_cards(demo: dict[str, Any], policy: dict[str, Any]) -> str:
    cards: list[str] = []
    best_policy = policy.get("best")
    static_baseline = policy.get("static_baseline")

    if best_policy is not None:
        cards.append(
            render_metric_card(
                "Best policy",
                str(best_policy["strategy"]),
                delta=f"mission-fit {_fmt(_as_float(best_policy, 'mission_fit_score'))}",
            )
        )
        cards.append(
            render_metric_card(
                "Task completion",
                _fmt(_as_float(best_policy, "task_completion_rate")),
                delta="best policy",
            )
        )
        cards.append(
            render_metric_card(
                "Mean response (steps)",
                _fmt(_as_float(best_policy, "mean_task_response_time"), digits=2),
                delta="lower is better",
            )
        )
        cards.append(
            render_metric_card(
                "Weighted coverage",
                _fmt(_as_float(best_policy, "final_weighted_coverage")),
                delta="best policy",
            )
        )

    if best_policy is not None and static_baseline is not None:
        completion_lift = policy.get("task_completion_lift_vs_static")
        if completion_lift is not None:
            cards.append(
                render_metric_card(
                    "Completion lift vs static",
                    _fmt(float(completion_lift)),
                    delta="best policy minus static baseline",
                )
            )

    if not cards:
        return '<div class="empty"><strong>No runs found yet.</strong> Generate a run with <code>make demo</code> and <code>make policy</code> to fill these cards.</div>'

    return f'<section class="cards">{"".join(cards)}</section>'


def _ops_section(demo: dict[str, Any], policy: dict[str, Any]) -> str:
    demo_label = demo.get("run_label") or "no demo runs yet"
    policy_label = policy.get("run_label") or "no policy runs yet"

    return f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">01 \u00b7 Mission snapshot</span>
      <h2>Latest run, latest answer.</h2>
    </div>
    <p>Both views auto-refresh from the most recent local run. The cards summarize the dynamic policy comparison; the rankings below show the priority-weighted trade study and the policy ranking.</p>
  </div>
  {_metric_cards(demo, policy)}
  <div class="panel-grid">
    <article class="panel">
      <h3>Latest demo run</h3>
      <p class="panel-sub">Priority-weighted trade study (static vs patrol).</p>
      <span class="tag tag-signal">{html.escape(str(demo_label))}</span>
    </article>
    <article class="panel">
      <h3>Latest policy run</h3>
      <p class="panel-sub">Heterogeneous fleet, dynamic tasks, four policies.</p>
      <span class="tag">{html.escape(str(policy_label))}</span>
    </article>
  </div>
</section>
"""


def _ranking_section(demo: dict[str, Any], policy: dict[str, Any]) -> str:
    demo_rows = [
        [
            html.escape(str(row["strategy"])),
            str(_as_int(row, "num_drones")),
            str(_as_int(row, "sensor_radius")),
            _fmt(_as_float(row, "mission_fit_score")),
            _fmt(_as_float(row, "final_weighted_coverage")),
            _fmt(_as_float(row, "pct_priority_revisits_within_threshold")),
        ]
        for row in demo["top_configs"]
    ]

    policy_rows = [
        [
            html.escape(str(row["strategy"])),
            _fmt(_as_float(row, "mission_fit_score")),
            _fmt(_as_float(row, "final_weighted_coverage")),
            _fmt(_as_float(row, "avg_task_service_rate")),
            _fmt(_as_float(row, "task_completion_rate")),
            _fmt(_as_float(row, "mean_task_response_time"), digits=2),
        ]
        for row in policy["ranking"]
    ]

    demo_table = render_table(
        ["Strategy", "Drones", "Radius", "Mission Fit", "Weighted Cov", "Priority Persist"],
        demo_rows,
        numeric_cols=(1, 2, 3, 4, 5),
        empty_text="Run `make demo` to populate this ranking.",
    )
    policy_table = render_table(
        ["Strategy", "Mission Fit", "Weighted Cov", "Task Service", "Completion", "Mean Response"],
        policy_rows,
        numeric_cols=(1, 2, 3, 4, 5),
        highlight_first_row=True,
        empty_text="Run `make policy` to populate this ranking.",
    )

    return f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">02 \u00b7 Rankings</span>
      <h2>Two views, two questions.</h2>
    </div>
    <p>The priority-weighted demo asks how to spend a homogeneous fleet against priority zones. The policy comparison asks which policy serves a heterogeneous fleet best when surveillance tasks arrive on a clock.</p>
  </div>
  <div class="panel-grid">
    <article class="panel">
      <h3>Priority-weighted trade study</h3>
      <p class="panel-sub">Static and patrol over the priority demo grid.</p>
      {demo_table}
    </article>
    <article class="panel">
      <h3>Dynamic policy comparison</h3>
      <p class="panel-sub">Static, random patrol, greedy, priority-aware patrol on a heterogeneous fleet.</p>
      {policy_table}
    </article>
  </div>
</section>
"""


def _figures_section(figures_root: Path, live_demo_root: Path) -> str:
    figure_html: list[str] = []
    for filename, caption in _STABLE_FIGURES:
        path = figures_root / filename
        rel = relative_to(live_demo_root, path)
        if rel is None:
            continue
        if not path.exists():
            continue
        figure_html.append(render_figure(rel, caption))

    body = "".join(figure_html) if figure_html else (
        '<div class="empty"><strong>No figures yet.</strong> '
        'Run <code>make demo</code> and <code>make policy</code> to generate the showcase figures under <code>docs/figures/</code>.</div>'
    )

    return f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">03 \u00b7 Evidence</span>
      <h2>Stable showcase figures.</h2>
    </div>
    <p>These plots are committed in the repo (regenerated on every run) so this page is reviewable without checking out the timestamped result folders.</p>
  </div>
  <div class="gallery">{body}</div>
</section>
"""


def _commands_section(docs_root: Path, live_demo_root: Path) -> str:
    role = relative_to(live_demo_root, docs_root / "06_role_alignment.md")
    walkthrough = relative_to(live_demo_root, docs_root / "05_demo_walkthrough.md")
    dynamic = relative_to(live_demo_root, docs_root / "07_dynamic_policy_comparison.md")
    results = relative_to(live_demo_root, docs_root / "04_results_summary.md")

    def _doc_link(label: str, rel: str | None) -> str:
        if rel is None:
            return f'<a aria-disabled="true" href="#">{html.escape(label)}</a>'
        return f'<a href="{html.escape(rel)}">{html.escape(label)}</a>'

    return f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">04 \u00b7 Run it locally</span>
      <h2>One-command rebuild.</h2>
    </div>
    <p>The site is fully reproducible from the local artifacts: rebuild the runs, rebuild the static figures, rebuild the page.</p>
  </div>
  <div class="panel-grid">
    <article class="panel">
      <h3>Commands</h3>
      <pre class="code-block"><span class="comment"># 1. install</span>
<span class="prompt">$</span> python -m pip install -e .

<span class="comment"># 2. regenerate demo + policy artifacts</span>
<span class="prompt">$</span> make demo
<span class="prompt">$</span> make policy

<span class="comment"># 3. rebuild the live demo + serve it</span>
<span class="prompt">$</span> make live-demo
<span class="prompt">$</span> make serve-demo

<span class="comment"># open</span>
http://127.0.0.1:8010/docs/live_demo/index.html</pre>
    </article>
    <article class="panel">
      <h3>Read more</h3>
      <p class="panel-sub">The deeper writeups live in <code>docs/</code>.</p>
      <dl class="kv">
        <dt>Role fit</dt><dd>{_doc_link("docs/06_role_alignment.md", role)}</dd>
        <dt>Walkthrough</dt><dd>{_doc_link("docs/05_demo_walkthrough.md", walkthrough)}</dd>
        <dt>Dynamic policies</dt><dd>{_doc_link("docs/07_dynamic_policy_comparison.md", dynamic)}</dd>
        <dt>Results</dt><dd>{_doc_link("docs/04_results_summary.md", results)}</dd>
      </dl>
    </article>
  </div>
</section>
"""


def build_live_demo_site(repo_root: Path, site_path: Path) -> None:
    """Render the live-demo HTML at ``site_path`` from the repo's latest artifacts."""
    results_root = repo_root / "results"
    docs_root = repo_root / "docs"
    figures_root = docs_root / "figures"
    live_demo_root = site_path.parent

    css_href = relative_to(live_demo_root, live_demo_root / "assets" / "styles.css") or "assets/styles.css"

    demo = _build_demo_snapshot(results_root, live_demo_root)
    policy = _build_policy_snapshot(results_root, live_demo_root)

    body = "\n".join(
        [
            _hero_block(demo, policy),
            _ops_section(demo, policy),
            _ranking_section(demo, policy),
            _figures_section(figures_root, live_demo_root),
            _commands_section(docs_root, live_demo_root),
        ]
    )

    page = render_page(
        title="ISR Trade Study \u00b7 Live Demo",
        css_href=css_href,
        body=body,
        topbar_links=(
            ("README", "../../README.md"),
            ("GitHub", "https://github.com/joshleh/isr-drone-deployment-trade-study"),
        ),
    )

    site_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.write_text(page, encoding="utf-8")


def stable_figures() -> Sequence[tuple[str, str]]:
    """Expose the stable-figure list so callers can verify what should exist."""
    return _STABLE_FIGURES
