"""AP1 to AP4 evidence, the D-062 BQ composite, and the D-060 classroom drill-down queue."""

from pathlib import Path

import pytest

from src.ingestion.store import DuckDBStore


ROOT = Path(__file__).parents[1]
GOLD = "edu_access.`05-gold`"
ANALYTICS = "edu_access.`06-analytics`"
CONTROL = "edu_access.`01-control`"


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
        annex_status STRING, is_offered BOOLEAN, learner_count BIGINT, barangay_psgc_code STRING)""")
    years = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    # S5 is matched to Town Two but to no single barangay, so Town Two's barangay count is an upper bound
    schools = [("S1", "C1", 100, "C1-B1"), ("S2", "C1", 100, "C1-B2"), ("S3", "C2", 300, "C2-B1"),
               ("S4", "M1", 120, "M1-B1"), ("S5", "M2", 180, "M2-UNKNOWN")]
    for year_index, year in enumerate(years):
        for school_id, code, base, barangay in schools:
            learners = base + year_index * 10
            value.sql(f"""INSERT INTO {GOLD}.fact_school_enrollment VALUES
                ('{school_id}','{year}','ES','{code}','Public','matched','Mother School',TRUE,{learners},'{barangay}'),
                ('{school_id}','{year}','JHS','{code}','Public','matched','Mother School',FALSE,0,'{barangay}'),
                ('{school_id}','{year}','SHS','{code}','Public','matched','Mother School',FALSE,0,'{barangay}')""")
    value.sql(f"""CREATE TABLE {GOLD}.dim_barangay (
        barangay_psgc_code STRING, barangay_name STRING, city_mun_psgc_code STRING, urban_rural STRING,
        member_type STRING)""")
    value.sql(f"""INSERT INTO {GOLD}.dim_barangay VALUES
        ('C1-B1','One','C1','U','regular'),('C1-B2','Two','C1','U','regular'),
        ('C2-B1','One','C2','U','regular'),('C2-B2','Two','C2','R','regular'),
        ('M1-B1','One','M1','R','regular'),('M2-B1','One','M2','R','regular'),
        ('C1-UNKNOWN','Unknown barangay in City One','C1',NULL,'unknown'),
        ('C2-UNKNOWN','Unknown barangay in City Two','C2',NULL,'unknown'),
        ('M1-UNKNOWN','Unknown barangay in Town One','M1',NULL,'unknown'),
        ('M2-UNKNOWN','Unknown barangay in Town Two','M2',NULL,'unknown')""")
    # S1 and S2 are 0.5 km apart in urban City One; S3 and S4 stand alone; S5 has no barangay, so no urban or
    # rural class, and is not tested
    value.sql(f"""CREATE TABLE {GOLD}.dim_school_location (
        school_id STRING, school_year STRING, city_mun_psgc_code STRING, barangay_psgc_code STRING,
        urban_rural STRING, longitude DOUBLE, latitude DOUBLE, coordinate_flag STRING,
        boundary_test_status STRING, is_location_usable BOOLEAN, location_source STRING)""")
    value.sql(f"""INSERT INTO {GOLD}.dim_school_location VALUES
        ('S1','2023-24','C1','C1-B1','U',121.0,14.0,NULL,'inside',TRUE,'deped_psgc_coordinates'),
        ('S2','2023-24','C1','C1-B2','U',121.0,14.0045,NULL,'inside',TRUE,'deped_psgc_coordinates'),
        ('S3','2023-24','C2','C2-B1','U',124.0,10.0,NULL,'inside',TRUE,'deped_psgc_coordinates'),
        ('S4','2023-24','M1','M1-B1','R',125.0,8.0,NULL,'inside',TRUE,'deped_psgc_coordinates'),
        ('S5','2023-24','M2','M2-UNKNOWN',NULL,120.0,16.0,NULL,'inside',TRUE,'deped_psgc_coordinates')""")
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


STEPS = [
    ("01_answer_ap1.sql", "90_validate_ap1.sql"),
    ("02_answer_ap2.sql", "90_validate_ap2.sql"),
    ("03_answer_ap3.sql", "90_validate_ap3.sql"),
    ("04_answer_ap4.sql", "90_validate_ap4.sql"),
    ("05_build_priority_matrix.sql", "90_validate_priority_matrix.sql"),
]


def run_all(store, steps=STEPS):
    for build, gate in steps:
        run(store, build)
        run(store, gate)


def add_public_school(store, school_id, code, learners, rooms, teachers=None):
    store.sql(f"""INSERT INTO {GOLD}.fact_school_enrollment VALUES
        ('{school_id}','2023-24','ES','{code}','Public','matched','Mother School',TRUE,{learners},'{code}-B1'),
        ('{school_id}','2023-24','JHS','{code}','Public','matched','Mother School',FALSE,0,'{code}-B1'),
        ('{school_id}','2023-24','SHS','{code}','Public','matched','Mother School',FALSE,0,'{code}-B1')""")
    store.sql(f"INSERT INTO {GOLD}.fact_school_classroom_capacity VALUES ('{school_id}','2023-24',{rooms})")
    if teachers is not None:
        store.sql(f"INSERT INTO {GOLD}.fact_school_teacher_capacity VALUES ('{school_id}','2023-24','ES',{teachers})")


def test_ap_outputs_stay_descriptive_and_no_d057_tier_is_published(store):
    # D-062 scores only in lgu_priority_matrix; the AP outputs themselves publish no percentile or tier
    run_all(store)
    for table in ["ap1_school_provision", "ap2_classroom_pressure", "ap3_teacher_pressure", "lgu_priority_matrix"]:
        columns = {c[0] for c in store.query(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")}
        assert not {c for c in columns if c in {"is_high", "tier", "national_tier"} or c.endswith("_percentile")}
        if table != "lgu_priority_matrix":
            assert not {c for c in columns if "percentile" in c or "score" in c}


def test_ap1_is_descriptive_only(store):
    run_all(store, STEPS[:1])
    assert store.query(f"""SELECT learners_per_public_school, school_age_population_per_public_school, is_assessed
        FROM {ANALYTICS}.ap1_school_provision WHERE city_mun_psgc_code = 'C2'""") == [
        (330.0, pytest.approx(1976.0), True)]


def test_ap2_flags_schools_then_aggregates_affected_learners(store):
    add_public_school(store, "X1", "M1", 60, 1)
    run_all(store, STEPS[:2])
    assert store.query(f"""SELECT congested_school_count, learners_in_congested_schools,
        congested_learner_share_pct, benchmark_status FROM {ANALYTICS}.ap2_classroom_pressure
        WHERE city_mun_psgc_code = 'M1'""") == [
        (1, 60, pytest.approx(60 / 210 * 100), "reported congestion identified")]


def test_ap2_threshold_is_inclusive_at_50(store):
    store.sql(f"""UPDATE {GOLD}.fact_school_enrollment SET learner_count = 100
        WHERE school_id = 'S1' AND school_year = '2023-24' AND education_level_code = 'ES'""")
    store.sql(f"UPDATE {GOLD}.fact_school_classroom_capacity SET instructional_classrooms_total = 2 WHERE school_id = 'S1'")
    run_all(store, STEPS[1:2])
    assert store.query(f"""SELECT congested_school_count, learners_in_congested_schools
        FROM {ANALYTICS}.ap2_classroom_pressure WHERE city_mun_psgc_code = 'C1'""") == [(1, 100)]


def test_ap2_coverage_failure_goes_to_classroom_data_review(store):
    # S1 loses its room count: City One keeps half its learners in the ratio, below the 90% gate
    store.sql(f"DELETE FROM {GOLD}.fact_school_classroom_capacity WHERE school_id = 'S1'")
    run_all(store)
    assert store.query(f"""SELECT learner_coverage_pct, is_assessed, not_assessed_reason
        FROM {ANALYTICS}.ap2_classroom_pressure WHERE city_mun_psgc_code = 'C1'""") == [
        (50.0, False, "learner coverage below 90%")]
    assert store.query(f"""SELECT ap2_assessed, classroom_priority_group, classroom_priority_rank
        FROM {ANALYTICS}.lgu_priority_matrix WHERE city_mun_psgc_code = 'C1'""") == [
        (False, "data_review", None)]


def test_classroom_queue_orders_by_affected_learners_and_preserves_ties(store):
    add_public_school(store, "X1", "M1", 60, 1)
    add_public_school(store, "X2", "M2", 60, 1)
    store.sql(f"""UPDATE {GOLD}.fact_school_classroom_capacity SET instructional_classrooms_total = 8
        WHERE school_id = 'S5'""")
    run_all(store)
    rows = {r[0]: r[1:] for r in store.query(f"""SELECT city_mun_psgc_code, ap2_affected_learners,
        ap2_screened_congested_school_count, classroom_priority_rank FROM {ANALYTICS}.lgu_priority_matrix
        WHERE classroom_priority_group = 'reported_congestion_screen'""")}
    assert rows["M1"] == (60, 1, 1)
    assert rows["M2"] == (60, 1, 1)


def test_ap3_pressure_signal_precedes_incomplete_level(store):
    store.sql(f"""UPDATE {GOLD}.fact_school_enrollment SET is_offered = TRUE, learner_count = 200
        WHERE school_id = 'S1' AND school_year = '2023-24' AND education_level_code = 'JHS'""")
    store.sql(f"INSERT INTO {GOLD}.fact_school_teacher_capacity VALUES ('S1','2023-24','JHS',4)")
    store.sql(f"""UPDATE {GOLD}.fact_school_enrollment SET is_offered = TRUE, learner_count = 50
        WHERE school_id = 'S2' AND school_year = '2023-24' AND education_level_code = 'SHS'""")
    run_all(store, STEPS[:3])
    assert store.query(f"""SELECT is_assessed, jhs_benchmark_status, shs_benchmark_status, benchmark_status
        FROM {ANALYTICS}.ap3_teacher_pressure WHERE city_mun_psgc_code = 'C1'""") == [
        (False, "above derived deployment comparison", "not assessed", "pressure signal identified")]


def test_teacher_context_never_assigns_a_teacher_priority_rank(store):
    run_all(store)
    columns = {c[0] for c in store.query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'lgu_priority_matrix'")}
    assert "ap3_review_status" in columns
    assert not {c for c in columns if "teacher_priority" in c}


def test_ap4_gives_the_gap_at_both_censuses_and_never_enters_the_classroom_queue(store):
    for code, population in [("C1", 900), ("C2", 1800), ("M1", 800), ("M2", 1000)]:
        for age in range(5, 18):
            value = population // 26
            store.sql(f"INSERT INTO {GOLD}.fact_city_school_age_population VALUES "
                      f"('{code}',2020,{age},'male',{value},'matched',TRUE),"
                      f"('{code}',2020,{age},'female',{value},'matched',TRUE)")
    store.sql(f"""UPDATE {GOLD}.fact_city_school_age_population SET is_2020_2024_geography_comparable = FALSE
        WHERE city_mun_psgc_code = 'M2'""")
    run_all(store)
    rows = {(r[0], r[1]): r[2:] for r in store.query(f"""SELECT city_mun_psgc_code, school_year, school_age_population,
        enrollment_all_sectors, population_enrollment_gap, census_context FROM {ANALYTICS}.ap4_enrollment_trend""")}
    # City One: 2020 population 34 x 26 = 884 against SY 2020-21 enrollment 200; 2024: 988 against 280
    assert rows[("C1", "2020-21")] == (884, 200, 684, "available")
    assert rows[("C1", "2024-25")] == (988, 280, 708, "available")
    assert rows[("C1", "2023-24")] == (None, 260, None, "not available: no census in this school year")
    gaps = {r[0]: r[1:] for r in store.query(f"""SELECT city_mun_psgc_code, ap4_gap_2020, ap4_gap_2024, ap4_gap_change,
        ap4_enrollment_trend, classroom_priority_group, classroom_priority_rank FROM {ANALYTICS}.lgu_priority_matrix""")}
    assert gaps["C1"][:4] == (684, 708, 24, "increasing")
    assert gaps["M2"][2] is None                      # geography not comparable: no change in gap
    # AP4 is context: a large gap never puts an LGU in the classroom queue (no school here reaches 50 per room)
    assert {g[4:] for g in gaps.values()} == {("no_reported_congestion_screen", None)}


def test_ap3_keeps_a_school_whose_offered_counts_are_all_blank(store):
    # review on #210: S7 offers JHS in City One with a blank count. It is not active, but the JHS level must stay
    # offered and incomplete, so AP3 is not fully assessed instead of reading as no pressure.
    store.sql(f"""INSERT INTO {GOLD}.fact_school_enrollment VALUES
        ('S7','2023-24','ES','C1','Public','matched','Mother School',FALSE,0,'C1-B1'),
        ('S7','2023-24','JHS','C1','Public','matched','Mother School',TRUE,NULL,'C1-B1'),
        ('S7','2023-24','SHS','C1','Public','matched','Mother School',FALSE,0,'C1-B1')""")
    store.sql(f"INSERT INTO {GOLD}.fact_school_teacher_capacity VALUES ('S7','2023-24','JHS',3)")
    run_all(store)
    assert store.query(f"""SELECT jhs_offered_school_count, jhs_incomplete_school_count, jhs_passes_gate,
        offered_level_count, passing_level_count, is_assessed, benchmark_status FROM {ANALYTICS}.ap3_teacher_pressure
        WHERE city_mun_psgc_code = 'C1'""") == [(1, 1, False, 2, 1, False, "not fully assessed")]
    assert store.query(f"""SELECT ap3_fully_assessed, ap3_review_status FROM {ANALYTICS}.lgu_priority_matrix
        WHERE city_mun_psgc_code = 'C1'""") == [(False, "not fully assessed")]


def test_ap2_publishes_no_45_to_1_line(store):
    # review on #210: RA 7880's 45:1 does not apply to the NSBI room count (D-045), so no column may invite a target line
    run_all(store, STEPS[1:2])
    columns = [c[0] for c in store.query(f"""SELECT column_name FROM information_schema.columns
        WHERE table_name = 'ap2_classroom_pressure'""")]
    assert "learners_per_classroom" in columns
    assert not [c for c in columns if "45" in c]


def test_no_d057_or_d058_logic_remains():
    read = lambda name: (ROOT / "etl/06_analytics" / name).read_text(encoding="utf-8")
    answers = "\n".join(read(name) for name in ["01_answer_ap1.sql", "02_answer_ap2.sql", "03_answer_ap3.sql",
                                                "04_answer_ap4.sql"])
    assert "PERCENT_RANK" not in answers          # D-062 scores LGUs only in the priority matrix
    sql = answers + read("05_build_priority_matrix.sql")
    for gone in ["national_same_type_ratio", "relative_pressure", "Priority 1", "Lower Priority",
                 "Critical", "D-057", "D-058"]:
        assert gone not in sql


def test_priority_gate_rejects_a_wrong_classroom_rank(store):
    add_public_school(store, "X1", "M1", 60, 1)
    run_all(store)
    before = store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code")
    store.sql(f"""UPDATE {ANALYTICS}.lgu_priority_matrix_candidate SET classroom_priority_rank = 99
        WHERE city_mun_psgc_code = 'M1'""")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_priority_matrix.sql")
    assert store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code") == before


def test_ap3_gate_rejects_a_wrong_reference_status(store):
    run_all(store, STEPS[:2])
    run(store, "03_answer_ap3.sql")
    store.sql(f"""UPDATE {ANALYTICS}.ap3_teacher_pressure_candidate
        SET es_benchmark_status = 'official shortage' WHERE city_mun_psgc_code = 'C2'""")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_ap3.sql")


def test_gate_summaries_are_dropped(store):
    run_all(store)
    leftovers = "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%gate_summary_r_%'"
    assert store.query(leftovers) == []


def test_benchmark_registry_matches_published_values(store):
    import json

    registry = json.loads((ROOT / "config/analytics_benchmarks.json").read_text(encoding="utf-8"))
    run_all(store, STEPS[:3])
    assert store.query(f"SELECT DISTINCT congestion_benchmark FROM {ANALYTICS}.ap2_classroom_pressure") == [
        (registry["ap2"]["threshold"],)]
    assert store.query(f"""SELECT DISTINCT es_benchmark_max_learners_per_teacher,
        jhs_benchmark_max_learners_per_teacher, shs_benchmark_max_learners_per_teacher
        FROM {ANALYTICS}.ap3_teacher_pressure""") == [
        (registry["ap3"]["es_max_learners_per_teacher"], registry["ap3"]["jhs_max_learners_per_teacher"],
         pytest.approx(registry["ap3"]["shs_max_learners_per_teacher"]))]



def ap1_presence(store):
    return {r[0]: r[1:] for r in store.query(f"""SELECT city_mun_psgc_code, regular_barangay_count,
        barangays_with_public_es, barangays_without_public_es, barangays_without_public_es_pct,
        es_count_is_upper_bound, es_benchmark_status, public_jhs_school_count, jhs_benchmark_status,
        benchmark_status FROM {ANALYTICS}.ap1_school_provision""")}


def test_ap1_screens_every_barangay_for_a_public_es_under_do_40(store):
    run_all(store, STEPS[:1])
    rows = ap1_presence(store)
    gap = "school-presence gap identified"
    assert rows["C1"] == (2, 2, 0, 0.0, False, "every barangay has a public ES", 0, "no public JHS", gap)
    assert rows["C2"] == (2, 1, 1, 50.0, False, "barangay without public ES", 0, "no public JHS", gap)
    # Town Two's only school has no barangay match, so "1 barangay without" is at most 1
    assert rows["M2"] == (1, 0, 1, 100.0, True, "barangay without public ES", 0, "no public JHS", gap)


def test_ap1_needs_a_public_es_and_a_public_jhs_for_no_gap(store):
    store.sql(f"""UPDATE {GOLD}.fact_school_enrollment SET is_offered = TRUE, learner_count = 40
        WHERE school_id = 'S1' AND education_level_code = 'JHS'""")
    run_all(store, STEPS[:1])
    assert ap1_presence(store)["C1"][-3:] == (1, "public JHS present", "no school-presence gap identified")


def test_ap1_an_inactive_or_non_es_school_does_not_serve_a_barangay(store):
    # S2 stops offering ES and offers JHS only: it no longer serves its barangay, but it is City One's public JHS
    store.sql(f"""UPDATE {GOLD}.fact_school_enrollment SET is_offered = (education_level_code = 'JHS'),
        learner_count = CASE WHEN education_level_code = 'JHS' THEN 90 ELSE 0 END
        WHERE school_id = 'S2' AND school_year = '2023-24'""")
    run_all(store, STEPS[:1])
    assert ap1_presence(store)["C1"][:3] == (2, 1, 1)
    assert ap1_presence(store)["C1"][6:8] == (1, "public JHS present")


def test_ap1_screen_never_enters_the_classroom_queue(store):
    run_all(store)
    rows = store.query(f"""SELECT city_mun_psgc_code, ap1_school_presence_status, ap1_barangays_without_public_es,
        classroom_priority_rank FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code""")
    # every LGU has a presence gap here and none has 50 learners per room, so the gap is shown but nothing is ranked
    assert [(r[0], r[1], r[3]) for r in rows] == [
        (code, "school-presence gap identified", None) for code in ["C1", "C2", "M1", "M2"]]
    assert [r[2] for r in rows] == [0, 1, 0, 1]


def test_ap1_gate_rejects_a_wrong_barangay_count(store):
    run(store, "01_answer_ap1.sql")
    store.sql(f"""UPDATE {ANALYTICS}.ap1_school_provision_candidate
        SET barangays_without_public_es = 0 WHERE city_mun_psgc_code = 'C2'""")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_ap1.sql")


def test_ap1_gate_rejects_a_wrong_benchmark_status(store):
    run(store, "01_answer_ap1.sql")
    store.sql(f"""UPDATE {ANALYTICS}.ap1_school_provision_candidate
        SET es_benchmark_status = 'school shortage' WHERE city_mun_psgc_code = 'C2'""")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_ap1.sql")


def test_ap1_gate_records_the_d061_checks_under_catalog_names(store):
    # existing names in config/quality_attributes.yml, so the data-quality dashboard file is not regenerated
    run_all(store, STEPS[:1])
    checks = dict(store.query("""SELECT check_name, status FROM edu_access.`01-control`.data_quality_results
        WHERE source_id = 'ap1_school_provision' AND check_name IN ('counts_reconcile', 'derived_values_reconcile',
        'assessment_status_valid')"""))
    assert checks == {"counts_reconcile": "PASS", "derived_values_reconcile": "PASS", "assessment_status_valid": "PASS"}
    assert store.query(f"""SELECT COUNT_IF(barangays_without_public_es > 0), SUM(barangays_without_public_es),
        COUNT_IF(public_jhs_school_count = 0) FROM {ANALYTICS}.ap1_school_provision""") == [(2, 2, 4)]


def test_ap1_reference_registry_matches_published_values(store):
    import json

    registry = json.loads((ROOT / "config/analytics_benchmarks.json").read_text(encoding="utf-8"))["ap1"]
    run_all(store, STEPS[:1])
    assert registry["priority_use"] == "none" and registry["ratio_reference"] is None
    assert store.query(f"""SELECT DISTINCT reference_id, es_reference_min_schools_per_barangay,
        jhs_reference_min_schools_per_lgu FROM {ANALYTICS}.ap1_school_provision""") == [
        (registry["reference_id"], registry["es_reference_min_schools_per_barangay"],
         registry["jhs_reference_min_schools_per_lgu"])]
    statuses = store.query(f"SELECT DISTINCT es_benchmark_status, jhs_benchmark_status FROM {ANALYTICS}.ap1_school_provision")
    assert {s[0] for s in statuses} <= set(registry["es_statuses"])
    assert {s[1] for s in statuses} <= set(registry["jhs_statuses"])
    spacing = {r[0] for r in store.query(f"SELECT DISTINCT spacing_benchmark_status FROM {ANALYTICS}.ap1_school_provision")}
    assert spacing <= set(registry["spacing_statuses"])


def ap1_spacing(store):
    return {r[0]: r[1:] for r in store.query(f"""SELECT city_mun_psgc_code, active_public_es_school_count,
        spacing_tested_es_school_count, isolated_es_school_count, learners_in_isolated_es_schools,
        spacing_benchmark_status FROM {ANALYTICS}.ap1_school_provision""")}


def test_ap1_flags_a_public_es_with_no_other_within_do_40_spacing(store):
    run_all(store, STEPS[:1])
    rows = ap1_spacing(store)
    assert rows["C1"] == (2, 2, 0, 0, "no isolated public ES")              # 0.5 km apart, within 1 km
    assert rows["C2"] == (1, 1, 1, 330, "isolated public ES identified")
    assert rows["M1"] == (1, 1, 1, 150, "isolated public ES identified")
    assert rows["M2"] == (1, 0, 0, 0, "not assessed")                       # no urban or rural class


def test_ap1_spacing_is_2_km_in_a_rural_barangay_and_1_km_in_an_urban_one(store):
    # a new ES school 1.5 km north of S4 (rural): within 2 km, so neither is isolated
    add_public_school(store, "X1", "M1", 90, 3)
    store.sql(f"""INSERT INTO {GOLD}.dim_school_location VALUES
        ('X1','2023-24','M1','M1-B1','R',125.0,8.0135,NULL,'inside',TRUE,'deped_psgc_coordinates')""")
    run_all(store, STEPS[:1])
    assert ap1_spacing(store)["M1"][2:] == (0, 0, "no isolated public ES")
    # the same 1.5 km in an urban barangay is beyond 1 km, so both are isolated
    store.sql(f"UPDATE {GOLD}.dim_school_location SET urban_rural = 'U' WHERE school_id IN ('S4', 'X1')")
    run_all(store, STEPS[:1])
    assert ap1_spacing(store)["M1"][2:] == (2, 240, "isolated public ES identified")


def test_ap1_a_point_that_failed_the_boundary_test_is_not_used(store):
    store.sql(f"""UPDATE {GOLD}.dim_school_location SET boundary_test_status = 'outside', is_location_usable = FALSE
        WHERE school_id = 'S2'""")
    run_all(store, STEPS[:1])
    # S2 is no longer a neighbour, and City One's coverage drops to 50%
    assert ap1_spacing(store)["C1"] == (2, 1, 1, 130, "not assessed")


def test_ap1_spacing_finds_a_neighbour_across_a_grid_cell_and_an_lgu_boundary(store):
    # X2 in City Two is 0.3 km from S3 but in the next 0.02-degree cell
    add_public_school(store, "X2", "C2", 80, 2)
    store.sql(f"""UPDATE {GOLD}.dim_school_location SET latitude = 10.0199 WHERE school_id = 'S3'""")
    store.sql(f"""INSERT INTO {GOLD}.dim_school_location VALUES
        ('X2','2023-24','C2','C2-B1','U',124.0,10.0226,NULL,'inside',TRUE,'deped_psgc_coordinates')""")
    run_all(store, STEPS[:1])
    assert ap1_spacing(store)["C2"][2:] == (0, 0, "no isolated public ES")


def test_ap1_gate_rejects_a_wrong_isolated_count(store):
    run(store, "01_answer_ap1.sql")
    store.sql(f"""UPDATE {ANALYTICS}.ap1_school_provision_candidate
        SET isolated_es_school_count = 0 WHERE city_mun_psgc_code = 'C2'""")
    with pytest.raises(Exception, match="Analytics gate failed"):
        run(store, "90_validate_ap1.sql")


def test_ap1_spacing_registry_matches_published_values(store):
    import json

    criteria = json.loads((ROOT / "config/analytics_benchmarks.json").read_text(encoding="utf-8"))[
        "ap1"]["establishment_criteria"]
    run_all(store, STEPS[:1])
    assert store.query(f"""SELECT DISTINCT spacing_km_rural_reference, spacing_km_urban_reference
        FROM {ANALYTICS}.ap1_school_provision""") == [(criteria["spacing_km_rural"], criteria["spacing_km_urban"])]


def bq_rows(store):
    return {r[0]: r[1:] for r in store.query(f"""SELECT city_mun_psgc_code, ap1_gap, ap2_gap, ap3_gap,
        ap1_score, ap2_score, ap3_score, composite_score, bq_priority_group, bq_priority_rank
        FROM {ANALYTICS}.lgu_priority_matrix""")}


def add_bq_pressure(store):
    # City Two: 330 learners in 5 rooms (66 per room); Town One: 150 ES learners for 3 teachers (50 against ES 35)
    store.sql(f"UPDATE {GOLD}.fact_school_classroom_capacity SET instructional_classrooms_total = 5 WHERE school_id = 'S3'")
    store.sql(f"UPDATE {GOLD}.fact_school_teacher_capacity SET teacher_count = 3 WHERE school_id = 'S4'")


def test_bq_gaps_follow_d062_formulas(store):
    add_bq_pressure(store)
    run_all(store)
    rows = bq_rows(store)
    # AP1: school-age population per school against the median of its own type (cities 494 and 1976: 1235)
    assert rows["C2"][0] == pytest.approx(1976 / 1235 - 1)
    assert rows["C1"][0] == 0.0
    # AP2: pooled learners per reported room against PIDS 50
    assert rows["C2"][1] == pytest.approx(66 / 50 - 1)
    # AP3: reference teachers (150 / 35) against reported teachers (3)
    assert rows["M1"][2] == pytest.approx(150 / 35 / 3 - 1)
    assert {r[2] for code, r in rows.items() if code != "M1"} == {0.0}


def test_bq_scores_are_percentile_ranks_and_the_composite_is_an_equal_weight_mean(store):
    add_bq_pressure(store)
    run_all(store)
    rows = bq_rows(store)
    for code, (_, _, _, s1, s2, s3, composite, group, _) in rows.items():
        assert group == "ranked"
        assert composite == pytest.approx((s1 + s2 + s3) / 3)
    # a zero gap scores 0; with four LGUs the only positive AP2 gap scores (4 - 1) / (4 - 1) = 100
    assert rows["C1"][3:6] == (0.0, 0.0, 0.0)
    assert rows["C2"][4] == 100.0
    # City Two fails AP1 and AP2, so it is first; ties share a rank
    assert rows["C2"][8] == 1
    assert rows["C1"][8] == max(r[8] for r in rows.values())


def test_bq_missing_ap_is_data_review_and_never_scored_as_zero(store):
    add_bq_pressure(store)
    store.sql(f"DELETE FROM {GOLD}.fact_school_classroom_capacity WHERE school_id = 'S1'")
    run_all(store)
    rows = bq_rows(store)
    assert rows["C1"][1] is None and rows["C1"][3:] == (None, None, None, None, "data_review", None)
    # the other three are ranked among themselves: City Two's AP2 gap is the only positive one
    assert rows["C2"][4] == 100.0
    assert sorted(r[7] for code, r in rows.items() if code != "C1") == ["ranked"] * 3


def test_bq_gate_rejects_a_changed_score_and_a_score_on_data_review(store):
    add_bq_pressure(store)
    store.sql(f"DELETE FROM {GOLD}.fact_school_classroom_capacity WHERE school_id = 'S1'")
    run_all(store)
    before = store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code")
    for change in ["composite_score = composite_score + 1 WHERE city_mun_psgc_code = 'C2'",
                   "ap2_score = 0 WHERE city_mun_psgc_code = 'C1'"]:
        run(store, "05_build_priority_matrix.sql")
        store.sql(f"UPDATE {ANALYTICS}.lgu_priority_matrix_candidate SET {change}")
        with pytest.raises(Exception, match="Analytics gate failed"):
            run(store, "90_validate_priority_matrix.sql")
    assert store.query(f"SELECT * FROM {ANALYTICS}.lgu_priority_matrix ORDER BY city_mun_psgc_code") == before


def test_bq_sensitivity_reports_each_variant(store):
    add_bq_pressure(store)
    run_all(store)
    rows = {r[0]: r[1:] for r in store.query(f"""SELECT variant, ranked_lgus, top_50_overlap, top_50_lgus
        FROM {ANALYTICS}.bq_priority_sensitivity""")}
    assert set(rows) == {"without_ap1", "without_ap2", "without_ap3", "min_max_scores"}
    assert {r for r in rows.values()} == {(4, 4, 4)}
    recorded = {r[0] for r in store.query(f"""SELECT check_name FROM {CONTROL}.data_quality_results
        WHERE source_id = 'lgu_priority_matrix' AND status = 'PASS'""")}
    assert {"derived_values_reconcile", "counts_reconcile"} <= recorded


def test_bq_registry_matches_the_composite_inputs():
    import json

    registry = json.loads((ROOT / "config/analytics_benchmarks.json").read_text(encoding="utf-8"))
    bq = registry["bq"]
    assert bq["decision"] == "D-062"
    assert bq["weights"] == {"ap1": 1, "ap2": 1, "ap3": 1}
    assert bq["ap2_baseline"] == registry["ap2"]["threshold"]
    assert bq["ap3_baselines"] == {"es": registry["ap3"]["es_max_learners_per_teacher"],
                                   "jhs": registry["ap3"]["jhs_max_learners_per_teacher"],
                                   "shs": registry["ap3"]["shs_max_learners_per_teacher"]}
    sql = (ROOT / "etl/06_analytics/05_build_priority_matrix.sql").read_text(encoding="utf-8")
    assert "/ 50.0 - 1" in sql and "/ 35.0" in sql and "/ 36.0" in sql and "/ (80.0 / 3)" in sql
    assert all(step["references"] for step in bq["steps"])
