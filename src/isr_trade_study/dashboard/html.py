"""Per-run static HTML dashboard.

Each policy-comparison run drops a ``dashboard.html`` next to its
DuckDB / Parquet outputs. The page shares CSS with the live-demo site
so every artifact looks like part of the same product.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

from .theme import (
    relative_to,
    render_figure,
    render_metric_card,
    render_page,
    render_table,
)


_CSS_RELATIVE_PATH = ("..", "..", "..", "docs", "live_demo", "assets", "styles.css")


def _resolve_css(html_path: Path) -> str:
    """Build a relative href to the shared stylesheet from the dashboard's location."""
    css_target = html_path.parent
    for part in _CSS_RELATIVE_PATH:
        css_target = css_target / part
    rel = relative_to(html_path.parent, css_target.resolve())
    return rel or "../../docs/live_demo/assets/styles.css"


def _summary_cards(summary: pd.DataFrame) -> str:
    cards: list[str] = []
    for row in summary.itertuples(index=False):
        cards.append(render_metric_card(str(row.metric), str(row.value)))
    if not cards:
        return ""
    return f'<section class="cards">{"".join(cards)}</section>'


def _format_cell(value) -> str:
    if isinstance(value, float):
        if value != value:  # NaN
            return "n/a"
        return f"{value:.3f}"
    return html.escape(str(value))


def _top_table(top_configs: pd.DataFrame) -> str:
    headers = list(top_configs.columns)
    numeric_cols = tuple(
        idx
        for idx, col in enumerate(headers)
        if pd.api.types.is_numeric_dtype(top_configs[col])
    )
    rows = [[_format_cell(value) for value in row] for row in top_configs.itertuples(index=False, name=None)]
    return render_table(
        headers,
        rows,
        numeric_cols=numeric_cols,
        highlight_first_row=True,
        empty_text="No rows in this table.",
    )


def _figure_section(html_path: Path, figure_paths: Iterable[Path]) -> str:
    figure_html: list[str] = []
    for path in figure_paths:
        if not path.exists():
            continue
        rel = os.path.relpath(path, start=html_path.parent).replace(os.sep, "/")
        caption = path.stem.replace("_", " ")
        figure_html.append(render_figure(rel, caption))

    if not figure_html:
        return ""

    return f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">Figures</span>
      <h2>Stable showcase plots.</h2>
    </div>
    <p>Regenerated on every run; the same files back the live-demo gallery.</p>
  </div>
  <div class="gallery">{"".join(figure_html)}</div>
</section>
"""


def build_static_dashboard(
    duckdb_path: Path,
    html_path: Path,
    summary_table: str,
    top_table: str,
    title: str,
    subtitle: str,
    figure_paths: Iterable[Path],
) -> None:
    """Render a per-run dashboard using the project-wide theme."""
    html_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        summary = con.execute(summary_table).fetchdf()
        top_configs = con.execute(top_table).fetchdf()

    css_href = _resolve_css(html_path)

    body_parts: list[str] = []
    body_parts.append(
        f"""
<section class="hero">
  <div class="hero-copy">
    <span class="eyebrow">Dashboard</span>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
    <div class="actions">
      <a class="action action-primary" href="../../../docs/live_demo/index.html">Back to live demo</a>
      <a class="action" href="policy_report.md">Open policy brief</a>
    </div>
  </div>
  <aside class="brief">
    <span class="brief-title">Asset map</span>
    <ul class="brief-list">
      <li>DuckDB: <code>{html.escape(duckdb_path.name)}</code></li>
      <li>HTML: <code>{html.escape(html_path.name)}</code></li>
      <li>Parquet tables sit next to the DuckDB file for downstream BI / notebooks.</li>
    </ul>
  </aside>
</section>
"""
    )

    body_parts.append(
        f"""
<section class="section">
  <div class="section-head">
    <div>
      <span class="section-tag">Summary</span>
      <h2>Headline numbers.</h2>
    </div>
    <p>Generated from <code>{html.escape(duckdb_path.name)}</code>. The top-ranked policy is highlighted below.</p>
  </div>
  {_summary_cards(summary)}
  <article class="panel">
    <h3>Top configurations</h3>
    <p class="panel-sub">Sorted by mission-fit score. Scroll horizontally if your viewport is narrow.</p>
    {_top_table(top_configs)}
  </article>
  <article class="panel" style="margin-top:18px;">
    <h3>Why DuckDB + Parquet</h3>
    <p class="panel-sub">The same outputs feed BI, notebooks, and lightweight ETL.</p>
    <p style="color:var(--ink-soft);font-size:0.92rem;margin:0;">Each run writes one DuckDB file plus one Parquet file per logical table. That makes downstream consumption (notebooks, dashboards, sweep aggregation jobs) the same shape as a tiny analytics warehouse instead of a folder of CSVs.</p>
  </article>
</section>
"""
    )

    figures_html = _figure_section(html_path, list(figure_paths))
    if figures_html:
        body_parts.append(figures_html)

    page = render_page(
        title=title,
        css_href=css_href,
        body="\n".join(body_parts),
        topbar_links=(
            ("Live demo", "../../../docs/live_demo/index.html"),
            ("Policy brief", "policy_report.md"),
        ),
    )

    html_path.write_text(page, encoding="utf-8")
