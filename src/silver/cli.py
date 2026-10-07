"""Command line for Silver. Run from the repository root.

    python -m src.silver.cli build      --source deped_enrollment
    python -m src.silver.cli status     --source deped_enrollment
    python -m src.silver.cli sql        --source deped_enrollment > etl/03_silver/01_create_deped_enrollment_clean.sql
    python -m src.silver.cli gate       --source deped_enrollment > etl/03_silver/90_validate_deped_enrollment_clean.sql
    python -m src.silver.cli dictionary --source deped_enrollment > docs/data/silver/deped-enrollment-clean.md

`build` reads Bronze through 01-control.current_batches and rebuilds the
source's Silver tables, or skips when nothing changed since the last
successful build (--force rebuilds anyway). Locally the tables live in the
DuckDB file that ingestion uses (default local_state/edu_access.duckdb); on
Databricks the job runs this file with --backend spark. Exit codes: 0 built or
skipped; 1 the build or its gate failed; 2 configuration error; 3 environment
error.
"""

import argparse
import inspect
import sys
from pathlib import Path

# Resolved from this file's compiled code, not from __file__: Databricks runs a
# job's Python file with exec(compile(source, path, "exec")), which defines no
# __file__ (see src/ingestion/cli.py).
REPO_ROOT = Path(inspect.currentframe().f_code.co_filename).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingestion import control
from src.ingestion.errors import (
    EXIT_BATCH_FAILED, EXIT_CONFIG_ERROR, EXIT_ENVIRONMENT_ERROR, EXIT_OK, IngestionError,
)
from src.ingestion.revision import resolve_code_revision
from src.ingestion.store import table_name
from src.silver.dictionary import dictionary_markdown
from src.silver.run import SilverRun
from src.silver.spec import load_spec
from src.silver.sql import build_sql, gate_sql

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


def cmd_build(args):
    revision = resolve_code_revision(REPO_ROOT, args.code_revision, require_commit=args.environment != "local")
    store = _store(args)
    try:
        summary = SilverRun(store, REPO_ROOT, args.source, args.environment, revision, force=args.force).execute()
    finally:
        store.close()
    print(f"run {summary.run_id}  source={args.source}  environment={args.environment}  code_revision={revision}")
    print(f"  {summary.action or '-'} ({summary.reason or '-'})  batches: {summary.input_batch_ids or '-'}")
    if summary.action == "build" and summary.bronze_rows is not None:
        print(f"  bronze={summary.bronze_rows} clean={summary.clean_rows} quarantined={summary.quarantined_rows}  "
              f"build {summary.build_seconds}s, checks {summary.gate_seconds}s")
    if summary.error:
        print(f"  FAILED: {summary.error}")
    print(f"status: {summary.status}")
    return EXIT_OK if summary.status == "succeeded" else EXIT_BATCH_FAILED


def cmd_status(args):
    store = _store(args)
    try:
        rows = store.records(
            "SELECT b.finished_at_utc, b.action, b.reason, b.outcome, b.bronze_rows, b.clean_rows, b.quarantined_rows, "
            "b.input_batch_ids, b.code_revision "
            f"FROM {table_name(control.SCHEMA, control.BUILDS)} AS b "
            f"WHERE b.source_id = '{args.source}' ORDER BY b.finished_at_utc")
    except Exception:
        print("No Silver runs yet in this database.")
        return EXIT_OK
    finally:
        store.close()
    print(f"{'finished (UTC)':26} {'action':6} {'reason':24} {'outcome':9} {'bronze':>7} {'clean':>7} {'quar.':>5}  revision")
    for r in rows:
        print(f"{str(r['finished_at_utc'])[:26]:26} {r['action']:6} {r['reason']:24} {r['outcome']:9} "
              f"{r['bronze_rows'] if r['bronze_rows'] is not None else '-':>7} "
              f"{r['clean_rows'] if r['clean_rows'] is not None else '-':>7} "
              f"{r['quarantined_rows'] if r['quarantined_rows'] is not None else '-':>5}  {r['code_revision'][:12]}")
    return EXIT_OK


def cmd_print(generate):
    def run(args):
        sys.stdout.write(generate(load_spec(REPO_ROOT, args.source)))
        return EXIT_OK
    return run


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m src.silver.cli", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="rebuild the source's Silver tables from current Bronze batches, or skip")
    build.add_argument("--source", required=True)
    build.add_argument("--environment", default="local", choices=["local", "dev", "prod"])
    build.add_argument("--code-revision", help="commit SHA; required off local, taken from git locally")
    build.add_argument("--force", action="store_true", help="rebuild even if nothing changed")
    build.add_argument("--backend", default="duckdb", choices=["duckdb", "spark"])
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    build.set_defaults(func=cmd_build)

    status = sub.add_parser("status", help="show every Silver run of a source: built or skipped, and counts")
    status.add_argument("--source", required=True)
    status.add_argument("--backend", default="duckdb", choices=["duckdb", "spark"])
    status.add_argument("--db", type=Path, default=DEFAULT_DB)
    status.set_defaults(func=cmd_status)

    for name, generate, text in (("sql", build_sql, "the Silver build SQL"), ("gate", gate_sql, "the Silver gate SQL"),
                                 ("dictionary", dictionary_markdown, "the Silver data dictionary (Markdown)")):
        p = sub.add_parser(name, help=f"print {text} generated from the contract and the mapping")
        p.add_argument("--source", required=True)
        p.set_defaults(func=cmd_print(generate))

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except IngestionError as e:
        print(f"error: {e}", file=sys.stderr)
        if e.stage == "config":
            return EXIT_CONFIG_ERROR
        if e.stage == "setup":
            return EXIT_ENVIRONMENT_ERROR
        return EXIT_BATCH_FAILED


if __name__ == "__main__":
    exit_code = main()
    # Exit only on failure: Databricks runs this file inside IPython, which
    # reports even SystemExit(0) as a failed task.
    if exit_code != EXIT_OK:
        sys.exit(exit_code)
