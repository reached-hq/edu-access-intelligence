-- ap1 publication gate; a failure leaves the last valid output unchanged.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap1_gate_expected_population AS
SELECT city_mun_psgc_code, CAST(SUM(population) AS BIGINT) AS school_age_population
FROM edu_access.`05-gold`.fact_city_school_age_population
WHERE reference_year = 2024 AND sex IN ('male', 'female') AND age BETWEEN 5 AND 17
  AND psgc_match_status = 'matched'
GROUP BY city_mun_psgc_code;

CREATE OR REPLACE TEMPORARY VIEW ap1_gate_expected_schools AS
WITH rows AS (
  SELECT school_id, city_mun_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS active,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2024-25' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id, city_mun_psgc_code
)
SELECT city_mun_psgc_code, COUNT_IF(active = 1) AS active_public_school_count,
       COUNT_IF(active = 1 AND incomplete = 0) AS complete_enrollment_school_count
FROM rows GROUP BY city_mun_psgc_code;

CREATE OR REPLACE TEMPORARY VIEW ap1_gate_summary AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'),
type_refs AS (
  SELECT lgu_type, CAST(SUM(school_age_population) AS DOUBLE) / NULLIF(SUM(active_public_school_count), 0) AS ratio
  FROM c WHERE school_age_population IS NOT NULL GROUP BY lgu_type
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows,
  (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT_IF(city_mun_psgc_code IS NULL OR lgu_type IS NULL OR classification IS NULL) FROM c) AS null_required,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN ap1_gate_expected_population p USING (city_mun_psgc_code)
    WHERE c.school_age_population IS DISTINCT FROM p.school_age_population) AS population_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN ap1_gate_expected_schools s USING (city_mun_psgc_code)
    WHERE c.active_public_school_count IS DISTINCT FROM COALESCE(s.active_public_school_count, 0)
       OR c.complete_enrollment_school_count IS DISTINCT FROM COALESCE(s.complete_enrollment_school_count, 0)) AS school_mismatch,
  (SELECT COUNT(*) FROM c JOIN type_refs r USING (lgu_type)
    WHERE (c.national_same_type_ratio IS NULL) <> (r.ratio IS NULL)
       OR (c.national_same_type_ratio IS NOT NULL AND r.ratio IS NOT NULL
           AND ABS(c.national_same_type_ratio - r.ratio) > 1e-9)) AS pooled_reference_mismatch,
  (SELECT COUNT_IF((active_public_school_count = 0 AND school_age_population_per_public_school IS NOT NULL)
    OR (active_public_school_count > 0 AND school_age_population IS NOT NULL
      AND ABS(school_age_population_per_public_school - school_age_population * 1.0 / active_public_school_count) > 1e-9)) FROM c)
    AS ratio_mismatch,
  (SELECT COUNT_IF((coverage_pct IS NOT NULL AND (coverage_pct < 0 OR coverage_pct > 100))
    OR (coverage_pct < 90 AND classification <> 'Data Review')
    OR (outlier_flag AND classification <> 'Data Review')
    OR (quality_issue_reason IS NOT NULL AND classification <> 'Data Review')
    OR (quality_issue_reason IS NULL AND NOT outlier_flag AND relative_pressure > 1 AND classification <> 'Above Reference')
    OR (quality_issue_reason IS NULL AND NOT outlier_flag AND relative_pressure <= 1 AND classification <> 'At or Below Reference')) FROM c)
    AS classification_mismatch;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap1_school_provision', 'analytics', 'edu_access.06-analytics.ap1_school_provision_candidate',
       check_name, CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END, CAST(expected AS STRING),
       CAST(actual AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, expected_rows AS expected, rows AS actual FROM ap1_gate_summary
  UNION ALL SELECT 'key_unique', 0, duplicate_keys FROM ap1_gate_summary
  UNION ALL SELECT 'required_values_present', 0, null_required FROM ap1_gate_summary
  UNION ALL SELECT 'lgu_membership_reconciles', 0, lgu_mismatch FROM ap1_gate_summary
  UNION ALL SELECT 'population_reconciles', 0, population_mismatch FROM ap1_gate_summary
  UNION ALL SELECT 'schools_reconcile', 0, school_mismatch FROM ap1_gate_summary
  UNION ALL SELECT 'same_type_reference_is_pooled', 0, pooled_reference_mismatch FROM ap1_gate_summary
  UNION ALL SELECT 'ratio_arithmetic', 0, ratio_mismatch FROM ap1_gate_summary
  UNION ALL SELECT 'classification_valid', 0, classification_mismatch FROM ap1_gate_summary
) AS checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap1_school_provision: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap1_school_provision' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap1_school_provision USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap1_school_provision IS 'AP1 school-age population per active public school by regular LGU.';
ALTER TABLE edu_access.`06-analytics`.ap1_school_provision OWNER TO `reached-hq`;

