"""AP1 school-provision output (#144), exercised through its build and publication gate."""

import uuid

import pytest

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.store import DuckDBStore

CONTROL = "edu_access.`01-control`"
GOLD = "edu_access.`05-gold`"
ANALYTICS = "edu_access.`06-analytics`"
FACT = f"{GOLD}.fact_school_enrollment"
OUTPUT = f"{ANALYTICS}.ap1_school_provision"
BUILD = REPO_ROOT / "etl" / "06_analytics" / "01_answer_ap1.sql"
GATE = REPO_ROOT / "etl" / "06_analytics" / "90_validate_ap1.sql"


class Env:
    def __init__(self):
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        for schema in ("05-gold", "06-analytics"):
            self.store.sql(f"CREATE SCHEMA IF NOT EXISTS edu_access.`{schema}`")
        self.store.sql(f"""CREATE TABLE {GOLD}.dim_city_municipality (
            city_mun_psgc_code STRING, city_mun_name STRING, lgu_type STRING,
            province_psgc_code STRING, province_name STRING, region_psgc_code STRING,
            region_name STRING, member_type STRING)""")
        self.store.sql(f"""INSERT INTO {GOLD}.dim_city_municipality VALUES
            ('0100100000', 'Alpha', 'municipality', '0100000000', 'Province', '0100000000', 'Region', 'regular'),
            ('0100200000', 'Beta', 'municipality', '0100000000', 'Province', '0100000000', 'Region', 'regular'),
            ('UNKNOWN', 'Unknown', NULL, NULL, NULL, NULL, NULL, 'unknown')""")
        self.store.sql(f"""CREATE TABLE {GOLD}.dim_barangay (
            barangay_psgc_code STRING, city_mun_psgc_code STRING, member_type STRING)""")
        self.store.sql(f"""INSERT INTO {GOLD}.dim_barangay VALUES
            ('0100100001', '0100100000', 'regular'), ('0100100002', '0100100000', 'regular'),
            ('0100100000-UNKNOWN', '0100100000', 'unknown'), ('0100200001', '0100200000', 'regular'),
            ('0100200000-UNKNOWN', '0100200000', 'unknown')""")
        self.store.sql(f"""CREATE TABLE {GOLD}.fact_city_population (
            city_mun_psgc_code STRING, reference_year INT, population BIGINT,
            estimate_status STRING, status_reason STRING)""")
        self.store.sql(f"""INSERT INTO {GOLD}.fact_city_population VALUES
            ('0100100000', 2024, 1000, 'available', NULL),
            ('0100200000', 2024, NULL, 'missing', 'PSGC publishes no 2024 population')""")
        self.store.sql(f"""CREATE TABLE {FACT} (
            school_id STRING, school_year STRING, education_level_code STRING,
            city_mun_psgc_code STRING, barangay_psgc_code STRING, psgc_match_status STRING,
            sector STRING, annex_status STRING, is_offered BOOLEAN, learner_count BIGINT)""")
        rows = [
            ("A", "ES", "0100100001", "Standalone School", True, 10),
            ("A", "JHS", "0100100001", "Standalone School", True, 20),
            ("A", "SHS", "0100100001", "Standalone School", False, 0),
            ("B", "ES", "0100100000-UNKNOWN", "Annex/Extension School", True, 5),
            ("B", "JHS", "0100100000-UNKNOWN", "Annex/Extension School", True, None),
            ("B", "SHS", "0100100000-UNKNOWN", "Annex/Extension School", False, 0),
            ("C", "ES", "0100100002", "Standalone School", True, 100),
            ("C", "JHS", "0100100002", "Standalone School", False, 0),
            ("C", "SHS", "0100100002", "Standalone School", False, 0),
            ("D", "ES", "0100200001", "Standalone School", True, 0),
            ("D", "JHS", "0100200001", "Standalone School", False, 0),
            ("D", "SHS", "0100200001", "Standalone School", False, 0),
        ]
        for school_id, level, barangay, annex, offered, learners in rows:
            sector = "Private" if school_id == "C" else "Public"
            city = "0100200000" if school_id == "D" else "0100100000"
            self.store.sql(f"INSERT INTO {FACT} VALUES (?, '2023-24', ?, ?, ?, 'matched', ?, ?, ?, ?)",
                           [school_id, level, city, barangay, sector, annex, offered, learners])

    def run(self, tamper=None):
        params = {"run_id": str(uuid.uuid4()), "code_revision": "c" * 40, "environment": "local"}
        try:
            self.store.run_file(BUILD, params)
            if tamper:
                self.store.sql(tamper)
            self.store.run_file(GATE, params)
        except Exception as error:
            return params["run_id"], str(error)
        return params["run_id"], None

    def row(self, city, level):
        return self.store.records(
            f"SELECT * FROM {OUTPUT} WHERE city_mun_psgc_code = ? AND education_level_code = ?", [city, level])[0]

    def failed(self, run_id):
        return {row["check_name"] for row in self.store.records(
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = ? AND status = 'FAIL'", [run_id])}


def test_ap1_follows_active_complete_and_population_rules():
    env = Env()
    run_id, error = env.run()
    assert error is None and not env.failed(run_id)
    row = env.row("0100100000", "ALL")
    assert (row["public_school_count"], row["complete_enrollment_school_count"],
            row["incomplete_enrollment_school_count"]) == (2, 1, 1)
    assert row["public_school_enrollment"] == 30
    assert row["learners_per_public_school"] == 30
    assert row["population_reference_year"] == 2024
    assert row["population_per_public_school"] == 500
    es = env.row("0100100000", "ES")
    assert (es["public_school_count"], es["public_school_enrollment"], es["learners_per_public_school"]) == (2, 15, 7.5)
    assert es["population_denominator_school_count"] == 2 and es["population_per_public_school"] == 500


def test_barangay_screen_uses_regular_barangays_and_labels_upper_bound():
    env = Env()
    _, error = env.run()
    assert error is None
    row = env.row("0100100000", "ALL")
    assert (row["barangay_count"], row["barangays_with_public_es"], row["barangays_without_public_es"]) == (2, 1, 1)
    assert row["barangays_without_public_es_pct"] == 50
    assert row["public_es_schools_without_barangay_match"] == 1
    assert row["active_public_es_school_count"] == 2
    assert row["public_es_schools_with_barangay_match"] == 1
    assert row["barangay_match_coverage_pct"] == 50
    assert row["barangay_count_is_upper_bound"] is True


def test_lgu_without_active_school_or_population_is_retained():
    env = Env()
    _, error = env.run()
    assert error is None
    row = env.row("0100200000", "ALL")
    assert row["public_school_count"] == 0
    assert row["learners_per_public_school"] is None
    assert row["population_per_public_school"] is None
    assert row["population_ratio_null_reason"] == "PSGC publishes no 2024 population"
    assert row["barangays_without_public_es"] == 1


def test_rerun_is_deterministic():
    env = Env()
    _, error = env.run()
    assert error is None
    first = env.store.records(f"SELECT * FROM {OUTPUT} ORDER BY city_mun_psgc_code, school_year, education_level_code")
    _, error = env.run()
    assert error is None
    assert env.store.records(f"SELECT * FROM {OUTPUT} ORDER BY city_mun_psgc_code, school_year, education_level_code") == first


def test_gate_catches_a_valid_looking_changed_school_count_and_keeps_last_good_output():
    env = Env()
    _, error = env.run()
    assert error is None
    before = env.row("0100100000", "ALL")
    candidate = f"{ANALYTICS}.ap1_school_provision_candidate"
    run_id, error = env.run(
        f"UPDATE {candidate} SET public_school_count = 3, incomplete_enrollment_school_count = 2, "
        "population_per_public_school = population_2024 / 3.0 WHERE city_mun_psgc_code = '0100100000' "
        "AND education_level_code = 'ALL'")
    assert error and "Analytics gate failed for ap1_school_provision" in error
    assert "school_counts_and_enrollment_match_fact" in env.failed(run_id)
    assert env.row("0100100000", "ALL") == before


@pytest.mark.parametrize("change, expected_check", [
    ("barangays_with_public_es = 2, barangays_without_public_es = 0, "
     "barangays_without_public_es_pct = 0", "barangay_metrics_match_fact_and_dimension"),
    ("population_2024 = 1200, population_per_public_school = 600", "identity_and_population_match_gold"),
])
def test_gate_reconciles_source_values_even_when_derived_values_still_agree(change, expected_check):
    env = Env()
    candidate = f"{ANALYTICS}.ap1_school_provision_candidate"
    run_id, error = env.run(
        f"UPDATE {candidate} SET {change} WHERE city_mun_psgc_code = '0100100000' AND education_level_code = 'ALL'")
    assert error and "Analytics gate failed for ap1_school_provision" in error
    assert expected_check in env.failed(run_id)
