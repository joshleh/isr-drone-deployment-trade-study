from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd


def _relative_paths(base_dir: Path, paths: Iterable[Path]) -> list[str]:
    rels: list[str] = []
    for path in paths:
        rels.append(os.path.relpath(path, start=base_dir))
    return rels


def build_static_dashboard(
    duckdb_path: Path,
    html_path: Path,
    summary_table: str,
    top_table: str,
    title: str,
    subtitle: str,
    figure_paths: Iterable[Path],
) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(duckdb_path), read_only=True) as con:
        summary = con.execute(summary_table).fetchdf()
        top_configs = con.execute(top_table).fetchdf()

    figure_links = _relative_paths(html_path.parent, figure_paths)
    cards = "".join(
        f"<div class='card'><div class='label'>{row.metric}</div><div class='value'>{row.value}</div></div>"
        for row in summary.itertuples(index=False)
    )
    figures = "".join(
        f"<section class='figure'><img src='{src}' alt='dashboard figure'><div class='caption'>{Path(src).name}</div></section>"
        for src in figure_links
    )

    dashboard = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: #fffaf3;
      --ink: #17313c;
      --muted: #5d6b70;
      --accent: #bf5b04;
      --line: #d9cfbf;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top left, #f9f4ea, var(--bg));
      color: var(--ink);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    h1 {{
      margin: 0;
      font-size: 2.4rem;
    }}
    .subtitle {{
      color: var(--muted);
      margin: 10px 0 24px;
      max-width: 760px;
      line-height: 1.5;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 26px;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 24px rgba(23, 49, 60, 0.07);
    }}
    .card {{
      padding: 16px 18px;
    }}
    .label {{
      font-size: 0.84rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .value {{
      font-size: 1.65rem;
      margin-top: 8px;
      color: var(--accent);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      padding: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 10px 8px;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .figures {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}
    .figure {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 24px rgba(23, 49, 60, 0.07);
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: white;
    }}
    .caption {{
      padding: 12px 14px 16px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    @media (max-width: 860px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <section class="cards">{cards}</section>
    <section class="layout">
      <article class="panel">
        <h2>Top Configurations</h2>
        {top_configs.to_html(index=False, classes="table", border=0)}
      </article>
      <article class="panel">
        <h2>Data Assets</h2>
        <p>This dashboard is backed by DuckDB and Parquet exports so the analysis can feed downstream BI, notebooks, or lightweight ETL work instead of living only in CSVs.</p>
        <p><strong>DuckDB:</strong> {duckdb_path.name}</p>
        <p><strong>HTML:</strong> {html_path.name}</p>
      </article>
    </section>
    <section class="figures">{figures}</section>
  </main>
</body>
</html>"""
    html_path.write_text(dashboard, encoding="utf-8")
