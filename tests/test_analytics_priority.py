"""Revised AP1 to AP4 outputs and the downstream LGU priority matrix."""

from pathlib import Path

import pytest

from src.ingestion.store import DuckDBStore


ROOT = Path(__file__).parents[1]
GOLD = "edu_access.`05-gold`"
ANALYTICS = "edu_access.`06-analytics`"


@pytest.fixture()
def store(tmp_path):
    value = DuckDBStore(tmp_path / "analytics.duckdb")
    value.sql("CREATE SCHEMA IF NOT EXISTS edu_access.`01-control`")
    value.sql("CREATE SCHEMA IF NOT EXISTS edu_access.`05-gold`")
    value.run_file(ROOT / "etl/01_control/04_create_data_quality_results.sql")
    value.sql(f"""CREATE TABLE {GOLD}.dim_city_municipality (
        city_mun_psgc_code STRING, city_mun_name STRING, lgu_type STRING,
        province_psgc_code STRING, province_name STRING, region_psgc_code STRING,
        region_name STRING, member_type STRING)""")
    value.sql(f"""INSERT INTO {GOLD}.dim_city_municipality VALUES
        ('C1','City One','City','P','Province','R','Region','regular'),
        ('C2','City Two','City','P','Province','R','Region','regular'),
        ('M1','Town One','Municipality','P','Province','R','Region','regular'),
        ('M2','Town Two','Municipality','P','Province','R','Region','regular')""")
    value.sql(f"""CREATE TABLE {GOLD}.fact_school_enrollment (
        school_id STRING, school_year STRING, education_level_code STRING,
        city_mun_psgc_code STRING, sector STRING, psgc_match_status STRING,
        annex_status STRING, is_offered BOOLEAN, learner_count BIGINT)""")
    years = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    schools = [("S1", "C1", 100), ("S2", "C1", 100), ("S3", "C2", 300),
               ("S4", "M1", 120), ("S5", "M2", 180)]
    for year_index, year in enumerate(years):
        for school_id, code, base in schools:
            learners = base + year_index * 10
            value.sql(f"""INSERT INTO {GOLD}.fact_school_enrollment VALUES
                ('{school_id}','{year}','ES','{code}','Public','matched','Mother School',TRUE,{learners}),
                ('{school_id}','{year}','JHS','{code}','Public','matched','Mother School',FALSE,0),
                ('{school_id}','{year}','SHS','{code}','Public','matched','Mother School',FALSE,0)""")
    value.sql(f"""CREATE TABLE {GOLD}.fact_city_school_age_population (
        city_mun_psgc_code STRING, reference_year INT, age INT, sex STRING,
        population BIGINT, psgc_match_status STRING, is_2020_2024_geography_comparable BOOLEAN)""")
    for code, population in [("C1", 1000), ("C2", 2000), ("M1", 900), ("M2", 1100)]:
        for age in range(5, 18):
            male = population // 26
            female = population // 26
            value.sql(f"INSERT INTO {GOLD}.fact_city_school_age_population VALUES "
                      f"('{code}',2024,{age},'male',{male},'matched',TRUE),"
                      f"('{code}',2024,{age},'female',{female},'matched',TRUE)")
    value.sql(f"""CREATE TABLE {GOLD}.fact_school_classroom_capacity (
        school_id STRING, school_year STRING, instructional_classrooms_total BIGINT)""")
    value.sql(f"""INSERT INTO {GOLD}.fact_school_classroom_capacity VALUES
        ('S1','2023-24',5),('S2','2023-24',5),('S3','2023-24',10),
        ('S4','2023-24',6),('S5','2023-24',9)""")
    value.sql(f"""CREATE TABLE {GOLD}.fact_school_teacher_capacity (
        school_id STRING, school_year STRING, education_level_code STRING, teacher_count BIGINT)""")
    value.sql(f"""INSERT INTO {GOLD}.fact_school_teacher_capacity VALUES
        ('S1','2023-24','ES',5),('S2','2023-24','ES',5),('S3','2023-24','ES',10),
        ('S4','2023-24','ES',6),('S5','2023-24','ES',9)""")
    value.sql(f"""CREATE TABLE {GOLD}.fact_school_year_source_availability (
        school_year STRING, source_id STRING, has_data BOOLEAN)""")
    for year in years:
        value.sql(f"INSERT INTO {GOLD}.fact_school_year_source_availability VALUES "
                  f"('{year}','deped_enrollment',TRUE)")
    yield value
    value.close()


def run(store, file_name):
    store.run_file(ROOT / "etl/06_analytics" / file_name, {
        "run_id": "priority-test", "code_revision": "a" * 40, "environment": "local"})


def test_revised_outputs_and_priority_matrix(store):
    for build, gate in [
        ("01_answer_ap1.sql", "90_validate_ap1.sql"),
        ("02_answer_ap2.sql", "90_validate_ap2.sql"),
        ("03_answer_ap3.sql", "90_validate_ap3.sql"),
        ("04_answer_ap4.sql", "90_validate_ap4.sql"),
        ("05_build_priority_matrix.sql", "90_validate_priority_matrix.sql"),
    ]:
        run(store, build)
        run(store, gate)

    assert store.query(f"SELECT COUNT(*) FROM {ANALYTICS}.lgu_priority_matrix") == [(4,)]
    c2 = store.query(f"""SELECT ap1_classification, ap1_national_same_type_ratio,
        current_pressure_count, enrollment_trend, priority
        FROM {ANALYTICS}.lgu_priority_matrix WHERE city_mun_psgc_code = 'C2'""")[0]
    assert c2[0] == "Above Reference"
    assert c2[1] == pytest.approx((988 + 1976) / 3)
    assert c2[2] in (0, 1, 2, 3)
    assert c2[3] == "Growing"
    assert c2[4] in ("Priority 1", "Priority 3", "Monitor")


def test_no_percentile_priority_logic():
    sql = "\n".join((ROOT / "etl/06_analytics" / name).read_text(encoding="utf-8")
                    for name in ["01_answer_ap1.sql", "02_answer_ap2.sql", "03_answer_ap3.sql",
                                 "04_answer_ap4.sql", "05_build_priority_matrix.sql"])
    assert "PERCENT_RANK" not in sql.upper()
    assert "national_same_type_ratio" in sql
    assert "Data Review" in sql
    assert "PERCENTILE_CONT" in sql  # retained only for the school-level outlier review fence


def test_priority_gate_rejects_wrong_priority(store):
    test_revised_outputs_and_priority_matrix(store)
    before = store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code")
    store.sql(f"UPDATE {ANALYTICS}.lgu_priority_matrix_candidate SET priority = 'Priority 1'")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_priority_matrix.sql")
    assert store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code") == before
