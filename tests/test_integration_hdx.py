"""Integration for hdx_boundaries: the HDX ADM3 → PSGC crosswalk (hdx_adm3_psgc_map, #93).

Made-up rows go straight into the two published Silver tables it reads (hdx_adm3_clean and
psa_psgc_clean) in an in-memory DuckDB, then through the generated build and gate SQL, run the way
the job's two SQL tasks run them. Each made-up HDX feature exercises one rule of #74 (HB-2).
No real COD-AB or PSGC row is used.
"""

import copy
import json
import uuid

import pytest

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.errors import IngestionError
from src.ingestion.store import DuckDBStore
from src.integration import hdx_adm3_psgc as hdx

CONTROL = "edu_access.`01-control`"
MAP = "edu_access.`04-integration`.hdx_adm3_psgc_map"
CANDIDATE = "edu_access.`04-integration`.hdx_adm3_psgc_map_candidate"
RULES = json.loads((REPO_ROOT / "config" / "integration" / "hdx_adm3_psgc.json").read_text(encoding="utf-8"))

PSGC = [  # psgc_code, name, old_names, correspondence_code, geographic_level
    ("0100000000", "Region I (Ilocos Region)", None, "010000000", "Reg"),
    ("0102800000", "Ilocos Norte", None, "012800000", "Prov"),
    ("0102801000", "Adams", None, "012801000", "Mun"),
    ("0102802000", "Bacarra", None, "012802000", "Mun"),
    ("0102803000", "City of Batac", None, "012803000", "City"),
    ("0102804000", "Banna", None, "012804000", "Mun"),
    ("0102805000", "Banna", None, "012805000", "Mun"),
    ("0102806000", "Peñablanca", "Old Town", "012806000", "Mun"),
    ("1800000000", "Negros Island Region", None, None, "Reg"),
    ("1804500000", "Negros Occidental", None, "064500000", "Prov"),
    ("1804501000", "Bacolod City", None, "064501000", "City"),
    ("0906600000", "Sulu", None, "096600000", "Prov"),
    ("0906601000", "Jolo", None, "096601000", "Mun"),
    ("1908700000", "Maguindanao del Norte", None, None, "Prov"),
    ("1908711000", "Sultan Mastura", None, None, "Mun"),
    ("1908712000", "Parang", None, None, "Mun"),
]
# adm3_pcode, adm3_name, adm2_pcode, and what the map should say: (psgc_code, status, method, review)
HDX = {
    "PH0102801": ("Adams", "PH01028", ("0102801000", "matched", "code", "rule")),
    "PH1908711": ("Parang", "PH19087", ("1908712000", "matched", "name_exact", "rule")),   # the code names Sultan Mastura
    "PH0604501": ("Bacolod City", "PH06045", ("1804501000", "matched", "correspondence_code", "rule")),
    "PH1906601": ("Jolo", "PH19066", ("0906601000", "matched", "code_region_moved", "rule")),
    "PH0102802": ("Bacarra New Name", "PH01028", ("0102802000", "matched", "code_renamed", "pending")),
    "PH0102899": ("Batac City", "PH01028", ("0102803000", "matched", "name_exact", "rule")),
    "PH0102898": ("Banna", "PH01028", (None, "ambiguous", None, "pending")),
    "PH1909901": ("Special Geographic Area - Carmen", "PH19099", (None, "unmatched", None, "pending")),
    "PH0102897": ("Penablanca", "PH01028", ("0102806000", "matched", "name_normalized", "rule")),
}


class Env:
    def __init__(self, tmp_path, rules=None, hdx_rows=None, psgc_rows=None):
        self.tmp = tmp_path
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        self.store.sql("CREATE SCHEMA IF NOT EXISTS edu_access.`03-silver`")
        self.store.sql("CREATE TABLE edu_access.`03-silver`.psa_psgc_clean (psgc_code STRING, name STRING, old_names STRING, "
                       "correspondence_code STRING, geographic_level STRING, publication_period STRING, "
                       "is_master_reference BOOLEAN, batch_id STRING, source_row_number BIGINT)")
        for i, row in enumerate(psgc_rows or PSGC, 1):
            self.store.sql("INSERT INTO edu_access.`03-silver`.psa_psgc_clean VALUES (?, ?, ?, ?, ?, '2026-Q2', TRUE, 'P1', ?)",
                           [*row, i])
        self.store.sql("CREATE TABLE edu_access.`03-silver`.hdx_adm3_clean (adm3_pcode STRING, adm3_name STRING, "
                       "adm2_pcode STRING, adm2_name STRING, adm1_pcode STRING, valid_on DATE, batch_id STRING, "
                       "source_sha256 STRING, source_row_number BIGINT)")
        for i, (pcode, (name, adm2, _)) in enumerate((hdx_rows or HDX).items(), 1):
            self.store.sql("INSERT INTO edu_access.`03-silver`.hdx_adm3_clean VALUES "
                           "(?, ?, ?, NULL, ?, DATE '2025-02-13', 'B1', 'sha', ?)", [pcode, name, adm2, adm2[:4], i])
        spec = hdx.build_spec(rules or RULES)
        self.build, self.gate = tmp_path / "build.sql", tmp_path / "gate.sql"
        self.build.write_text(hdx.build_sql(spec), encoding="utf-8")
        self.gate.write_text(hdx.gate_sql(spec), encoding="utf-8")

    def run(self):
        run_id = str(uuid.uuid4())
        params = {"run_id": run_id, "code_revision": "c" * 40, "environment": "local"}
        try:
            self.store.run_file(self.build, params)
            self.store.run_file(self.gate, params)
        except Exception as e:
            return run_id, str(e)
        return run_id, None

    def rows(self, sql):
        return self.store.records(sql)

    def checks(self, run_id):
        return {r["check_name"]: r for r in self.rows(
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}' AND layer = 'integration'")}

    def run_status(self, run_id):
        return self.rows(f"SELECT status FROM {CONTROL}.pipeline_runs WHERE run_id = '{run_id}' "
                         "AND pipeline_name = 'integration_build'")[0]["status"]


def with_overrides(*overrides):
    rules = copy.deepcopy(RULES)
    rules["overrides"] = list(overrides)
    return rules


def published(env):
    return bool(env.rows("SELECT 1 FROM information_schema.tables WHERE table_schema = '04-integration' "
                         "AND table_name = 'hdx_adm3_psgc_map'"))


# --- The rules ----------------------------------------------------------------------------

def test_every_feature_gets_one_row_by_the_rules_in_order(tmp_path):
    env = Env(tmp_path)
    run_id, error = env.run()
    assert error is None
    got = {r["adm3_pcode"]: (r["psgc_code"], r["match_status"], r["match_method"], r["review_status"])
           for r in env.rows(f"SELECT * FROM {MAP}")}
    assert got == {pcode: expected for pcode, (_, _, expected) in HDX.items()}
    assert env.run_status(run_id) == "succeeded"


def test_a_code_alone_is_not_enough(tmp_path):
    """COD-AB PH1908711 is Parang; PSGC 1908711000 is Sultan Mastura. The name decides."""
    env = Env(tmp_path)
    env.run()
    row = env.rows(f"SELECT * FROM {MAP} WHERE adm3_pcode = 'PH1908711'")[0]
    assert (row["psgc_code"], row["psgc_name"]) == ("1908712000", "Parang")
    assert "the code names another unit" in row["reason"]


def test_every_row_keeps_its_source_and_psgc_side(tmp_path):
    env = Env(tmp_path)
    env.run()
    row = env.rows(f"SELECT * FROM {MAP} WHERE adm3_pcode = 'PH0604501'")[0]
    assert (row["source_id"], row["adm3_name"], row["code_candidate"], row["psgc_version"], row["geographic_level"]) == (
        "hdx_boundaries", "Bacolod City", "0604501000", "2026-Q2", "city_mun")
    assert (row["batch_id"], row["source_row_number"], row["psgc_batch_id"]) == ("B1", 3, "P1")


# --- The gate -----------------------------------------------------------------------------

def test_the_gate_passes_and_warns_on_what_needs_review(tmp_path):
    env = Env(tmp_path)
    run_id, _ = env.run()
    checks = env.checks(run_id)
    assert set(checks) == {n for n, _ in hdx.gate_checks(hdx.build_spec(RULES))}
    assert not [n for n, c in checks.items() if c["status"] == "FAIL"]
    assert {n: checks[n]["actual"] for n in ("review_pending", "unmatched", "ambiguous")} == {
        "review_pending": "3", "unmatched": "1", "ambiguous": "1"}
    assert {checks[n]["status"] for n in ("review_pending", "unmatched", "ambiguous")} == {"WARN"}
    assert checks["rows_reconcile"]["actual"] == str(len(HDX))


def test_overrides_are_applied_and_marked_reviewed(tmp_path):
    env = Env(tmp_path, rules=with_overrides(
        {"adm3_pcode": "PH1909901", "psgc_code": None, "match_method": None,
         "reason": "Special Geographic Area unit, no PSGC equivalent until a spatial check (D-031)", "evidence": "#74 HB-2"},
        {"adm3_pcode": "PH0102802", "psgc_code": "0102802000", "match_method": "code_renamed",
         "reason": "Renamed since COD-AB v03", "evidence": "made up"}))
    run_id, error = env.run()
    assert error is None
    got = {r["adm3_pcode"]: (r["match_status"], r["match_method"], r["review_status"]) for r in env.rows(f"SELECT * FROM {MAP}")}
    assert got["PH1909901"] == ("unmatched", None, "reviewed")
    assert got["PH0102802"] == ("matched", "code_renamed", "reviewed")
    assert env.checks(run_id)["overrides_applied"]["status"] == "PASS"


@pytest.mark.parametrize("override, failed", [
    ({"adm3_pcode": "PH0102898", "psgc_code": "0102801000", "match_method": "reviewed_alias",
      "reason": "takes Adams a second time", "evidence": "made up"}, "psgc_code_taken_once"),
    ({"adm3_pcode": "PH0109999", "psgc_code": None, "match_method": None,
      "reason": "not an HDX feature", "evidence": "made up"}, "overrides_applied"),
])
def test_a_bad_override_fails_the_gate_and_nothing_is_published(tmp_path, override, failed):
    env = Env(tmp_path, rules=with_overrides(override))
    run_id, error = env.run()
    assert error and "Integration gate failed" in error
    assert env.checks(run_id)[failed]["status"] == "FAIL"
    assert env.run_status(run_id) == "failed"
    assert not published(env)


def test_a_feature_is_never_dropped(tmp_path):
    env = Env(tmp_path, hdx_rows={"PH0700000": ("Nowhere", "PH07000", None)})
    run_id, error = env.run()
    assert error is None
    assert env.rows(f"SELECT match_status, reason FROM {MAP}") == [
        {"match_status": "unmatched", "reason": "no code or name match"}]


# --- The rules file and the committed files ------------------------------------------------

@pytest.mark.parametrize("override, message", [
    ({"adm3_pcode": "PH12", "psgc_code": None, "match_method": None, "reason": "r", "evidence": "e"}, "must match"),
    ({"adm3_pcode": "PH0102801", "psgc_code": "12", "match_method": "code", "reason": "r", "evidence": "e"}, "ten digits"),
    ({"adm3_pcode": "PH0102801", "psgc_code": "0102801000", "match_method": "guess", "reason": "r", "evidence": "e"}, "D-029"),
    ({"adm3_pcode": "PH0102801", "psgc_code": None, "match_method": "spatial", "reason": "r", "evidence": "e"}, "no match_method"),
    ({"adm3_pcode": "PH0102801", "psgc_code": "0102801000", "match_method": "code", "reason": "", "evidence": "e"}, "reason and evidence"),
    ({"adm3_pcode": "PH0102801", "psgc_code": "0102801000", "match_method": "code", "reason": "it's", "evidence": "e"}, "quotes"),
])
def test_a_bad_override_is_refused_before_any_sql(override, message):
    with pytest.raises(IngestionError, match=message):
        hdx.build_spec(with_overrides(override))


@pytest.mark.parametrize("command, path, function", [
    ("sql", "etl/04_integration/03_map_hdx_adm3_psgc.sql", hdx.build_sql),
    ("gate", "etl/04_integration/90_validate_hdx_adm3_psgc_map.sql", hdx.gate_sql),
])
def test_committed_files_match_the_generator(command, path, function):
    assert (REPO_ROOT / path).read_text(encoding="utf-8") == function(hdx.load_spec(REPO_ROOT)), (
        f"Regenerate: python -m src.integration.hdx_adm3_psgc {command} > {path}")
