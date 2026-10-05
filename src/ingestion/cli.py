"""Command line for ingestion. Run from the repository root.

    python -m src.ingestion.cli ingest --source deped_enrollment
    python -m src.ingestion.cli status --source deped_enrollment
    python -m src.ingestion.cli ddl    --source deped_enrollment > etl/02_bronze/01_create_deped_enrollment_raw.sql

Locally the tables live in a DuckDB file (default local_state/edu_access.duckdb,
git-ignored) and raw files are read from RAW_DATA_DIR. Exit codes: 0 every
delivery loaded or was already loaded; 1 a delivery failed or was blocked, or
the Bronze gate failed; 2 configuration error; 3 environment error (missing
landing folder, unreadable database).
"""

import argparse
import os
import sys
from pathlib import Path

from src.ingestion import bronze, control
from src.ingestion.contract import load_source_config
from src.ingestion.errors import (
    EXIT_BATCH_FAILED, EXIT_CONFIG_ERROR, EXIT_ENVIRONMENT_ERROR, EXIT_OK, IngestionError,
)
from src.ingestion.pipeline import IngestionRun
from src.ingestion.revision import resolve_code_revision
from src.ingestion.store import table_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "local_state" / "edu_access.duckdb"


def _store(args):
    from src.ingestion.store import DuckDBStore
    try:
        return DuckDBStore(args.db)
    except Exception as e:
        raise IngestionError("setup", "store_unavailable", f"cannot open {args.db}: {e}")


def cmd_ingest(args):
    landing = args.landing or os.environ.get("RAW_DATA_DIR")
    if not landing:
        raise IngestionError("setup", "missing_landing", "set --landing or RAW_DATA_DIR to the raw data root.")
    revision = resolve_code_revision(REPO_ROOT, args.code_revision, require_commit=args.environment != "local")
    store = _store(args)
    try:
        run = IngestionRun(store, REPO_ROOT, args.source, Path(landing).expanduser(), args.environment,
                           revision, rerun_batch_ids=args.rerun)
        summary = run.execute()
    finally:
        store.close()
    print(f"run {summary.run_id}  source={args.source}  environment={args.environment}  code_revision={revision}")
    for o in summary.outcomes:
        print(f"  {o.batch_id:44} {o.action:6} {o.load_type or '-':11} {o.outcome:9} "
              f"inserted={o.rows_inserted if o.rows_inserted is not None else '-':>6} "
              f"bronze={o.bronze_rows if o.bronze_rows is not None else '-':>6}"
              + (f"\n      {o.message}" if o.outcome in ("failed", "blocked") or o.action == "skip" and o.message else ""))
    if summary.gate_error:
        print(f"  Bronze gate: FAILED\n      {summary.gate_error}")
    print(f"status: {summary.status}")
    return EXIT_OK if summary.status == "succeeded" else EXIT_BATCH_FAILED


def cmd_status(args):
    config, _ = load_source_config(REPO_ROOT, args.source)
    store = _store(args)
    try:
        rows = store.records(
            f"SELECT batch_id, school_year, delivery_version, load_type, status, attempt_count, source_rows, "
            f"bronze_rows, error_code FROM {table_name(control.SCHEMA, control.BATCHES)} "
            f"WHERE source_id = '{config['source_id']}' ORDER BY school_year, delivery_version, batch_id")
    except Exception:
        print("No control tables yet: nothing has been ingested into this database.")
        return EXIT_OK
    finally:
        store.close()
    print(f"{'batch_id':44} {'year':7} {'ver':>3} {'load_type':11} {'status':10} {'tries':>5} {'source':>7} {'bronze':>7}  error")
    for r in rows:
        print(f"{r['batch_id']:44} {r['school_year'] or '-':7} {r['delivery_version'] or '-':>3} "
              f"{r['load_type'] or '-':11} {r['status']:10} {r['attempt_count']:>5} "
              f"{r['source_rows'] if r['source_rows'] is not None else '-':>7} "
              f"{r['bronze_rows'] if r['bronze_rows'] is not None else '-':>7}  {r['error_code'] or ''}")
    return EXIT_OK


def cmd_ddl(args):
    config, _ = load_source_config(REPO_ROOT, args.source)
    sys.stdout.write(bronze.bronze_ddl(config))
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
    ingest.add_argument("--db", type=Path, default=DEFAULT_DB)
    ingest.set_defaults(func=cmd_ingest)

    status = sub.add_parser("status", help="show every batch of a source and its state")
    status.add_argument("--source", required=True)
    status.add_argument("--db", type=Path, default=DEFAULT_DB)
    status.set_defaults(func=cmd_status)

    ddl = sub.add_parser("ddl", help="print the Bronze CREATE TABLE generated from the contract")
    ddl.add_argument("--source", required=True)
    ddl.set_defaults(func=cmd_ddl)

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
    sys.exit(main())
