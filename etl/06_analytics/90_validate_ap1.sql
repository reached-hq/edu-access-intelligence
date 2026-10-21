-- ap1 publication gate; a failure leaves the last valid output unchanged.
-- the one-row summary is written once to a table named for this run and dropped after the checks are recorded:
-- read many times as a temporary view, the same pattern made Databricks SQL fail with INTERNAL_ERROR (c64e949, #202).
-- FAIL: rows, keys or LGUs that differ from dim_city_municipality, school counts, enrollment or population that
-- differ from a recount from Gold, wrong ratio or coverage arithmetic, an assessment that does not follow the 90%
-- gate, barangay or JHS presence counts that differ from a recount from Gold and dim_barangay, or a reference value
-- or DO 40 status that does not follow D-061, or spacing counts that differ from a recount on a coarser grid
-- (0.05 degrees, so the build's 0.02-degree pairing is checked by a different pairing), or next-level (RA 12321 3 km)
-- counts that differ from the same 0.05-degree recount (the build pairs on 0.03 degrees). AP1 is descriptive and
-- publishes no percentile or priority flag. The D-061 checks use names already in config/quality_attributes.yml:
-- counts_reconcile (presence screen), derived_values_reconcile (spacing and next-level screens),
-- assessment_status_valid (references and statuses).
-- WARN: active public schools, learners and school-age population not placed in a city or municipality.
DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE analytics_gate_summary STRING;
SET VARIABLE analytics_gate_summary = '`edu_access`.`06-analytics`.`ap1_school_provision_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE analytics_gate_owner_sql STRING;

CREATE OR REPLACE TABLE IDENTIFIER(session.analytics_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one ap1_school_provision gate. The gate drops it once its checks are recorded in data_quality_results.' AS
WITH c AS (
  SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate
), regular AS (
  SELECT * FROM edu_access.`05-gold`.dim_city_municipality WHERE member_type = 'regular'
), school_rows AS (
  SELECT school_id, city_mun_psgc_code, MIN(barangay_psgc_code) AS barangay_psgc_code,
         MIN(psgc_match_status) AS psgc_match_status,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS active,
         MAX(CASE WHEN education_level_code = 'ES' AND is_offered THEN 1 ELSE 0 END) AS es,
         MAX(CASE WHEN education_level_code = 'JHS' AND is_offered THEN 1 ELSE 0 END) AS jhs,
         MAX(CASE WHEN education_level_code = 'SHS' AND is_offered THEN 1 ELSE 0 END) AS shs,
         SUM(CASE WHEN education_level_code = 'ES' AND is_offered THEN COALESCE(learner_count, 0) ELSE 0 END) AS es_learners,
         SUM(CASE WHEN education_level_code = 'JHS' AND is_offered THEN COALESCE(learner_count, 0) ELSE 0 END) AS jhs_learners,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete,
         COUNT_IF(is_offered) > 0 AND COUNT_IF(is_offered AND learner_count IS NOT NULL) = 0 AS blank,
         MAX(CASE WHEN annex_status = 'Annex/Extension School' THEN 1 ELSE 0 END) AS annex,
         SUM(CASE WHEN is_offered AND learner_count IS NOT NULL THEN learner_count ELSE 0 END) AS learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public'
  GROUP BY school_id, city_mun_psgc_code
), expected_schools AS (
  SELECT city_mun_psgc_code,
         COUNT_IF(active = 1) AS active_schools,
         COUNT_IF(active = 1 AND annex = 1) AS annex_schools,
         COUNT_IF(active = 1 AND incomplete = 0) AS complete_schools,
         COUNT_IF(active = 1 AND incomplete > 0) AS incomplete_schools,
         COUNT_IF(blank) AS blank_schools,
         SUM(CASE WHEN active = 1 AND incomplete = 0 THEN learners ELSE 0 END) AS enrollment
  FROM school_rows WHERE psgc_match_status = 'matched' GROUP BY city_mun_psgc_code
), expected_served AS (
  SELECT DISTINCT barangay_psgc_code FROM school_rows WHERE psgc_match_status = 'matched' AND active = 1 AND es = 1
), expected_barangays AS (
  SELECT b.city_mun_psgc_code, COUNT(*) AS barangays, COUNT(s.barangay_psgc_code) AS served
  FROM edu_access.`05-gold`.dim_barangay b
  LEFT JOIN expected_served s ON s.barangay_psgc_code = b.barangay_psgc_code
  WHERE b.member_type = 'regular'
  GROUP BY b.city_mun_psgc_code
), expected_presence AS (
  SELECT city_mun_psgc_code,
         COUNT_IF(active = 1 AND es = 1 AND barangay_psgc_code = city_mun_psgc_code || '-UNKNOWN') AS unknown_es,
         COUNT_IF(active = 1 AND jhs = 1) AS jhs_schools,
         COUNT_IF(active = 1 AND es = 1) AS es_schools
  FROM school_rows WHERE psgc_match_status = 'matched' GROUP BY city_mun_psgc_code
), expected_points AS (
  SELECT s.school_id, s.city_mun_psgc_code, s.learners, l.latitude, l.longitude,
         CASE l.urban_rural WHEN 'R' THEN 2.0 WHEN 'U' THEN 1.0 END AS km,
         CAST(FLOOR(l.latitude / 0.05) AS BIGINT) AS gy, CAST(FLOOR(l.longitude / 0.05) AS BIGINT) AS gx
  FROM school_rows s JOIN edu_access.`05-gold`.dim_school_location l USING (school_id)
  WHERE s.psgc_match_status = 'matched' AND s.active = 1 AND s.es = 1 AND l.is_location_usable
), expected_close AS (
  SELECT DISTINCT a.school_id
  FROM expected_points a
  CROSS JOIN (VALUES (-1), (0), (1)) AS dy(d)
  CROSS JOIN (VALUES (-1), (0), (1)) AS dx(d)
  JOIN expected_points b ON b.gy = a.gy + dy.d AND b.gx = a.gx + dx.d AND b.school_id <> a.school_id
  WHERE a.km IS NOT NULL
    AND 6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
      + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude)) * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2)))
      <= a.km
), expected_spacing AS (
  SELECT p.city_mun_psgc_code,
         COUNT_IF(p.km IS NOT NULL) AS tested,
         COUNT_IF(p.km IS NOT NULL AND c.school_id IS NULL) AS isolated,
         SUM(CASE WHEN p.km IS NOT NULL AND c.school_id IS NULL THEN p.learners ELSE 0 END) AS isolated_learners
  FROM expected_points p LEFT JOIN expected_close c USING (school_id)
  GROUP BY p.city_mun_psgc_code
), expected_located AS (
  SELECT s.school_id, s.city_mun_psgc_code, s.es, s.jhs, s.shs, s.es_learners, s.jhs_learners, l.latitude, l.longitude,
         CAST(FLOOR(l.latitude / 0.05) AS BIGINT) AS gy, CAST(FLOOR(l.longitude / 0.05) AS BIGINT) AS gx
  FROM school_rows s JOIN edu_access.`05-gold`.dim_school_location l USING (school_id)
  WHERE s.psgc_match_status = 'matched' AND s.active = 1 AND l.is_location_usable
), expected_jhs_near AS (
  SELECT DISTINCT a.school_id
  FROM expected_located a
  CROSS JOIN (VALUES (-1), (0), (1)) AS dy(d)
  CROSS JOIN (VALUES (-1), (0), (1)) AS dx(d)
  JOIN expected_located b ON b.gy = a.gy + dy.d AND b.gx = a.gx + dx.d
  WHERE b.jhs = 1 AND 6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
      + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude)) * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2))) <= 3.0
), expected_shs_near AS (
  SELECT DISTINCT a.school_id
  FROM expected_located a
  CROSS JOIN (VALUES (-1), (0), (1)) AS dy(d)
  CROSS JOIN (VALUES (-1), (0), (1)) AS dx(d)
  JOIN expected_located b ON b.gy = a.gy + dy.d AND b.gx = a.gx + dx.d
  WHERE b.shs = 1 AND 6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
      + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude)) * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2))) <= 3.0
), expected_next AS (
  SELECT p.city_mun_psgc_code,
         COUNT_IF(p.es = 1) AS es_tested,
         COUNT_IF(p.es = 1 AND j.school_id IS NULL) AS es_without,
         SUM(CASE WHEN p.es = 1 AND j.school_id IS NULL THEN p.es_learners ELSE 0 END) AS es_without_learners,
         COUNT_IF(p.jhs = 1) AS jhs_tested,
         COUNT_IF(p.jhs = 1 AND h.school_id IS NULL) AS jhs_without,
         SUM(CASE WHEN p.jhs = 1 AND h.school_id IS NULL THEN p.jhs_learners ELSE 0 END) AS jhs_without_learners
  FROM expected_located p
  LEFT JOIN expected_jhs_near j USING (school_id)
  LEFT JOIN expected_shs_near h USING (school_id)
  GROUP BY p.city_mun_psgc_code
), expected_population AS (
  SELECT city_mun_psgc_code, CAST(SUM(population) AS BIGINT) AS school_age_population
  FROM edu_access.`05-gold`.fact_city_school_age_population
  WHERE reference_year = 2024 AND sex IN ('male', 'female') AND age BETWEEN 5 AND 17 AND psgc_match_status = 'matched'
  GROUP BY city_mun_psgc_code
)
SELECT
  (SELECT COUNT(*) FROM c) AS rows,
  (SELECT COUNT(*) FROM regular) AS expected_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT city_mun_psgc_code) FROM c) AS duplicate_keys,
  (SELECT COUNT(*) FROM c FULL OUTER JOIN regular USING (city_mun_psgc_code)
    WHERE c.city_mun_psgc_code IS NULL OR regular.city_mun_psgc_code IS NULL) AS lgu_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_schools s USING (city_mun_psgc_code)
    WHERE c.active_public_school_count IS DISTINCT FROM COALESCE(s.active_schools, 0)
       OR c.annex_school_count IS DISTINCT FROM COALESCE(s.annex_schools, 0)
       OR c.complete_enrollment_school_count IS DISTINCT FROM COALESCE(s.complete_schools, 0)
       OR c.incomplete_enrollment_school_count IS DISTINCT FROM COALESCE(s.incomplete_schools, 0)
       OR c.blank_enrollment_school_count IS DISTINCT FROM COALESCE(s.blank_schools, 0)
       OR c.public_school_enrollment IS DISTINCT FROM CAST(COALESCE(s.enrollment, 0) AS BIGINT)) AS school_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_population p USING (city_mun_psgc_code)
    WHERE c.school_age_population IS DISTINCT FROM p.school_age_population) AS population_mismatch,
  (SELECT COALESCE(COUNT_IF(
       (complete_enrollment_school_count = 0 AND learners_per_public_school IS NOT NULL)
    OR (complete_enrollment_school_count > 0
      AND ABS(learners_per_public_school - public_school_enrollment * 1.0 / complete_enrollment_school_count) > 1e-9)
    OR (active_public_school_count = 0 AND school_age_population_per_public_school IS NOT NULL)
    OR (active_public_school_count > 0 AND school_age_population IS NOT NULL
      AND ABS(school_age_population_per_public_school - school_age_population * 1.0 / active_public_school_count) > 1e-9)
    OR (active_public_school_count + blank_enrollment_school_count > 0
      AND ABS(coverage_pct - 100.0 * complete_enrollment_school_count
        / (active_public_school_count + blank_enrollment_school_count)) > 1e-9)), 0) FROM c) AS arithmetic_mismatch,
  (SELECT COALESCE(COUNT_IF(is_assessed IS DISTINCT FROM (not_assessed_reason IS NULL)
    OR is_assessed IS DISTINCT FROM COALESCE(active_public_school_count > 0 AND learners_per_public_school IS NOT NULL
      AND coverage_pct >= 90, FALSE)), 0) FROM c) AS assessment_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_barangays b USING (city_mun_psgc_code)
    LEFT JOIN expected_presence p USING (city_mun_psgc_code)
    WHERE c.regular_barangay_count IS DISTINCT FROM COALESCE(b.barangays, 0)
       OR c.barangays_with_public_es IS DISTINCT FROM COALESCE(b.served, 0)
       OR c.barangays_without_public_es IS DISTINCT FROM COALESCE(b.barangays, 0) - COALESCE(b.served, 0)
       OR c.unknown_barangay_es_school_count IS DISTINCT FROM COALESCE(p.unknown_es, 0)
       OR c.public_jhs_school_count IS DISTINCT FROM COALESCE(p.jhs_schools, 0)
       OR (c.regular_barangay_count = 0 AND c.barangays_without_public_es_pct IS NOT NULL)
       OR (c.regular_barangay_count > 0 AND ABS(c.barangays_without_public_es_pct
         - 100.0 * c.barangays_without_public_es / c.regular_barangay_count) > 1e-9)
       OR c.es_count_is_upper_bound IS DISTINCT FROM
         (c.barangays_without_public_es > 0 AND c.unknown_barangay_es_school_count > 0)) AS presence_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_presence p USING (city_mun_psgc_code)
    LEFT JOIN expected_spacing x USING (city_mun_psgc_code)
    WHERE c.active_public_es_school_count IS DISTINCT FROM COALESCE(p.es_schools, 0)
       OR c.spacing_tested_es_school_count IS DISTINCT FROM COALESCE(x.tested, 0)
       OR c.isolated_es_school_count IS DISTINCT FROM COALESCE(x.isolated, 0)
       OR c.learners_in_isolated_es_schools IS DISTINCT FROM CAST(COALESCE(x.isolated_learners, 0) AS BIGINT)
       OR (c.active_public_es_school_count = 0 AND c.spacing_coverage_pct IS NOT NULL)
       OR (c.active_public_es_school_count > 0 AND ABS(c.spacing_coverage_pct
         - 100.0 * c.spacing_tested_es_school_count / c.active_public_es_school_count) > 1e-9)) AS spacing_mismatch,
  (SELECT COUNT(*) FROM c LEFT JOIN expected_next x USING (city_mun_psgc_code)
    WHERE c.next_level_tested_es_school_count IS DISTINCT FROM COALESCE(x.es_tested, 0)
       OR c.es_schools_without_jhs_within_3km IS DISTINCT FROM COALESCE(x.es_without, 0)
       OR c.es_learners_without_jhs_within_3km IS DISTINCT FROM CAST(COALESCE(x.es_without_learners, 0) AS BIGINT)
       OR c.next_level_tested_jhs_school_count IS DISTINCT FROM COALESCE(x.jhs_tested, 0)
       OR c.jhs_schools_without_shs_within_3km IS DISTINCT FROM COALESCE(x.jhs_without, 0)
       OR c.jhs_learners_without_shs_within_3km IS DISTINCT FROM CAST(COALESCE(x.jhs_without_learners, 0) AS BIGINT)
       OR (c.active_public_es_school_count = 0 AND c.es_to_jhs_coverage_pct IS NOT NULL)
       OR (c.active_public_es_school_count > 0 AND ABS(c.es_to_jhs_coverage_pct
         - 100.0 * c.next_level_tested_es_school_count / c.active_public_es_school_count) > 1e-9)
       OR (c.public_jhs_school_count = 0 AND c.jhs_to_shs_coverage_pct IS NOT NULL)
       OR (c.public_jhs_school_count > 0 AND ABS(c.jhs_to_shs_coverage_pct
         - 100.0 * c.next_level_tested_jhs_school_count / c.public_jhs_school_count) > 1e-9)) AS next_level_mismatch,
  (SELECT COALESCE(COUNT_IF(reference_id IS DISTINCT FROM 'deped_do_2014_40'
    OR es_reference_min_schools_per_barangay IS DISTINCT FROM 1
    OR jhs_reference_min_schools_per_lgu IS DISTINCT FROM 1
    OR es_benchmark_status IS DISTINCT FROM CASE WHEN regular_barangay_count = 0 THEN 'not assessed'
      WHEN barangays_without_public_es > 0 THEN 'barangay without public ES'
      ELSE 'every barangay has a public ES' END
    OR jhs_benchmark_status IS DISTINCT FROM CASE WHEN public_jhs_school_count = 0 THEN 'no public JHS'
      ELSE 'public JHS present' END
    OR benchmark_status IS DISTINCT FROM CASE WHEN regular_barangay_count = 0 THEN 'not assessed'
      WHEN barangays_without_public_es > 0 OR public_jhs_school_count = 0 THEN 'school-presence gap identified'
      ELSE 'no school-presence gap identified' END
    OR spacing_km_rural_reference IS DISTINCT FROM 2.0
    OR spacing_km_urban_reference IS DISTINCT FROM 1.0
    OR spacing_benchmark_status IS DISTINCT FROM CASE
      WHEN active_public_es_school_count = 0 OR spacing_coverage_pct < 90 THEN 'not assessed'
      WHEN isolated_es_school_count > 0 THEN 'isolated public ES identified'
      ELSE 'no isolated public ES' END
    OR access_reference_id IS DISTINCT FROM 'ra_12321_2026'
    OR access_km_reference IS DISTINCT FROM 3.0
    OR es_to_jhs_3km_status IS DISTINCT FROM CASE
      WHEN active_public_es_school_count = 0 OR es_to_jhs_coverage_pct < 90 THEN 'not assessed'
      WHEN es_schools_without_jhs_within_3km > 0 THEN 'ES without public JHS within 3 km'
      ELSE 'every ES has a public JHS within 3 km' END
    OR jhs_to_shs_3km_status IS DISTINCT FROM CASE
      WHEN public_jhs_school_count = 0 OR jhs_to_shs_coverage_pct < 90 THEN 'not assessed'
      WHEN jhs_schools_without_shs_within_3km > 0 THEN 'JHS without public SHS within 3 km'
      ELSE 'every JHS has a public SHS within 3 km' END), 0) FROM c) AS benchmark_mismatch,
  (SELECT COUNT(*) FROM school_rows WHERE active = 1 AND psgc_match_status <> 'matched') AS unplaced_active_schools,
  (SELECT COALESCE(SUM(learners), 0) FROM school_rows WHERE active = 1 AND psgc_match_status <> 'matched')
    AS unplaced_public_learners,
  (SELECT COALESCE(SUM(population), 0) FROM edu_access.`05-gold`.fact_city_school_age_population
    WHERE reference_year = 2024 AND sex IN ('male', 'female') AND age BETWEEN 5 AND 17
      AND psgc_match_status <> 'matched') AS unplaced_school_age_population;
SET VARIABLE analytics_gate_owner_sql = 'ALTER TABLE ' || session.analytics_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE analytics_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap1_school_provision', 'analytics', 'edu_access.06-analytics.ap1_school_provision_candidate',
       check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_regular_lgus' AS check_name, CASE WHEN rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status,
         CAST(expected_rows AS STRING) AS expected, CAST(rows AS STRING) AS actual FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'lgu_membership_reconciles', CASE WHEN lgu_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(lgu_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'schools_and_enrollment_reconcile', CASE WHEN school_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(school_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'population_reconciles', CASE WHEN population_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(population_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'ratio_and_coverage_arithmetic', CASE WHEN arithmetic_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(arithmetic_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'coverage_gate_valid', CASE WHEN assessment_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(assessment_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'counts_reconcile', CASE WHEN presence_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(presence_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'derived_values_reconcile', CASE WHEN spacing_mismatch + next_level_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(spacing_mismatch + next_level_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'assessment_status_valid', CASE WHEN benchmark_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(benchmark_mismatch AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'unplaced_active_public_schools', CASE WHEN unplaced_active_schools = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unplaced_active_schools AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'unplaced_public_learners', CASE WHEN unplaced_public_learners = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unplaced_public_learners AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
  UNION ALL SELECT 'unplaced_school_age_population', CASE WHEN unplaced_school_age_population = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(unplaced_school_age_population AS STRING) FROM IDENTIFIER(session.analytics_gate_summary)
) AS checks;

-- Every check is recorded, so the summary is no longer needed, whether the gate passes or fails.
DROP TABLE IF EXISTS IDENTIFIER(session.analytics_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap1_school_provision: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') ELSE 1 END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap1_school_provision' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap1_school_provision USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap1_school_provision_candidate;
COMMENT ON TABLE edu_access.`06-analytics`.ap1_school_provision IS 'AP1 descriptive learners and school-age population per public school by regular LGU, SY 2023-24, not a school-establishment priority.';
ALTER TABLE edu_access.`06-analytics`.ap1_school_provision OWNER TO `reached-hq`;
