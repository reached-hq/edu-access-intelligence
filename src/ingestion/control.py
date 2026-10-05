"""Reads and writes of the control tables in `01-control` (etl/01_control/).

Each function is one statement: a MERGE for current state (pipeline_runs,
ingestion_batches), an INSERT for the append-only logs (attempts, data-quality
results). Values reach SQL only through staged rows, never pasted into the
statement, so an error message with a quote in it cannot break a write.
"""

from pathlib import Path

from src.ingestion.store import table_name

SCHEMA = "01-control"
RUNS = "pipeline_runs"
BATCHES = "ingestion_batches"
ATTEMPTS = "ingestion_batch_attempts"
DQ = "data_quality_results"


def create_tables(store, repo_root):
    for path in sorted((Path(repo_root) / "etl" / "01_control").glob("[0-8]*.sql")):
        store.run_file(path)


def _upsert(store, table, key, row):
    columns = store.columns(SCHEMA, table)
    store.stage(f"{table}_stage", columns, [row])
    store.sql(
        f"MERGE INTO {table_name(SCHEMA, table)} AS t USING {table}_stage AS s ON t.{key} = s.{key} "
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"
    )


def _append(store, table, rows):
    if not rows:
        return
    columns = store.columns(SCHEMA, table)
    store.stage(f"{table}_stage", columns, rows)
    names = ", ".join(f"`{c}`" for c, _ in columns)
    store.sql(f"INSERT INTO {table_name(SCHEMA, table)} ({names}) SELECT {names} FROM {table}_stage")


def save_run(store, row):
    _upsert(store, RUNS, "run_id", row)


def save_batch(store, row):
    _upsert(store, BATCHES, "batch_id", row)


def add_attempt(store, row):
    _append(store, ATTEMPTS, [row])


def add_checks(store, rows):
    _append(store, DQ, rows)


def find_batch(store, archive_sha256):
    rows = store.records(
        f"SELECT * FROM {table_name(SCHEMA, BATCHES)} WHERE archive_sha256 = '{archive_sha256}'")
    return rows[0] if rows else None


def succeeded_years(store, source_id):
    rows = store.query(
        f"SELECT DISTINCT school_year FROM {table_name(SCHEMA, BATCHES)} "
        f"WHERE source_id = '{source_id}' AND status = 'succeeded'")
    return {r[0] for r in rows}
