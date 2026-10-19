"""Analytics AP4 (#147): the school-age population and enrollment gap, build and gate run the way the job's
two SQL tasks run them.

Made-up rows go straight into the two published Gold facts AP4 reads (fact_school_enrollment and
fact_city_school_age_population) in an in-memory DuckDB. No real DepEd or PSA row is used.
"""

import uuid

from factories.deped_deliveries import REPO_ROOT
from src.ingestion.store import DuckDBStore

CONTROL = "edu_access.`01-control`"
AP4 = "edu_access.`06-analytics`.ap4_school_age_enrollment_gap"
BUILD = REPO_ROOT / "etl" / "06_analytics" / "04_answer_ap4.sql"
GATE = REPO_ROOT / "etl" / "06_analytics" / "90_validate_ap4.sql"

A, MAKATI = "0102801000", "1380300000"

# school_id, school_year, city, sector, {level: (is_offered, learner_count)}
SCHOOLS = [
    ("S1", "2020-21", A, "Public", {"ES": (True, 300), "JHS": (True, 200), "SHS": (False, 0)}),
    ("S2", "2020-21", A, "Private", {"ES": (True, 50), "JHS": (False, 0), "SHS": (False, 0)}),
    ("S3", "2020-21", A, "Public", {"ES": (True, 40), "JHS": (True, None), "SHS": (False, 0)}),  # incomplete
    ("S4", "2020-21", A, "PSO", {"ES": (True, 999), "JHS": (False, 0), "SHS": (False, 0)}),      # never counted
    ("S1", "2024-25", A, "Public", {"ES": (True, 280), "JHS": (True, 190), "SHS": (True, 60)}),
    ("S2", "2024-25", A, "SUC/LUC", {"ES": (False, 0), "JHS": (False, 0), "SHS": (True, 30)}),
    ("S1", "2023-24", A, "Public", {"ES": (True, 777), "JHS": (False, 0), "SHS": (False, 0)}),   # no census year
    ("S5", "2024-25", MAKATI, "Public", {"ES": (True, 900), "JHS": (True, 600), "SHS": (True, 300)}),
    ("S6", "2024-25", "UNKNOWN", "Private", {"ES": (True, 25), "JHS": (False, 0), "SHS": (False, 0)}),
]
# city, year, comparable, population per sex for each age 5 to 17 (ages 4 and 18 are added and must be ignored)
POPULATION = [
    (A, 2020, True, 30), (A, 2024, True, 28),
    (MAKATI, 2020, False, 100), (MAKATI, 2024, False, 40),
    ("EXCLUDED", 2020, False, 2),
]


class Env:
    def __init__(self, schools=SCHOOLS):
        self.store = DuckDBStore()
        for path in sorted((REPO_ROOT / "etl" / "01_control").glob("0[1-4]_*.sql")):
            self.store.run_file(path)
        self.store.sql("CREATE SCHEMA IF NOT EXISTS edu_access.`05-gold`")
        self.store.sql("CREATE TABLE edu_access.`05-gold`.fact_school_enrollment (school_id STRING, school_year STRING, "
                       "education_level_code STRING, city_mun_psgc_code STRING, sector STRING, is_offered BOOLEAN, "
                       "learner_count BIGINT)")
        for school, year, city, sector, levels in schools:
            for level, (offered, count) in levels.items():
                self.store.sql("INSERT INTO edu_access.`05-gold`.fact_school_enrollment VALUES (?, ?, ?, ?, ?, ?, ?)",
                               [school, year, level, city, sector, offered, count])
        self.store.sql("CREATE TABLE edu_access.`05-gold`.fact_city_school_age_population (city_mun_psgc_code STRING, "
                       "reference_year INT, age INT, sex STRING, population BIGINT, is_2020_2024_geography_comparable BOOLEAN)")
        for city, year, comparable, per_age in POPULATION:
            for age in range(4, 19):
                for sex in ("male", "female"):
                    self.store.sql("INSERT INTO edu_access.`05-gold`.fact_city_school_age_population VALUES (?, ?, ?, ?, ?, ?)",
                                   [city, year, age, sex, per_age, comparable])

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
            f"SELECT * FROM {CONTROL}.data_quality_results WHERE run_id = '{run_id}' AND layer = 'analytics'")}

    def rows(self):
        return {(r["city_mun_psgc_code"], r["reference_year"]): r for r in self.store.records(f"SELECT * FROM {AP4}")}


PER_AGE_YEARS = 13 * 2  # ages 5 to 17, male and female


def test_one_row_per_member_and_aligned_period():
    env = Env()
    run_id, error = env.run()
    assert error is None
    rows = env.rows()
    assert sorted(rows) == sorted([("EXCLUDED", 2020), (A, 2020), (A, 2024), (MAKATI, 2020), (MAKATI, 2024), ("UNKNOWN", 2024)])
    assert {(r["reference_year"], r["school_year"]) for r in rows.values()} == {(2020, "2020-21"), (2024, "2024-25")}
    checks = env.checks(run_id)
    assert {c["status"] for c in checks.values()} == {"PASS", "WARN"}
    assert checks["schools_incomplete"]["actual"] == "1"
    assert checks["learners_on_technical_members"]["actual"] == "25"
    assert checks["population_on_excluded"]["actual"] == str(2 * PER_AGE_YEARS)


def test_population_enrollment_and_gap_follow_the_metric_specification():
    env = Env()
    env.run()
    rows = env.rows()
    a2020 = rows[(A, 2020)]
    assert a2020["school_age_population"] == 30 * PER_AGE_YEARS               # ages 4 and 18 ignored
    assert a2020["enrollment_all_sectors"] == 500 + 50                         # S3 incomplete, S4 PSO
    assert a2020["public_school_enrollment"] == 500
    assert (a2020["schools_counted"], a2020["schools_incomplete"]) == (2, 1)
    assert a2020["population_enrollment_gap"] == 30 * PER_AGE_YEARS - 550
    assert abs(a2020["gap_share"] - (30 * PER_AGE_YEARS - 550) / (30 * PER_AGE_YEARS)) < 1e-12
    assert abs(a2020["public_school_share"] - 500 / 550) < 1e-12
    assert a2020["gap_change_2020_2024"] is None
    a2024 = rows[(A, 2024)]
    assert a2024["enrollment_all_sectors"] == 530 + 30                        # SY 2023-24 never read
    assert a2024["gap_change_2020_2024"] == a2024["population_enrollment_gap"] - a2020["population_enrollment_gap"]
    assert (a2024["age_min"], a2024["age_max"]) == (5, 17)
    assert "not an out-of-school count" in a2024["interpretation_note"]
    assert "Philippine Schools Overseas excluded" in a2024["enrollment_scope"]


def test_negative_gap_is_kept_and_comparability_comes_from_the_population_fact():
    env = Env()
    env.run()
    rows = env.rows()
    makati = rows[(MAKATI, 2024)]
    assert makati["population_enrollment_gap"] == 40 * PER_AGE_YEARS - 1800 < 0
    assert makati["is_2020_2024_geography_comparable"] is False
    assert rows[(A, 2024)]["is_2020_2024_geography_comparable"] is True
    unknown = rows[("UNKNOWN", 2024)]
    assert (unknown["member_type"], unknown["school_age_population"], unknown["enrollment_all_sectors"]) == ("unknown", None, 25)
    assert unknown["gap_change_2020_2024"] is None and unknown["is_2020_2024_geography_comparable"] is False


def test_rerun_gives_the_same_table():
    env = Env()
    env.run()
    first = env.rows()
    _, error = env.run()
    assert error is None
    assert env.rows() == first


def test_a_changed_value_fails_and_keeps_the_last_good_output():
    candidate = "edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate"
    for change in ("enrollment_all_sectors = enrollment_all_sectors + 1, population_enrollment_gap = population_enrollment_gap - 1",
                   "is_2020_2024_geography_comparable = NOT is_2020_2024_geography_comparable",
                   "school_year = '2023-24'"):
        env = Env()
        env.run()
        good = env.rows()
        env.store.sql(f"UPDATE {candidate} SET {change} WHERE city_mun_psgc_code = '{A}' AND reference_year = 2024")
        run_id, error = env.run(build=False)
        assert error and "Analytics gate failed for ap4" in error, change
        assert env.rows() == good, change


def test_a_school_in_two_places_in_one_year_fails():
    schools = SCHOOLS + [("S7", "2024-25", A, "Public", {"ES": (True, 10)}),
                         ("S7", "2024-25", MAKATI, "Public", {"JHS": (True, 10)})]
    env = Env(schools)
    run_id, error = env.run()
    assert error
    assert env.checks(run_id)["one_place_per_school_year"]["status"] == "FAIL"
