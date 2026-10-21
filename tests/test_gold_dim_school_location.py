"""Gold dim_school_location (#217): its build and gate, run the way the job's two SQL tasks run them.

Made-up rows go straight into the published tables the build reads (deped_psgc_coordinates_clean,
deped_school_psgc_map, hdx_adm3_psgc_map, hdx_adm3_clean, dim_school) in an in-memory DuckDB, with square
boundaries whose answers are known. No real school, map or boundary is used.
"""

import uuid

import pytest

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.store import DuckDBStore

CONTROL = "edu_access.`01-control`"
SILVER = "edu_access.`03-silver`.deped_psgc_coordinates_clean"
SCHOOL_MAP = "edu_access.`04-integration`.deped_school_psgc_map"
HDX_MAP = "edu_access.`04-integration`.hdx_adm3_psgc_map"
HDX = "edu_access.`03-silver`.hdx_adm3_clean"
DIM_SCHOOL = "edu_access.`05-gold`.dim_school"
CANDIDATE = "edu_access.`05-gold`.dim_school_location_candidate"
DIM = "edu_access.`05-gold`.dim_school_location"
BUILD = REPO_ROOT / "etl" / "05_gold" / "07_build_dim_school_location.sql"
GATE = REPO_ROOT / "etl" / "05_gold" / "90_validate_dim_school_location.sql"
LATEST, OLDER = "2026-05-01", "2024-01-01"

CITY_A, CITY_B, CITY_C, CITY_D, CITY_E = "0102800000", "0102900000", "0103000000", "0103100000", "0103200000"


def square(lon, lat, size=1.0):
    ring = [[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]
    return '{"type": "Polygon", "coordinates": [' + str(ring) + "]}"


# school_id: (longitude, latitude, coordinate_flag, city in the SY 2023-24 map or None, map match_status)
SCHOOLS = {
    "100001": (120.5, 15.5, None, CITY_A, "matched"),        # inside A
    "100002": (122.5, 15.5, None, CITY_A, "matched"),        # outside A
    "100003": (None, None, "missing", CITY_A, "matched"),    # no point to test
    "100004": (120.5, 15.5, None, CITY_A, "ambiguous"),      # the map did not match a city
    "100005": (120.5, 15.5, None, CITY_B, "matched"),        # B has no boundary
    "100006": (125.5, 15.5, None, CITY_C, "matched"),        # C has two shapes; inside the second
    "100007": (126.5, 16.5, None, CITY_D, "matched"),        # D's only shape is in an older release
    "100008": (127.5, 17.5, None, CITY_E, "matched"),        # E's shape is not valid
    "100009": (120.5, 15.5, "zero", CITY_A, "matched"),      # flagged, even though the point would be inside
}
EXPECTED = {"100001": "inside", "100002": "outside", "100003": "no_usable_point", "100004": "no_matched_city",
            "100005": "no_boundary", "100006": "inside", "100007": "no_boundary", "100008": "no_boundary",
            "100009": "no_usable_point"}
FEATURES = [  # adm3_pcode, psgc_code, match_status, release, geometry, valid
    ("PH0102800", CITY_A, "matched", LATEST, square(120, 15), True),
    ("PH0103001", CITY_C, "matched", LATEST, square(122, 15), True),
    ("PH0103002", CITY_C, "matched", LATEST, square(125, 15), True),
    ("PH0103100", CITY_D, "matched", OLDER, square(126, 16), True),
    ("PH0103200", CITY_E, "matched", LATEST, square(127, 17), False),
    ("PH0109999", CITY_B, "unmatched", LATEST, square(120, 15), True),   # an unmatched feature is never used
]


class Env:
    def __init__(self, schools=None):
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        for schema in ("03-silver", "04-integration", "05-gold"):
            self.store.sql(f"CREATE SCHEMA IF NOT EXISTS edu_access.`{schema}`")
        self.store.sql(f"CREATE TABLE {SILVER} (school_year STRING, school_id STRING, longitude DOUBLE, latitude DOUBLE, "
                       "coordinate_flag STRING, run_id STRING)")
        self.store.sql(f"CREATE TABLE {SCHOOL_MAP} (school_year STRING, school_id STRING, geographic_level STRING, "
                       "psgc_code STRING, match_status STRING, run_id STRING)")
        self.store.sql(f"CREATE TABLE {HDX_MAP} (adm3_pcode STRING, psgc_code STRING, match_status STRING, "
                       "source_reference_date DATE, run_id STRING)")
        self.store.sql(f"CREATE TABLE {HDX} (adm3_pcode STRING, geometry STRING, geometry_is_valid BOOLEAN, valid_on DATE)")
        self.store.sql(f"CREATE TABLE {DIM_SCHOOL} (school_id STRING, school_name STRING)")
        self.load(SCHOOLS if schools is None else schools)
        for pcode, psgc, status, release, geometry, valid in FEATURES:
            self.store.sql(f"INSERT INTO {HDX_MAP} VALUES (?, ?, ?, CAST(? AS DATE), 'R-HDX')", [pcode, psgc, status, release])
            self.store.sql(f"INSERT INTO {HDX} VALUES (?, ?, ?, CAST(? AS DATE))", [pcode, geometry, valid, release])
        for run, pipeline, source in (("R-SILVER", "silver_build", "deped_psgc_coordinates"),
                                      ("R-MAP", "integration_build", "deped_enrollment"),
                                      ("R-HDX", "integration_build", "hdx_boundaries")):
            self.store.sql(f"INSERT INTO {CONTROL}.pipeline_runs (run_id, pipeline_name, source_id, environment, status, "
                           "code_revision, started_at_utc) VALUES (?, ?, ?, 'local', 'succeeded', 'c', TIMESTAMP '2026-10-21 00:00:00')",
                           [run, pipeline, source])

    def load(self, schools):
        for table in (SILVER, SCHOOL_MAP, DIM_SCHOOL):
            self.store.sql(f"DELETE FROM {table}")
        for school_id, (lon, lat, flag, city, status) in schools.items():
            self.store.sql(f"INSERT INTO {SILVER} VALUES ('2023-24', ?, ?, ?, ?, 'R-SILVER')", [school_id, lon, lat, flag])
            self.store.sql(f"INSERT INTO {DIM_SCHOOL} VALUES (?, 'Paaralan')", [school_id])
            if city:
                self.store.sql(f"INSERT INTO {SCHOOL_MAP} VALUES ('2023-24', ?, 'city_mun', ?, ?, 'R-MAP')", [school_id, city, status])
                self.store.sql(f"INSERT INTO {SCHOOL_MAP} VALUES ('2023-24', ?, 'bgy', ?, ?, 'R-MAP')", [school_id, city[:7] + "001", status])
            # Another school year puts every school in city B: never read, the location is SY 2023-24's.
            self.store.sql(f"INSERT INTO {SCHOOL_MAP} VALUES ('2024-25', ?, 'city_mun', ?, 'matched', 'R-MAP')", [school_id, CITY_B])

    def build(self, run_id=None):
        params = {"run_id": run_id or str(uuid.uuid4()), "code_revision": "c" * 40, "environment": "local"}
        self.store.run_file(BUILD, params)
        return params

    def gate(self, params):
        try:
            self.store.run_file(GATE, params)
        except Exception as e:  # the gate raises on FAIL after recording its checks
            return str(e)
        return None

    def run(self):
        params = self.build()
        return params["run_id"], self.gate(params)

    def checks(self, run_id):
        return {r["check_name"]: r for r in self.store.records(
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}' AND layer = 'gold'")}

    def dim(self):
        return {r["school_id"]: r for r in self.store.records(f"SELECT * FROM {DIM}")}


def test_each_school_gets_its_boundary_status_and_one_row():
    env = Env()
    run_id, error = env.run()
    assert error is None
    dim = env.dim()
    assert {k: v["boundary_status"] for k, v in dim.items()} == EXPECTED
    assert len(dim) == len(SCHOOLS)                                    # two shapes for city C did not add a row
    checks = env.checks(run_id)
    assert {c["status"] for c in checks.values()} == {"PASS"}
    assert checks["rows_reconcile"]["actual"] == str(len(SCHOOLS))
    assert (checks["schools_inside_boundary"]["actual"], checks["schools_outside_boundary"]["actual"],
            checks["schools_no_usable_point"]["actual"], checks["schools_no_matched_city"]["actual"],
            checks["schools_no_boundary"]["actual"]) == ("2", "1", "2", "1", "3")
    assert {name for name in checks if name.startswith("upstream_run_")} == {
        "upstream_run_deped_psgc_coordinates_clean", "upstream_run_deped_school_psgc_map", "upstream_run_hdx_adm3_psgc_map"}


def test_columns_follow_the_data_model_and_carry_silver_values_unchanged():
    env = Env()
    env.run()
    assert env.store.columns("05-gold", "dim_school_location") == [
        ("school_id", "VARCHAR"), ("longitude", "DOUBLE"), ("latitude", "DOUBLE"), ("coordinate_flag", "VARCHAR"),
        ("boundary_status", "VARCHAR")]
    dim = env.dim()
    assert (dim["100002"]["longitude"], dim["100002"]["latitude"], dim["100002"]["coordinate_flag"]) == (122.5, 15.5, None)
    assert (dim["100003"]["longitude"], dim["100003"]["coordinate_flag"]) == (None, "missing")   # never filled in
    assert dim["100009"]["coordinate_flag"] == "zero"


def test_a_rerun_rebuilds_the_same_rows_and_leaves_no_gate_table():
    env = Env()
    env.run()
    before = env.store.query(f"SELECT * FROM {DIM} ORDER BY school_id")
    env.run()
    assert env.store.query(f"SELECT * FROM {DIM} ORDER BY school_id") == before
    assert env.store.query("SELECT COUNT(*) FROM information_schema.tables "
                           "WHERE table_name LIKE 'dim_school_location_gate_summary_r_%'") == [(0,)]


def test_a_school_missing_from_dim_school_fails_and_keeps_the_last_good_build():
    env = Env()
    env.run()
    good = env.store.query(f"SELECT * FROM {DIM} ORDER BY school_id")
    env.store.sql(f"DELETE FROM {DIM_SCHOOL} WHERE school_id = '100002'")
    run_id, error = env.run()
    assert error and "FAIL" in error
    assert env.checks(run_id)["school_in_dim_school"]["status"] == "FAIL"
    assert env.store.query(f"SELECT * FROM {DIM} ORDER BY school_id") == good


def test_a_repeated_map_row_is_caught_not_hidden():
    """A second matched SY 2023-24 city row for one school would multiply it; the gate fails instead of DISTINCT."""
    env = Env()
    env.store.sql(f"INSERT INTO {SCHOOL_MAP} VALUES ('2023-24', '100001', 'city_mun', ?, 'matched', 'R-MAP')", [CITY_C])
    run_id, error = env.run()
    assert error and "FAIL" in error
    checks = env.checks(run_id)
    assert checks["key_unique"]["status"] == "FAIL" and checks["rows_reconcile"]["status"] == "FAIL"


@pytest.mark.parametrize("tamper, check", [
    ("boundary_status = 'inside' WHERE school_id = '100005'", "boundary_status_follows_inputs"),     # no boundary to be inside
    ("boundary_status = 'outside' WHERE school_id = '100003'", "boundary_status_follows_inputs"),    # flagged point tested
    ("boundary_status = 'unknown' WHERE school_id = '100001'", "boundary_status_allowed"),
    ("longitude = longitude + 0.001 WHERE school_id = '100001'", "values_match_source"),
    ("coordinate_flag = NULL WHERE school_id = '100003'", "values_match_source"),
])
def test_a_candidate_that_differs_from_its_inputs_fails_the_gate(tamper, check):
    env = Env()
    params = env.build()
    env.store.sql(f"UPDATE {CANDIDATE} SET {tamper}")
    error = env.gate(params)
    assert error and "FAIL" in error
    assert env.checks(params["run_id"])[check]["status"] == "FAIL"


def test_an_upstream_run_that_did_not_succeed_fails_the_gate():
    env = Env()
    env.store.sql(f"UPDATE {CONTROL}.pipeline_runs SET status = 'failed' WHERE run_id = 'R-HDX'")
    run_id, error = env.run()
    assert error and "FAIL" in error
    assert env.checks(run_id)["upstream_run_hdx_adm3_psgc_map"]["status"] == "FAIL"


def test_an_empty_silver_table_gives_an_empty_dimension_that_reconciles():
    """Silver's own gate never publishes an empty build (current_batch_present), so Gold only sees this if run
    by hand; it then publishes nothing to map rather than inventing rows."""
    env = Env(schools={})
    run_id, error = env.run()
    assert error is None
    assert env.dim() == {}
    assert env.checks(run_id)["rows_reconcile"]["actual"] == "0"
