"""Load raw exports into DuckDB and build the SQL models in dependency order."""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql"
LAYERS = ("staging", "intermediate", "marts")


def connect(db_path: Path | str = ":memory:") -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path))


def load_raw(con: duckdb.DuckDBPyConnection, raw_dir: Path = RAW_DIR) -> list[str]:
    """Land every CSV as an all-VARCHAR raw table; typing happens in staging."""
    tables = []
    for csv in sorted(raw_dir.glob("*.csv")):
        table = f"raw_{csv.stem}"
        con.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            f"SELECT * FROM read_csv(?, header = true, all_varchar = true)",
            [str(csv)],
        )
        tables.append(table)
    return tables


def build_models(con: duckdb.DuckDBPyConnection, sql_dir: Path = SQL_DIR) -> list[str]:
    """Each .sql file becomes a table named after the file. Layers run in order."""
    built = []
    for layer in LAYERS:
        for sql_file in sorted((sql_dir / layer).glob("*.sql")):
            con.execute(f"CREATE OR REPLACE TABLE {sql_file.stem} AS {sql_file.read_text()}")
            built.append(sql_file.stem)
    return built


def build(db_path: Path | str = ":memory:") -> duckdb.DuckDBPyConnection:
    con = connect(db_path)
    load_raw(con)
    build_models(con)
    return con
