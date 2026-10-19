"""AP2 classroom-pressure output (#145), exercised through its build and publication gate."""

import uuid

import pytest

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.store import DuckDBStore

CONTROL = "edu_access.`01-control`"
GOLD = "edu_access.`05-gold`"
ANALYTICS = "edu_access.`06-analytics`"
ENROLLMENT = f"{GOLD}.fact_school_enrollment"
CAPACITY = f"{GOLD}.fact_school_classroom_capacity"
CANDIDATE = f"{ANALYTICS}.ap2_classroom_pressure_candidate"
OUTPUT = f"{ANALYTICS}.ap2_classroom_pressure"
BUILD = REPO_ROOT / "etl" / "06_analytics" / "02_answer_ap2.sql"
GATE = REPO_ROOT / "etl" / "06_analytics" / "90_validate_ap2.sql"
REVISION = "c" * 40

ALPHA, BETA, GAMMA, DELTA, EPSILON = "0100100000", "0100200000", "0100300000", "0100400000", "0100500000"
STANDALONE, ANNEX = "Standalone School", "Annex/Extension School"

# (school_id, city, sector, annex_status, {level: (is_offered, learner_count)}, rooms or "none" for no row)
SCHOOLS = [
    ("A", ALPHA, "Public", STANDALONE, {"ES": (True, 100), "JHS": (True, 50)}, 5),  # in the ratio
    ("B", ALPHA, "Public", ANNEX, {"ES": (True, 30)}, None),                         # rooms all blank
    ("C", ALPHA, "Public", STANDALONE, {"ES": (True, 40)}, 0),                       # reported zero rooms
    ("D", ALPHA, "Public", STANDALONE, {"ES": (True, 20), "JHS": (True, None)}, 4),  # incomplete enrollment
    ("E", ALPHA, "Public", STANDALONE, {"ES": (True, 10)}, "none"),                  # no facilities row
    ("F", ALPHA, "Public", STANDALONE, {"ES": (True, 0)}, 2),                        # inactive
    ("P", ALPHA, "Private", STANDALONE, {"ES": (True, 999)}, 9),                     # not public
    ("H", GAMMA, "Public", STANDALONE, {"ES": (True, 90)}, 3),
    ("I", GAMMA, "Public", STANDALONE, {"ES": (True, 60), "JHS": (True, 0)}, 2),
    ("M", DELTA, "Public", STANDALONE, {"ES": (True, 10)}, 0),
    ("Q", EPSILON, "Public", STANDALONE, {"ES": (True, 10), "JHS": (True, None)}, 3),
    ("J", "UNKNOWN", "Public", STANDALONE, {"ES": (True, 70)}, 7),                   # unmatched geography
    ("L", "EXCLUDED", "Public", STANDALONE, {"ES": (True, 15)}, 1),
    ("K", "EXCLUDED", "PSO", STANDALONE, {"ES": (True, 25)}, "none"),                # overseas
]


class Env:
    def __init__(self, schools=SCHOOLS):
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        for schema in ("05-gold", "06-analytics"):
            self.store.sql(f"CREATE SCHEMA IF NOT EXISTS edu_access.`{schema}`")
        self.store.sql(f"""CREATE TABLE {GOLD}.dim_city_municipality (
            city_mun_psgc_code STRING, city_mun_name STRING, lgu_type STRING, province_psgc_code STRING,
            province_name STRING, region_psgc_code STRING, region_name STRING, member_type STRING,
            source_psgc_quarter STRING)""")
        for code, name, lgu_type in [(ALPHA, "Alpha", "municipality"), (BETA, "Beta", "municipality"),
                                     (GAMMA, "Gamma", "city"), (DELTA, "Delta", "municipality"),
                                     (EPSILON, "Epsilon", "municipality")]:
            self.store.sql(f"INSERT INTO {GOLD}.dim_city_municipality VALUES "
                           "(?, ?, ?, '0100000000', 'Province', '0100000000', 'Region', 'regular', '2Q 2026')",
                           [code, name, lgu_type])
        self.store.sql(f"""INSERT INTO {GOLD}.dim_city_municipality VALUES
            ('UNKNOWN', 'Unknown', NULL, NULL, NULL, NULL, NULL, 'unknown', '2Q 2026'),
            ('EXCLUDED', 'Excluded', NULL, NULL, NULL, NULL, NULL, 'excluded', '2Q 2026')""")
        self.store.sql(f"""CREATE TABLE {ENROLLMENT} (
            school_id STRING, school_year STRING, education_level_code STRING, city_mun_psgc_code STRING,
            barangay_psgc_code STRING, psgc_match_status STRING, sector STRING, annex_status STRING,
            is_offered BOOLEAN, learner_count BIGINT)""")
        self.store.sql(f"""CREATE TABLE {CAPACITY} (
            school_id STRING, school_year STRING, instructional_classrooms_total INT,
            temporary_learning_spaces INT, classes_using_temporary_learning_spaces INT,
            makeshift_rooms INT, classes_using_makeshift_rooms INT)""")
        for school in schools:
            self.add_school(*school)
        # Another school year in both facts, which AP2 must not read.
        self.add_school("G", ALPHA, "Public", STANDALONE, {"ES": (True, 500)}, 10, school_year="2024-25")

    def add_school(self, school_id, city, sector, annex, levels, rooms, school_year="2023-24"):
        status = {"UNKNOWN": "unmatched", "EXCLUDED": "excluded"}.get(city, "matched")
        for level in ("ES", "JHS", "SHS"):
            offered, learners = levels.get(level, (False, 0))
            self.store.sql(f"INSERT INTO {ENROLLMENT} VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
                           [school_id, school_year, level, city, status, sector, annex, offered, learners])
        if rooms != "none":
            # Temporary and makeshift spaces are set high so a denominator that used them would show.
            self.store.sql(f"INSERT INTO {CAPACITY} VALUES (?, ?, ?, 50, 50, 50, 50)", [school_id, school_year, rooms])

    def run(self, before_gate=None):
        params = {"run_id": str(uuid.uuid4()), "code_revision": REVISION, "environment": "local"}
        try:
            self.store.run_file(BUILD, params)
            if before_gate:
                self.store.sql(before_gate)
            self.store.run_file(GATE, params)
        except Exception as error:
            return params["run_id"], str(error)
        return params["run_id"], None

    def row(self, city, table=OUTPUT):
        return self.store.records(f"SELECT * FROM {table} WHERE city_mun_psgc_code = ?", [city])[0]

    def results(self, run_id, status=None):
        rows = self.store.records(f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = ?", [run_id])
        return {r["check_name"]: r for r in rows if status is None or r["status"] == status}


@pytest.fixture(scope="module")
def passed():
    env = Env()
    run_id, error = env.run()
    assert error is None, error
    return env, run_id


def test_gate_passes_and_publishes_one_row_per_regular_lgu_for_2023_24(passed):
    env, run_id = passed
    assert not env.results(run_id, "FAIL")
    rows = env.store.records(f"SELECT city_mun_psgc_code, school_year FROM {OUTPUT} ORDER BY 1")
    assert [r["city_mun_psgc_code"] for r in rows] == [ALPHA, BETA, GAMMA, DELTA, EPSILON]
    assert {r["school_year"] for r in rows} == {"2023-24"}


def test_ratio_is_a_ratio_of_sums_over_the_same_schools(passed):
    env, _ = passed
    alpha = env.row(ALPHA)
    # Only A is active, complete and has rooms above 0: 150 learners over 5 rooms. D's 4 rooms stay out
    # because its enrollment is incomplete; temporary and makeshift spaces are never added.
    assert (alpha["ratio_school_count"], alpha["ratio_learners"], alpha["ratio_instructional_rooms"]) == (1, 150, 5)
    assert alpha["learners_per_nsbi_instructional_room"] == 30
    gamma = env.row(GAMMA)
    # (90 + 60) / (3 + 2) = 30, not the mean of 30 and 30 by chance: the school ratios are 30 and 30.
    assert (gamma["ratio_learners"], gamma["ratio_instructional_rooms"]) == (150, 5)
    assert gamma["learners_per_nsbi_instructional_room"] == 30
    assert alpha["measure_label"] == "Learners per reported instructional room"
    assert alpha["source_label"] == "DepEd School Facilities (NSBI)"
    assert (alpha["validation_status"], alpha["benchmark_status"]) == ("provisional", "not applicable")
    assert alpha["code_revision"] == REVISION and alpha["source_psgc_quarter"] == "2Q 2026"


def test_ratio_of_sums_differs_from_an_average_of_school_ratios():
    env = Env([("X", ALPHA, "Public", STANDALONE, {"ES": (True, 100)}, 1),
               ("Y", ALPHA, "Public", STANDALONE, {"ES": (True, 100)}, 9)])
    _, error = env.run()
    assert error is None
    # Sum: 200 / 10 = 20. The mean of school ratios (100 and 11.1) would be 55.6.
    assert env.row(ALPHA)["learners_per_nsbi_instructional_room"] == 20


def test_coverage_follows_the_metric_specification(passed):
    env, _ = passed
    alpha = env.row(ALPHA)
    # Active schools A to E (F has no learners); A and D have rooms above 0.
    assert (alpha["active_public_school_count"], alpha["usable_room_school_count"]) == (5, 2)
    assert alpha["school_coverage_pct"] == pytest.approx(40)
    # Complete learners: A 150 + B 30 + C 40 + E 10; D is incomplete and has no total.
    assert alpha["public_school_enrollment"] == 230
    assert alpha["learner_coverage_pct"] == pytest.approx(150 / 230 * 100)
    assert alpha["usable_room_incomplete_enrollment_school_count"] == 1


def test_missing_zero_and_absent_rooms_stay_distinct(passed):
    env, run_id = passed
    alpha = env.row(ALPHA)
    assert (alpha["missing_room_school_count"], alpha["missing_room_learners"]) == (1, 30)
    assert (alpha["zero_room_school_count"], alpha["zero_room_learners"]) == (1, 40)
    assert (alpha["no_facilities_row_school_count"], alpha["no_facilities_row_learners"]) == (1, 10)
    warned = env.results(run_id, "WARN")
    assert warned["schools_missing_rooms"]["actual"] == "1"
    assert warned["schools_zero_rooms"]["actual"] == "2"  # C, and M in Delta
    assert warned["schools_without_facilities_row"]["actual"] == "1"


def test_incomplete_and_inactive_schools_remain_visible(passed):
    env, run_id = passed
    alpha = env.row(ALPHA)
    assert (alpha["complete_enrollment_school_count"], alpha["incomplete_enrollment_school_count"]) == (4, 1)
    # D's complete ES level is shown for audit, never as a school total.
    assert alpha["incomplete_enrollment_complete_level_learners"] == 20
    assert alpha["inactive_public_school_count"] == 1
    warned = env.results(run_id, "WARN")
    assert warned["schools_incomplete_enrollment"]["actual"] == "2"  # D and Q
    assert warned["schools_inactive"]["actual"] == "1"


def test_lgus_without_a_ratio_keep_a_null_and_a_reason(passed):
    env, _ = passed
    beta, delta, epsilon = env.row(BETA), env.row(DELTA), env.row(EPSILON)
    assert beta["learners_per_nsbi_instructional_room"] is None
    assert beta["ratio_null_reason"] == "no active public school"
    assert beta["school_coverage_pct"] is None and beta["coverage_null_reason"] == "no active public school"
    # A reported zero gives a NULL ratio, never 0, and 0% coverage.
    assert delta["learners_per_nsbi_instructional_room"] is None
    assert delta["ratio_null_reason"] == "no school with a reported room count above 0"
    assert (delta["school_coverage_pct"], delta["learner_coverage_pct"]) == (0, 0)
    assert epsilon["ratio_null_reason"] == "no school with both complete enrollment and a reported room count above 0"
    assert epsilon["school_coverage_pct"] == 100
    assert epsilon["learner_coverage_pct"] is None
    assert epsilon["coverage_null_reason"] == "no active public school with complete enrollment"


def test_annexes_are_flagged_not_treated_as_zero_room_schools(passed):
    env, run_id = passed
    alpha = env.row(ALPHA)
    assert alpha["annex_school_count"] == 1
    assert (alpha["annex_without_usable_room_school_count"], alpha["annex_without_usable_room_learners"]) == (1, 30)
    assert alpha["zero_room_school_count"] == 1  # C only; annex B has blank rooms, not zero
    warned = env.results(run_id, "WARN")
    assert warned["annexes_without_mother_link"]["actual"] == "1"
    assert warned["annexes_without_usable_rooms"]["actual"] == "1"


def test_unresolved_geography_and_overseas_schools_are_reported_not_attributed(passed):
    env, run_id = passed
    totals = env.store.records(f"SELECT SUM(active_public_school_count) AS schools FROM {OUTPUT}")[0]
    assert totals["schools"] == 9  # A-E, H, I, M, Q: not J, L, K, P or the 2024-25 school G
    assert not env.store.records(f"SELECT * FROM {OUTPUT} WHERE city_mun_psgc_code IN ('UNKNOWN', 'EXCLUDED')")
    warned = env.results(run_id, "WARN")
    assert (warned["schools_unknown_geography"]["actual"], warned["learners_unknown_geography"]["actual"]) == ("1", "70")
    assert (warned["schools_excluded_geography"]["actual"], warned["learners_excluded_geography"]["actual"]) == ("1", "15")
    assert warned["rooms_outside_regular_lgus"]["actual"] == "8"
    assert env.results(run_id)["no_overseas_school_in_lgus"]["status"] == "PASS"


def test_outliers_are_recorded_without_changing_values():
    schools = [(f"S{i}", ALPHA, "Public", STANDALONE, {"ES": (True, 10)}, 1) for i in range(4)]
    schools.append(("S9", ALPHA, "Public", STANDALONE, {"ES": (True, 100)}, 1))
    env = Env(schools)
    run_id, error = env.run()
    assert error is None
    outlier = env.results(run_id)["outlier_schools/municipality"]
    assert (outlier["status"], outlier["expected"], outlier["actual"]) == ("WARN", "fence 10.0", "1")
    alpha = env.row(ALPHA)
    assert (alpha["ratio_learners"], alpha["ratio_instructional_rooms"]) == (140, 5)


def test_a_repeated_capacity_row_fails_the_gate_and_keeps_the_last_output():
    env = Env()
    _, error = env.run()
    assert error is None
    env.store.sql(f"INSERT INTO {CAPACITY} VALUES ('A', '2023-24', 5, 0, 0, 0, 0)")
    run_id, error = env.run()
    assert "Analytics gate failed for ap2_classroom_pressure" in error
    failed = env.results(run_id, "FAIL")
    assert {"capacity_one_row_per_school", "capacity_join_adds_no_rows"} <= set(failed)
    assert env.row(ALPHA)["ratio_instructional_rooms"] == 5  # last good output, not the doubled build
    assert env.row(ALPHA, CANDIDATE)["ratio_instructional_rooms"] == 10


def test_capacity_without_2023_24_fails():
    env = Env()
    env.store.sql(f"DELETE FROM {CAPACITY} WHERE school_year = '2023-24'")
    run_id, error = env.run()
    assert error is not None
    assert "capacity_has_2023_24" in env.results(run_id, "FAIL")


@pytest.mark.parametrize(("tamper", "check"), [
    (f"UPDATE {CANDIDATE} SET learners_per_nsbi_instructional_room = 31 WHERE city_mun_psgc_code = '{ALPHA}'",
     "ratio_is_ratio_of_sums"),
    (f"UPDATE {CANDIDATE} SET ratio_instructional_rooms = 6 WHERE city_mun_psgc_code = '{ALPHA}'",
     "ratio_rooms_match_capacity_fact"),
    (f"UPDATE {CANDIDATE} SET ratio_learners = 151 WHERE city_mun_psgc_code = '{ALPHA}'",
     "ratio_learners_match_enrollment_fact"),
    (f"UPDATE {CANDIDATE} SET learner_coverage_pct = 100 WHERE city_mun_psgc_code = '{ALPHA}'",
     "coverage_arithmetic"),
    (f"UPDATE {CANDIDATE} SET zero_room_school_count = 0 WHERE city_mun_psgc_code = '{ALPHA}'",
     "school_and_learner_partitions_reconcile"),
    (f"UPDATE {CANDIDATE} SET ratio_null_reason = NULL WHERE city_mun_psgc_code = '{BETA}'", "null_has_reason"),
    (f"UPDATE {CANDIDATE} SET school_year = '2024-25' WHERE city_mun_psgc_code = '{BETA}'",
     "school_year_2023_24_only"),
    (f"UPDATE {CANDIDATE} SET measure_label = 'DepEd classroom-learner ratio'", "labels_and_status"),
    (f"UPDATE {CANDIDATE} SET benchmark_status = '45:1'", "labels_and_status"),
    (f"DELETE FROM {CANDIDATE} WHERE city_mun_psgc_code = '{BETA}'", "keys_match_regular_lgus"),
    (f"INSERT INTO {CANDIDATE} SELECT * FROM {CANDIDATE} WHERE city_mun_psgc_code = '{BETA}'", "grain_unique"),
])
def test_a_broken_candidate_fails_and_is_not_published(tamper, check):
    env = Env()
    run_id, error = env.run(before_gate=tamper)
    assert "Analytics gate failed for ap2_classroom_pressure" in error
    assert check in env.results(run_id, "FAIL")
    assert not env.store.records("SELECT * FROM information_schema.tables WHERE table_name = 'ap2_classroom_pressure'")


def test_rerun_with_the_same_inputs_gives_the_same_rows():
    env = Env()
    env.run()
    first = env.store.records(f"SELECT * FROM {OUTPUT} ORDER BY city_mun_psgc_code")
    _, error = env.run()
    assert error is None
    assert env.store.records(f"SELECT * FROM {OUTPUT} ORDER BY city_mun_psgc_code") == first
