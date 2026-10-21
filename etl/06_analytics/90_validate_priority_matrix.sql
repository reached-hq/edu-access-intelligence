-- D-061 publication gate for the lgu planning-priority matrix.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE analytics_gate_summary STRING;
SET VARIABLE analytics_gate_summary = '`edu_access`.`06-analytics`.`lgu_priority_matrix_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE analytics_gate_owner_sql STRING;

CREATE OR REPLACE TABLE IDENTIFIER(session.analytics_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one D-061 gate.' AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'),
expected_joined AS (
  SELECT l.city_mun_psgc_code, COALESCE(b.is_assessed, FALSE) AS ap2_assessed,
    COALESCE(c.is_assessed, FALSE) AS ap3_assessed,
    CAST(CASE WHEN b.is_assessed AND b.congested_school_count > 0 THEN 1 ELSE 0 END AS INT) AS classroom_pressure_flag,
    CAST(CASE WHEN c.is_assessed AND (c.es_benchmark_status = 'above historical study reference'
      OR c.jhs_benchmark_status = 'above derived deployment comparison'
      OR c.shs_benchmark_status = 'above derived deployment comparison') THEN 1 ELSE 0 END AS INT) AS teacher_pressure_flag,
    COALESCE(b.learners_in_congested_schools, 0) AS ap2_affected_learners,
    CAST((CASE WHEN c.es_benchmark_status = 'above historical study reference' THEN c.es_eligible_learners ELSE 0 END)
      + (CASE WHEN c.jhs_benchmark_status = 'above derived deployment comparison' THEN c.jhs_eligible_learners ELSE 0 END)
      + (CASE WHEN c.shs_benchmark_status = 'above derived deployment comparison' THEN c.shs_eligible_learners ELSE 0 END) AS BIGINT)
      AS ap3_affected_learners,
    CAST((CASE WHEN c.es_benchmark_status = 'above historical study reference' THEN 1 ELSE 0 END)
      + (CASE WHEN c.jhs_benchmark_status = 'above derived deployment comparison' THEN 1 ELSE 0 END)
      + (CASE WHEN c.shs_benchmark_status = 'above derived deployment comparison' THEN 1 ELSE 0 END) AS INT)
      AS ap3_pressured_level_count,
    d.public_enrollment_change_first_to_latest AS ap4_public_enrollment_change,
    100 * d.public_enrollment_change_pct_first_to_latest AS ap4_public_enrollment_change_pct,
    CASE WHEN d.public_enrollment_trend = 'increasing' THEN TRUE
         WHEN d.public_enrollment_trend IN ('decreasing', 'no change') THEN FALSE END AS growing_enrollment
  FROM regular AS l
  LEFT JOIN edu_access.`06-analytics`.ap2_classroom_pressure AS b USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap3_teacher_pressure AS c USING (city_mun_psgc_code)
  LEFT JOIN edu_access.`06-analytics`.ap4_enrollment_trend AS d
    ON d.city_mun_psgc_code = l.city_mun_psgc_code AND d.school_year = d.latest_school_year
), expected_grouped AS (
  SELECT *, classroom_pressure_flag + teacher_pressure_flag AS current_pressure_count,
    GREATEST(ap2_affected_learners, ap3_affected_learners) AS priority_affected_learners,
    CASE WHEN NOT ap2_assessed OR NOT ap3_assessed OR growing_enrollment IS NULL THEN 'Data review'
         WHEN classroom_pressure_flag + teacher_pressure_flag = 2 AND growing_enrollment THEN 'Priority 1'
         WHEN classroom_pressure_flag + teacher_pressure_flag = 2
           OR (classroom_pressure_flag + teacher_pressure_flag = 1 AND growing_enrollment) THEN 'Priority 2'
         WHEN classroom_pressure_flag + teacher_pressure_flag = 1 THEN 'Priority 3'
         WHEN growing_enrollment THEN 'Monitor' ELSE 'No current pressure identified' END AS priority_category
  FROM expected_joined
), expected AS (
  SELECT *, ROW_NUMBER() OVER (
    ORDER BY CASE priority_category WHEN 'Priority 1' THEN 1 WHEN 'Priority 2' THEN 2 WHEN 'Priority 3' THEN 3
                                    WHEN 'Monitor' THEN 4 WHEN 'No current pressure identified' THEN 5 ELSE 6 END,
      current_pressure_count DESC, priority_affected_learners DESC, ap2_affected_learners DESC,
      ap3_pressured_level_count DESC, ap4_public_enrollment_change DESC,
      ap4_public_enrollment_change_pct DESC, city_mun_psgc_code) AS priority_order
  FROM expected_grouped
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT_IF(current_pressure_count <> classroom_pressure_flag + teacher_pressure_flag
      OR classroom_pressure_flag NOT IN (0, 1) OR teacher_pressure_flag NOT IN (0, 1)
      OR priority_affected_learners <> GREATEST(COALESCE(ap2_affected_learners, 0), COALESCE(ap3_affected_learners, 0))
      OR priority_category IS DISTINCT FROM
        CASE WHEN NOT COALESCE(ap2_assessed, FALSE) OR NOT COALESCE(ap3_assessed, FALSE)
               OR growing_enrollment IS NULL THEN 'Data review'
             WHEN current_pressure_count = 2 AND growing_enrollment THEN 'Priority 1'
             WHEN current_pressure_count = 2 OR (current_pressure_count = 1 AND growing_enrollment) THEN 'Priority 2'
             WHEN current_pressure_count = 1 THEN 'Priority 3'
             WHEN growing_enrollment THEN 'Monitor'
             ELSE 'No current pressure identified' END
      OR rule_version <> 'D-061') FROM c) AS rule_mismatch,
  (SELECT COUNT(*) FROM c JOIN expected AS e USING (city_mun_psgc_code)
    WHERE c.classroom_pressure_flag IS DISTINCT FROM e.classroom_pressure_flag
       OR c.teacher_pressure_flag IS DISTINCT FROM e.teacher_pressure_flag
       OR c.growing_enrollment IS DISTINCT FROM e.growing_enrollment
       OR c.current_pressure_count IS DISTINCT FROM e.current_pressure_count
       OR c.priority_affected_learners IS DISTINCT FROM e.priority_affected_learners
       OR c.priority_category IS DISTINCT FROM e.priority_category) AS source_reconciliation_mismatch,
  (SELECT COUNT(*) FROM c JOIN expected AS e USING (city_mun_psgc_code)
    WHERE c.priority_order IS DISTINCT FROM e.priority_order) AS ordering_mismatch,
  (SELECT COUNT(*) - COUNT(DISTINCT priority_order) FROM c) AS duplicate_orders,
  (SELECT COUNT_IF(priority_category = 'Data review') FROM c) AS data_review_lgus,
  (SELECT COUNT_IF(priority_category = 'Priority 1') FROM c) AS priority_1_lgus;
SET VARIABLE analytics_gate_owner_sql = 'ALTER TABLE ' || session.analytics_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE analytics_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'lgu_priority_matrix', 'analytics', 'edu_access.06-analytics.lgu_priority_matrix_candidate',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, CASE WHEN rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(rows AS STRING) AS actual FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'lgu_membership_reconciles', CASE WHEN lgu_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(lgu_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'priority_rule_follows_d061', CASE WHEN rule_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(rule_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'priority_inputs_reconcile_to_ap2_ap3_ap4', CASE WHEN source_reconciliation_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(source_reconciliation_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'priority_order_recomputed', CASE WHEN ordering_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(ordering_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'priority_order_unique', CASE WHEN duplicate_orders = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_orders AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'data_review_lgus', 'PASS', NULL, CAST(data_review_lgus AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'priority_1_lgus', 'PASS', NULL, CAST(priority_1_lgus AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
) AS checks;

DROP TABLE IF EXISTS IDENTIFIER(session.analytics_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for lgu_priority_matrix: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'lgu_priority_matrix' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.lgu_priority_matrix USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.lgu_priority_matrix_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.lgu_priority_matrix IS 'LGU planning-priority categories from separate AP2 and AP3 pressure flags and AP4 public-enrollment growth under D-061.';
ALTER TABLE edu_access.`06-analytics`.lgu_priority_matrix OWNER TO `reached-hq`;
