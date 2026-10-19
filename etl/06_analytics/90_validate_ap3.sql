-- ap3 publication gate; a failure leaves the last valid output unchanged.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap3_gate_expected AS
WITH active AS (
  SELECT school_id, MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS active
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id
), rows AS (
  SELECT e.city_mun_psgc_code, e.school_id, e.education_level_code, e.learner_count, e.annex_status,
         t.teacher_count,
         COALESCE(t.teacher_count > 0, FALSE) AS usable,
         COALESCE(e.annex_status = 'Annex/Extension School' AND t.teacher_count = 0, FALSE) AS zero_annex
  FROM edu_access.`05-gold`.fact_school_enrollment e
  JOIN active a ON a.school_id = e.school_id AND a.active = 1
  LEFT JOIN edu_access.`05-gold`.fact_school_teacher_capacity t
    ON t.school_id = e.school_id AND t.school_year = e.school_year AND t.education_level_code = e.education_level_code
  WHERE e.school_year = '2023-24' AND e.sector = 'Public' AND e.psgc_match_status = 'matched' AND e.is_offered
)
SELECT city_mun_psgc_code,
       CAST(COALESCE(SUM(CASE WHEN usable OR zero_annex THEN learner_count ELSE 0 END), 0) AS BIGINT) AS eligible_learners,
       CAST(COALESCE(SUM(CASE WHEN usable AND learner_count IS NOT NULL THEN teacher_count ELSE 0 END), 0) AS BIGINT)
         AS teachers
FROM rows GROUP BY city_mun_psgc_code;

CREATE OR REPLACE TEMPORARY VIEW ap3_gate_summary AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.ap3_teacher_pressure_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'),
type_refs AS (
  SELECT lgu_type, CAST(SUM(eligible_learners) AS DOUBLE) / NULLIF(SUM(approved_teacher_count), 0) AS ratio
  FROM c GROUP BY lgu_type
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN ap3_gate_expected e USING (city_mun_psgc_code)
    WHERE c.eligible_learners IS DISTINCT FROM COALESCE(e.eligible_learners, 0)
       OR c.approved_teacher_count IS DISTINCT FROM COALESCE(e.teachers, 0)) AS gold_mismatch,
  (SELECT COUNT(*) FROM c JOIN type_refs r USING (lgu_type)
    WHERE (c.national_same_type_ratio IS NULL) <> (r.ratio IS NULL)
       OR (c.national_same_type_ratio IS NOT NULL AND r.ratio IS NOT NULL
           AND ABS(c.national_same_type_ratio - r.ratio) > 1e-9)) AS pooled_reference_mismatch,
  (SELECT COUNT_IF((approved_teacher_count = 0 AND learners_per_teacher IS NOT NULL)
    OR (approved_teacher_count > 0
      AND ABS(learners_per_teacher - eligible_learners * 1.0 / approved_teacher_count) > 1e-9)) FROM c) AS ratio_mismatch,
  (SELECT COUNT_IF((school_coverage_pct IS NOT NULL AND (school_coverage_pct < 0 OR school_coverage_pct > 100))
    OR (learner_coverage_pct IS NOT NULL AND (learner_coverage_pct < 0 OR learner_coverage_pct > 100))
    OR ((school_coverage_pct < 90 OR learner_coverage_pct < 90 OR outlier_flag) AND classification <> 'Data Review')
    OR (quality_issue_reason IS NOT NULL AND classification <> 'Data Review')
    OR (quality_issue_reason IS NULL AND relative_pressure > 1 AND classification <> 'Above Reference')
    OR (quality_issue_reason IS NULL AND relative_pressure <= 1 AND classification <> 'At or Below Reference')) FROM c)
    AS classification_mismatch;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap3_teacher_pressure', 'analytics', 'edu_access.06-analytics.ap3_teacher_pressure_candidate',
       check_name, CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END, CAST(expected AS STRING),
       CAST(actual AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, expected_rows AS expected, rows AS actual FROM ap3_gate_summary
  UNION ALL SELECT 'key_unique', 0, duplicate_keys FROM ap3_gate_summary
  UNION ALL SELECT 'lgu_membership_reconciles', 0, lgu_mismatch FROM ap3_gate_summary
  UNION ALL SELECT 'numerator_denominator_reconcile', 0, gold_mismatch FROM ap3_gate_summary
  UNION ALL SELECT 'same_type_reference_is_pooled', 0, pooled_reference_mismatch FROM ap3_gate_summary
  UNION ALL SELECT 'ratio_arithmetic', 0, ratio_mismatch FROM ap3_gate_summary
  UNION ALL SELECT 'classification_valid', 0, classification_mismatch FROM ap3_gate_summary
) checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap3_teacher_pressure: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap3_teacher_pressure' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap3_teacher_pressure USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap3_teacher_pressure_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap3_teacher_pressure IS 'AP3 pooled teacher pressure by regular LGU, with same-type reference and quality gate.';
ALTER TABLE edu_access.`06-analytics`.ap3_teacher_pressure OWNER TO `reached-hq`;

