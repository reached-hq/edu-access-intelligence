"""Silver for deped_enrollment: cleaning rules, quarantine, the gate, and the run record.

Made-up deliveries (tests/factories/deped_deliveries.py) go through the real
Bronze pipeline into an in-memory DuckDB, then through the committed Silver
SQL files, run the way the job's two SQL tasks run them: the build, then the
gate, with the job parameters bound. No real DepEd row is used.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

import pytest

from factories.deped_deliveries import (
    REPO_ROOT, approve, columns, empty_config, fake_repo, make_delivery, make_rows, real_config, with_values,
    write_config,
)
from src.ingestion.errors import IngestionError
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore, to_duckdb
from src.silver.dictionary import dictionary_markdown
from src.silver.spec import build_spec, load_spec
from src.silver.sql import build_sql, gate_sql

REVISION = "c" * 40
BRONZE = "edu_access.`02-bronze`.deped_enrollment_raw"
CLEAN = "edu_access.`03-silver`.deped_enrollment_clean"
QUARANTINE = "edu_access.`03-silver`.deped_enrollment_quarantine"
CONTROL = "edu_access.`01-control`"
V1, V2 = columns("v1"), columns("v2")


@dataclass
class SilverResult:
    run_id: str
    status: str            # succeeded | failed | built (the gate was not run)
    error: str = None


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


class Env:
    def __init__(self, tmp_path):
        self.config = empty_config()
        self.inbox = tmp_path / "landing" / "deped"
        self.repo = fake_repo(tmp_path / "repo", self.config)
        self.store = DuckDBStore()

    def deliver(self, school_year, schema_version="v1", folder="original", version=1, supersedes=None, **kwargs):
        encoding = "cp1252" if schema_version == "v2" else "utf-8"
        path = make_delivery(self.inbox / folder, school_year, schema_version, encoding=encoding, **kwargs)
        approve(self.config, path, school_year, schema_version, encoding, delivery_version=version, supersedes=supersedes)
        write_config(self.repo, self.config)
        return path

    def bronze(self):
        summary = IngestionRun(self.store, self.repo, "deped_enrollment", self.inbox.parent, "local", REVISION).execute()
        assert summary.status == "succeeded", summary
        return summary

    def silver(self, run_id=None, hook=None, gate=True):
        """The job's two Silver SQL tasks: the build, then (if it succeeded) the gate."""
        run_id = run_id or str(uuid.uuid4())
        params = {"run_id": run_id, "code_revision": REVISION, "environment": "local"}
        folder = self.repo / "etl" / "03_silver"
        try:
            self.store.run_file(folder / "01_clean_deped_enrollment.sql", params)
        except Exception as e:
            return SilverResult(run_id, "failed", f"build: {e}")
        if hook:
            hook()
        if not gate:
            return SilverResult(run_id, "built")
        try:
            self.store.run_file(folder / "90_validate_deped_enrollment_clean.sql", params)
        except Exception as e:
            return SilverResult(run_id, "failed", str(e))
        return SilverResult(run_id, "succeeded")

    def silver_run(self, run_id):
        return self.rows(f"SELECT * FROM {CONTROL}.pipeline_runs WHERE run_id = '{run_id}' "
                         "AND pipeline_name = 'silver_build'")[0]

    def q(self, sql):
        return self.store.query(sql)

    def one(self, sql):
        return self.q(sql)[0][0]

    def rows(self, sql):
        return self.store.records(sql)

    def checks(self, run_id, status=None):
        where = f" AND status = '{status}'" if status else ""
        return {(r["check_name"], r["batch_id"]): r for r in self.rows(
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}'{where}")}

    def failed_checks(self, run_id):
        return sorted({name for name, _ in self.checks(run_id, "FAIL")})


def v2_row(i, values=None, first_id=950001):
    """A made-up SY 2025-26 row with that year's labels; school IDs from 950001."""
    row = make_rows(V2, n_rows=i + 1, first_id=first_id)[i]
    base = {"offers_es": "Yes", "offers_jhs": "No", "offers_shs": "No", "school_management": "DepED Managed",
            "annex_status": "School with no Annexes", "sector": "Public"}
    return with_values(V2, row, {**base, **(values or {})})


def v1_rows(n=3, changes=None):
    """Made-up SY 2023-24 rows; changes = {row index: {column: value}}."""
    rows = make_rows(V1, n_rows=n)
    return [with_values(V1, row, (changes or {}).get(i, {})) for i, row in enumerate(rows)]


# --- Cleaning rules -------------------------------------------------------------------

def test_counts_are_typed_and_blanks_stay_null_not_zero(env):
    env.deliver("2023-24", rows=v1_rows(changes={1: {"g1_male": "", "g2_female": "17"}}))
    env.bronze()
    assert env.silver().status == "succeeded"
    row = env.rows(f"SELECT * FROM {CLEAN} WHERE school_id = '900002'")[0]
    assert row["g1_male"] is None                  # published blank: NULL, never 0
    assert row["g2_female"] == 17 and isinstance(row["g2_female"], int)
    assert row["g11_unique_male"] is None          # blank in every made-up v1 row, as in SY 2023-24 (O-16)
    types = dict(env.q("SELECT column_name, data_type FROM information_schema.columns "
                       "WHERE table_schema = '03-silver' AND table_name = 'deped_enrollment_clean'"))
    assert {types[c] for c in V1 if c.endswith(("_male", "_female"))} == {"INTEGER"}
    assert (types["offers_es"], types["school_id"], types["source_row_number"]) == ("BOOLEAN", "VARCHAR", "BIGINT")


def test_absent_columns_are_null_and_told_apart_by_schema_version(env):
    env.deliver("2023-24")
    env.deliver("2025-26", "v2", rows=[v2_row(0, {"g11_sshs_acad_male": "", "g11_sshs_acad_female": "4"})])
    env.bronze()
    assert env.silver().status == "succeeded"
    v1 = env.rows(f"SELECT schema_version, g11_sshs_acad_male, modified_curricular_offering_classification "
                  f"FROM {CLEAN} WHERE school_year = '2023-24'")
    assert {(r["schema_version"], r["g11_sshs_acad_male"], r["modified_curricular_offering_classification"]) for r in v1} \
        == {("v1", None, None)}                    # not in the v1 file at all
    v2 = env.rows(f"SELECT * FROM {CLEAN} WHERE school_year = '2025-26'")[0]
    assert (v2["schema_version"], v2["g11_sshs_acad_male"], v2["g11_sshs_acad_female"]) == ("v2", None, 4)  # published blank
    assert v2["modified_curricular_offering_classification"] == "Purely ES"


def test_labels_and_booleans_map_to_one_standard_set(env):
    env.deliver("2023-24", rows=v1_rows(1, {0: {"sector": "SUC/LUC", "school_management": "SUC"}}))
    env.deliver("2025-26", "v2", rows=[
        v2_row(0, {"sector": "SUCsLUCs", "school_management": "SUC Managed", "offers_shs": "Yes"}),
        v2_row(1, {"school_management": "Non-Sectarian ", "annex_status": "Mother school", "offers_es": ""}),
        v2_row(2, {"school_management": "SCHOOL ABROAD", "sector": "PSO", "region": "PSO"}),
    ])
    env.bronze()
    assert env.silver().status == "succeeded"
    got = {r["school_id"]: r for r in env.rows(f"SELECT * FROM {CLEAN}")}
    assert (got["900001"]["sector"], got["950001"]["sector"]) == ("SUC/LUC", "SUC/LUC")
    assert (got["900001"]["school_management"], got["950001"]["school_management"]) == ("SUC", "SUC")
    assert got["950002"]["school_management"] == "Non-Sectarian"      # trailing space trimmed before mapping
    assert got["950002"]["annex_status"] == "Mother School"
    assert got["950003"]["school_management"] == "PSO" and got["950003"]["is_overseas"] is True
    assert (got["900001"]["offers_es"], got["900001"]["offers_jhs"]) == (True, False)      # True/False
    assert (got["950001"]["offers_es"], got["950001"]["offers_shs"]) == (True, True)       # Yes
    assert got["950002"]["offers_es"] is None                                           # blank, not FALSE


def test_text_is_trimmed_collapsed_and_repaired_but_place_names_are_not_rewritten(env):
    env.deliver("2025-26", "v2", rows=[v2_row(0, {
        "province": "NCR   SECOND DISTRICT", "municipality": "CITY OF MALOLOS  (Capital)",
        "barangay": "AGUSAN PEQUEÃ‘O", "school_name": "Sto.\tNiÃ±o Elementary School ",
        "street_address": "-",
    }), v2_row(1, {"street_address": "N/A", "barangay": ""}), v2_row(2, {"street_address": "Purok 1"})])
    env.bronze()
    assert env.silver().status == "succeeded"
    got = {r["school_id"]: r for r in env.rows(f"SELECT * FROM {CLEAN}")}
    first = got["950001"]
    assert first["province"] == "NCR SECOND DISTRICT"
    assert first["municipality"] == "CITY OF MALOLOS (Capital)"  # "(Capital)" stays: matching is Integration's job
    assert first["barangay"] == "AGUSAN PEQUEÑO"
    assert first["school_name"] == "Sto. Niño Elementary School"
    assert first["street_address"] is None                        # placeholder
    assert (got["950002"]["street_address"], got["950002"]["barangay"]) == (None, None)
    assert got["950003"]["street_address"] == "Purok 1"
    # Bronze keeps what was published.
    assert env.one(f"SELECT barangay FROM {BRONZE} WHERE school_id = '950001'") == "AGUSAN PEQUEÃ‘O"


def test_flags_mark_rows_and_never_drop_them(env):
    long_name = "AURORA HILL PROPER (MALVAR-SGT. FLORESCA"
    assert len(long_name) == 40
    zeros = {c: "0" for c in V1 if c.endswith(("_male", "_female")) and "unique" not in c}
    env.deliver("2023-24", rows=v1_rows(4, {
        0: {**zeros, "g1_male": "5"},
        1: zeros,                                                       # every published count is 0
        2: {"region": "PSO", "sector": "PSO", "school_management": "PSO", "legislative_district": "PSO"},
        3: {"barangay": long_name},
    }))
    blanks = {c: "" for c in V2 if c.endswith(("_male", "_female"))}
    env.deliver("2025-26", "v2", rows=[v2_row(0, blanks)])  # no count published at all
    env.bronze()
    assert env.silver().status == "succeeded"
    got = {r["school_id"]: r for r in env.rows(f"SELECT * FROM {CLEAN}")}
    assert len(got) == 5
    assert got["900001"]["enrollment_status"] == "has_learners"
    assert got["900002"]["enrollment_status"] == "all_zero"
    assert got["950001"]["enrollment_status"] == "no_counts"
    assert got["950001"]["g1_male"] is None                             # blank, not zero
    assert got["900003"]["is_overseas"] is True and got["900001"]["is_overseas"] is False
    assert got["900004"]["barangay_possibly_truncated"] is True and got["900001"]["barangay_possibly_truncated"] is False


def test_flags_are_never_null_so_gold_filters_cannot_drop_rows(env):
    """`WHERE NOT flag` silently drops rows whose flag is NULL; Silver's flags are never NULL.
    Nullable values (a blank offers_shs) need IS NOT TRUE, which Gold must use."""
    env.deliver("2025-26", "v2", rows=[v2_row(0), v2_row(1, {"offers_shs": ""})])
    env.bronze()
    env.silver()
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE is_overseas IS NULL OR barangay_possibly_truncated IS NULL "
                   "OR enrollment_status IS NULL") == 0
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE NOT is_overseas") == 2
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE NOT offers_shs") == 1           # the trap: the NULL row is gone
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE offers_shs IS NOT TRUE") == 2   # NULL-safe


# --- Quarantine -------------------------------------------------------------------------

def test_negative_and_uncastable_counts_are_quarantined_with_reasons_not_dropped(env):
    env.deliver("2023-24", rows=v1_rows(150, {3: {"g1_male": "-3"}}))
    env.deliver("2024-25", rows=v1_rows(250, {7: {"g7_female": "5.0"}, 8: {"kinder_male": "abc"}}))
    env.bronze()
    summary = env.silver()
    assert summary.status == "succeeded"                      # 1 of 150 and 2 of 250 rows: under 1%, so WARN
    quarantined = {r["school_id"]: r for r in env.rows(f"SELECT * FROM {QUARANTINE}")}
    assert quarantined["900004"]["quarantine_reasons"] == ["count_negative"]
    assert quarantined["900008"]["quarantine_reasons"] == ["count_uncastable"]
    assert quarantined["900009"]["quarantine_reasons"] == ["count_uncastable"]
    assert set(quarantined) == {"900004", "900008", "900009"} and quarantined["900004"]["batch_id"].endswith(
        env.one(f"SELECT archive_sha256 FROM {CONTROL}.ingestion_batches WHERE school_year = '2023-24'")[:12])
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE (school_year = '2023-24' AND school_id = '900004') "
                   "OR (school_year = '2024-25' AND school_id IN ('900008', '900009'))") == 0
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN}") == 400 - 3
    checks = env.checks(summary.run_id)
    rate = {r["batch_id"].split("__")[1]: r["status"] for (name, _), r in checks.items() if name == "quarantine_rate"}
    assert rate == {"2023-24": "WARN", "2024-25": "WARN"}
    assert env.one(f"SELECT COUNT(*) FROM {BRONZE}") == 400   # Bronze untouched


def test_quarantine_above_one_percent_fails_the_run(env):
    env.deliver("2023-24", rows=v1_rows(3, {0: {"g1_male": "-1"}}))
    env.bronze()
    summary = env.silver()
    assert summary.status == "failed" and "Silver gate failed" in summary.error
    assert env.failed_checks(summary.run_id) == ["quarantine_rate"]
    run = env.silver_run(summary.run_id)
    assert (run["status"], run["failure_stage"], run["error_message"]) == (
        "failed", "gate", "1 FAIL result(s) in data_quality_results")


def test_duplicate_school_id_quarantines_every_copy(env):
    rows = v1_rows(200)
    rows.append(with_values(V1, rows[0], {"g1_male": "9"}))   # same school, different counts
    env.deliver("2023-24", rows=rows)
    env.bronze()                                                # Bronze keeps both and WARNs
    summary = env.silver()
    assert summary.status == "succeeded"
    assert env.q(f"SELECT school_id, quarantine_reasons FROM {QUARANTINE} ORDER BY source_row_number") == [
        ("900001", ["school_id_duplicated"]), ("900001", ["school_id_duplicated"])]
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN}") == 199
    assert env.checks(summary.run_id)[("school_id_unique", env.one(f"SELECT batch_id FROM {CLEAN} LIMIT 1"))]["status"] == "PASS"


def test_blank_null_and_malformed_school_ids_are_quarantined_without_losing_a_row(env):
    """A NULL school_id makes NULL-unsafe conditions NULL; the row must still land somewhere."""
    env.deliver("2023-24", rows=v1_rows(400, {5: {"school_id": "12345"}}))
    env.bronze()
    for number, value in ((901, "NULL"), (902, "''")):        # Bronze refuses these files, so insert directly
        env.store.sql(f"INSERT INTO {BRONZE} SELECT * REPLACE ({value} AS school_id, {number} AS source_row_number) "
                      f"FROM {BRONZE} WHERE source_row_number = 1")
    summary = env.silver()
    assert summary.status == "succeeded"                       # 3 of 402 rows: under 1%, so WARN
    reasons = dict(env.q(f"SELECT source_row_number, quarantine_reasons FROM {QUARANTINE}"))
    assert reasons == {6: ["school_id_malformed"], 901: ["school_id_blank"], 902: ["school_id_blank"]}
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN}") + env.one(f"SELECT COUNT(*) FROM {QUARANTINE}") == 402
    warned = {name for name, _ in env.checks(summary.run_id, "WARN")}
    assert warned == {"quarantine_rate", "quarantine_reason_school_id_blank", "quarantine_reason_school_id_malformed"}


# --- The gate ---------------------------------------------------------------------------

def test_an_unmapped_label_fails_the_gate(env):
    env.deliver("2023-24")
    env.bronze()
    assert env.silver().status == "succeeded"
    env.deliver("2025-26", "v2", rows=[v2_row(0, {"sector": "Charter"}), v2_row(1)])   # a new year brings a new label
    env.bronze()
    summary = env.silver()
    assert summary.status == "failed"
    assert env.failed_checks(summary.run_id) == ["labels_mapped_sector"]
    assert env.one(f"SELECT sector FROM {CLEAN} WHERE school_id = '950001'") is None
    assert env.silver_run(summary.run_id)["status"] == "failed"
    assert env.silver().status == "failed"   # and on every run, until the mapping is reviewed


def test_an_unknown_boolean_label_fails_the_gate(env):
    env.deliver("2023-24", rows=v1_rows(3, {1: {"offers_jhs": "Maybe"}}))
    env.bronze()
    summary = env.silver()
    assert env.failed_checks(summary.run_id) == ["labels_mapped_offers_jhs"]


def test_an_unmapped_label_on_a_quarantined_row_still_fails_the_gate(env):
    """A quarantined row has no clean value; its labels are checked against the mapping itself."""
    env.deliver("2023-24", rows=v1_rows(200, {0: {"g1_male": "-1", "sector": "Charter"},
                                              1: {"g2_female": "abc", "offers_es": "Maybe"}}))
    env.bronze()
    summary = env.silver()                               # 2 of 200 rows quarantined: under 1%, so only a WARN
    assert summary.status == "failed"
    assert env.failed_checks(summary.run_id) == ["labels_mapped_offers_es", "labels_mapped_sector"]
    assert env.one(f"SELECT COUNT(*) FROM {QUARANTINE}") == 2


def test_reconciliation_and_learner_totals_pass_on_a_clean_load(env):
    env.deliver("2023-24", n_rows=5)
    env.deliver("2025-26", "v2", rows=[v2_row(i) for i in range(4)])
    env.bronze()
    summary = env.silver()
    assert summary.status == "succeeded"
    checks = env.checks(summary.run_id)
    assert {r["status"] for r in checks.values()} == {"PASS"}
    bronze_total = env.one(f"SELECT SUM(" + " + ".join(
        f"COALESCE(TRY_CAST({c} AS BIGINT), 0)" for c in V2 if c.endswith(("_male", "_female"))) + f") FROM {BRONZE}")
    learners = [r for (name, _), r in checks.items() if name == "learners_reconcile"]
    assert sum(int(r["actual"]) for r in learners) == bronze_total
    assert all(r["expected"] == r["actual"] for r in learners)
    rows = [r for (name, _), r in checks.items() if name == "rows_reconcile"]
    assert sorted((r["expected"], r["actual"]) for r in rows) == [("4", "4"), ("5", "5")]


def test_the_gate_catches_a_count_turned_into_zero(env):
    """Blank → 0 keeps learner totals equal; missing_counts_stay_null is what catches it."""
    env.deliver("2025-26", "v2", rows=[v2_row(0, {"g1_male": ""}), v2_row(1)])
    env.bronze()

    def blank_becomes_zero():
        env.store.sql(f"UPDATE {CLEAN} SET g1_male = 0 WHERE g1_male IS NULL")

    summary = env.silver(hook=blank_becomes_zero)
    assert summary.status == "failed"
    assert env.failed_checks(summary.run_id) == ["missing_counts_stay_null"]


def test_the_gate_catches_a_lost_row_and_a_stale_row(env):
    env.deliver("2023-24", n_rows=4)
    env.bronze()

    def tamper():
        env.store.sql(f"DELETE FROM {CLEAN} WHERE school_id = '900002'")
        env.store.sql(f"UPDATE {CLEAN} SET run_id = 'an-old-run' WHERE school_id = '900003'")

    summary = env.silver(hook=tamper)
    assert env.failed_checks(summary.run_id) == ["learners_reconcile", "missing_counts_stay_null",
                                                 "rows_built_by_this_run", "rows_reconcile"]


def test_lineage_and_code_revision_on_every_row_and_result(env):
    env.deliver("2023-24")
    env.deliver("2025-26", "v2", rows=[v2_row(0)])
    env.bronze()
    summary = env.silver()
    joined = env.one(f"SELECT COUNT(*) FROM {CLEAN} AS c JOIN {BRONZE} AS b "
                     "ON c.source_sha256 = b.source_sha256 AND c.source_row_number = b.source_row_number "
                     "AND c.batch_id = b.batch_id AND c.school_id = b.school_id AND c.delivery_version = b.delivery_version "
                     "AND c.schema_version = b.schema_version")
    assert joined == env.one(f"SELECT COUNT(*) FROM {CLEAN}") == 4
    assert env.q(f"SELECT DISTINCT run_id, code_revision FROM {CLEAN}") == [(summary.run_id, REVISION)]
    assert env.q(f"SELECT DISTINCT code_revision FROM {CONTROL}.data_quality_results "
                 f"WHERE run_id = '{summary.run_id}'") == [(REVISION,)]
    assert env.one(f"SELECT COUNT(DISTINCT layer) FROM {CONTROL}.data_quality_results WHERE run_id = '{summary.run_id}'") == 1


def test_clean_and_quarantine_share_one_timestamp(env):
    env.deliver("2023-24", rows=v1_rows(150, {0: {"g1_male": "-1"}}))
    env.bronze()
    summary = env.silver()
    stamps = env.q(f"SELECT DISTINCT cleaned_at_utc FROM {CLEAN} UNION SELECT DISTINCT cleaned_at_utc FROM {QUARANTINE}")
    assert len(stamps) == 1 and isinstance(stamps[0][0], datetime)
    assert env.silver_run(summary.run_id)["started_at_utc"] == stamps[0][0]


def test_check_results_hold_counts_not_values(env):
    env.deliver("2023-24", rows=v1_rows(3, {1: {"sector": "Secret Label"}}))
    env.bronze()
    summary = env.silver()
    texts = [str(v) for r in env.checks(summary.run_id).values() for v in (r["expected"], r["actual"])]
    assert not [t for t in texts if "Secret" in t or "Test School" in t]


# --- Which Bronze rows, and when to build ---------------------------------------------------

def test_only_current_batches_are_read_and_a_revision_replaces_its_year(env):
    env.deliver("2023-24")
    first = env.deliver("2025-26", "v2", rows=[v2_row(i) for i in range(3)])
    env.bronze()
    assert env.silver().status == "succeeded"
    v1_sha = env.config["deliveries"][1]["archive_sha256"]
    env.deliver("2025-26", "v2", folder="2026-08-01", version=2, supersedes=v1_sha,
                rows=[v2_row(i, {"g1_male": "7"}, first_id=960001) for i in range(5)])
    env.bronze()
    assert env.one(f"SELECT COUNT(*) FROM {BRONZE} WHERE school_year = '2025-26'") == 8   # both versions kept
    summary = env.silver()
    assert summary.status == "succeeded"
    assert env.q(f"SELECT DISTINCT delivery_version, school_id LIKE '96%' FROM {CLEAN} WHERE school_year = '2025-26'") \
        == [(2, True)]
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE school_year = '2025-26'") == 5
    assert env.one(f"SELECT COUNT(*) FROM {CLEAN} WHERE school_year = '2023-24'") == 3
    assert first.exists()


def test_every_run_rebuilds_the_same_tables(env):
    """Silver rebuilds on every run (D-025): the same Bronze gives the same rows, never more."""
    env.deliver("2023-24", rows=v1_rows(150, {2: {"g1_male": "-1"}}))
    env.deliver("2025-26", "v2", rows=[v2_row(i) for i in range(3)])
    env.bronze()
    content = ("SELECT * EXCLUDE (run_id, cleaned_at_utc) FROM {} ORDER BY school_year, source_row_number")
    first = env.silver()
    before = (env.q(content.format(CLEAN)), env.q(content.format(QUARANTINE)))
    env.bronze()                                           # a Bronze rerun that loads nothing new
    again = env.silver()
    assert first.status == again.status == "succeeded" and first.run_id != again.run_id
    assert (env.q(content.format(CLEAN)), env.q(content.format(QUARANTINE))) == before
    assert (env.one(f"SELECT COUNT(*) FROM {CLEAN}"), env.one(f"SELECT COUNT(*) FROM {QUARANTINE}")) == (152, 1)
    assert env.one(f"SELECT COUNT(*) - COUNT(DISTINCT school_id || school_year) FROM {CLEAN}") == 0
    assert env.q(f"SELECT DISTINCT run_id FROM {CLEAN}") == [(again.run_id,)]


def test_a_run_is_succeeded_only_after_its_gate_passes(env):
    env.deliver("2023-24")
    env.bronze()
    built = env.silver(gate=False)                       # the build task ran; the gate task never did
    run = env.silver_run(built.run_id)
    assert (run["status"], run["environment"], run["code_revision"]) == ("running", "local", REVISION)
    assert run["finished_at_utc"] is None
    done = env.silver()
    run = env.silver_run(done.run_id)
    assert run["status"] == "succeeded" and run["finished_at_utc"] >= run["started_at_utc"]
    assert env.silver_run(built.run_id)["status"] == "running"   # never mistaken for a good build


def test_a_repaired_run_is_judged_by_its_own_checks(env):
    """Databricks' Repair run keeps the run_id: the gate must not count an earlier attempt's FAIL."""
    env.deliver("2023-24", n_rows=4)
    env.bronze()

    def lose_a_row():
        env.store.sql(f"DELETE FROM {CLEAN} WHERE school_id = '900002'")

    first = env.silver(run_id="job-run-9", hook=lose_a_row)
    assert first.status == "failed"
    repaired = env.silver(run_id="job-run-9")
    assert repaired.status == "succeeded"
    assert env.silver_run("job-run-9")["status"] == "succeeded"
    assert env.one(f"SELECT COUNT(*) FROM {CONTROL}.data_quality_results WHERE run_id = 'job-run-9' AND status = 'FAIL'") > 0


def test_no_current_batch_fails_the_gate(env):
    from src.ingestion import control
    control.create_tables(env.store, env.repo)          # what the job's first task does before any load
    env.store.run_file(env.repo / "etl" / "02_bronze" / "01_create_deped_enrollment_raw.sql")
    summary = env.silver()
    assert summary.status == "failed"
    assert "current_batches_present" in env.failed_checks(summary.run_id)


# --- The committed SQL, the mapping, and the command line ------------------------------------

MAPPINGS = sorted((REPO_ROOT / "config" / "mappings").glob("*.json"))


@pytest.mark.parametrize("mapping", MAPPINGS, ids=lambda p: p.stem)
@pytest.mark.parametrize("kind, path, generate", [
    ("sql", "etl/03_silver/{clean_file}", build_sql),
    ("gate", "etl/03_silver/90_validate_{table}.sql", gate_sql),
    ("dictionary", "docs/data/silver/{doc}.md", dictionary_markdown),
])
def test_silver_files_match_the_mapping(mapping, kind, path, generate):
    spec = load_spec(REPO_ROOT, mapping.stem)
    target = REPO_ROOT / path.format(
        table=spec.clean_table,
        clean_file=spec.clean_file,
        doc=spec.clean_table.replace("_", "-"),
    )
    assert target.is_file(), f"missing {target.relative_to(REPO_ROOT)}"
    assert target.read_text(encoding="utf-8") == generate(spec), (
        f"Regenerate: python -m src.silver.cli {kind} --source {mapping.stem} > {target.relative_to(REPO_ROOT)}")


def test_silver_names_come_from_the_table_registry():
    spec = load_spec(REPO_ROOT, "deped_enrollment")
    assert (spec.clean_table, spec.quarantine_table) == ("deped_enrollment_clean", "deped_enrollment_quarantine")


def _spec(mapping=None, contract=None):
    import yaml
    registry = yaml.safe_load((REPO_ROOT / "config" / "tables.yml").read_text(encoding="utf-8"))
    entry = next(s for s in registry["source_tables"] if s["source_id"] == "deped_enrollment")
    mapping = mapping or json.loads((REPO_ROOT / "config" / "mappings" / "deped_enrollment.json").read_text(encoding="utf-8"))
    return build_spec(mapping, contract or real_config(), entry)


def test_a_new_publisher_column_needs_a_reviewed_mapping():
    contract = real_config()
    contract["schema_versions"]["v3"] = {"first_school_year": "2026-27", "note": "test",
                                         "columns": columns("v2") + ["school_head"]}
    with pytest.raises(IngestionError, match="'school_head' must be classified exactly once"):
        _spec(contract=contract)
    contract["schema_versions"]["v3"]["columns"][-1] = "g13_male"   # a count is recognized by its name
    assert _spec(contract=contract).column("g13_male").kind == "count"


@pytest.mark.parametrize("break_it, message", [
    (lambda m: m["categories"]["sector"]["labels"].append({"published": "Charter", "standard": "Charter", "evidence": ""}),
     "not in the standard set"),
    (lambda m: m["categories"]["sector"]["labels"].append({"published": "Public", "standard": "Public", "evidence": ""}),
     "listed twice"),
    (lambda m: m["categories"]["sector"]["labels"].append({"published": "It's", "standard": "Public", "evidence": ""}),
     "quotes or backslashes"),
    (lambda m: m["booleans"]["true"].append("No"), "both true and false"),
    (lambda m: m.update(silver_table="enrollment_silver"), "config/tables.yml"),
    (lambda m: m["free_text_columns"].append("school_head"), "contract does not have"),
])
def test_the_mapping_refuses_ambiguous_rules(break_it, message):
    mapping = json.loads((REPO_ROOT / "config" / "mappings" / "deped_enrollment.json").read_text(encoding="utf-8"))
    break_it(mapping)
    with pytest.raises(IngestionError, match=message):
        _spec(mapping=mapping)


def test_silver_sql_uses_only_what_both_engines_share():
    """DuckDB-only syntax would pass locally and fail on Databricks; backslashes in literals mean
    different things to the two engines; a ';' in a string would break store.split_statements."""
    for path in sorted((REPO_ROOT / "etl" / "03_silver").glob("*.sql")):
        code = "\n".join(line.split("--", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())
        for token in ("\\", "::", "regexp_matches", "list_", "string_split", "regexp_replace_all", " EXCLUDE ", "[]"):
            assert token not in code, f"{path.name} uses {token!r}"
        for literal in __import__("re").findall(r"'[^']*'", code):
            assert ";" not in literal, f"{path.name}: ';' inside {literal}"


@pytest.mark.parametrize("databricks, duckdb", [
    ("regexp_like(x, '^[0-9]{6}$')", "regexp_matches(x, '^[0-9]{6}$')"),
    ("regexp_replace(x, ' +', ' ')", "regexp_replace_all(x, ' +', ' ')"),
    ("SELECT session.silver_run_id AS run_id", "SELECT getvariable('silver_run_id') AS run_id"),
])
def test_the_duckdb_translation_of_regular_expressions(databricks, duckdb):
    assert to_duckdb(databricks) == duckdb


def test_session_variables_work_locally_as_on_databricks(tmp_path):
    """A SQL task keeps one value for a whole file in a session variable (DECLARE, then SET from a
    job parameter); DuckDB skips the DECLARE and reads the variable through getvariable."""
    sql = tmp_path / "v.sql"
    sql.write_text("DECLARE OR REPLACE VARIABLE silver_run_id STRING;\n"
                   "SET VARIABLE silver_run_id = COALESCE(NULLIF(:run_id, ''), 'UNSET');\n"
                   "CREATE OR REPLACE TEMPORARY VIEW stamped AS SELECT session.silver_run_id AS run_id;\n")
    store = DuckDBStore()
    store.run_file(sql, {"run_id": "job-run-7"})
    assert store.query("SELECT run_id FROM stamped") == [("job-run-7",)]


def test_translated_regular_expressions_behave_like_spark():
    store = DuckDBStore()
    assert store.query("SELECT regexp_replace('a  b   c ', ' +', ' ')") == [("a b c ",)]   # every match, as Spark
    assert store.query("SELECT regexp_like('123456', '^[0-9]{6}$'), regexp_like('12345', '^[0-9]{6}$'), "
                       "regexp_like('x123456', '[0-9]{6}')") == [(True, False, True)]       # partial match, as rlike
    assert store.query("SELECT TRY_CAST('5.0' AS INT)") == [(5,)]   # why counts are checked as digits first
