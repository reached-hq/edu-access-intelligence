-- AP2 validation gate (#145, D-050, D-057). A failed candidate never replaces the last good output.
--
-- Recomputes every school's status from the published Gold facts by a second route (a school's levels are
-- complete when every level row has a learner_count, since a level not offered is 0), then compares the
-- candidate with it LGU by LGU and in national totals summed from each fact's own rows.
--
-- FAIL: wrong grain or key set, a year other than 2023-24, identity that differs from the dimension, a
-- room join that adds rows, counts or totals that do not reconcile, wrong ratio or coverage arithmetic,
-- a ratio or coverage without its NULL reason, wrong labels or code revision, a missing input year, or a
-- non-public, overseas or unmatched school inside a regular LGU.
-- WARN (counts only, no school rows): missing, zero and absent room counts, incomplete enrollment,
-- inactive schools, annexes without a mother-school link (D-044), public schools outside every regular
-- LGU, LGUs under 90% learner coverage, and schools above the D-057 outlier fence. Values are never
-- changed; these stay visible for review before the dashboard is published.

DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap2_gate_schools AS
WITH enrollment AS (
  SELECT school_id, school_year, city_mun_psgc_code, psgc_match_status, annex_status, is_offered, learner_count
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public'
),
by_school AS (
  SELECT
    school_id, school_year,
    COUNT(DISTINCT city_mun_psgc_code) AS geographies,
    MAX(city_mun_psgc_code) AS city_mun_psgc_code,
    MAX(psgc_match_status) AS psgc_match_status,
    COUNT_IF(annex_status = 'Annex/Extension School') > 0 AS is_annex,
    COALESCE(MAX(CASE WHEN is_offered THEN learner_count END), 0) > 0 AS is_active,
    COUNT(*) = COUNT(learner_count) AS is_complete,
    SUM(learner_count) AS level_sum,
    SUM(CASE WHEN is_offered THEN learner_count END) AS offered_sum
  FROM enrollment
  GROUP BY school_id, school_year
),
capacity AS (
  SELECT school_id, school_year, COUNT(*) AS capacity_rows, MAX(instructional_classrooms_total) AS rooms
  FROM edu_access.`05-gold`.fact_school_classroom_capacity
  WHERE school_year = '2023-24'
  GROUP BY school_id, school_year
)
SELECT
  b.*,
  l.lgu_type,
  l.city_mun_psgc_code IS NOT NULL AS in_regular_lgu,
  CASE WHEN b.is_complete THEN b.level_sum END AS total_learners,
  COALESCE(c.capacity_rows, 0) AS capacity_rows,
  c.rooms,
  b.is_active AND b.is_complete AND COALESCE(c.rooms > 0, FALSE) AS in_ratio
FROM by_school AS b
LEFT JOIN edu_access.`05-gold`.dim_city_municipality AS l
  ON l.city_mun_psgc_code = b.city_mun_psgc_code AND l.member_type = 'regular'
LEFT JOIN capacity AS c USING (school_id, school_year);

-- Computed once into a table, as the Gold gates do: the checks below read it many times.
CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate USING DELTA AS
WITH output AS (
  SELECT * FROM edu_access.`06-analytics`.ap2_classroom_pressure_candidate
),
regular AS (
  SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'
),
scope AS (
  SELECT * FROM ap2_gate_schools WHERE in_regular_lgu AND is_active
),
expected AS (
  SELECT
    city_mun_psgc_code,
    COUNT(*) AS active_schools,
    COUNT_IF(is_complete) AS complete_schools,
    SUM(CASE WHEN is_complete THEN total_learners ELSE 0 END) AS enrollment,
    COUNT_IF(rooms > 0) AS usable_schools,
    COUNT_IF(in_ratio) AS ratio_schools,
    SUM(CASE WHEN in_ratio THEN total_learners ELSE 0 END) AS ratio_learners,
    SUM(CASE WHEN in_ratio THEN rooms ELSE 0 END) AS ratio_rooms,
    COUNT_IF(capacity_rows > 0 AND rooms IS NULL) AS missing_schools,
    COUNT_IF(rooms = 0) AS zero_schools,
    COUNT_IF(capacity_rows = 0) AS no_row_schools,
    COUNT_IF(is_annex) AS annex_schools,
    COUNT_IF(is_annex AND NOT COALESCE(rooms > 0, FALSE)) AS annex_without_rooms
  FROM scope
  GROUP BY city_mun_psgc_code
),
inactive AS (
  SELECT city_mun_psgc_code, COUNT(*) AS inactive_schools
  FROM ap2_gate_schools WHERE in_regular_lgu AND NOT is_active
  GROUP BY city_mun_psgc_code
),
eligible AS (
  SELECT school_id FROM scope WHERE in_ratio
)
SELECT
  (SELECT COUNT(*) FROM output) AS output_rows,
  (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT (city_mun_psgc_code, school_year)) FROM output) AS duplicate_keys,
  (SELECT COUNT_IF(city_mun_psgc_code IS NULL OR school_year IS NULL) FROM output) AS null_keys,
  (SELECT COUNT_IF(o.city_mun_psgc_code IS NULL OR r.city_mun_psgc_code IS NULL)
    FROM output AS o FULL OUTER JOIN regular AS r USING (city_mun_psgc_code)) AS mismatched_keys,
  (SELECT COUNT_IF(school_year IS DISTINCT FROM '2023-24') FROM output) AS wrong_school_year,
  (SELECT COUNT_IF(o.city_mun_name IS DISTINCT FROM r.city_mun_name OR o.lgu_type IS DISTINCT FROM r.lgu_type
      OR o.province_psgc_code IS DISTINCT FROM r.province_psgc_code OR o.province_name IS DISTINCT FROM r.province_name
      OR o.region_psgc_code IS DISTINCT FROM r.region_psgc_code OR o.region_name IS DISTINCT FROM r.region_name
      OR o.source_psgc_quarter IS DISTINCT FROM r.source_psgc_quarter)
    FROM output AS o JOIN regular AS r USING (city_mun_psgc_code)) AS identity_differs,
  (SELECT COUNT(*) FROM edu_access.`05-gold`.fact_school_enrollment
    WHERE school_year = '2023-24' AND sector = 'Public') AS public_enrollment_rows,
  (SELECT COUNT(*) FROM edu_access.`05-gold`.fact_school_classroom_capacity
    WHERE school_year = '2023-24') AS capacity_rows,
  (SELECT COUNT_IF(geographies > 1) FROM ap2_gate_schools) AS schools_with_two_geographies,
  (SELECT COUNT_IF(capacity_rows > 1) FROM ap2_gate_schools) AS schools_with_repeated_capacity,
  (SELECT COUNT(*) FROM ap2_gate_schools AS s
    LEFT JOIN edu_access.`05-gold`.fact_school_classroom_capacity AS c
      ON c.school_id = s.school_id AND c.school_year = s.school_year) - (SELECT COUNT(*) FROM ap2_gate_schools)
    AS rows_added_by_capacity_join,
  (SELECT COUNT_IF(in_regular_lgu AND psgc_match_status IS DISTINCT FROM 'matched') FROM ap2_gate_schools)
    AS unmatched_in_regular_lgu,
  (SELECT COUNT(DISTINCT e.school_id) FROM edu_access.`05-gold`.fact_school_enrollment AS e
    JOIN regular AS r USING (city_mun_psgc_code)
    WHERE e.school_year = '2023-24' AND e.sector = 'PSO') AS overseas_in_regular_lgu,
  (SELECT COUNT_IF(is_complete AND offered_sum IS DISTINCT FROM level_sum) FROM ap2_gate_schools)
    AS level_rule_differs,
  (SELECT COUNT_IF(
      o.active_public_school_count <> COALESCE(e.active_schools, 0)
      OR o.complete_enrollment_school_count <> COALESCE(e.complete_schools, 0)
      OR o.public_school_enrollment <> COALESCE(e.enrollment, 0)
      OR o.usable_room_school_count <> COALESCE(e.usable_schools, 0)
      OR o.ratio_school_count <> COALESCE(e.ratio_schools, 0)
      OR o.ratio_learners <> COALESCE(e.ratio_learners, 0)
      OR o.ratio_instructional_rooms <> COALESCE(e.ratio_rooms, 0)
      OR o.missing_room_school_count <> COALESCE(e.missing_schools, 0)
      OR o.zero_room_school_count <> COALESCE(e.zero_schools, 0)
      OR o.no_facilities_row_school_count <> COALESCE(e.no_row_schools, 0)
      OR o.annex_school_count <> COALESCE(e.annex_schools, 0)
      OR o.annex_without_usable_room_school_count <> COALESCE(e.annex_without_rooms, 0)
      OR o.inactive_public_school_count <> COALESCE(i.inactive_schools, 0))
    FROM output AS o
    LEFT JOIN expected AS e USING (city_mun_psgc_code)
    LEFT JOIN inactive AS i USING (city_mun_psgc_code)) AS lgu_metrics_differ,
  (SELECT COALESCE(SUM(ratio_instructional_rooms), 0) FROM output) AS output_ratio_rooms,
  (SELECT COALESCE(SUM(instructional_classrooms_total), 0) FROM edu_access.`05-gold`.fact_school_classroom_capacity
    WHERE school_year = '2023-24' AND school_id IN (SELECT school_id FROM eligible)) AS fact_ratio_rooms,
  (SELECT COALESCE(SUM(ratio_learners), 0) FROM output) AS output_ratio_learners,
  (SELECT COALESCE(SUM(learner_count), 0) FROM edu_access.`05-gold`.fact_school_enrollment
    WHERE school_year = '2023-24' AND sector = 'Public' AND school_id IN (SELECT school_id FROM eligible))
    AS fact_ratio_learners,
  (SELECT COALESCE(SUM(public_school_enrollment), 0) FROM output) AS output_enrollment,
  (SELECT COALESCE(SUM(learner_count), 0) FROM edu_access.`05-gold`.fact_school_enrollment
    WHERE school_year = '2023-24' AND sector = 'Public'
      AND school_id IN (SELECT school_id FROM scope WHERE is_complete)) AS fact_enrollment,
  (SELECT COUNT_IF(
      active_public_school_count <> complete_enrollment_school_count + incomplete_enrollment_school_count
      OR active_public_school_count <> usable_room_school_count + missing_room_school_count
        + zero_room_school_count + no_facilities_row_school_count
      OR usable_room_school_count <> ratio_school_count + usable_room_incomplete_enrollment_school_count
      OR public_school_enrollment <> ratio_learners + missing_room_learners + zero_room_learners
        + no_facilities_row_learners
      OR annex_without_usable_room_school_count > annex_school_count
      OR annex_school_count > active_public_school_count) FROM output) AS partitions_differ,
  (SELECT COUNT_IF(LEAST(inactive_public_school_count, active_public_school_count, complete_enrollment_school_count,
      incomplete_enrollment_school_count, incomplete_enrollment_complete_level_learners, public_school_enrollment,
      usable_room_school_count, ratio_school_count, ratio_learners, ratio_instructional_rooms,
      missing_room_school_count, missing_room_learners, zero_room_school_count, zero_room_learners,
      no_facilities_row_school_count, no_facilities_row_learners, annex_school_count,
      annex_without_usable_room_school_count, annex_without_usable_room_learners) < 0) FROM output) AS negative_counts,
  -- COALESCE: an ABS over two NULLs is NULL, which is not a failure.
  (SELECT COUNT_IF(COALESCE(
      (learners_per_nsbi_instructional_room IS NULL) <> (ratio_instructional_rooms = 0)
      OR ABS(learners_per_nsbi_instructional_room
        - CAST(ratio_learners AS DOUBLE) / NULLIF(ratio_instructional_rooms, 0)) > 1e-9, FALSE)) FROM output)
    AS ratio_arithmetic_differs,
  (SELECT COUNT_IF(COALESCE(
      (school_coverage_pct IS NULL) <> (active_public_school_count = 0)
      OR (learner_coverage_pct IS NULL) <> (public_school_enrollment = 0)
      OR ABS(school_coverage_pct - 100.0 * usable_room_school_count / NULLIF(active_public_school_count, 0)) > 1e-9
      OR ABS(learner_coverage_pct - 100.0 * ratio_learners / NULLIF(public_school_enrollment, 0)) > 1e-9
      OR school_coverage_pct NOT BETWEEN 0 AND 100 OR learner_coverage_pct NOT BETWEEN 0 AND 100, FALSE)) FROM output)
    AS coverage_arithmetic_differs,
  (SELECT COUNT_IF((learners_per_nsbi_instructional_room IS NULL) <> (ratio_null_reason IS NOT NULL)
      OR (learner_coverage_pct IS NULL) <> (coverage_null_reason IS NOT NULL)) FROM output) AS null_reason_differs,
  (SELECT COUNT_IF(measure_label IS DISTINCT FROM 'Learners per reported instructional room'
      OR source_label IS DISTINCT FROM 'DepEd School Facilities (NSBI)'
      OR indicator_type IS DISTINCT FROM 'project-defined'
      OR validation_status IS DISTINCT FROM 'provisional'
      OR benchmark_status IS DISTINCT FROM 'not applicable') FROM output) AS labels_differ,
  (SELECT COALESCE(SUM(missing_room_school_count), 0) FROM output) AS missing_room_schools,
  (SELECT COALESCE(SUM(zero_room_school_count), 0) FROM output) AS zero_room_schools,
  (SELECT COALESCE(SUM(no_facilities_row_school_count), 0) FROM output) AS no_facilities_row_schools,
  (SELECT COALESCE(SUM(incomplete_enrollment_school_count), 0) FROM output) AS incomplete_enrollment_schools,
  (SELECT COALESCE(SUM(inactive_public_school_count), 0) FROM output) AS inactive_schools,
  (SELECT COALESCE(SUM(annex_school_count), 0) FROM output) AS annex_schools,
  (SELECT COALESCE(SUM(annex_without_usable_room_school_count), 0) FROM output) AS annexes_without_usable_room,
  (SELECT COUNT_IF(learners_per_nsbi_instructional_room IS NULL) FROM output) AS lgus_without_ratio,
  (SELECT COUNT_IF(learner_coverage_pct IS NULL OR learner_coverage_pct < 90) FROM output) AS lgus_under_90pct_coverage,
  (SELECT COUNT_IF(city_mun_psgc_code = 'UNKNOWN') FROM ap2_gate_schools) AS unknown_geography_schools,
  (SELECT COALESCE(SUM(total_learners), 0) FROM ap2_gate_schools WHERE city_mun_psgc_code = 'UNKNOWN')
    AS unknown_geography_learners,
  (SELECT COUNT_IF(city_mun_psgc_code = 'EXCLUDED') FROM ap2_gate_schools) AS excluded_geography_schools,
  (SELECT COALESCE(SUM(total_learners), 0) FROM ap2_gate_schools WHERE city_mun_psgc_code = 'EXCLUDED')
    AS excluded_geography_learners,
  (SELECT COALESCE(SUM(rooms), 0) FROM ap2_gate_schools WHERE NOT in_regular_lgu AND rooms > 0)
    AS rooms_outside_regular_lgus;

ALTER TABLE edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate OWNER TO `reached-hq`;

-- D-057 outlier check, recorded only: schools above Q3 + 3 x IQR of their own learners per room, with the
-- quartiles (linear interpolation) taken within LGU type over the schools in the ratio. Nothing is removed.
CREATE OR REPLACE TEMPORARY VIEW ap2_gate_outliers AS
WITH ratios AS (
  SELECT lgu_type, CAST(total_learners AS DOUBLE) / rooms AS learners_per_room
  FROM ap2_gate_schools
  WHERE in_regular_lgu AND is_active AND in_ratio
),
fences AS (
  SELECT lgu_type,
         percentile_cont(0.25) WITHIN GROUP (ORDER BY learners_per_room) AS q1,
         percentile_cont(0.75) WITHIN GROUP (ORDER BY learners_per_room) AS q3
  FROM ratios
  GROUP BY lgu_type
)
SELECT f.lgu_type, f.q3 + 3 * (f.q3 - f.q1) AS fence, COUNT_IF(r.learners_per_room > f.q3 + 3 * (f.q3 - f.q1)) AS schools
FROM fences AS f JOIN ratios AS r USING (lgu_type)
GROUP BY f.lgu_type, f.q1, f.q3;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap2_classroom_pressure', 'analytics', 'edu_access.06-analytics.ap2_classroom_pressure',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_reconcile' AS check_name, CASE WHEN output_rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(output_rows AS STRING) AS actual FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'grain_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'key_not_null', CASE WHEN null_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_keys AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'keys_match_regular_lgus', CASE WHEN mismatched_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(mismatched_keys AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'school_year_2023_24_only', CASE WHEN wrong_school_year = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(wrong_school_year AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'identity_matches_dimension', CASE WHEN identity_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(identity_differs AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'enrollment_has_2023_24', CASE WHEN public_enrollment_rows > 0 THEN 'PASS' ELSE 'FAIL' END, '>0', CAST(public_enrollment_rows AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'capacity_has_2023_24', CASE WHEN capacity_rows > 0 THEN 'PASS' ELSE 'FAIL' END, '>0', CAST(capacity_rows AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'one_geography_per_school', CASE WHEN schools_with_two_geographies = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(schools_with_two_geographies AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'capacity_one_row_per_school', CASE WHEN schools_with_repeated_capacity = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(schools_with_repeated_capacity AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'capacity_join_adds_no_rows', CASE WHEN rows_added_by_capacity_join = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(rows_added_by_capacity_join AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'only_matched_schools_in_lgus', CASE WHEN unmatched_in_regular_lgu = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(unmatched_in_regular_lgu AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'no_overseas_school_in_lgus', CASE WHEN overseas_in_regular_lgu = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(overseas_in_regular_lgu AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'not_offered_levels_are_zero', CASE WHEN level_rule_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(level_rule_differs AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'lgu_metrics_match_facts', CASE WHEN lgu_metrics_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(lgu_metrics_differ AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'ratio_rooms_match_capacity_fact', CASE WHEN output_ratio_rooms = fact_ratio_rooms THEN 'PASS' ELSE 'FAIL' END, CAST(fact_ratio_rooms AS STRING), CAST(output_ratio_rooms AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'ratio_learners_match_enrollment_fact', CASE WHEN output_ratio_learners = fact_ratio_learners THEN 'PASS' ELSE 'FAIL' END, CAST(fact_ratio_learners AS STRING), CAST(output_ratio_learners AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'enrollment_matches_enrollment_fact', CASE WHEN output_enrollment = fact_enrollment THEN 'PASS' ELSE 'FAIL' END, CAST(fact_enrollment AS STRING), CAST(output_enrollment AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'school_and_learner_partitions_reconcile', CASE WHEN partitions_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(partitions_differ AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'counts_not_negative', CASE WHEN negative_counts = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(negative_counts AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'ratio_is_ratio_of_sums', CASE WHEN ratio_arithmetic_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(ratio_arithmetic_differs AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'coverage_arithmetic', CASE WHEN coverage_arithmetic_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(coverage_arithmetic_differs AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'null_has_reason', CASE WHEN null_reason_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_reason_differs AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'labels_and_status', CASE WHEN labels_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(labels_differ AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'code_revision_is_run', CASE WHEN COUNT_IF(code_revision IS DISTINCT FROM :code_revision) = 0 THEN 'PASS' ELSE 'FAIL' END,
         '0', CAST(COUNT_IF(code_revision IS DISTINCT FROM :code_revision) AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_candidate
  UNION ALL SELECT 'schools_missing_rooms', CASE WHEN missing_room_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(missing_room_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_zero_rooms', CASE WHEN zero_room_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(zero_room_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_without_facilities_row', CASE WHEN no_facilities_row_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(no_facilities_row_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_incomplete_enrollment', CASE WHEN incomplete_enrollment_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(incomplete_enrollment_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_inactive', CASE WHEN inactive_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(inactive_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'annexes_without_mother_link', CASE WHEN annex_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(annex_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'annexes_without_usable_rooms', CASE WHEN annexes_without_usable_room = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(annexes_without_usable_room AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'lgus_without_ratio', CASE WHEN lgus_without_ratio = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(lgus_without_ratio AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'lgus_under_90pct_learner_coverage', CASE WHEN lgus_under_90pct_coverage = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(lgus_under_90pct_coverage AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_unknown_geography', CASE WHEN unknown_geography_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unknown_geography_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'learners_unknown_geography', CASE WHEN unknown_geography_learners = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unknown_geography_learners AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'schools_excluded_geography', CASE WHEN excluded_geography_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(excluded_geography_schools AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'learners_excluded_geography', CASE WHEN excluded_geography_learners = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(excluded_geography_learners AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'rooms_outside_regular_lgus', CASE WHEN rooms_outside_regular_lgus = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(rooms_outside_regular_lgus AS STRING) FROM edu_access.`06-analytics`.ap2_classroom_pressure_gate_summary_candidate
  UNION ALL SELECT 'outlier_schools/' || lgu_type, CASE WHEN schools = 0 THEN 'PASS' ELSE 'WARN' END,
         'fence ' || CAST(ROUND(fence, 2) AS STRING), CAST(schools AS STRING) FROM ap2_gate_outliers
) AS checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap2_classroom_pressure: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s) in data_quality_results for run ' || :run_id) END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap2_classroom_pressure' AND layer = 'analytics'
  AND status = 'FAIL' AND checked_at_utc >= session.analytics_gate_started_at_utc;

-- Every check passed: publish the candidate.
CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_classroom_pressure USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap2_classroom_pressure_candidate;

COMMENT ON TABLE edu_access.`06-analytics`.ap2_classroom_pressure IS 'AP2, SY 2023-24: learners per reported instructional room (DepEd School Facilities, NSBI) by regular city or municipality, with coverage. Provisional: annexes are not linked to mother schools (D-044) and the upper tail is under review (D-057). Not the DepEd classroom-learner ratio.';
ALTER TABLE edu_access.`06-analytics`.ap2_classroom_pressure OWNER TO `reached-hq`;
