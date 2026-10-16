"""The DepEd school-to-PSGC crosswalk in Silver (D-049, #163): padding, null reasons, the Sulu recode,
coordinate flags, repeated and malformed school IDs, reconciliation, and the gate's FAIL checks.

Each test builds a made-up EMISD workbook (tests/factories/report_workbooks.py), loads it through the
real Bronze pipeline, and runs the generated Silver SQL on DuckDB. No row of the real workbook is used.
"""

import uuid

import pytest

from factories.deped_deliveries import fake_repo, write_config
from factories.report_workbooks import NA, approve, empty_config, make_workbook, school
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore
from src.silver import deped_enrollment_psgc
from src.silver.generators import REPO_ROOT

REVISION = "f" * 40
SOURCE = "deped_enrollment_psgc"
CONTROL = "edu_access.`01-control`"
BRONZE = "edu_access.`02-bronze`.deped_enrollment_psgc_raw"
CLEAN = "edu_access.`03-silver`.deped_enrollment_psgc_clean"
QUARANTINE = "edu_access.`03-silver`.deped_enrollment_psgc_quarantine"
ORDINARY = 500   # enough ordinary schools that the 4 quarantined rows stay under the 1% FAIL line

SULU = (1900000000, 1906600000, 1906601000, 1906601018)
CODED = (100000000, 102800000, 102802000, 102802013)


def rows():
    """{Excel row: cells}: ordinary schools, then one row for each rule, a blank row, and a no-ID row."""
    out = {9 + i: school(200000 + i) for i in range(ORDINARY)}
    r = 9 + ORDINARY
    special = [
        school(300101, codes=SULU),                                       # Sulu, recoded
        school(300102, codes=(NA, NA, NA, NA), lon=NA, lat=NA),          # #N/A at every level
        school(300103, codes=(CODED[0], CODED[1], CODED[2], NA)),        # city known, barangay #N/A
        school(300104, lon=0, lat=0),                                    # (0, 0)
        school(300105, lon=112.1, lat=12.7),                             # outside the Philippines
        school(300106, codes=(CODED[0], CODED[1], CODED[2], 102803001)),  # barangay outside its city
        school(300201), school(300201),                                  # identical repeat: one is kept
        school(300202, name="Paaralang Una"), school(300202, name="Paaralang Ikalawa"),  # differing repeat
        school(1000004, codes=("", "", "", ""), lon="", lat=""),          # malformed ID, no codes
    ]
    for cells in special:
        out[r] = cells
        r += 1
    r += 1                                         # a blank row
    out[r] = [""] * 17 + [NA] * 13                 # a row with no school ID
    return out, r


@pytest.fixture
def lane(tmp_path):
    cells, last = rows()
    config = empty_config()
    path = make_workbook(tmp_path / "landing" / "deped" / "original", rows=cells)
    units = len(cells) - 1
    approve(config, path, row_count=last - 8, unit_rows=units, blank_rows=1, no_identifier_rows=1, last_row=last)
    repo = fake_repo(tmp_path / "repo", config)
    store = DuckDBStore()
    summary = IngestionRun(store, repo, SOURCE, tmp_path / "landing", "local", REVISION).execute()
    assert summary.status == "succeeded", summary
    return store, repo, units


def build(store, repo, run_id=None):
    params = {"run_id": run_id or str(uuid.uuid4()), "code_revision": REVISION, "environment": "local"}
    silver = repo / "etl" / "03_silver"
    store.run_file(silver / "07_clean_deped_enrollment_psgc.sql", params)
    return params, silver


def gate(store, silver, params):
    store.run_file(silver / "90_validate_deped_enrollment_psgc_clean.sql", params)


def row(store, school_id, columns):
    return store.query(f"SELECT {columns} FROM {CLEAN} WHERE school_id = '{school_id}'")


def checks(store, run_id):
    return {name: (status, actual) for name, status, actual in store.query(
        f"SELECT check_name, status, actual FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}' AND layer = 'silver'")}


def test_crosswalk_rules_reconcile_and_pass_the_gate(lane):
    store, repo, units = lane
    params, silver = build(store, repo)
    gate(store, silver, params)
    clean = store.query(f"SELECT COUNT(*) FROM {CLEAN}")[0][0]
    quarantined = store.query(f"SELECT COUNT(*) FROM {QUARANTINE}")[0][0]
    assert (clean, quarantined) == (units - 4, 4)                       # Bronze unit rows = clean + quarantine

    # Padded to 10 digits; never shorter, never changed otherwise.
    assert row(store, "200000", "psgc_region, psgc_province, psgc_city_municipality, psgc_barangay") == [
        ("0100000000", "0102800000", "0102802000", "0102802013")]
    # Sulu: province, city and barangay take 09066, the region becomes Region IX.
    assert row(store, "300101", "psgc_region, psgc_province, psgc_city_municipality, psgc_barangay, psgc_recoded") == [
        ("0900000000", "0906600000", "0906601000", "0906601018", True)]
    assert row(store, "200000", "psgc_recoded") == [(False,)]
    # Null reasons: #N/A everywhere; a known city with a #N/A barangay; no codes at all.
    assert row(store, "300102", "psgc_region, psgc_city_municipality, psgc_city_municipality_null_reason, psgc_barangay_null_reason") == [
        (None, None, "source_na", "source_na")]
    assert row(store, "300103", "psgc_city_municipality, psgc_city_municipality_null_reason, psgc_barangay, psgc_barangay_null_reason") == [
        ("0102802000", None, None, "source_na")]
    assert row(store, "300106", "barangay_outside_city") == [(True,)]
    # Coordinates kept as published and flagged.
    assert row(store, "200000", "longitude, latitude, coordinate_flag") == [(120.5, 16.25, None)]
    assert row(store, "300102", "longitude, coordinate_flag") == [(None, "missing")]
    assert row(store, "300104", "longitude, latitude, coordinate_flag") == [(0.0, 0.0, "zero")]
    assert row(store, "300105", "coordinate_flag") == [("outside_philippines",)]
    # Repeats and malformed IDs.
    assert row(store, "300201", "COUNT(*)") == [(1,)]
    assert store.query(f"SELECT school_id, quarantine_reasons FROM {QUARANTINE} ORDER BY school_id, source_row_number") == [
        ("1000004", ["school_id_malformed"]), ("300201", ["school_id_identical_copy"]),
        ("300202", ["school_id_duplicated"]), ("300202", ["school_id_duplicated"])]
    # Only unit rows: the blank and no-ID rows are counted, not carried.
    found = checks(store, params["run_id"])
    assert found["rows_reconcile"] == ("PASS", str(units))
    assert found["profiled_bronze_other_rows"][1] == "2"
    assert found["quarantine_rate"][0] == "WARN"
    assert not [name for name, (status, _) in found.items() if status == "FAIL"]
    assert set(found) == set(deped_enrollment_psgc.gate_checks(deped_enrollment_psgc.load_spec(REPO_ROOT)))
    # No enrollment count reaches Silver.
    columns = {name for (name, *_) in store.query(f"DESCRIBE {CLEAN}")}
    assert not {c for c in columns if c.endswith(("_male", "_female"))}


def test_profiled_counts_warn_when_they_change_and_never_fail(lane):
    store, repo, _ = lane
    params, silver = build(store, repo)
    gate(store, silver, params)
    found = checks(store, params["run_id"])
    profiled = {name: status for name, (status, _) in found.items() if name.startswith("profiled_")}
    assert profiled and set(profiled.values()) <= {"PASS", "WARN"}
    assert found["profiled_recoded"] == ("WARN", "1")       # the made-up workbook has 1 Sulu school, not 467


@pytest.mark.parametrize("update, check", [
    ("psgc_barangay = 'unknown'", "code_values_recognized"),
    ("longitude = 'n/a'", "coordinate_values_recognized"),
])
def test_an_unexpected_value_fails_the_gate_and_publishes_nothing(lane, update, check):
    store, repo, _ = lane
    store.sql(f"UPDATE {BRONZE} SET {update} WHERE school_id = '200001'")
    params, silver = build(store, repo)
    with pytest.raises(Exception, match="FAIL result"):
        gate(store, silver, params)
    assert checks(store, params["run_id"])[check][0] == "FAIL"
    assert store.query(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'deped_enrollment_psgc_clean'") == [(0,)]


def test_quarantine_above_one_percent_fails(lane):
    store, repo, _ = lane
    store.sql(f"UPDATE {BRONZE} SET school_id = school_id || '9' WHERE source_row_kind = 'unit' AND school_id LIKE '2000%'")
    params, silver = build(store, repo)
    with pytest.raises(Exception, match="FAIL result"):
        gate(store, silver, params)
    assert checks(store, params["run_id"])["quarantine_rate"][0] == "FAIL"


def test_a_rerun_rebuilds_the_same_rows(lane):
    store, repo, _ = lane
    first, silver = build(store, repo)
    gate(store, silver, first)
    before = store.query(f"SELECT * EXCLUDE (run_id, cleaned_at_utc) FROM {CLEAN} ORDER BY school_id")
    second, _ = build(store, repo)
    gate(store, silver, second)
    assert store.query(f"SELECT * EXCLUDE (run_id, cleaned_at_utc) FROM {CLEAN} ORDER BY school_id") == before
    assert store.query(f"SELECT DISTINCT run_id FROM {CLEAN}") == [(second["run_id"],)]
