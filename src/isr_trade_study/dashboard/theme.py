"""Shared HTML helpers used by both the live-demo site and the per-run dashboards.

Both surfaces share a single CSS asset (``docs/live_demo/assets/styles.css``)
so every generated artifact looks like part of the same product.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Iterable, Sequence


def render_topbar(links: Sequence[tuple[str, str]] = ()) -> str:
    """Brand strip + nav links shown on every page."""
    link_html = "".join(
        f'<a href="{html.escape(url)}">{html.escape(label)}</a>'
        for label, url in links
    )
    return f"""<header class="topbar">
  <div class="brand">
    <div class="brand-mark" aria-hidden="true"></div>
    <div class="brand-meta">
      <span class="brand-title">ISR Trade Study</span>
      <span class="brand-sub">Drone deployment analysis</span>
    </div>
  </div>
  <nav class="topbar-links">{link_html}</nav>
</header>
"""


def render_footer() -> str:
    return (
        '<footer class="site-footer">'
        '<span>ISR Trade Study \u00b7 simulation + decision-support harness</span>'
        '<span>Local artifact \u00b7 generated from the latest run</span>'
        '</footer>'
    )


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    numeric_cols: Iterable[int] = (),
    highlight_first_row: bool = False,
    empty_text: str = "Run the workflow to populate this table.",
) -> str:
    """HTML table with right-aligned monospace numeric columns."""
    if not rows:
        return f'<div class="empty"><strong>No data yet.</strong> {html.escape(empty_text)}</div>'

    numeric_set = set(numeric_cols)

    head_cells = "".join(
        f'<th class="numeric">{html.escape(h)}</th>' if idx in numeric_set
        else f"<th>{html.escape(h)}</th>"
        for idx, h in enumerate(headers)
    )

    body_rows: list[str] = []
    for row_idx, row in enumerate(rows):
        cls = ' class="is-best"' if highlight_first_row and row_idx == 0 else ""
        cells = "".join(
            f'<td class="numeric">{cell}</td>' if idx in numeric_set else f"<td>{cell}</td>"
            for idx, cell in enumerate(row)
        )
        body_rows.append(f"<tr{cls}>{cells}</tr>")

    return (
        f'<table><thead><tr>{head_cells}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def render_metric_card(label: str, value: str, *, delta: str | None = None) -> str:
    delta_html = f'<span class="delta">{html.escape(delta)}</span>' if delta else ""
    return (
        '<div class="card">'
        f'<span class="label">{html.escape(label)}</span>'
        f'<span class="value">{html.escape(value)}</span>'
        f"{delta_html}"
        "</div>"
    )


def render_figure(src: str, caption: str) -> str:
    return (
        '<figure class="figure">'
        f'<img src="{html.escape(src)}" alt="{html.escape(caption)}">'
        f'<figcaption>{html.escape(caption)}</figcaption>'
        "</figure>"
    )


def render_page(
    *,
    title: str,
    css_href: str,
    body: str,
    topbar_links: Sequence[tuple[str, str]] = (),
) -> str:
    """Wrap a body fragment in the standard <html> shell."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body>
  <div class="shell">
    {render_topbar(links=topbar_links)}
    {body}
    {render_footer()}
  </div>
</body>
</html>
"""


def relative_to(base_dir: Path, target: Path | None) -> str | None:
    """``os.path.relpath`` but tolerant of ``None`` and forced to forward slashes."""
    if target is None:
        return None
    rel = os.path.relpath(target, start=base_dir)
    return rel.replace(os.sep, "/")
