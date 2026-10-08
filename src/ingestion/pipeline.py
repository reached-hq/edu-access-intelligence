"""One ingestion run for one source: discover, decide, validate, load, reconcile, record.

The flow is the same for every source; what differs by delivery format (a
DepEd zip or a PSA workbook) is in formats.py.

The order of writes matters because Delta commits one table at a time:

1. the batch is marked `validating`, then `loading` (ingestion_batches);
2. the rows are merged into Bronze (one atomic MERGE);
3. Bronze is reconciled against the file;
4. only then is the batch marked `succeeded`.

If the process dies between 2 and 4, the batch stays `loading`. Its rows may
be in Bronze, but downstream reads only succeeded batches
(`01-control`.current_batches), and the next run retries it: the MERGE adds
nothing that is already there, reconciliation passes, and the batch succeeds.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.ingestion import bronze, control, formats
from src.ingestion.archive import sha256_file
from src.ingestion.batch import batch_id, choose_action
from src.ingestion.contract import delivery_file, delivery_sha256, find_delivery, load_source_config
from src.ingestion.errors import IngestionError
from src.ingestion.validate import FAIL, PASS, WARN

PIPELINE_NAME = "bronze_ingest"
ENVIRONMENTS = ("local", "dev", "prod")
MAX_MESSAGE = 1000
LOAD_ACTIONS = ("load", "retry", "rerun")


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class BatchOutcome:
    batch_id: str
    archive_name: str
    school_year: str
    action: str
    load_type: str
    outcome: str
    rows_inserted: int = None
    bronze_rows: int = None
    message: str = None


@dataclass
class RunSummary:
    run_id: str
    status: str
    outcomes: list = field(default_factory=list)
    gate_error: str = None
    missing_deliveries: list = field(default_factory=list)


def year_from_archive_name(config, name):
    return formats.ZipCsv(config).period_from_name(name)


def _sort_key(config, path):
    """Oldest period first, so a first run loads in time order: school year from
    the name for zips; for workbooks the approved estimate years, else the name."""
    fmt = formats.for_config(config)
    return (fmt.period_from_name(path.name) or "", path.name)


def discover(config, landing_root):
    """Every delivery file under the source's landing folder that is named like a
    delivery or is an approved delivery under another name. The same bytes in two
    places are one delivery. Ordered oldest period first."""
    fmt = formats.for_config(config)
    root = Path(landing_root) / config["landing_dir"]
    if not root.is_dir():
        raise IngestionError("discover", "missing_landing",
                             f"landing folder {root} does not exist. Set --landing (or RAW_DATA_DIR) to the raw root.")
    approved = {delivery_sha256(d) for d in config["deliveries"]}
    pattern = re.compile(config[fmt.pattern_key])
    # Office's lock files ('~$name.xlsx') are not deliveries.
    paths = sorted(p for p in root.rglob(fmt.glob) if not p.name.startswith("~$"))
    named = [path for path in paths if pattern.match(path.name)]
    differently_named = [path for path in paths if not pattern.match(path.name)]
    found = {}
    for path in named:
        digest = sha256_file(path)
        if digest not in found:
            found[digest] = path
    missing_approved = approved - found.keys()
    for path in differently_named:
        if not missing_approved:
            break
        digest = sha256_file(path)
        if digest in missing_approved:
            found[digest] = path
            missing_approved.remove(digest)
    def period(item):
        delivery = find_delivery(config, item[0])
        if delivery and "estimate_years" in delivery:
            return (min(delivery["estimate_years"]), item[1].name)
        return _sort_key(config, item[1])

    return sorted(found.items(), key=period)


class IngestionRun:
    def __init__(self, store, repo_root, source_id, landing_root, environment, code_revision,
                 rerun_batch_ids=(), hook=None, run_gate=True, setup_tables=True):
        if environment not in ENVIRONMENTS:
            raise IngestionError("config", "unknown_environment", f"environment must be one of {ENVIRONMENTS}.")
        self.store = store
        self.repo_root = Path(repo_root)
        self.landing_root = Path(landing_root)
        self.environment = environment
        self.code_revision = code_revision
        self.rerun_batch_ids = set(rerun_batch_ids)
        self.hook = hook or (lambda stage: None)
        # Off when the job runs the source's Bronze gate as its own SQL task
        # right after this one (databricks.yml); the gate then fails that task.
        self.run_gate = run_gate
        # Off when databricks.yml runs the control and source DDL as explicit
        # upstream SQL tasks. Standalone CLI runs keep automatic setup.
        self.setup_tables = setup_tables
        self.config, self.registry_entry = load_source_config(repo_root, source_id)
        self.format = formats.for_config(self.config)
        self.source_id = source_id
        if environment == "prod" and self.registry_entry["status"] != "accepted":
            raise IngestionError("config", "source_not_accepted",
                                 f"{source_id} is '{self.registry_entry['status']}'. Only accepted sources load into prod; "
                                 "use dev until the team accepts it.")
        table = self.config["bronze_table"]
        ddl_matches = sorted((self.repo_root / "etl" / "02_bronze").glob(f"[0-8][0-9]_create_{table}.sql"))
        if len(ddl_matches) != 1:
            found = [str(path.relative_to(self.repo_root)) for path in ddl_matches]
            raise IngestionError(
                "config",
                "missing_sql" if not found else "ambiguous_sql",
                f"expected exactly one NN_create_{table}.sql in etl/02_bronze; found {found}.",
            )
        self.bronze_ddl = ddl_matches[0]
        self.bronze_gate = self.repo_root / "etl" / "02_bronze" / f"90_validate_{table}.sql"
        for path in (self.bronze_ddl, self.bronze_gate):
            if not path.is_file():
                raise IngestionError("config", "missing_sql", f"{path.relative_to(self.repo_root)} does not exist.")
        self.run_id = str(uuid.uuid4())
        self.dq_table = f"edu_access.02-bronze.{table}"

    # -- run ------------------------------------------------------------------

    def execute(self):
        if self.setup_tables:
            control.create_tables(self.store, self.repo_root)
            self.store.run_file(self.bronze_ddl)
        bronze.add_missing_columns(self.store, self.config)

        started = utc_now()
        run = {
            "run_id": self.run_id, "pipeline_name": PIPELINE_NAME, "source_id": self.source_id,
            "environment": self.environment, "status": "running", "started_at_utc": started,
            "finished_at_utc": None, "duration_seconds": None, "deliveries_found": None,
            "batches_loaded": None, "batches_skipped": None, "batches_failed": None, "batches_blocked": None,
            "failure_stage": None, "error_message": None, "code_revision": self.code_revision,
        }
        control.save_run(self.store, run)
        summary = RunSummary(self.run_id, "running")

        try:
            deliveries = discover(self.config, self.landing_root)
        except IngestionError as e:
            run.update(failure_stage=e.stage, error_message=e.message[:MAX_MESSAGE])
            self._finish(run, summary, started, deliveries_found=0)
            raise

        if not self._check_approved_present(summary, {sha for sha, _ in deliveries}):
            run.update(failure_stage="discover", error_message=(
                f"approved deliveries missing from the landing folder: {', '.join(summary.missing_deliveries)}. "
                "Upload them to raw storage (never over an existing file), then run again.")[:MAX_MESSAGE])
        for archive_sha256, path in deliveries:
            summary.outcomes.append(self._process(path, archive_sha256))

        if self.run_gate:
            try:
                self.store.run_file(self.bronze_gate, {"run_id": self.run_id, "code_revision": self.code_revision})
            except Exception as e:  # the gate raises on any FAIL; a broken gate must fail the run too
                summary.gate_error = str(e)[:MAX_MESSAGE]
                if not run["failure_stage"]:  # keep an earlier, more specific cause
                    run.update(failure_stage="gate", error_message=summary.gate_error)
        self._finish(run, summary, started, deliveries_found=len(deliveries))
        return summary

    def _finish(self, run, summary, started, deliveries_found):
        counts = {k: sum(1 for o in summary.outcomes if o.outcome == k) for k in ("succeeded", "skipped", "failed", "blocked")}
        failed = counts["failed"] or counts["blocked"] or run["failure_stage"]
        if failed and not run["failure_stage"]:
            first = next(o for o in summary.outcomes if o.outcome in ("failed", "blocked"))
            run.update(failure_stage="batch", error_message=f"{first.batch_id}: {first.message}"[:MAX_MESSAGE])
        finished = utc_now()
        run.update(
            status="failed" if failed else "succeeded", finished_at_utc=finished,
            duration_seconds=(finished - started).total_seconds(), deliveries_found=deliveries_found,
            batches_loaded=counts["succeeded"], batches_skipped=counts["skipped"],
            batches_failed=counts["failed"], batches_blocked=counts["blocked"],
        )
        control.save_run(self.store, run)
        summary.status = run["status"]

    def _check_approved_present(self, summary, found):
        """An approved delivery missing from the landing folder was never uploaded or was lost
        from raw storage. Nothing can be loaded from it, so it is a WARN naming the files, or a
        FAIL that fails the run if the contract sets `require_approved_deliveries` (PSGC: one
        workbook per quarter, so a missing quarter is a gap, not a detail). Returns False on FAIL."""
        approved = self.config["deliveries"]
        summary.missing_deliveries = [delivery_file(d) for d in approved if delivery_sha256(d) not in found]
        missing = ", ".join(summary.missing_deliveries) or "none"
        problem = FAIL if self.config.get("require_approved_deliveries") else WARN
        self._record_checks(None, [("approved_deliveries_present", problem if summary.missing_deliveries else PASS,
                                    len(approved), f"{len(approved) - len(summary.missing_deliveries)}; missing: {missing}")])
        return not (summary.missing_deliveries and problem == FAIL)

    # -- one archive ------------------------------------------------------------

    def _process(self, path, archive_sha256):
        started = utc_now()
        existing = control.find_batch(self.store, archive_sha256)
        delivery = find_delivery(self.config, archive_sha256)
        period = self.format.describe(delivery, path)
        bid = existing["batch_id"] if existing else batch_id(self.source_id, period["period"], archive_sha256)
        batch = dict(existing) if existing else {
            "batch_id": bid, "source_id": self.source_id, "school_year": period["school_year"],
            "logical_dataset": period["logical_dataset"], "estimate_years_covered": period["estimate_years_covered"],
            "source_sheet": period["source_sheet"], "delivery_version": None,
            "supersedes_archive_sha256": None, "load_type": None, "status": None,
            "archive_path": path.relative_to(self.landing_root).as_posix(), "archive_name": path.name,
            "archive_sha256": archive_sha256, "source_file": None, "source_sha256": None, "encoding": None,
            "schema_version": None, "schema_fingerprint": None, "expected_rows": None, "source_rows": None,
            "rows_inserted": None, "bronze_rows": None, "rejected_rows": 0, "attempt_count": 0,
            "first_run_id": self.run_id, "last_run_id": self.run_id, "first_attempt_at_utc": started,
            "last_attempt_at_utc": started, "succeeded_at_utc": None, "failure_stage": None,
            "error_code": None, "error_message": None, "environment": self.environment,
            "code_revision": self.code_revision,
        }
        batch.update(last_run_id=self.run_id, last_attempt_at_utc=started, environment=self.environment,
                     code_revision=self.code_revision)
        ctx = {"batch": batch, "started": started, "path": path}

        if delivery is None:
            return self._refuse(ctx)

        action = choose_action(existing, rerun=bid in self.rerun_batch_ids)
        if action == "skip":
            return self._attempt(ctx, "skip", "skipped", message="already loaded; same SHA-256")

        keep_type = action in ("retry", "rerun") and batch.get("load_type")
        batch.update({k: v for k, v in period.items() if k != "period"})
        batch.update(
            delivery_version=delivery["delivery_version"], supersedes_archive_sha256=delivery["supersedes"],
            load_type=batch["load_type"] if keep_type else self.format.load_type(self.store, self.source_id, delivery),
            expected_rows=self.format.expected_rows(delivery), status="validating", attempt_count=batch["attempt_count"] + 1,
            rows_inserted=None, bronze_rows=None, failure_stage=None, error_code=None, error_message=None,
        )
        control.save_batch(self.store, batch)
        try:
            return self._load(ctx, action, delivery)
        except IngestionError as e:
            return self._fail(ctx, action, e.stage, e.code, e.message)
        except Exception as e:  # recorded, so a crash in one batch does not hide the others
            return self._fail(ctx, action, "unexpected", type(e).__name__, str(e))

    def _refuse(self, ctx):
        """Record an archive that is not an approved delivery: blocked, or skipped if it is a re-zipped copy."""
        batch = ctx["batch"]
        try:
            self.format.identify(ctx["path"])
        except IngestionError as e:
            refusal = e
        else:
            raise AssertionError(f"{ctx['path']} was identified although it is not approved")
        skipped = refusal.code == "repackaged_delivery"
        if not skipped and self.format.blocked_is_revision(self.store, self.source_id, batch, ctx["path"]):
            batch["load_type"] = "revision"  # changed bytes for a period already loaded
        batch.update(status="skipped" if skipped else "blocked", attempt_count=batch["attempt_count"] + 1,
                     failure_stage=None if skipped else refusal.stage, error_code=refusal.code,
                     error_message=refusal.message[:MAX_MESSAGE])
        control.save_batch(self.store, batch)
        return self._attempt(ctx, "skip" if skipped else "block", "skipped" if skipped else "blocked",
                             code=refusal.code, stage=None if skipped else refusal.stage, message=refusal.message)

    def _load(self, ctx, action, delivery):
        batch = ctx["batch"]
        prepared = self.format.prepare(self.registry_entry, ctx["path"])
        batch.update(source_file=prepared.data_member, source_sha256=prepared.data_member_sha256,
                     encoding=prepared.encoding, schema_version=prepared.schema_version,
                     schema_fingerprint=prepared.schema_fingerprint, source_rows=len(prepared.rows))
        self._record_checks(batch["batch_id"], [(c.check_name, c.status, c.expected, c.actual) for c in prepared.checks])
        if prepared.failed_checks:
            names = ", ".join(c.check_name for c in prepared.failed_checks)
            raise IngestionError("validate", "failed_checks", f"FAIL in {names}; see data_quality_results. Nothing was loaded.")

        batch["status"] = "loading"
        control.save_batch(self.store, batch)
        before = bronze.count_file_rows(self.store, self.config, prepared.data_member_sha256)
        columns = [c for c, _ in bronze.bronze_columns(self.config)]
        rows = bronze.build_rows(prepared, self.registry_entry, batch["batch_id"], self.run_id,
                                 ctx["started"], self.code_revision, columns)
        bronze.merge_rows(self.store, self.config, rows)
        self.hook("after_bronze_merge")
        after = bronze.count_file_rows(self.store, self.config, prepared.data_member_sha256)
        batch.update(rows_inserted=after - before, bronze_rows=after)

        results = bronze.reconcile(self.store, self.config, prepared)
        self._record_checks(batch["batch_id"], [(n, PASS if ok else FAIL, e, a) for n, ok, e, a in results])
        bad = [n for n, ok, _, _ in results if not ok]
        if bad:
            raise IngestionError("reconcile", "reconciliation_failed",
                                 f"Bronze does not match the file: {', '.join(bad)}. The batch is not marked succeeded, "
                                 "so downstream does not read it; inspect, then retry.")
        self.hook("reconciled")

        batch.update(status="succeeded", succeeded_at_utc=batch["succeeded_at_utc"] or utc_now())
        control.save_batch(self.store, batch)
        return self._attempt(ctx, action, "succeeded")

    def _fail(self, ctx, action, stage, code, message):
        batch = ctx["batch"]
        batch.update(status="failed", failure_stage=stage, error_code=code, error_message=message[:MAX_MESSAGE])
        control.save_batch(self.store, batch)
        return self._attempt(ctx, action, "failed", code=code, stage=stage, message=message)

    def _attempt(self, ctx, action, outcome, code=None, stage=None, message=None):
        batch = ctx["batch"]
        finished = utc_now()
        inserted = batch["rows_inserted"] if action in LOAD_ACTIONS else 0
        control.add_attempt(self.store, {
            "run_id": self.run_id, "batch_id": batch["batch_id"], "source_id": self.source_id,
            "school_year": batch["school_year"], "logical_dataset": batch.get("logical_dataset"),
            "estimate_years_covered": batch.get("estimate_years_covered"), "archive_name": batch["archive_name"],
            "archive_sha256": batch["archive_sha256"], "action": action, "load_type": batch["load_type"],
            "outcome": outcome, "started_at_utc": ctx["started"], "finished_at_utc": finished,
            "duration_seconds": (finished - ctx["started"]).total_seconds(),
            "source_rows": batch["source_rows"], "rows_inserted": inserted,
            "bronze_rows": batch["bronze_rows"], "failure_stage": stage, "error_code": code,
            "error_message": (message or "")[:MAX_MESSAGE] or None, "environment": self.environment,
            "code_revision": self.code_revision,
        })
        return BatchOutcome(batch["batch_id"], batch["archive_name"], batch["school_year"] or batch.get("estimate_years_covered"), action,
                            batch["load_type"], outcome, inserted,
                            batch["bronze_rows"], message)

    def _record_checks(self, bid, results):
        now = utc_now()
        control.add_checks(self.store, [{
            "run_id": self.run_id, "batch_id": bid, "source_id": self.source_id, "layer": "bronze",
            "table_name": self.dq_table, "check_name": name, "status": status, "expected": str(expected),
            "actual": str(actual), "checked_at_utc": now, "code_revision": self.code_revision,
        } for name, status, expected, actual in results])
