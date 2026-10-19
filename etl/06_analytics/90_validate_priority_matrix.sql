-- priority-matrix publication gate; a failure leaves the last valid output unchanged.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW priority_matrix_gate_summary AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular')
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT_IF(ap1_classification IS NULL OR ap2_classification IS NULL OR ap3_classification IS NULL
    OR enrollment_trend_status IS NULL) FROM c) AS missing_ap_outputs,
  (SELECT COUNT_IF(current_pressure_count NOT BETWEEN 0 AND 3) FROM c) AS invalid_pressure_count,
  (SELECT COUNT_IF(ap1_pressure_flag IS DISTINCT FROM (ap1_classification = 'Above Reference')
    OR ap2_pressure_flag IS DISTINCT FROM (ap2_classification = 'Above Reference')
    OR ap3_pressure_flag IS DISTINCT FROM (ap3_classification = 'Above Reference')) FROM c) AS flag_mismatch,
  (SELECT COUNT_IF(growing_enrollment_flag IS DISTINCT FROM COALESCE(enrollment_trend = 'Growing', FALSE)) FROM c)
    AS growth_flag_mismatch,
  (SELECT COUNT_IF(current_pressure_count <>
    CAST(ap1_pressure_flag AS INT) + CAST(ap2_pressure_flag AS INT) + CAST(ap3_pressure_flag AS INT)) FROM c)
    AS count_mismatch,
  (SELECT COUNT_IF(priority IS DISTINCT FROM CASE
      WHEN ap1_classification IS NULL OR ap2_classification IS NULL OR ap3_classification IS NULL
        OR ap1_classification = 'Data Review' OR ap2_classification = 'Data Review'
        OR ap3_classification = 'Data Review' THEN 'Data Review'
      WHEN current_pressure_count >= 2 AND growing_enrollment_flag THEN 'Priority 1'
      WHEN current_pressure_count >= 2 THEN 'Priority 2'
      WHEN current_pressure_count = 1 AND growing_enrollment_flag THEN 'Priority 3'
      WHEN current_pressure_count = 1 THEN 'Monitor'
      WHEN current_pressure_count = 0 AND growing_enrollment_flag THEN 'Monitor'
      ELSE 'Lower Priority' END) FROM c) AS priority_mismatch,
  (SELECT COUNT_IF((ap1_classification = 'Data Review' OR ap2_classification = 'Data Review'
    OR ap3_classification = 'Data Review') AND priority <> 'Data Review') FROM c) AS data_review_not_overriding;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'lgu_priority_matrix', 'analytics', 'edu_access.06-analytics.lgu_priority_matrix_candidate',
       check_name, CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END, CAST(expected AS STRING),
       CAST(actual AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, expected_rows AS expected, rows AS actual FROM priority_matrix_gate_summary
  UNION ALL SELECT 'key_unique', 0, duplicate_keys FROM priority_matrix_gate_summary
  UNION ALL SELECT 'lgu_membership_reconciles', 0, lgu_mismatch FROM priority_matrix_gate_summary
  UNION ALL SELECT 'all_ap_outputs_joined', 0, missing_ap_outputs FROM priority_matrix_gate_summary
  UNION ALL SELECT 'pressure_count_valid', 0, invalid_pressure_count FROM priority_matrix_gate_summary
  UNION ALL SELECT 'pressure_flags_match', 0, flag_mismatch FROM priority_matrix_gate_summary
  UNION ALL SELECT 'growth_flag_matches', 0, growth_flag_mismatch FROM priority_matrix_gate_summary
  UNION ALL SELECT 'pressure_count_matches', 0, count_mismatch FROM priority_matrix_gate_summary
  UNION ALL SELECT 'priority_logic_matches', 0, priority_mismatch FROM priority_matrix_gate_summary
  UNION ALL SELECT 'data_review_overrides', 0, data_review_not_overriding FROM priority_matrix_gate_summary
) checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for lgu_priority_matrix: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'lgu_priority_matrix' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.lgu_priority_matrix USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.lgu_priority_matrix IS 'Dashboard-ready LGU priority matrix from validated AP1 to AP4 outputs.';
ALTER TABLE edu_access.`06-analytics`.lgu_priority_matrix OWNER TO `reached-hq`;

