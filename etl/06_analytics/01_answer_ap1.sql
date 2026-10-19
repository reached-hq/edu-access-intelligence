-- AP1 school-provision output (#144, D-045, D-047, D-050).
-- Grain: one regular city or municipality, enrollment school year, and reporting level
-- (ALL, ES, JHS, SHS). Barangay measures are repeated by level for the LGU-year and are never ranked.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap1_school_provision_candidate USING DELTA AS
WITH levels AS (
  SELECT * FROM VALUES ('ALL'), ('ES'), ('JHS'), ('SHS') AS v(education_level_code)
),
lgus AS (
  SELECT city_mun_psgc_code, city_mun_name, lgu_type, province_psgc_code, province_name,
         region_psgc_code, region_name
  FROM edu_access.`05-gold`.dim_city_municipality
  WHERE member_type = 'regular'
),
years AS (
  SELECT DISTINCT school_year FROM edu_access.`05-gold`.fact_school_enrollment
),
public_rows AS (
  SELECT * FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE sector = 'Public' AND city_mun_psgc_code NOT IN ('UNKNOWN', 'EXCLUDED')
),
school_year AS (
  SELECT
    school_id, school_year, city_mun_psgc_code,
    MAX(barangay_psgc_code) AS barangay_psgc_code,
    MAX(annex_status) AS annex_status,
    MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
    MAX(CASE WHEN education_level_code = 'ES' AND is_offered THEN 1 ELSE 0 END) AS offers_es,
    SUM(CASE WHEN is_offered AND learner_count IS NULL THEN 1 ELSE 0 END) AS incomplete_offered_levels,
    SUM(CASE WHEN is_offered THEN learner_count ELSE 0 END) AS complete_level_sum
  FROM public_rows
  GROUP BY school_id, school_year, city_mun_psgc_code
),
school_level AS (
  SELECT
    p.school_id, p.school_year, p.city_mun_psgc_code, p.education_level_code,
    p.annex_status, s.is_active,
    CASE WHEN p.is_offered THEN 1 ELSE 0 END AS is_in_level,
    CASE WHEN p.is_offered AND p.learner_count IS NOT NULL THEN 1 ELSE 0 END AS enrollment_complete,
    CASE WHEN p.is_offered THEN p.learner_count END AS learner_count
  FROM public_rows AS p
  JOIN school_year AS s USING (school_id, school_year, city_mun_psgc_code)
  UNION ALL
  SELECT
    school_id, school_year, city_mun_psgc_code, 'ALL', annex_status, is_active, 1,
    CASE WHEN incomplete_offered_levels = 0 THEN 1 ELSE 0 END,
    CASE WHEN incomplete_offered_levels = 0 THEN complete_level_sum END
  FROM school_year
),
school_metrics AS (
  SELECT
    city_mun_psgc_code, school_year, education_level_code,
    COUNT(DISTINCT CASE WHEN is_active = 1 AND is_in_level = 1 THEN school_id END) AS public_school_count,
    COUNT(DISTINCT CASE WHEN is_active = 1 AND is_in_level = 1 AND enrollment_complete = 1 THEN school_id END)
      AS complete_enrollment_school_count,
    COUNT(DISTINCT CASE WHEN is_active = 1 AND is_in_level = 1 AND enrollment_complete = 0 THEN school_id END)
      AS incomplete_enrollment_school_count,
    COUNT(DISTINCT CASE WHEN is_active = 1 AND is_in_level = 1 AND annex_status = 'Annex/Extension School'
      THEN school_id END) AS annex_school_count,
    COUNT(DISTINCT CASE WHEN is_in_level = 1 AND learner_count = 0 THEN school_id END) AS zero_enrollment_school_count,
    SUM(CASE WHEN is_active = 1 AND is_in_level = 1 AND enrollment_complete = 1 THEN learner_count ELSE 0 END)
      AS public_school_enrollment
  FROM school_level
  GROUP BY city_mun_psgc_code, school_year, education_level_code
),
all_school_count AS (
  SELECT city_mun_psgc_code, school_year,
         COUNT(DISTINCT CASE WHEN is_active = 1 THEN school_id END) AS population_denominator_school_count
  FROM school_year
  GROUP BY city_mun_psgc_code, school_year
),
barangays AS (
  SELECT city_mun_psgc_code, COUNT(*) AS barangay_count
  FROM edu_access.`05-gold`.dim_barangay
  WHERE member_type = 'regular'
  GROUP BY city_mun_psgc_code
),
served_barangays AS (
  SELECT s.city_mun_psgc_code, s.school_year, COUNT(DISTINCT s.barangay_psgc_code) AS barangays_with_public_es
  FROM school_year AS s
  JOIN edu_access.`05-gold`.dim_barangay AS b
    ON b.barangay_psgc_code = s.barangay_psgc_code AND b.city_mun_psgc_code = s.city_mun_psgc_code
  WHERE s.is_active = 1 AND s.offers_es = 1 AND b.member_type = 'regular'
  GROUP BY s.city_mun_psgc_code, s.school_year
),
es_geography_coverage AS (
  SELECT s.city_mun_psgc_code, s.school_year,
         COUNT(DISTINCT s.school_id) AS active_public_es_school_count,
         COUNT(DISTINCT CASE WHEN b.member_type = 'regular' THEN s.school_id END)
           AS public_es_schools_with_barangay_match,
         COUNT(DISTINCT CASE WHEN b.member_type = 'unknown' THEN s.school_id END)
           AS public_es_schools_without_barangay_match
  FROM school_year AS s
  JOIN edu_access.`05-gold`.dim_barangay AS b
    ON b.barangay_psgc_code = s.barangay_psgc_code AND b.city_mun_psgc_code = s.city_mun_psgc_code
  WHERE s.is_active = 1 AND s.offers_es = 1
  GROUP BY s.city_mun_psgc_code, s.school_year
),
population AS (
  SELECT city_mun_psgc_code, population, estimate_status, status_reason
  FROM edu_access.`05-gold`.fact_city_population
  WHERE reference_year = 2024
),
grid AS (
  SELECT l.*, y.school_year, v.education_level_code
  FROM lgus AS l CROSS JOIN years AS y CROSS JOIN levels AS v
)
SELECT
  g.city_mun_psgc_code, g.city_mun_name, g.lgu_type, g.province_psgc_code, g.province_name,
  g.region_psgc_code, g.region_name, g.school_year, g.education_level_code,
  COALESCE(m.public_school_count, 0) AS public_school_count,
  COALESCE(m.complete_enrollment_school_count, 0) AS complete_enrollment_school_count,
  COALESCE(m.incomplete_enrollment_school_count, 0) AS incomplete_enrollment_school_count,
  COALESCE(m.annex_school_count, 0) AS annex_school_count,
  COALESCE(m.zero_enrollment_school_count, 0) AS zero_enrollment_school_count,
  COALESCE(m.public_school_enrollment, 0) AS public_school_enrollment,
  CAST(CASE WHEN m.complete_enrollment_school_count > 0
    THEN m.public_school_enrollment * 1.0 / m.complete_enrollment_school_count END AS DOUBLE)
    AS learners_per_public_school,
  CAST(CASE WHEN m.public_school_count > 0
    THEN m.complete_enrollment_school_count * 100.0 / m.public_school_count END AS DOUBLE)
    AS enrollment_coverage_pct,
  CAST(2024 AS INT) AS population_reference_year,
  CASE WHEN p.estimate_status = 'available' THEN p.population END AS population_2024,
  COALESCE(a.population_denominator_school_count, 0) AS population_denominator_school_count,
  CAST(CASE WHEN p.estimate_status = 'available' AND a.population_denominator_school_count > 0
    THEN p.population * 1.0 / a.population_denominator_school_count END AS DOUBLE) AS population_per_public_school,
  CASE
    WHEN p.city_mun_psgc_code IS NULL THEN 'no 2024 population row'
    WHEN p.estimate_status <> 'available' THEN p.status_reason
    WHEN COALESCE(a.population_denominator_school_count, 0) = 0 THEN 'no active public school'
  END AS population_ratio_null_reason,
  COALESCE(b.barangay_count, 0) AS barangay_count,
  COALESCE(s.barangays_with_public_es, 0) AS barangays_with_public_es,
  COALESCE(b.barangay_count, 0) - COALESCE(s.barangays_with_public_es, 0) AS barangays_without_public_es,
  CAST(CASE WHEN b.barangay_count > 0
    THEN (b.barangay_count - COALESCE(s.barangays_with_public_es, 0)) * 100.0 / b.barangay_count END AS DOUBLE)
    AS barangays_without_public_es_pct,
  COALESCE(e.active_public_es_school_count, 0) AS active_public_es_school_count,
  COALESCE(e.public_es_schools_with_barangay_match, 0) AS public_es_schools_with_barangay_match,
  COALESCE(e.public_es_schools_without_barangay_match, 0) AS public_es_schools_without_barangay_match,
  CAST(CASE WHEN e.active_public_es_school_count > 0 THEN
    e.public_es_schools_with_barangay_match * 100.0 / e.active_public_es_school_count END AS DOUBLE)
    AS barangay_match_coverage_pct,
  COALESCE(e.public_es_schools_without_barangay_match, 0) > 0 AS barangay_count_is_upper_bound,
  'active public schools including annexes, ALL requires complete enrollment in every offered level' AS school_count_rule
FROM grid AS g
LEFT JOIN school_metrics AS m USING (city_mun_psgc_code, school_year, education_level_code)
LEFT JOIN all_school_count AS a USING (city_mun_psgc_code, school_year)
LEFT JOIN barangays AS b USING (city_mun_psgc_code)
LEFT JOIN served_barangays AS s USING (city_mun_psgc_code, school_year)
LEFT JOIN es_geography_coverage AS e USING (city_mun_psgc_code, school_year)
LEFT JOIN population AS p USING (city_mun_psgc_code);

COMMENT ON TABLE edu_access.`06-analytics`.ap1_school_provision_candidate IS 'Unpublished AP1 build. Do not read: use ap1_school_provision.';
ALTER TABLE edu_access.`06-analytics`.ap1_school_provision_candidate OWNER TO `reached-hq`;
