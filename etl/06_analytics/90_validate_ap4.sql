-- Analytics gate for AP4 (#147). Checks ap4_school_age_enrollment_gap_candidate against the published
-- Gold facts it reads, writes every result to data_quality_results (layer 'analytics'), stops on any
-- FAIL, and only then publishes ap4_school_age_enrollment_gap. A FAIL keeps the last good output.
--
-- FAIL: a repeated or NULL key; a period other than 2020 with SY 2020-21 and 2024 with SY 2024-25 (only
-- aligned years are compared); a school placed in two cities or municipalities in one school year; a
-- year's school-age population (5 to 17, male and female) or all-sector enrollment that differs from
-- the Gold facts (which count no Philippine School Overseas); a gap, share or 2020-to-2024 change
-- that is not the arithmetic of its own row; a member_type that does not fit the code; a regular city
-- or municipality with 2024 school-age population but no 2024 row; and any row that differs, in any
-- column, from the row expected from the Gold facts (rows_match_gold).
-- WARN: schools left out because an offered level has no learner_count; learners in schools on the
-- UNKNOWN or EXCLUDED member; school-age population on EXCLUDED; regular rows without population.
-- Counts only (PASS): rows, population, enrollment and gap per period; negative gaps; rows not comparable.

DECLARE OR REPLACE VARIABLE analytics_gate_started_at_utc TIMESTAMP;
SET VARIABLE analytics_gate_started_at_utc = current_timestamp();

-- Every row as the Gold facts say it should be, built once for the full-row comparison.
CREATE OR REPLACE TEMPORARY VIEW ap4_expected AS
WITH periods AS (
  SELECT * FROM (VALUES (2020, '2020-21'), (2024, '2024-25')) AS v(reference_year, school_year)
),
levels AS (
  SELECT e.*, p.reference_year
  FROM edu_access.`05-gold`.fact_school_enrollment AS e
  JOIN periods AS p ON p.school_year = e.school_year
  WHERE e.sector <> 'PSO'
),
schools AS (
  SELECT reference_year, school_id, MIN(city_mun_psgc_code) AS city_mun_psgc_code, MIN(sector) AS sector,
         BOOL_AND(is_offered IS NOT NULL AND (NOT is_offered OR learner_count IS NOT NULL)) AS complete,
         SUM(CASE WHEN is_offered THEN learner_count ELSE 0 END) AS learners
  FROM levels GROUP BY reference_year, school_id
),
enrollment AS (
  SELECT reference_year, city_mun_psgc_code,
         SUM(CASE WHEN complete THEN learners ELSE 0 END) AS enrollment_all_sectors,
         SUM(CASE WHEN complete AND sector = 'Public' THEN learners ELSE 0 END) AS public_school_enrollment,
         COUNT_IF(complete) AS schools_counted, COUNT_IF(NOT complete) AS schools_incomplete
  FROM schools GROUP BY reference_year, city_mun_psgc_code
),
population AS (
  SELECT reference_year, city_mun_psgc_code, SUM(population) AS school_age_population,
         BOOL_AND(is_2020_2024_geography_comparable) AS comparable
  FROM edu_access.`05-gold`.fact_city_school_age_population
  WHERE reference_year IN (2020, 2024) AND sex IN ('male', 'female') AND age >= 5 AND age <= 17
  GROUP BY reference_year, city_mun_psgc_code
),
keys AS (
  SELECT reference_year, city_mun_psgc_code FROM population
  UNION
  SELECT reference_year, city_mun_psgc_code FROM enrollment
)
SELECT
  k.city_mun_psgc_code,
  CAST(k.reference_year AS INT) AS reference_year,
  CAST(n.school_age_population AS BIGINT) AS school_age_population,
  CAST(COALESCE(e.enrollment_all_sectors, 0) AS BIGINT) AS enrollment_all_sectors,
  CAST(COALESCE(e.public_school_enrollment, 0) AS BIGINT) AS public_school_enrollment,
  COALESCE(e.schools_counted, 0) AS schools_counted,
  COALESCE(e.schools_incomplete, 0) AS schools_incomplete,
  COALESCE(k.city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED') AND n.comparable, FALSE) AS is_2020_2024_geography_comparable
FROM keys AS k
LEFT JOIN population AS n ON n.reference_year = k.reference_year AND n.city_mun_psgc_code = k.city_mun_psgc_code
LEFT JOIN enrollment AS e ON e.reference_year = k.reference_year AND e.city_mun_psgc_code = k.city_mun_psgc_code;

DECLARE OR REPLACE VARIABLE analytics_ap4_rows_not_matching BIGINT;
SET VARIABLE analytics_ap4_rows_not_matching = (
  (SELECT COUNT(*) FROM (
     SELECT city_mun_psgc_code, reference_year, school_age_population, enrollment_all_sectors, public_school_enrollment,
            schools_counted, schools_incomplete, is_2020_2024_geography_comparable
     FROM edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate
     EXCEPT ALL SELECT * FROM ap4_expected) AS x)
  + (SELECT COUNT(*) FROM (
     SELECT * FROM ap4_expected
     EXCEPT ALL
     SELECT city_mun_psgc_code, reference_year, school_age_population, enrollment_all_sectors, public_school_enrollment,
            schools_counted, schools_incomplete, is_2020_2024_geography_comparable
     FROM edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate) AS x));

-- The full-row comparison is computed once, above, because the summary view is read once per result row.
CREATE OR REPLACE TEMPORARY VIEW ap4_gate_summary AS
WITH ap4 AS (
  SELECT * FROM edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate
),
gold_enrollment AS (
  SELECT * FROM edu_access.`05-gold`.fact_school_enrollment WHERE school_year IN ('2020-21', '2024-25')
),
school_places AS (
  SELECT school_year, school_id, COUNT(DISTINCT city_mun_psgc_code) AS places
  FROM gold_enrollment GROUP BY school_year, school_id
),
expected_by_year AS (
  SELECT reference_year, SUM(school_age_population) AS population, SUM(enrollment_all_sectors) AS enrollment
  FROM ap4_expected GROUP BY reference_year
),
ap4_by_year AS (
  SELECT reference_year, SUM(school_age_population) AS population, SUM(enrollment_all_sectors) AS enrollment
  FROM ap4 GROUP BY reference_year
),
regular_2024 AS (
  SELECT DISTINCT city_mun_psgc_code
  FROM edu_access.`05-gold`.fact_city_school_age_population
  WHERE reference_year = 2024 AND city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED')
)
SELECT
  session.analytics_ap4_rows_not_matching AS rows_not_matching_gold,
  (SELECT COUNT(*) FROM ap4) - (SELECT COUNT(*) FROM (SELECT DISTINCT city_mun_psgc_code, reference_year FROM ap4) AS k) AS duplicate_keys,
  (SELECT COUNT_IF(city_mun_psgc_code IS NULL OR reference_year IS NULL) FROM ap4) AS null_keys,
  (SELECT COUNT_IF(NOT ((reference_year = 2020 AND school_year = '2020-21') OR (reference_year = 2024 AND school_year = '2024-25'))
                   OR school_year IS NULL) FROM ap4) AS unaligned_rows,
  (SELECT COUNT_IF(places > 1) FROM school_places) AS schools_in_two_places,
  (SELECT COUNT(*) FROM expected_by_year AS x FULL OUTER JOIN ap4_by_year AS a ON a.reference_year = x.reference_year
    WHERE a.population IS DISTINCT FROM x.population) AS population_years_not_reconciled,
  (SELECT COUNT(*) FROM expected_by_year AS x FULL OUTER JOIN ap4_by_year AS a ON a.reference_year = x.reference_year
    WHERE a.enrollment IS DISTINCT FROM x.enrollment) AS enrollment_years_not_reconciled,
  (SELECT COUNT_IF(population_enrollment_gap IS DISTINCT FROM school_age_population - enrollment_all_sectors
                OR gap_share IS DISTINCT FROM CAST(population_enrollment_gap AS DOUBLE) / NULLIF(school_age_population, 0)
                OR public_school_share IS DISTINCT FROM CAST(public_school_enrollment AS DOUBLE) / NULLIF(enrollment_all_sectors, 0)
                OR public_school_enrollment > enrollment_all_sectors
                OR age_min <> 5 OR age_max <> 17) FROM ap4) AS arithmetic_errors,
  (SELECT COUNT(*) FROM ap4 AS a LEFT JOIN ap4 AS b
     ON b.city_mun_psgc_code = a.city_mun_psgc_code AND b.reference_year = 2020
   WHERE a.gap_change_2020_2024 IS DISTINCT FROM
         CASE WHEN a.reference_year = 2024 AND a.member_type = 'regular'
              THEN a.population_enrollment_gap - b.population_enrollment_gap END) AS change_errors,
  (SELECT COUNT_IF(member_type IS DISTINCT FROM CASE city_mun_psgc_code WHEN 'UNKNOWN' THEN 'unknown'
                                                      WHEN 'EXCLUDED' THEN 'excluded' ELSE 'regular' END) FROM ap4) AS bad_member_type,
  (SELECT COUNT(*) FROM regular_2024 AS r
    WHERE NOT EXISTS (SELECT 1 FROM ap4 AS a WHERE a.city_mun_psgc_code = r.city_mun_psgc_code AND a.reference_year = 2024)) AS regular_missing_2024,
  (SELECT COALESCE(SUM(schools_incomplete), 0) FROM ap4) AS schools_incomplete,
  (SELECT COALESCE(SUM(enrollment_all_sectors), 0) FROM ap4 WHERE member_type <> 'regular') AS learners_on_technical_members,
  (SELECT COALESCE(SUM(school_age_population), 0) FROM ap4 WHERE member_type = 'excluded') AS population_on_excluded,
  (SELECT COUNT_IF(member_type = 'regular' AND school_age_population IS NULL) FROM ap4) AS regular_without_population,
  (SELECT COUNT_IF(reference_year = 2020) FROM ap4) AS rows_2020,
  (SELECT COUNT_IF(reference_year = 2024) FROM ap4) AS rows_2024,
  (SELECT SUM(CASE WHEN reference_year = 2020 THEN school_age_population END) FROM ap4) AS population_2020,
  (SELECT SUM(CASE WHEN reference_year = 2024 THEN school_age_population END) FROM ap4) AS population_2024,
  (SELECT SUM(CASE WHEN reference_year = 2020 THEN enrollment_all_sectors END) FROM ap4) AS enrollment_2020,
  (SELECT SUM(CASE WHEN reference_year = 2024 THEN enrollment_all_sectors END) FROM ap4) AS enrollment_2024,
  (SELECT COUNT_IF(member_type = 'regular' AND population_enrollment_gap < 0) FROM ap4) AS negative_gaps,
  (SELECT COUNT_IF(member_type = 'regular' AND reference_year = 2024 AND NOT is_2020_2024_geography_comparable) FROM ap4) AS regular_not_comparable;

INSERT INTO edu_access.`01-control`.data_quality_results (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'ap4', 'analytics', 'edu_access.06-analytics.ap4_school_age_enrollment_gap', check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_match_gold' AS check_name, CASE WHEN rows_not_matching_gold = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '0' AS expected, CAST(rows_not_matching_gold AS STRING) AS actual FROM ap4_gate_summary
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'key_not_null', CASE WHEN null_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_keys AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'only_aligned_years', CASE WHEN unaligned_rows = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(unaligned_rows AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'one_place_per_school_year', CASE WHEN schools_in_two_places = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(schools_in_two_places AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'population_reconciles_by_year', CASE WHEN population_years_not_reconciled = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(population_years_not_reconciled AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'enrollment_reconciles_by_year', CASE WHEN enrollment_years_not_reconciled = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(enrollment_years_not_reconciled AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'arithmetic_holds', CASE WHEN arithmetic_errors = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(arithmetic_errors AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'change_2020_2024_holds', CASE WHEN change_errors = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(change_errors AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'member_type_fits_code', CASE WHEN bad_member_type = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(bad_member_type AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'every_regular_city_in_2024', CASE WHEN regular_missing_2024 = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(regular_missing_2024 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'schools_incomplete', CASE WHEN schools_incomplete = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(schools_incomplete AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'learners_on_technical_members', CASE WHEN learners_on_technical_members = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(learners_on_technical_members AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'population_on_excluded', CASE WHEN population_on_excluded = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(population_on_excluded AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'regular_without_population', CASE WHEN regular_without_population = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(regular_without_population AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'rows_2020', 'PASS', CAST(NULL AS STRING), CAST(rows_2020 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'rows_2024', 'PASS', CAST(NULL AS STRING), CAST(rows_2024 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'population_2020', 'PASS', CAST(NULL AS STRING), CAST(population_2020 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'population_2024', 'PASS', CAST(NULL AS STRING), CAST(population_2024 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'enrollment_2020', 'PASS', CAST(NULL AS STRING), CAST(enrollment_2020 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'enrollment_2024', 'PASS', CAST(NULL AS STRING), CAST(enrollment_2024 AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'negative_gaps', 'PASS', CAST(NULL AS STRING), CAST(negative_gaps AS STRING) FROM ap4_gate_summary
  UNION ALL SELECT 'regular_not_comparable_2024', 'PASS', CAST(NULL AS STRING), CAST(regular_not_comparable AS STRING) FROM ap4_gate_summary
) AS results;

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Analytics gate failed for ap4: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s) in data_quality_results for run ' || :run_id) END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'ap4' AND layer = 'analytics' AND status = 'FAIL'
  AND checked_at_utc >= session.analytics_gate_started_at_utc;

-- Every check passed: publish.
CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap USING DELTA AS
SELECT * FROM edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate;

COMMENT ON TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap IS 'AP4: school-age population (5 to 17) minus all-sector enrollment (PSO excluded) by city or municipality, 2020 with SY 2020-21 and 2024 with SY 2024-25. An arithmetic difference, not an out-of-school count or enrollment rate.';
ALTER TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap OWNER TO `reached-hq`;
