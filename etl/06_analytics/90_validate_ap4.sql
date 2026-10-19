-- ap4 publication gate; a failure leaves the last valid output unchanged.
-- gap checks: census population reconciles with Gold, gap, gap rate and public share arithmetic, and the change in
-- gap only where the geography is comparable. trend checks: annual enrollment, change, ±5% band and status.
-- the one-row summary is written once to a table named for this run and dropped after the checks are recorded:
-- read many times as a temporary view, the same pattern made Databricks SQL fail with INTERNAL_ERROR (c64e949, #202).
-- WARN: all-sector learners at schools not placed in a city or municipality (UNKNOWN or EXCLUDED) in SY 2020-21
-- and SY 2025-26. Counts only (PASS): the matched-learner share at each endpoint.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE analytics_gate_summary STRING;
SET VARIABLE analytics_gate_summary = '`edu_access`.`06-analytics`.`ap4_enrollment_trend_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE analytics_gate_owner_sql STRING;

CREATE OR REPLACE TABLE IDENTIFIER(session.analytics_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one ap4_enrollment_trend gate. The gate drops it once its checks are recorded in data_quality_results.' AS
WITH c AS (
  SELECT * FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate
), regular AS (
  SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'
), school_totals AS (
  SELECT school_id, school_year, city_mun_psgc_code, MIN(psgc_match_status) AS psgc_match_status,
         CASE WHEN COUNT_IF(is_offered IS NULL OR (is_offered AND learner_count IS NULL)) > 0 THEN NULL
              ELSE SUM(CASE WHEN is_offered THEN learner_count ELSE 0 END) END AS learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year IN ('2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26')
    AND sector IN ('Public', 'Private', 'SUC/LUC')
  GROUP BY school_id, school_year, city_mun_psgc_code
), expected AS (
  SELECT city_mun_psgc_code, school_year, CAST(COALESCE(SUM(learners), 0) AS BIGINT) AS enrollment
  FROM school_totals WHERE psgc_match_status = 'matched' GROUP BY city_mun_psgc_code, school_year
), available AS (
  SELECT school_year, TRUE AS has_data FROM edu_access.`05-gold`.fact_school_enrollment GROUP BY school_year
), shares AS (
  SELECT school_year,
         CAST(100.0 * SUM(CASE WHEN psgc_match_status = 'matched' THEN learners ELSE 0 END)
           / NULLIF(SUM(learners), 0) AS DOUBLE) AS matched_share,
         COALESCE(SUM(CASE WHEN psgc_match_status <> 'matched' THEN learners END), 0) AS unplaced_learners
  FROM school_totals GROUP BY school_year
), expected_population AS (
  SELECT city_mun_psgc_code,
         CAST(SUM(CASE WHEN reference_year = 2020 THEN population END) AS BIGINT) AS pop_2020,
         CAST(SUM(CASE WHEN reference_year = 2024 THEN population END) AS BIGINT) AS pop_2024
  FROM edu_access.`05-gold`.fact_city_school_age_population
  WHERE reference_year IN (2020, 2024) AND sex IN ('male', 'female') AND age BETWEEN 5 AND 17
    AND psgc_match_status = 'matched'
  GROUP BY city_mun_psgc_code
), actual AS (
  SELECT city_mun_psgc_code, '2020-21' AS school_year, enrollment_2020_21 AS enrollment FROM c
  UNION ALL SELECT city_mun_psgc_code, '2021-22', enrollment_2021_22 FROM c
  UNION ALL SELECT city_mun_psgc_code, '2022-23', enrollment_2022_23 FROM c
  UNION ALL SELECT city_mun_psgc_code, '2023-24', enrollment_2023_24 FROM c
  UNION ALL SELECT city_mun_psgc_code, '2024-25', enrollment_2024_25 FROM c
  UNION ALL SELECT city_mun_psgc_code, '2025-26', enrollment_2025_26 FROM c
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows, (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM actual a
    LEFT JOIN available v ON v.school_year = a.school_year
    LEFT JOIN expected e ON e.city_mun_psgc_code = a.city_mun_psgc_code AND e.school_year = a.school_year
    WHERE a.enrollment IS DISTINCT FROM CASE WHEN COALESCE(v.has_data, FALSE) THEN COALESCE(e.enrollment, 0) END)
    AS annual_enrollment_mismatch,
  (SELECT COUNT(*) FROM c
    LEFT JOIN shares f ON f.school_year = '2020-21'
    LEFT JOIN shares t ON t.school_year = '2025-26'
    WHERE c.matched_learner_share_2020_21_pct IS DISTINCT FROM f.matched_share
       OR c.matched_learner_share_2025_26_pct IS DISTINCT FROM t.matched_share) AS matched_share_mismatch,
  (SELECT COALESCE(COUNT_IF(((enrollment_2020_21 IS NULL OR enrollment_2020_21 = 0) AND pct_change IS NOT NULL)
    OR (enrollment_2020_21 > 0 AND available_year_count = 6
      AND ABS(pct_change - (enrollment_2025_26 - enrollment_2020_21) * 1.0 / enrollment_2020_21) > 1e-9)), 0) FROM c)
    AS change_mismatch,
  (SELECT COALESCE(COUNT_IF((pct_change > 0.05 AND trend_direction IS DISTINCT FROM 'Growing')
    OR (pct_change < -0.05 AND trend_direction IS DISTINCT FROM 'Declining')
    OR (ABS(pct_change) <= 0.05 AND trend_direction IS DISTINCT FROM 'Stable')
    OR (pct_change IS NULL AND trend_direction IS NOT NULL)), 0) FROM c) AS trend_mismatch,
  (SELECT COALESCE(COUNT_IF((trend_status = 'Complete') <> COALESCE(available_year_count = 6
    AND enrollment_2020_21 > 0 AND incomplete_school_year_rows = 0
    AND ABS(matched_learner_share_2025_26_pct - matched_learner_share_2020_21_pct) <= 2, FALSE)), 0) FROM c)
    AS status_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_population p USING (city_mun_psgc_code)
    WHERE c.school_age_population_2020 IS DISTINCT FROM p.pop_2020
       OR c.school_age_population_2024 IS DISTINCT FROM p.pop_2024) AS population_mismatch,
  (SELECT COALESCE(COUNT_IF(gap_2020 IS DISTINCT FROM school_age_population_2020 - enrollment_2020_21
    OR gap_2024 IS DISTINCT FROM school_age_population_2024 - enrollment_2024_25
    OR (school_age_population_2020 > 0 AND ABS(gap_rate_2020_pct - 100.0 * gap_2020 / school_age_population_2020) > 1e-9)
    OR (school_age_population_2024 > 0 AND ABS(gap_rate_2024_pct - 100.0 * gap_2024 / school_age_population_2024) > 1e-9)
    OR (enrollment_2024_25 > 0
      AND ABS(public_school_share_2024_25_pct - 100.0 * public_enrollment_2024_25 / enrollment_2024_25) > 1e-9)
    OR gap_change IS DISTINCT FROM CASE WHEN is_2020_2024_geography_comparable THEN gap_2024 - gap_2020 END), 0) FROM c)
    AS gap_mismatch,
  (SELECT COALESCE(MAX(unplaced_learners), 0) FROM shares WHERE school_year = '2020-21') AS unplaced_learners_2020_21,
  (SELECT COALESCE(MAX(unplaced_learners), 0) FROM shares WHERE school_year = '2025-26') AS unplaced_learners_2025_26,
  (SELECT MAX(matched_share) FROM shares WHERE school_year = '2020-21') AS matched_share_2020_21,
  (SELECT MAX(matched_share) FROM shares WHERE school_year = '2025-26') AS matched_share_2025_26;
SET VARIABLE analytics_gate_owner_sql = 'ALTER TABLE ' || session.analytics_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE analytics_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap4_enrollment_trend', 'analytics', 'edu_access.06-analytics.ap4_enrollment_trend_candidate',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, CASE WHEN rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(rows AS STRING) AS actual FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'lgu_membership_reconciles', CASE WHEN lgu_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(lgu_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'annual_enrollment_reconciles', CASE WHEN annual_enrollment_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(annual_enrollment_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'census_population_reconciles', CASE WHEN population_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(population_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'gap_arithmetic', CASE WHEN gap_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(gap_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'matched_share_reconciles', CASE WHEN matched_share_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(matched_share_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'change_arithmetic', CASE WHEN change_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(change_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'trend_direction_valid', CASE WHEN trend_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(trend_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'trend_status_valid', CASE WHEN status_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(status_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'unplaced_learners_2020_21', CASE WHEN unplaced_learners_2020_21 = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unplaced_learners_2020_21 AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'unplaced_learners_2025_26', CASE WHEN unplaced_learners_2025_26 = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unplaced_learners_2025_26 AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'matched_learner_share_2020_21_pct', 'PASS', CAST(NULL AS STRING), CAST(matched_share_2020_21 AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'matched_learner_share_2025_26_pct', 'PASS', CAST(NULL AS STRING), CAST(matched_share_2025_26 AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
) AS checks;

-- Every check is recorded, so the summary is no longer needed, whether the gate passes or fails.
DROP TABLE IF EXISTS IDENTIFIER(session.analytics_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap4_enrollment_trend: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap4_enrollment_trend' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap4_enrollment_trend USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap4_enrollment_trend_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap4_enrollment_trend IS 'AP4 school-age population and enrollment gap (2020, 2024) and enrollment direction (SY 2020-21 to 2025-26) by regular LGU. Context only under D-057.';
ALTER TABLE edu_access.`06-analytics`.ap4_enrollment_trend OWNER TO `reached-hq`;
