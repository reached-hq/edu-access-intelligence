"""AP3 build and gate tests using made-up Gold inputs."""

from pathlib import Path
import uuid

import pytest

from src.ingestion.store import DuckDBStore


ROOT = Path(__file__).resolve().parents[1]

BUILD = ROOT / "etl/06_analytics/03_answer_ap3.sql"
GATE = ROOT / "etl/06_analytics/90_validate_ap3.sql"

GOLD = "edu_access.`05-gold`"
OUTPUT = "edu_access.`06-analytics`.ap3_teacher_pressure"
CANDIDATE = f"{OUTPUT}_candidate"

CITY_A = "0102801000"
CITY_B = "0102802000"


class Env:
    def __init__(self):
        self.store = DuckDBStore()

        for path in sorted(
            (ROOT / "etl/01_control").glob("0[1-4]_*.sql")
        ):
            self.store.run_file(path)

        self.store.sql(f"CREATE SCHEMA {GOLD}")

        self.store.sql(
            f"""
            CREATE TABLE {GOLD}.dim_city_municipality (
                city_mun_psgc_code STRING,
                city_mun_name STRING,
                lgu_type STRING,
                province_psgc_code STRING,
                province_name STRING,
                region_psgc_code STRING,
                region_name STRING,
                member_type STRING
            )
            """
        )

        self.store.sql(
            f"""
            INSERT INTO {GOLD}.dim_city_municipality VALUES
                (
                    '{CITY_A}', 'Made-up City', 'city',
                    '0102800000', 'Made-up Province',
                    '0100000000', 'Made-up Region', 'regular'
                ),
                (
                    '{CITY_B}', 'Made-up Town', 'municipality',
                    '0102800000', 'Made-up Province',
                    '0100000000', 'Made-up Region', 'regular'
                ),
                (
                    'UNKNOWN', 'Unknown', NULL,
                    NULL, NULL, NULL, NULL, 'unknown'
                ),
                (
                    'EXCLUDED', 'Excluded', NULL,
                    NULL, NULL, NULL, NULL, 'excluded'
                )
            """
        )

        self.store.sql(
            f"""
            CREATE TABLE {GOLD}.fact_school_enrollment (
                school_id STRING,
                school_year STRING,
                education_level_code STRING,
                city_mun_psgc_code STRING,
                barangay_psgc_code STRING,
                psgc_match_status STRING,
                sector STRING,
                annex_status STRING,
                is_offered BOOLEAN,
                learner_count BIGINT
            )
            """
        )

        self.store.sql(
            f"""
            CREATE TABLE {GOLD}.fact_school_teacher_capacity (
                school_id STRING,
                school_year STRING,
                education_level_code STRING,
                teacher_count INT,
                sef_provincial_teacher_count INT,
                sef_city_municipal_teacher_count INT,
                lgu_funded_teacher_count INT,
                other_funded_teacher_count INT
            )
            """
        )

        self.store.sql(
            f"""
            CREATE TABLE {GOLD}.fact_school_year_source_availability (
                school_year STRING,
                source_id STRING,
                has_data BOOLEAN
            )
            """
        )

        self.store.sql(
            f"""
            INSERT INTO {GOLD}.fact_school_year_source_availability
            VALUES
                ('2023-24', 'deped_enrollment', TRUE),
                ('2023-24', 'deped_personnel', TRUE)
            """
        )

        # Four active ES schools:
        # usable teachers, zero-teacher annex,
        # zero-teacher non-annex, and missing teacher data.
        self.school("100001", 100, 5, funding=(1, 1, 1, 1))
        self.school("100002", 50, 0, annex=True)
        self.school("100003", 50, 0)
        self.school("100004", 100, None)

    def school(
        self,
        school_id,
        learners,
        teachers,
        *,
        city=CITY_A,
        level="ES",
        year="2023-24",
        annex=False,
        sector="Public",
        status="matched",
        offered=True,
        capacity=True,
        funding=(None, None, None, None),
    ):
        self.store.sql(
            f"""
            INSERT INTO {GOLD}.fact_school_enrollment
            VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            [
                school_id,
                year,
                level,
                city,
                status,
                sector,
                (
                    "Annex/Extension School"
                    if annex
                    else "Standalone School"
                ),
                offered,
                learners,
            ],
        )

        if capacity:
            self.store.sql(
                f"""
                INSERT INTO {GOLD}.fact_school_teacher_capacity
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    school_id,
                    year,
                    level,
                    teachers,
                    *funding,
                ],
            )

    def run(self, change=None):
        params = {
            "run_id": str(uuid.uuid4()),
            "code_revision": "a" * 40,
        }

        self.store.run_file(BUILD, params)

        if change:
            self.store.sql(change)

        self.store.run_file(GATE, params)
        return params

    def rows(self):
        return self.store.records(
            f"""
            SELECT *
            FROM {OUTPUT}
            ORDER BY
                city_mun_psgc_code,
                school_year,
                education_level_code
            """
        )

    def row(self, city=CITY_A, level="ES", year="2023-24"):
        return next(
            row
            for row in self.rows()
            if (
                row["city_mun_psgc_code"],
                row["education_level_code"],
                row["school_year"],
            )
            == (city, level, year)
        )


@pytest.fixture
def env():
    value = Env()
    yield value
    value.store.close()


def test_complete_regular_lgu_level_grid(env):
    env.run()
    rows = env.rows()

    assert len(rows) == 6

    assert {
        (
            row["city_mun_psgc_code"],
            row["school_year"],
            row["education_level_code"],
        )
        for row in rows
    } == {
        (city, "2023-24", level)
        for city in (CITY_A, CITY_B)
        for level in ("ES", "JHS", "SHS")
    }


def test_annex_exception_and_coverage(env):
    env.run()
    row = env.row()

    assert row["public_school_count"] == 4
    assert row["public_school_enrollment"] == 300

    # Usable school's 100 learners + annex's 50 learners.
    assert row["enrollment_included_in_ratio"] == 150
    assert row["teacher_count"] == 5
    assert row["learners_per_teacher"] == 30

    assert row["school_coverage_pct"] == 25
    assert row["learner_coverage_pct"] == 50

    assert row["zero_teacher_annex_school_count"] == 1
    assert row["zero_teacher_annex_learner_count"] == 50
    assert row["learners_without_same_level_teachers"] == 50
    assert row["schools_without_teacher_data"] == 1


def test_funding_is_not_added_to_teacher_total_again(env):
    env.run()
    row = env.row()

    assert row["sef_provincial_teacher_count"] == 1
    assert row["sef_city_municipal_teacher_count"] == 1
    assert row["lgu_funded_teacher_count"] == 1
    assert row["other_funded_teacher_count"] == 1

    assert row["teacher_count"] == 5
    assert row["learners_per_teacher"] == 30


def test_no_active_school_retains_row_and_null_reason(env):
    env.run()
    row = env.row(city=CITY_B)

    assert row["public_school_count"] == 0
    assert row["learners_per_teacher"] is None
    assert row["school_coverage_pct"] is None
    assert row["learner_coverage_pct"] is None

    assert row["ratio_null_reason"] == (
        "no active public school offering this level"
    )


def test_level_specific_ratios_and_incomplete_enrollment(env):
    # School is active because its ES enrollment is complete.
    env.school("100001", 60, 3, level="JHS")
    env.school("100001", None, 10, level="SHS")

    env.run()

    jhs = env.row(level="JHS")
    shs = env.row(level="SHS")

    assert jhs["learners_per_teacher"] == 20
    assert jhs["teacher_count"] == 3

    assert shs["public_school_count"] == 1
    assert shs["incomplete_enrollment_school_count"] == 1
    assert shs["public_school_enrollment"] is None
    assert shs["teacher_count"] is None
    assert shs["learners_per_teacher"] is None
    assert shs["learner_coverage_pct"] is None


def test_null_annex_teachers_are_not_treated_as_zero(env):
    env.school("100005", 100, None, annex=True)
    env.run()
    row = env.row()

    assert row["public_school_enrollment"] == 400
    assert row["enrollment_included_in_ratio"] == 150
    assert row["zero_teacher_annex_school_count"] == 1
    assert row["learner_coverage_pct"] == 37.5


def test_missing_capacity_does_not_drop_enrollment(env):
    env.school("100005", 100, None, capacity=False)
    env.run()
    row = env.row()

    assert row["public_school_count"] == 5
    assert row["schools_without_capacity_row"] == 1
    assert row["schools_without_teacher_data"] == 2
    assert row["public_school_enrollment"] == 400


def test_all_zero_teacher_annex_has_coverage_but_no_ratio(env):
    env.school("100005", 100, 0, city=CITY_B, annex=True)
    env.run()
    row = env.row(city=CITY_B)

    assert row["enrollment_included_in_ratio"] == 100
    assert row["learner_coverage_pct"] == 100
    assert row["school_coverage_pct"] == 0
    assert row["learners_per_teacher"] is None

    assert row["ratio_null_reason"] == (
        "no usable positive teacher denominator"
    )


def test_sum_before_division_and_lgu_separation(env):
    env.school("100005", 300, 5)
    env.school("100006", 80, 2, city=CITY_B)

    env.run()

    # (100 + 50 annex + 300) / (5 + 5).
    assert env.row()["learners_per_teacher"] == 45
    assert env.row()["teacher_count"] == 10

    assert env.row(city=CITY_B)["learners_per_teacher"] == 40
    assert env.row(city=CITY_B)["teacher_count"] == 2


def test_private_overseas_and_inactive_schools_are_excluded(env):
    env.school("100005", 900, 1, sector="Private")
    env.school(
        "100006", 900, 1,
        city="EXCLUDED", status="excluded"
    )
    env.school(
        "100007", 900, 1,
        city="UNKNOWN", status="unmatched"
    )
    env.school("100008", 0, 10)
    env.school("100009", 0, 10, offered=False)

    env.run()
    row = env.row()

    assert row["public_school_count"] == 4
    assert row["public_school_enrollment"] == 300
    assert row["teacher_count"] == 5


def test_year_without_personnel_is_explicitly_unavailable(env):
    env.school(
        "100010", 100, None,
        year="2020-21", capacity=False
    )

    env.store.sql(
        f"""
        INSERT INTO {GOLD}.fact_school_year_source_availability
        VALUES
            ('2020-21', 'deped_enrollment', TRUE),
            ('2020-21', 'deped_personnel', FALSE)
        """
    )

    env.run()
    row = env.row(year="2020-21")

    assert row["personnel_available"] is False
    assert row["public_school_enrollment"] == 100
    assert row["teacher_count"] is None
    assert row["learners_per_teacher"] is None
    assert row["learner_coverage_pct"] is None

    assert row["ratio_null_reason"] == (
        "personnel source not available for school year"
    )


def test_labels_do_not_claim_an_official_indicator(env):
    env.run()

    for row in env.rows():
        assert row["indicator_type"] == "project-defined"
        assert row["validation_status"] == "provisional"
        assert row["benchmark_status"] == "not applicable"


def test_rerun_is_identical(env):
    env.run()
    before = env.rows()

    env.run()

    assert env.rows() == before


@pytest.mark.parametrize(
    "change",
    [
        # Change the teacher total and adjust the ratio consistently.
        # Arithmetic alone would pass, but Gold reconciliation must fail.
        f"""
        UPDATE {CANDIDATE}
        SET teacher_count = 10, learners_per_teacher = 15
        WHERE city_mun_psgc_code = '{CITY_A}'
          AND education_level_code = 'ES'
        """,
        f"""
        UPDATE {CANDIDATE}
        SET school_coverage_pct = 100
        WHERE city_mun_psgc_code = '{CITY_A}'
          AND education_level_code = 'ES'
        """,
        f"""
        UPDATE {CANDIDATE}
        SET benchmark_status = 'official'
        """,
        f"""
        DELETE FROM {CANDIDATE}
        WHERE city_mun_psgc_code = '{CITY_B}'
        """,
        f"""
        INSERT INTO {CANDIDATE}
        SELECT * FROM {CANDIDATE}
        """,
    ],
)
def test_failed_candidate_keeps_last_good_output(env, change):
    env.run()
    before = env.rows()

    with pytest.raises(
        Exception,
        match="Analytics gate failed for AP3",
    ):
        env.run(change=change)

    assert env.rows() == before


def test_duplicate_capacity_join_key_fails(env):
    env.run()
    before = env.rows()

    env.store.sql(
        f"""
        INSERT INTO {GOLD}.fact_school_teacher_capacity
        SELECT *
        FROM {GOLD}.fact_school_teacher_capacity
        WHERE school_id = '100001'
        """
    )

    with pytest.raises(
        Exception,
        match="Analytics gate failed for AP3",
    ):
        env.run()

    assert env.rows() == before