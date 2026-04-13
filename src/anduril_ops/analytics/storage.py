from __future__ import annotations

from pathlib import Path
from typing import Mapping

import duckdb
import pandas as pd


def persist_tables_to_duckdb(
    output_dir: Path,
    duckdb_path: Path,
    tables: Mapping[str, pd.DataFrame],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(duckdb_path)) as con:
        for name, df in tables.items():
            parquet_path = output_dir / f"{name}.parquet"
            relation_name = f"{name}_df"
            con.register(relation_name, df)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM {relation_name}")
            con.execute(f"COPY {name} TO '{parquet_path.as_posix()}' (FORMAT PARQUET)")
            con.unregister(relation_name)
