-- ap2 publication gate; a failure leaves the last valid output unchanged.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap2_gate_expected AS
WITH enrollment AS (
  SELECT school_id, city_mun_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS active,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete,
         SUM(CASE WHEN is_offered AND learner_count IS NOT NULL THEN learner_count ELSE 0 END) AS learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id, city_mun_psgc_code
), joined AS (
  SELECT e.*, c.instructional_classrooms_total AS rooms
  FROM enrollment e LEFT JOIN edu_access.`05-gold`.fact_school_classroom_capacity c
    ON c.school_id = e.school_id AND c.school_year = '2023-24'
)
SELECT city_mun_psgc_code,
       CAST(COALESCE(SUM(CASE WHEN active = 1 AND incomplete = 0 AND rooms > 0 THEN learners ELSE 0 END), 0) AS BIGINT)
         AS eligible_learners,
       CAST(COALESCE(SUM(CASE WHEN active = 1 AND incomplete = 0 AND rooms > 0 THEN rooms ELSE 0 END), 0) AS BIGINT)
         AS rooms
FROM joined GROUP BY city_mun_psgc_code;

CREATE OR REPLACE TEMPORARY VIEW ap2_gate_summary AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.ap2_classroom_pressure_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'),
type_refs AS (
  SELECT lgu_type, CAST(SUM(eligible_learners) AS DOUBLE) / NULLIF(SUM(reported_instructional_classrooms), 0) AS ratio
  FROM c GROUP BY lgu_type
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN ap2_gate_expected e USING (city_mun_psgc_code)
    WHERE c.eligible_learners IS DISTINCT FROM COALESCE(e.eligible_learners, 0)
       OR c.reported_instructional_classrooms IS DISTINCT FROM COALESCE(e.rooms, 0)) AS gold_mismatch,
  (SELECT COUNT(*) FROM c JOIN type_refs r USING (lgu_type)
    WHERE (c.national_same_type_ratio IS NULL) <> (r.ratio IS NULL)
       OR (c.national_same_type_ratio IS NOT NULL AND r.ratio IS NOT NULL
           AND ABS(c.national_same_type_ratio - r.ratio) > 1e-9)) AS pooled_reference_mismatch,
  (SELECT COUNT_IF((reported_instructional_classrooms = 0 AND learners_per_classroom IS NOT NULL)
    OR (reported_instructional_classrooms > 0
      AND ABS(learners_per_classroom - eligible_learners * 1.0 / reported_instructional_classrooms) > 1e-9)) FROM c) AS ratio_mismatch,
  (SELECT COUNT_IF((school_coverage_pct IS NOT NULL AND (school_coverage_pct < 0 OR school_coverage_pct > 100))
    OR (learner_coverage_pct IS NOT NULL AND (learner_coverage_pct < 0 OR learner_coverage_pct > 100))
    OR ((school_coverage_pct < 90 OR learner_coverage_pct < 90 OR outlier_flag) AND classification <> 'Data Review')
    OR (quality_issue_reason IS NOT NULL AND classification <> 'Data Review')
    OR (quality_issue_reason IS NULL AND relative_pressure > 1 AND classification <> 'Above Reference')
    OR (quality_issue_reason IS NULL AND relative_pressure <= 1 AND classification <> 'At or Below Reference')) FROM c)
    AS classification_mismatch;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap2_classroom_pressure', 'analytics', 'edu_access.06-analytics.ap2_classroom_pressure_candidate',
       check_name, CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END, CAST(expected AS STRING),
       CAST(actual AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, expected_rows AS expected, rows AS actual FROM ap2_gate_summary
  UNION ALL SELECT 'key_unique', 0, duplicate_keys FROM ap2_gate_summary
  UNION ALL SELECT 'lgu_membership_reconciles', 0, lgu_mismatch FROM ap2_gate_summary
  UNION ALL SELECT 'numerator_denominator_reconcile', 0, gold_mismatch FROM ap2_gate_summary
  UNION ALL SELECT 'same_type_reference_is_pooled', 0, pooled_reference_mismatch FROM ap2_gate_summary
  UNION ALL SELECT 'ratio_arithmetic', 0, ratio_mismatch FROM ap2_gate_summary
  UNION ALL SELECT 'classification_valid', 0, classification_mismatch FROM ap2_gate_summary
) checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap2_classroom_pressure: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap2_classroom_pressure' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap2_classroom_pressure USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap2_classroom_pressure_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap2_classroom_pressure IS 'AP2 classroom pressure by regular LGU, with same-type pooled reference and quality gate.';
ALTER TABLE edu_access.`06-analytics`.ap2_classroom_pressure OWNER TO `reached-hq`;

