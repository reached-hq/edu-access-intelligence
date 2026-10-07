"""One Silver run for one source: decide, then build and check, or skip.

Skip when nothing changed. The Silver tables are rebuilt only when the current
Bronze batches (01-control.current_batches) or the Silver rules (the committed
build and gate SQL) differ from the last successful build, or when the previous
Silver run did not finish. That is the compute saving on Free Edition: a run
with nothing to do reads two control tables and writes three rows.

When something changed, both tables are rebuilt from the current batches with
CREATE OR REPLACE TABLE ... AS SELECT. At about 180,000 rows a full rebuild is
the simplest design that is atomic per table and gives the same result however
often it runs; a revised delivery replaces its school year because
current_batches moves to the new version.

The order of writes matters, because Delta commits one table at a time:

1. pipeline_runs: the run is 'running';
2. both Silver tables are replaced (two commits);
3. column types are checked and the gate writes its results; any FAIL raises;
4. layer_builds records what was built, from which batches, with which rules;
5. pipeline_runs: the run is 'succeeded' or 'failed', written last.

If the process dies anywhere before 5, the run stays 'running', and the next
run rebuilds rather than skips. Gold must read Silver only when the latest
silver_build run of the source succeeded (docs/operations/silver.md).
"""

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.ingestion import control
from src.ingestion.errors import IngestionError
from src.ingestion.pipeline import ENVIRONMENTS, MAX_MESSAGE, utc_now
from src.ingestion.store import table_name
from src.ingestion.validate import FAIL, PASS
from src.silver.sql import dq_table_name
from src.silver.spec import SCHEMA, load_spec

PIPELINE_NAME = "silver_build"
LAYER = "silver"

# Engine type names, normalized to the spec's (Spark simpleString) names.
TYPE_NAMES = {
    "varchar": "string", "string": "string", "integer": "int", "int": "int", "bigint": "bigint",
    "boolean": "boolean", "timestamp": "timestamp", "varchar[]": "array<string>", "array<string>": "array<string>",
}


@dataclass
class SilverSummary:
    run_id: str
    status: str
    action: str = None
    reason: str = None
    input_batch_ids: str = None
    bronze_rows: int = None
    clean_rows: int = None
    quarantined_rows: int = None
    build_seconds: float = None
    gate_seconds: float = None
    error: str = None


def rules_fingerprint(paths):
    digest = hashlib.sha256()
    for path in paths:
        digest.update(Path(path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class SilverRun:
    def __init__(self, store, repo_root, source_id, environment, code_revision, force=False, hook=None):
        if environment not in ENVIRONMENTS:
            raise IngestionError("config", "unknown_environment", f"environment must be one of {ENVIRONMENTS}.")
        self.store = store
        self.repo_root = Path(repo_root)
        self.source_id = source_id
        self.environment = environment
        self.code_revision = code_revision
        self.force = force
        self.hook = hook or (lambda stage: None)
        self.spec = load_spec(repo_root, source_id)
        folder = self.repo_root / "etl" / "03_silver"
        self.build_file = folder / f"01_create_{self.spec.clean_table}.sql"
        self.gate_file = folder / f"90_validate_{self.spec.clean_table}.sql"
        for path in (self.build_file, self.gate_file):
            if not path.is_file():
                raise IngestionError("config", "missing_sql", f"{path.relative_to(self.repo_root)} does not exist.")
        self.fingerprint = rules_fingerprint([self.build_file, self.gate_file])
        self.run_id = str(uuid.uuid4())
        self.clean = dq_table_name(self.spec.clean_table)
        self.quarantine = dq_table_name(self.spec.quarantine_table)

    # -- run ------------------------------------------------------------------

    def execute(self):
        control.create_tables(self.store, self.repo_root)
        started = utc_now()
        run = {
            "run_id": self.run_id, "pipeline_name": PIPELINE_NAME, "source_id": self.source_id,
            "environment": self.environment, "status": "running", "started_at_utc": started,
            "finished_at_utc": None, "duration_seconds": None, "deliveries_found": None,
            "batches_loaded": None, "batches_skipped": None, "batches_failed": None, "batches_blocked": 0,
            "failure_stage": None, "error_message": None, "code_revision": self.code_revision,
        }
        control.save_run(self.store, run)
        summary = SilverSummary(self.run_id, "running")
        build = {"started_at_utc": started, "cleaned_at_utc": None, "failure_stage": None, "error_message": None}

        try:
            batches = self._current_batches()
            summary.input_batch_ids = ",".join(batches)
            summary.action, summary.reason = self._decide(batches)
            if summary.action == "build":
                self._build(summary, build)
        except IngestionError as e:
            build.update(failure_stage=e.stage, error_message=e.message[:MAX_MESSAGE])
        except Exception as e:  # recorded, so the run row never stays 'running' after a handled error
            build.update(failure_stage="unexpected", error_message=f"{type(e).__name__}: {e}"[:MAX_MESSAGE])

        failed = build["failure_stage"] is not None
        if summary.action:
            self._record_build(summary, build, "failed" if failed else ("skipped" if summary.action == "skip" else "succeeded"))
        n = len(summary.input_batch_ids.split(",")) if summary.input_batch_ids else 0
        finished = utc_now()
        run.update(
            status="failed" if failed else "succeeded", finished_at_utc=finished,
            duration_seconds=(finished - started).total_seconds(), deliveries_found=n,
            batches_loaded=n if summary.action == "build" and not failed else 0,
            batches_skipped=n if summary.action == "skip" and not failed else 0,
            batches_failed=n if failed else 0,
            failure_stage=build["failure_stage"], error_message=build["error_message"],
        )
        control.save_run(self.store, run)  # last write: the commit marker
        summary.status, summary.error = run["status"], build["error_message"]
        return summary

    # -- decide ------------------------------------------------------------------

    def _current_batches(self):
        rows = self.store.query(
            f"SELECT batch_id FROM {table_name(control.SCHEMA, 'current_batches')} "
            f"WHERE source_id = '{self.source_id}' ORDER BY batch_id")
        if not rows:
            raise IngestionError("decide", "no_current_batches",
                                 f"no succeeded Bronze batch for {self.source_id}; load Bronze first.")
        return [r[0] for r in rows]

    def _decide(self, batches):
        """('build' | 'skip', reason). Skips only when the last run finished and nothing it built from changed."""
        if self.force:
            return "build", "forced"
        last = self.store.records(
            f"SELECT input_batch_ids, rules_fingerprint FROM {table_name(control.SCHEMA, control.BUILDS)} "
            f"WHERE layer = '{LAYER}' AND source_id = '{self.source_id}' AND action = 'build' AND outcome = 'succeeded' "
            "ORDER BY finished_at_utc DESC LIMIT 1")
        if not last:
            return "build", "first_build"
        previous = self.store.query(
            f"SELECT status FROM {table_name(control.SCHEMA, control.RUNS)} "
            f"WHERE pipeline_name = '{PIPELINE_NAME}' AND source_id = '{self.source_id}' AND run_id <> '{self.run_id}' "
            "ORDER BY started_at_utc DESC LIMIT 1")
        if not previous or previous[0][0] != "succeeded":
            return "build", "previous_run_incomplete"
        if not (self._exists(self.spec.clean_table) and self._exists(self.spec.quarantine_table)):
            return "build", "tables_missing"
        if last[0]["input_batch_ids"] != ",".join(batches):
            return "build", "bronze_changed"
        if last[0]["rules_fingerprint"] != self.fingerprint:
            return "build", "rules_changed"
        return "skip", "unchanged"

    def _exists(self, table):
        try:
            return bool(self.store.columns(SCHEMA, table))
        except Exception:  # Spark raises for a missing table; DuckDB returns no columns
            return False

    # -- build --------------------------------------------------------------------

    def _build(self, summary, build):
        cleaned_at = utc_now()
        build["cleaned_at_utc"] = cleaned_at
        self.store.stage("silver_run", [("run_id", "string"), ("cleaned_at_utc", "timestamp"), ("code_revision", "string")],
                         [{"run_id": self.run_id, "cleaned_at_utc": cleaned_at, "code_revision": self.code_revision}])
        t0 = time.monotonic()
        try:
            self.store.run_file(self.build_file)
        except Exception as e:
            raise IngestionError("build", "build_failed", f"{self.build_file.name}: {e}")
        summary.build_seconds = round(time.monotonic() - t0, 3)
        self.hook("after_build")

        t0 = time.monotonic()
        self._check_types()
        try:
            self.store.run_file(self.gate_file, {"run_id": self.run_id, "code_revision": self.code_revision})
            gate_error = None
        except Exception as e:  # the gate raises on any FAIL; a broken gate must fail the run too
            gate_error = str(e)
        summary.gate_seconds = round(time.monotonic() - t0, 3)
        summary.bronze_rows, summary.clean_rows, summary.quarantined_rows = self._counts()
        if gate_error:
            raise IngestionError("gate", "gate_failed", gate_error)

    def _check_types(self):
        """The CTAS infers types from expressions; prove each column has the type the spec promises."""
        results = []
        for table, expected in ((self.spec.clean_table, self.spec.clean_columns()),
                                (self.spec.quarantine_table, self.spec.quarantine_columns())):
            actual = [(name, TYPE_NAMES.get(kind.lower(), kind.lower())) for name, kind in self.store.columns(SCHEMA, table)]
            wrong = len([1 for pair in expected if pair not in actual]) + abs(len(actual) - len(expected))
            results.append((dq_table_name(table), "columns_typed", PASS if wrong == 0 else FAIL,
                            f"{len(expected)} columns as specified", f"{wrong} differ"))
        now = utc_now()
        control.add_checks(self.store, [{
            "run_id": self.run_id, "batch_id": None, "source_id": self.source_id, "layer": LAYER,
            "table_name": table, "check_name": name, "status": status, "expected": expected,
            "actual": actual, "checked_at_utc": now, "code_revision": self.code_revision,
        } for table, name, status, expected, actual in results])

    def _counts(self):
        bronze = self.store.query(
            f"SELECT COUNT(*) FROM edu_access.`02-bronze`.{self.spec.bronze_table} AS r "
            f"JOIN {table_name(control.SCHEMA, 'current_batches')} AS c ON r.batch_id = c.batch_id "
            f"WHERE c.source_id = '{self.source_id}'")[0][0]
        clean = self.store.query(f"SELECT COUNT(*) FROM {table_name(SCHEMA, self.spec.clean_table)}")[0][0]
        quarantined = self.store.query(f"SELECT COUNT(*) FROM {table_name(SCHEMA, self.spec.quarantine_table)}")[0][0]
        return bronze, clean, quarantined

    # -- record --------------------------------------------------------------------

    def _record_build(self, summary, build, outcome):
        finished = utc_now()
        control.add_layer_build(self.store, {
            "run_id": self.run_id, "layer": LAYER, "source_id": self.source_id, "target_table": self.clean,
            "quarantine_table": self.quarantine, "action": summary.action, "reason": summary.reason,
            "outcome": outcome, "input_batch_ids": summary.input_batch_ids, "rules_fingerprint": self.fingerprint,
            "bronze_rows": summary.bronze_rows, "clean_rows": summary.clean_rows,
            "quarantined_rows": summary.quarantined_rows, "cleaned_at_utc": build["cleaned_at_utc"],
            "build_seconds": summary.build_seconds, "gate_seconds": summary.gate_seconds,
            "started_at_utc": build["started_at_utc"], "finished_at_utc": finished,
            "duration_seconds": (finished - build["started_at_utc"]).total_seconds(),
            "failure_stage": build["failure_stage"], "error_message": build["error_message"],
            "environment": self.environment, "code_revision": self.code_revision,
        })
