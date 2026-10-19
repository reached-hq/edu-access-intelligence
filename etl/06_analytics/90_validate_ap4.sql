-- ap4 publication gate; a failure leaves the last valid output unchanged.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

CREATE OR REPLACE TEMPORARY VIEW ap4_gate_expected AS
WITH school_totals AS (
  SELECT school_id, school_year, city_mun_psgc_code,
         CASE WHEN COUNT_IF(is_offered IS NULL OR (is_offered AND learner_count IS NULL)) > 0 THEN NULL
              ELSE SUM(CASE WHEN is_offered THEN learner_count ELSE 0 END) END AS learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year IN ('2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26')
    AND sector IN ('Public', 'Private', 'SUC/LUC') AND psgc_match_status = 'matched'
  GROUP BY school_id, school_year, city_mun_psgc_code
)
SELECT city_mun_psgc_code, school_year, CAST(COALESCE(SUM(learners), 0) AS BIGINT) AS enrollment
FROM school_totals GROUP BY city_mun_psgc_code, school_year;

CREATE OR REPLACE TEMPORARY VIEW ap4_gate_actual AS
SELECT city_mun_psgc_code, '2020-21' AS school_year, enrollment_2020_21 AS enrollment FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
UNION ALL SELECT city_mun_psgc_code, '2021-22', enrollment_2021_22 FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
UNION ALL SELECT city_mun_psgc_code, '2022-23', enrollment_2022_23 FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
UNION ALL SELECT city_mun_psgc_code, '2023-24', enrollment_2023_24 FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
UNION ALL SELECT city_mun_psgc_code, '2024-25', enrollment_2024_25 FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
UNION ALL SELECT city_mun_psgc_code, '2025-26', enrollment_2025_26 FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate;

CREATE OR REPLACE TEMPORARY VIEW ap4_gate_summary AS
WITH c AS (SELECT * FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate),
regular AS (SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular')
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM ap4_gate_actual a
    LEFT JOIN (SELECT school_year, TRUE AS has_data FROM edu_access.`05-gold`.fact_school_enrollment
      GROUP BY school_year) v ON v.school_year = a.school_year
    LEFT JOIN ap4_gate_expected e ON e.city_mun_psgc_code = a.city_mun_psgc_code AND e.school_year = a.school_year
    WHERE a.enrollment IS DISTINCT FROM CASE WHEN COALESCE(v.has_data, FALSE) THEN COALESCE(e.enrollment, 0) END)
    AS annual_enrollment_mismatch,
  (SELECT COALESCE(COUNT_IF((enrollment_2020_21 IS NULL OR enrollment_2020_21 = 0) AND pct_change IS NOT NULL
    OR (enrollment_2020_21 > 0 AND available_year_count = 6
      AND ABS(pct_change - (enrollment_2025_26 - enrollment_2020_21) * 1.0 / enrollment_2020_21) > 1e-9)), 0) FROM c)
    AS change_mismatch,
  (SELECT COALESCE(COUNT_IF((pct_change > 0 AND trend_direction <> 'Growing')
    OR (pct_change < 0 AND trend_direction <> 'Declining')
    OR (pct_change = 0 AND trend_direction <> 'Stable')
    OR (pct_change IS NULL AND trend_direction IS NOT NULL)), 0) FROM c) AS trend_mismatch;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap4_enrollment_trend', 'analytics', 'edu_access.06-analytics.ap4_enrollment_trend_candidate',
       check_name, CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END, CAST(expected AS STRING),
       CAST(actual AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, expected_rows AS expected, rows AS actual FROM ap4_gate_summary
  UNION ALL SELECT 'key_unique', 0, duplicate_keys FROM ap4_gate_summary
  UNION ALL SELECT 'lgu_membership_reconciles', 0, lgu_mismatch FROM ap4_gate_summary
  UNION ALL SELECT 'annual_enrollment_reconciles', 0, annual_enrollment_mismatch FROM ap4_gate_summary
  UNION ALL SELECT 'change_arithmetic', 0, change_mismatch FROM ap4_gate_summary
  UNION ALL SELECT 'trend_direction_valid', 0, trend_mismatch FROM ap4_gate_summary
) checks;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap4_enrollment_trend: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap4_enrollment_trend' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap4_enrollment_trend USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap4_enrollment_trend IS 'AP4 enrollment direction by regular LGU for SY 2020-21 through SY 2025-26.';
ALTER TABLE edu_access.`06-analytics`.ap4_enrollment_trend OWNER TO `reached-hq`;

