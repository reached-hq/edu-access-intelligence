"""Command line for ingestion. Run from the repository root.

    python -m src.ingestion.cli ingest --source deped_enrollment
    python -m src.ingestion.cli ingest --source psa_poverty_stat
    python -m src.ingestion.cli status --source deped_enrollment
    python -m src.ingestion.cli columns
    python -m src.ingestion.cli ddl    --source deped_enrollment > etl/02_bronze/01_create_deped_enrollment_raw.sql
    python -m src.ingestion.cli gate   --source deped_enrollment > etl/02_bronze/90_validate_deped_enrollment_raw.sql

Locally the tables live in a DuckDB file (default local_state/edu_access.duckdb,
git-ignored) and raw files are read from RAW_DATA_DIR. On Databricks the job runs
this file with --backend spark and --landing /Volumes/edu_access/00-source/raw
(databricks.yml). Exit codes: 0 every
delivery loaded or was already loaded; 1 a delivery failed or was blocked, or
the Bronze gate failed; 2 configuration error; 3 environment error (missing
landing folder, unreadable database).
"""

import argparse
import inspect
import os
import sys
from pathlib import Path

# Resolved from this file's compiled code, not from __file__: Databricks runs a
# job's Python file with exec(compile(source, path, "exec")), which defines no
# __file__ (and no __package__). Putting the repository root on the path lets
# `src.ingestion` import when the file is run directly rather than with -m.
REPO_ROOT = Path(inspect.currentframe().f_code.co_filename).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion import bronze, control
from src.ingestion.contract import load_source_config
from src.ingestion.errors import (
    EXIT_BATCH_FAILED, EXIT_CONFIG_ERROR, EXIT_ENVIRONMENT_ERROR, EXIT_OK, IngestionError,
)
from src.ingestion.pipeline import IngestionRun
from src.ingestion.revision import resolve_code_revision
from src.ingestion.store import table_name

DEFAULT_DB = REPO_ROOT / "local_state" / "edu_access.duckdb"


def _store(args):
    try:
        if args.backend == "spark":
            from pyspark.sql import SparkSession

            from src.ingestion.store import SparkStore
            return SparkStore(SparkSession.builder.getOrCreate())
        from src.ingestion.store import DuckDBStore
        return DuckDBStore(args.db)
    except Exception as e:
        where = "Spark (is this running on Databricks?)" if args.backend == "spark" else args.db
        raise IngestionError("setup", "store_unavailable", f"cannot open {where}: {e}")


def cmd_ingest(args):
    landing = args.landing or os.environ.get("RAW_DATA_DIR")
    if not landing:
        raise IngestionError("setup", "missing_landing", "set --landing or RAW_DATA_DIR to the raw data root.")
    revision = resolve_code_revision(REPO_ROOT, args.code_revision, require_commit=args.environment != "local")
    store = _store(args)
    try:
        run = IngestionRun(store, REPO_ROOT, args.source, Path(landing).expanduser(), args.environment,
                           revision, rerun_batch_ids=args.rerun, run_gate=not args.no_gate,
                           setup_tables=not args.no_setup, job_run_id=args.job_run_id)
        summary = run.execute()
    finally:
        store.close()
    print(f"run {summary.run_id}  source={args.source}  environment={args.environment}  code_revision={revision}")
    for o in summary.outcomes:
        print(f"  {o.batch_id:52} {o.action:6} {o.load_type or '-':11} {o.outcome:9} "
              f"inserted={o.rows_inserted if o.rows_inserted is not None else '-':>6} "
              f"bronze={o.bronze_rows if o.bronze_rows is not None else '-':>6}"
              + (f"\n      {o.message}" if o.outcome in ("failed", "blocked") or o.action == "skip" and o.message else ""))
    if summary.missing_deliveries:
        print(f"  WARN approved but not in the landing folder: {', '.join(summary.missing_deliveries)}")
    if summary.gate_error:
        print(f"  Bronze gate: FAILED\n      {summary.gate_error}")
    print(f"status: {summary.status}")
    return EXIT_OK if summary.status == "succeeded" else EXIT_BATCH_FAILED


def cmd_status(args):
    config, _ = load_source_config(REPO_ROOT, args.source)
    store = _store(args)
    try:
        # The period is the school year, or the estimate years for a workbook source.
        rows = store.records(
            f"SELECT batch_id, COALESCE(school_year, estimate_years_covered) AS period, delivery_version, load_type, "
            f"status, attempt_count, source_rows, bronze_rows, error_code "
            f"FROM {table_name(control.SCHEMA, control.BATCHES)} "
            f"WHERE source_id = '{config['source_id']}' ORDER BY period, delivery_version, batch_id")
    except Exception:
        print("No control tables yet: nothing has been ingested into this database.")
        return EXIT_OK
    finally:
        store.close()
    print(f"{'batch_id':52} {'period':14} {'ver':>3} {'load_type':11} {'status':10} {'tries':>5} {'source':>7} {'bronze':>7}  error")
    for r in rows:
        print(f"{r['batch_id']:52} {r['period'] or '-':14} {r['delivery_version'] or '-':>3} "
              f"{r['load_type'] or '-':11} {r['status']:10} {r['attempt_count']:>5} "
              f"{r['source_rows'] if r['source_rows'] is not None else '-':>7} "
              f"{r['bronze_rows'] if r['bronze_rows'] is not None else '-':>7}  {r['error_code'] or ''}")
    return EXIT_OK


def cmd_columns(args):
    """Add the control-table columns added after the tables were first created (ADDED_COLUMNS).
    The job runs this between the control tables and the views that read those columns."""
    store = _store(args)
    try:
        control.add_missing_columns(store)
    finally:
        store.close()
    return EXIT_OK


def cmd_ddl(args):
    config, _ = load_source_config(REPO_ROOT, args.source)
    sys.stdout.write(bronze.bronze_ddl(config))
    return EXIT_OK


def cmd_gate(args):
    config, _ = load_source_config(REPO_ROOT, args.source)
    sys.stdout.write(bronze.bronze_gate(config))
    return EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m src.ingestion.cli", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="discover, validate, and load approved deliveries into Bronze")
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--landing", help="raw data root holding the publisher folders (default: RAW_DATA_DIR)")
    ingest.add_argument("--environment", default="local", choices=["local", "dev", "prod"])
    ingest.add_argument("--code-revision", help="commit SHA; required off local, taken from git locally")
    ingest.add_argument("--rerun", action="append", default=[], metavar="BATCH_ID",
                        help="validate and merge a succeeded batch again (adds no rows); repeatable")
    ingest.add_argument("--no-gate", action="store_true",
                        help="leave the Bronze gate to the job task that runs it as SQL right after this one")
    ingest.add_argument("--no-setup", action="store_true",
                        help="require upstream SQL tasks to have created the control and Bronze tables")
    ingest.add_argument("--job-run-id",
                        help="Databricks job run id, stored on pipeline_runs to join the load to its gate task's results")
    ingest.add_argument("--backend", default="duckdb", choices=["duckdb", "spark"],
                        help="duckdb: local file (--db); spark: Unity Catalog tables on Databricks")
    ingest.add_argument("--db", type=Path, default=DEFAULT_DB)
    ingest.set_defaults(func=cmd_ingest)

    status = sub.add_parser("status", help="show every batch of a source and its state")
    status.add_argument("--source", required=True)
    status.add_argument("--backend", default="duckdb", choices=["duckdb", "spark"])
    status.add_argument("--db", type=Path, default=DEFAULT_DB)
    status.set_defaults(func=cmd_status)

    columns = sub.add_parser("columns", help="add control-table columns that existing tables are missing")
    columns.add_argument("--backend", default="duckdb", choices=["duckdb", "spark"])
    columns.add_argument("--db", type=Path, default=DEFAULT_DB)
    columns.set_defaults(func=cmd_columns)

    ddl = sub.add_parser("ddl", help="print the Bronze CREATE TABLE generated from the contract")
    ddl.add_argument("--source", required=True)
    ddl.set_defaults(func=cmd_ddl)

    gate = sub.add_parser("gate", help="print the Bronze gate SQL generated from the contract")
    gate.add_argument("--source", required=True)
    gate.set_defaults(func=cmd_gate)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except IngestionError as e:
        print(f"error: {e}", file=sys.stderr)
        if e.stage == "config":
            return EXIT_CONFIG_ERROR
        if e.stage in ("setup", "discover"):
            return EXIT_ENVIRONMENT_ERROR
        return EXIT_BATCH_FAILED


if __name__ == "__main__":
    exit_code = main()
    # Exit only on failure. Databricks runs this file inside IPython, which
    # reports even SystemExit(0) as a failed task; returning normally is success
    # everywhere, and a nonzero code still fails the task and the shell.
    if exit_code != EXIT_OK:
        sys.exit(exit_code)
