"""Gold dim_school_location (D-061): its build and gate, run the way the job's two SQL tasks run them.

Made-up rows go straight into the published tables the build reads (deped_psgc_coordinates_clean,
fact_school_enrollment, dim_barangay, hdx_adm3_psgc_map, hdx_adm3_clean) in an in-memory DuckDB. No real DepEd
point or COD-AB boundary is used: each city is a one-degree square.
"""

import uuid

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.store import DuckDBStore

CONTROL = "edu_access.`01-control`"
DIM = "edu_access.`05-gold`.dim_school_location"
CANDIDATE = "edu_access.`05-gold`.dim_school_location_candidate"
BUILD = REPO_ROOT / "etl" / "05_gold" / "07_build_dim_school_location.sql"
GATE = REPO_ROOT / "etl" / "05_gold" / "90_validate_dim_school_location.sql"
RELEASE, OLD_RELEASE = "2025-02-13", "2023-11-06"

C1, C2, C3 = "0102801000", "0102802000", "0102803000"   # C3 has no matched HDX feature


def square(west, south, east, north):
    return ('{"type": "Polygon", "coordinates": [[[%s, %s], [%s, %s], [%s, %s], [%s, %s], [%s, %s]]]}'
            % (west, south, east, south, east, north, west, north, west, south))


# adm3_pcode, release, psgc_code, match_status, geometry
HDX = [
    ("PH0102801", RELEASE, C1, "matched", square(120, 14, 121, 15)),
    ("PH0102802", RELEASE, C2, "matched", square(121, 14, 122, 15)),
    ("PH0102803", RELEASE, C3, "unmatched", square(122, 14, 123, 15)),     # not matched: never a boundary
    ("PH0102801", OLD_RELEASE, C1, "matched", square(120, 14, 122, 15)),   # an older release: never read
]

# school_id, school_year, longitude, latitude, coordinate_flag
POINTS = [
    ("A1", "2023-24", 120.5, 14.5, None),            # inside City One
    ("A2", "2023-24", 121.5, 14.5, None),            # matched to City One, but the point is in City Two
    ("A3", "2023-24", None, None, "missing"),
    ("A4", "2023-24", 120.5, 14.25, None),           # no matched city in fact_school_enrollment
    ("A5", "2023-24", 122.5, 14.5, None),            # its city has no matched HDX feature
    ("A1", "2022-23", 121.5, 14.5, None),            # another school year: never read
]

# school_id, school_year, education_level, city, sector, psgc_match_status, barangay
FACT = [
    ("A1", "2023-24", "ES", C1, "Public", "matched", f"{C1}-B1"),
    ("A1", "2023-24", "JHS", C1, "Public", "matched", f"{C1}-B1"),
    ("A2", "2023-24", "ES", C1, "Public", "matched", f"{C1}-B2"),
    ("A3", "2023-24", "ES", C1, "Public", "matched", f"{C1}-B1"),
    ("A4", "2023-24", "ES", "UNKNOWN", "Public", "unmatched", "UNKNOWN"),
    ("A5", "2023-24", "ES", C3, "Public", "matched", f"{C3}-B1"),
]

BARANGAYS = [(f"{C1}-B1", "U"), (f"{C1}-B2", "R"), (f"{C3}-B1", "R"), ("UNKNOWN", None)]


class Env:
    def __init__(self, hdx=HDX):
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        for schema in ("03-silver", "04-integration", "05-gold"):
            self.store.sql(f"CREATE SCHEMA IF NOT EXISTS edu_access.`{schema}`")
        self.store.sql("CREATE TABLE edu_access.`03-silver`.deped_psgc_coordinates_clean (school_id STRING, "
                       "school_year STRING, longitude DOUBLE, latitude DOUBLE, coordinate_flag STRING)")
        self.store.con.executemany(
            "INSERT INTO edu_access.\"03-silver\".deped_psgc_coordinates_clean VALUES (?, ?, ?, ?, ?)", POINTS)
        self.store.sql("CREATE TABLE edu_access.`05-gold`.fact_school_enrollment (school_id STRING, school_year STRING, "
                       "education_level STRING, city_mun_psgc_code STRING, sector STRING, psgc_match_status STRING, "
                       "barangay_psgc_code STRING)")
        self.store.con.executemany(
            "INSERT INTO edu_access.\"05-gold\".fact_school_enrollment VALUES (?, ?, ?, ?, ?, ?, ?)", FACT)
        self.store.sql("CREATE TABLE edu_access.`05-gold`.dim_barangay (barangay_psgc_code STRING, urban_rural STRING)")
        self.store.con.executemany("INSERT INTO edu_access.\"05-gold\".dim_barangay VALUES (?, ?)", BARANGAYS)
        self.store.sql("CREATE TABLE edu_access.`03-silver`.hdx_adm3_clean (adm3_pcode STRING, valid_on DATE, "
                       "geometry STRING, run_id STRING)")
        self.store.sql("CREATE TABLE edu_access.`04-integration`.hdx_adm3_psgc_map (adm3_pcode STRING, "
                       "source_reference_date DATE, psgc_code STRING, match_status STRING, run_id STRING)")
        for pcode, release, code, status, geometry in hdx:
            self.store.sql(f"INSERT INTO edu_access.`03-silver`.hdx_adm3_clean VALUES (?, DATE '{release}', ?, 'S1')",
                           [pcode, geometry])
            self.store.sql(f"INSERT INTO edu_access.`04-integration`.hdx_adm3_psgc_map VALUES (?, DATE '{release}', ?, ?, "
                           "'M1')", [pcode, code, status])

    def run(self, build=True):
        run_id = str(uuid.uuid4())
        params = {"run_id": run_id, "code_revision": "c" * 40, "environment": "local"}
        try:
            if build:
                self.store.run_file(BUILD, params)
            self.store.run_file(GATE, params)
        except Exception as e:
            return run_id, str(e)
        return run_id, None

    def checks(self, run_id):
        return {r["check_name"]: r for r in self.store.records(
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}' AND layer = 'gold'")}

    def dim(self):
        return {r["school_id"]: r for r in self.store.records(f"SELECT * FROM {DIM}")}


def test_one_row_per_school_with_its_boundary_test_status():
    env = Env()
    run_id, error = env.run()
    assert error is None
    dim = env.dim()
    assert {school: row["boundary_test_status"] for school, row in dim.items()} == {
        "A1": "inside", "A2": "outside", "A3": "no_point", "A4": "no_city_match", "A5": "no_boundary"}
    assert [school for school, row in dim.items() if row["is_location_usable"]] == ["A1"]
    a1 = dim["A1"]
    assert (a1["school_year"], a1["city_mun_psgc_code"], a1["barangay_psgc_code"], a1["urban_rural"]) == \
        ("2023-24", C1, f"{C1}-B1", "U")
    assert (a1["longitude"], a1["latitude"], a1["location_source"]) == (120.5, 14.5, "deped_psgc_coordinates")
    assert dim["A2"]["urban_rural"] == "R"
    assert dim["A4"]["city_mun_psgc_code"] is None and dim["A4"]["urban_rural"] is None
    assert dim["A3"]["coordinate_flag"] == "missing" and dim["A3"]["longitude"] is None   # kept, never filled


def test_columns_follow_the_data_model():
    env = Env()
    env.run()
    assert env.store.columns("05-gold", "dim_school_location") == [
        ("school_id", "VARCHAR"), ("school_year", "VARCHAR"), ("city_mun_psgc_code", "VARCHAR"),
        ("barangay_psgc_code", "VARCHAR"), ("urban_rural", "VARCHAR"), ("longitude", "DOUBLE"),
        ("latitude", "DOUBLE"), ("coordinate_flag", "VARCHAR"), ("boundary_test_status", "VARCHAR"),
        ("is_location_usable", "BOOLEAN"), ("location_source", "VARCHAR")]


def test_gate_records_every_check_under_catalog_names():
    # names already in config/quality_attributes.yml, so the data-quality dashboard file is not regenerated
    env = Env()
    run_id, error = env.run()
    assert error is None
    checks = env.checks(run_id)
    assert {name: c["status"] for name, c in checks.items() if c["status"] != "PASS"} == {
        "schools_city_unknown": "WARN", "psgc_units_without_feature": "WARN"}
    assert {name for name, c in checks.items() if c["status"] == "PASS"} == {
        "rows_reconcile", "key_unique", "key_not_null", "coordinates_reconcile", "values_match_source",
        "status_valid", "derived_values_reconcile", "outlier_schools"}
    assert (checks["rows_reconcile"]["expected"], checks["rows_reconcile"]["actual"]) == ("5", "5")
    assert checks["outlier_schools"]["actual"] == "1"              # A2: outside its own city (S-1)
    assert checks["psgc_units_without_feature"]["actual"] == "1"   # C3
    assert checks["schools_city_unknown"]["actual"] == "1"         # A4
    tables = [r["table_name"] for r in env.store.records(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'dim_school_location_gate_summary%'")]
    assert tables == []


def test_only_the_latest_hdx_release_is_used():
    # The older release's City One also covers A2's point; with only that release A2 would be inside.
    env = Env(hdx=[row for row in HDX if row[1] == OLD_RELEASE])
    run_id, error = env.run()
    assert error is None
    assert env.dim()["A2"]["boundary_test_status"] == "inside"
    env = Env()
    env.run()
    assert env.dim()["A2"]["boundary_test_status"] == "outside"


def test_gate_rejects_a_boundary_result_it_cannot_recompute_and_keeps_the_last_good_build():
    env = Env()
    _, error = env.run()
    assert error is None
    env.store.sql(f"UPDATE {CANDIDATE} SET boundary_test_status = 'inside', is_location_usable = TRUE "
                  "WHERE school_id = 'A2'")
    run_id, error = env.run(build=False)
    assert "Gold gate failed for dim_school_location" in error
    checks = env.checks(run_id)
    assert checks["derived_values_reconcile"]["status"] == "FAIL"
    assert checks["derived_values_reconcile"]["actual"] == "1"
    assert env.dim()["A2"]["boundary_test_status"] == "outside"   # dim_school_location was not replaced


def test_gate_rejects_a_usable_location_that_is_not_inside():
    env = Env()
    env.run()
    env.store.sql(f"UPDATE {CANDIDATE} SET is_location_usable = TRUE WHERE school_id = 'A5'")
    run_id, error = env.run(build=False)
    assert error is not None
    assert env.checks(run_id)["status_valid"]["status"] == "FAIL"


def test_gate_rejects_a_point_that_differs_from_silver():
    env = Env()
    env.run()
    env.store.sql(f"UPDATE {CANDIDATE} SET latitude = 14.6 WHERE school_id = 'A1'")
    run_id, error = env.run(build=False)
    assert error is not None
    assert env.checks(run_id)["coordinates_reconcile"]["status"] == "FAIL"
