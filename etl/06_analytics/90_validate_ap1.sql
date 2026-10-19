-- AP1 validation gate (#144, D-050). A failed candidate never replaces the last good output.

DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap1_gate_summary AS
WITH output AS (
  SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate
),
expected_keys AS (
  SELECT c.city_mun_psgc_code, y.school_year, l.education_level_code
  FROM edu_access.`05-gold`.dim_city_municipality AS c
  CROSS JOIN (SELECT DISTINCT school_year FROM edu_access.`05-gold`.fact_school_enrollment) AS y
  CROSS JOIN (SELECT * FROM VALUES ('ALL'), ('ES'), ('JHS'), ('SHS') AS v(education_level_code)) AS l
  WHERE c.member_type = 'regular'
),
key_reconciliation AS (
  SELECT COUNT_IF(o.city_mun_psgc_code IS NULL OR e.city_mun_psgc_code IS NULL) AS mismatched_keys
  FROM output AS o FULL OUTER JOIN expected_keys AS e
    USING (city_mun_psgc_code, school_year, education_level_code)
),
regular_barangays AS (
  SELECT city_mun_psgc_code, COUNT(*) AS barangays
  FROM edu_access.`05-gold`.dim_barangay WHERE member_type = 'regular'
  GROUP BY city_mun_psgc_code
),
public_rows AS (
  SELECT * FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE sector = 'Public' AND city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED')
),
active_schools AS (
  SELECT school_id, school_year, city_mun_psgc_code, MAX(barangay_psgc_code) AS barangay_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
         SUM(CASE WHEN is_offered AND learner_count IS NULL THEN 1 ELSE 0 END) AS incomplete_levels,
         SUM(CASE WHEN is_offered THEN learner_count ELSE 0 END) AS complete_level_sum
  FROM public_rows
  GROUP BY school_id, school_year, city_mun_psgc_code
),
expected_barangay_metrics AS (
  SELECT a.city_mun_psgc_code, a.school_year,
         COUNT(DISTINCT CASE WHEN b.member_type = 'regular' THEN a.barangay_psgc_code END) AS served_barangays,
         COUNT(DISTINCT a.school_id) AS es_schools,
         COUNT(DISTINCT CASE WHEN b.member_type = 'regular' THEN a.school_id END) AS matched_es_schools,
         COUNT(DISTINCT CASE WHEN b.member_type = 'unknown' THEN a.school_id END) AS unmatched_es_schools
  FROM active_schools AS a
  JOIN public_rows AS p USING (school_id, school_year, city_mun_psgc_code)
  JOIN edu_access.`05-gold`.dim_barangay AS b
    ON b.barangay_psgc_code = a.barangay_psgc_code AND b.city_mun_psgc_code = a.city_mun_psgc_code
  WHERE a.is_active = 1 AND p.education_level_code = 'ES' AND p.is_offered
  GROUP BY a.city_mun_psgc_code, a.school_year
),
expected_school_metrics AS (
  SELECT p.city_mun_psgc_code, p.school_year, p.education_level_code,
         COUNT(DISTINCT CASE WHEN a.is_active = 1 AND p.is_offered THEN p.school_id END) AS schools,
         COUNT(DISTINCT CASE WHEN a.is_active = 1 AND p.is_offered AND p.learner_count IS NOT NULL THEN p.school_id END)
           AS complete_schools,
         SUM(CASE WHEN a.is_active = 1 AND p.is_offered AND p.learner_count IS NOT NULL THEN p.learner_count ELSE 0 END)
           AS learners
  FROM public_rows AS p JOIN active_schools AS a USING (school_id, school_year, city_mun_psgc_code)
  GROUP BY p.city_mun_psgc_code, p.school_year, p.education_level_code
  UNION ALL
  SELECT city_mun_psgc_code, school_year, 'ALL',
         COUNT(DISTINCT CASE WHEN is_active = 1 THEN school_id END),
         COUNT(DISTINCT CASE WHEN is_active = 1 AND incomplete_levels = 0 THEN school_id END),
         SUM(CASE WHEN is_active = 1 AND incomplete_levels = 0 THEN complete_level_sum ELSE 0 END)
  FROM active_schools
  GROUP BY city_mun_psgc_code, school_year
),
school_reconciliation AS (
  SELECT COUNT_IF(o.public_school_count <> COALESCE(e.schools, 0)
    OR o.complete_enrollment_school_count <> COALESCE(e.complete_schools, 0)
    OR o.public_school_enrollment <> COALESCE(e.learners, 0)) AS differing_rows
  FROM output AS o
  LEFT JOIN expected_school_metrics AS e
    USING (city_mun_psgc_code, school_year, education_level_code)
),
barangay_reconciliation AS (
  SELECT COUNT_IF(o.barangays_with_public_es <> COALESCE(e.served_barangays, 0)
    OR o.active_public_es_school_count <> COALESCE(e.es_schools, 0)
    OR o.public_es_schools_with_barangay_match <> COALESCE(e.matched_es_schools, 0)
    OR o.public_es_schools_without_barangay_match <> COALESCE(e.unmatched_es_schools, 0)) AS differing_rows
  FROM output AS o
  LEFT JOIN expected_barangay_metrics AS e USING (city_mun_psgc_code, school_year)
),
population_rows AS (
  SELECT city_mun_psgc_code, COUNT(*) AS rows
  FROM edu_access.`05-gold`.fact_city_population WHERE reference_year = 2024
  GROUP BY city_mun_psgc_code
)
SELECT
  (SELECT COUNT(*) FROM output) AS output_rows,
  (SELECT COUNT(*) FROM expected_keys) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT (city_mun_psgc_code, school_year, education_level_code)) FROM output) AS duplicate_keys,
  (SELECT COUNT_IF(city_mun_psgc_code IS NULL OR school_year IS NULL OR education_level_code IS NULL) FROM output) AS null_keys,
  (SELECT mismatched_keys FROM key_reconciliation) AS mismatched_keys,
  (SELECT COUNT_IF(public_school_count < 0 OR complete_enrollment_school_count < 0
    OR incomplete_enrollment_school_count < 0 OR public_school_enrollment < 0
    OR barangays_without_public_es < 0 OR barangays_without_public_es > barangay_count) FROM output) AS invalid_counts,
  (SELECT COUNT_IF(public_school_count <> complete_enrollment_school_count + incomplete_enrollment_school_count)
    FROM output) AS school_coverage_not_reconciled,
  (SELECT COUNT_IF(learners_per_public_school IS DISTINCT FROM
    CASE WHEN complete_enrollment_school_count > 0
      THEN public_school_enrollment * 1.0 / complete_enrollment_school_count END) FROM output) AS learner_ratio_differs,
  (SELECT COUNT_IF(population_per_public_school IS DISTINCT FROM
    CASE WHEN population_2024 IS NOT NULL AND population_denominator_school_count > 0
      THEN population_2024 * 1.0 / population_denominator_school_count END) FROM output) AS population_ratio_differs,
  (SELECT COUNT_IF(population_reference_year <> 2024) FROM output) AS wrong_population_year,
  (SELECT COUNT_IF(barangays_with_public_es + barangays_without_public_es <> barangay_count) FROM output)
    AS barangays_not_counted_once,
  (SELECT COUNT_IF(o.barangay_count <> COALESCE(b.barangays, 0))
    FROM output AS o LEFT JOIN regular_barangays AS b USING (city_mun_psgc_code)) AS barangay_totals_differ,
  (SELECT differing_rows FROM school_reconciliation) AS school_metrics_differ,
  (SELECT differing_rows FROM barangay_reconciliation) AS barangay_metrics_differ,
  (SELECT COUNT_IF(o.city_mun_name IS DISTINCT FROM c.city_mun_name
      OR o.lgu_type IS DISTINCT FROM c.lgu_type
      OR o.province_psgc_code IS DISTINCT FROM c.province_psgc_code
      OR o.province_name IS DISTINCT FROM c.province_name
      OR o.region_psgc_code IS DISTINCT FROM c.region_psgc_code
      OR o.region_name IS DISTINCT FROM c.region_name
      OR o.population_2024 IS DISTINCT FROM CASE WHEN p.estimate_status = 'available' THEN p.population END
      OR o.population_ratio_null_reason IS DISTINCT FROM CASE
        WHEN p.city_mun_psgc_code IS NULL THEN 'no 2024 population row'
        WHEN p.estimate_status <> 'available' THEN p.status_reason
        WHEN o.population_denominator_school_count = 0 THEN 'no active public school'
      END)
    FROM output AS o
    JOIN edu_access.`05-gold`.dim_city_municipality AS c USING (city_mun_psgc_code)
    LEFT JOIN edu_access.`05-gold`.fact_city_population AS p
      ON p.city_mun_psgc_code = o.city_mun_psgc_code AND p.reference_year = 2024) AS identity_or_population_differs,
  (SELECT COUNT_IF(barangay_count_is_upper_bound IS DISTINCT FROM (public_es_schools_without_barangay_match > 0))
    FROM output) AS upper_bound_label_differs,
  (SELECT COUNT_IF(active_public_es_school_count <>
      public_es_schools_with_barangay_match + public_es_schools_without_barangay_match
    OR barangay_match_coverage_pct IS DISTINCT FROM CASE WHEN active_public_es_school_count > 0
      THEN public_es_schools_with_barangay_match * 100.0 / active_public_es_school_count END)
    FROM output) AS geography_coverage_differs,
  (SELECT COUNT_IF(rows > 1) FROM population_rows) AS duplicate_population_rows;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap1_school_provision', 'analytics', 'edu_access.06-analytics.ap1_school_provision',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_reconcile' AS check_name, CASE WHEN output_rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(output_rows AS STRING) AS actual FROM ap1_gate_summary
  UNION ALL SELECT 'grain_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'key_not_null', CASE WHEN null_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_keys AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'keys_reconcile', CASE WHEN mismatched_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(mismatched_keys AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'counts_valid', CASE WHEN invalid_counts = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(invalid_counts AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'school_coverage_reconciles', CASE WHEN school_coverage_not_reconciled = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(school_coverage_not_reconciled AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'learner_ratio_reconciles', CASE WHEN learner_ratio_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(learner_ratio_differs AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'population_ratio_reconciles', CASE WHEN population_ratio_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(population_ratio_differs AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'population_reference_year_2024', CASE WHEN wrong_population_year = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(wrong_population_year AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'barangays_counted_once', CASE WHEN barangays_not_counted_once = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(barangays_not_counted_once AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'barangay_total_matches_dimension', CASE WHEN barangay_totals_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(barangay_totals_differ AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'school_counts_and_enrollment_match_fact', CASE WHEN school_metrics_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(school_metrics_differ AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'barangay_metrics_match_fact_and_dimension', CASE WHEN barangay_metrics_differ = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(barangay_metrics_differ AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'identity_and_population_match_gold', CASE WHEN identity_or_population_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(identity_or_population_differs AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'upper_bound_label_follows_unmatched_count', CASE WHEN upper_bound_label_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(upper_bound_label_differs AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'barangay_match_coverage_reconciles', CASE WHEN geography_coverage_differs = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(geography_coverage_differs AS STRING) FROM ap1_gate_summary
  UNION ALL SELECT 'population_one_row_per_lgu', CASE WHEN duplicate_population_rows = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_population_rows AS STRING) FROM ap1_gate_summary
) AS checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap1_school_provision: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap1_school_provision' AND layer = 'analytics'
  AND status = 'FAIL' AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap1_school_provision USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate;

COMMENT ON TABLE edu_access.`06-analytics`.ap1_school_provision IS 'AP1 school-provision output by regular LGU, school year, and reporting level.';
ALTER TABLE edu_access.`06-analytics`.ap1_school_provision OWNER TO `reached-hq`;
