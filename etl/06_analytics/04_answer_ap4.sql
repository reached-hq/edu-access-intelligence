-- Analytics output for AP4 (#147): school-age population and enrollment gap, by city or municipality
-- and AP4 period. Implements the AP4 contract of docs/business/metric-specification.md (D-050, D-042).
--
-- Grain: one row per city or municipality member and AP4 period, key (city_mun_psgc_code,
-- reference_year). Periods pair a census with the school year that starts in the same year:
--   2020  2020 Census of Population and Housing (May 1, 2020)  with  SY 2020-21
--   2024  2024 Census of Population (July 1, 2024)               with  SY 2024-25
-- No other school year has an AP4 value ("not available"); nothing is interpolated or extrapolated.
--
-- Reads published Gold only: fact_city_school_age_population and fact_school_enrollment. Writes
-- ap4_school_age_enrollment_gap_candidate; the gate (the next task) checks it and publishes
-- ap4_school_age_enrollment_gap only if no check fails, so a FAIL keeps the last good output.
--
-- Rules:
--   - school_age_population: ages 5 to 17, male plus female rows (never the published both-sexes total),
--     PSA Total Population. Ages 18 to 24 in the fact are not used.
--   - enrollment_all_sectors: learners in Public, Private and SUC/LUC schools located in the city or
--     municipality that school year; Philippine Schools Overseas excluded. A school counts with its
--     all-level total: ES + JHS + SHS when every offered level has a learner_count, otherwise NULL
--     ("Enrollment aggregation and missingness"). NULL totals are left out of the sums and counted in
--     schools_incomplete, never read as 0. A city or municipality with no school that year has 0.
--   - population_enrollment_gap = school_age_population - enrollment_all_sectors, kept when negative.
--     gap_share = gap / school_age_population; public_school_share = public / all-sector enrollment;
--     each is NULL when its denominator is NULL or 0.
--   - gap_change_2020_2024 is on the 2024 row only: the 2024 gap minus the 2020 gap, for a regular
--     member with both gaps. is_2020_2024_geography_comparable is the population fact's flag (territory
--     changes and units that exist in one census only are FALSE); technical members are FALSE.
--   - Every member that has population or enrollment in a period gets a row, the UNKNOWN and EXCLUDED
--     technical members included (member_type), so the rows add up to the national totals and
--     unplaced schools and people stay visible. Dashboards filter member_type = 'regular'.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate USING DELTA AS
WITH periods AS (
  SELECT * FROM (VALUES
    (2020, '2020-21', DATE '2020-05-01', '2020 Census of Population and Housing (CPH), PSA Total Population'),
    (2024, '2024-25', DATE '2024-07-01', '2024 Census of Population (POPCEN), PSA Total Population')
  ) AS v(reference_year, school_year, population_reference_date, population_source)
),
-- One all-level total per school and school year: NULL when any offered level has no learner_count.
school_totals AS (
  SELECT
    e.school_year,
    e.school_id,
    e.city_mun_psgc_code,
    e.sector,
    CASE WHEN COUNT_IF(e.is_offered IS NULL OR (e.is_offered AND e.learner_count IS NULL)) > 0 THEN NULL
         ELSE SUM(CASE WHEN e.is_offered THEN e.learner_count ELSE 0 END) END AS school_learners
  FROM edu_access.`05-gold`.fact_school_enrollment AS e
  JOIN periods AS p ON p.school_year = e.school_year
  WHERE e.sector IN ('Public', 'Private', 'SUC/LUC')
  GROUP BY e.school_year, e.school_id, e.city_mun_psgc_code, e.sector
),
enrollment AS (
  SELECT
    p.reference_year,
    t.city_mun_psgc_code,
    CAST(COALESCE(SUM(t.school_learners), 0) AS BIGINT) AS enrollment_all_sectors,
    CAST(COALESCE(SUM(CASE WHEN t.sector = 'Public' THEN t.school_learners END), 0) AS BIGINT) AS public_school_enrollment,
    COUNT(t.school_learners) AS schools_counted,
    COUNT_IF(t.school_learners IS NULL) AS schools_incomplete
  FROM school_totals AS t
  JOIN periods AS p ON p.school_year = t.school_year
  GROUP BY p.reference_year, t.city_mun_psgc_code
),
population AS (
  SELECT
    f.reference_year,
    f.city_mun_psgc_code,
    CAST(SUM(f.population) AS BIGINT) AS school_age_population,
    BOOL_AND(f.is_2020_2024_geography_comparable) AS is_2020_2024_geography_comparable
  FROM edu_access.`05-gold`.fact_city_school_age_population AS f
  JOIN periods AS p ON p.reference_year = f.reference_year
  WHERE f.sex IN ('male', 'female') AND f.age BETWEEN 5 AND 17
  GROUP BY f.reference_year, f.city_mun_psgc_code
),
combined AS (
  SELECT
    COALESCE(n.city_mun_psgc_code, e.city_mun_psgc_code) AS city_mun_psgc_code,
    COALESCE(n.reference_year, e.reference_year) AS reference_year,
    n.school_age_population,
    n.is_2020_2024_geography_comparable,
    COALESCE(e.enrollment_all_sectors, 0) AS enrollment_all_sectors,
    COALESCE(e.public_school_enrollment, 0) AS public_school_enrollment,
    COALESCE(e.schools_counted, 0) AS schools_counted,
    COALESCE(e.schools_incomplete, 0) AS schools_incomplete
  FROM population AS n
  FULL OUTER JOIN enrollment AS e
    ON e.city_mun_psgc_code = n.city_mun_psgc_code AND e.reference_year = n.reference_year
),
gaps AS (
  SELECT
    c.*,
    CASE c.city_mun_psgc_code WHEN 'UNKNOWN' THEN 'unknown' WHEN 'EXCLUDED' THEN 'excluded' ELSE 'regular' END AS member_type,
    c.school_age_population - c.enrollment_all_sectors AS population_enrollment_gap
  FROM combined AS c
)
SELECT
  g.city_mun_psgc_code,
  g.member_type,
  CAST(g.reference_year AS INT) AS reference_year,
  p.school_year,
  p.population_source,
  p.population_reference_date,
  5 AS age_min,
  17 AS age_max,
  g.school_age_population,
  g.enrollment_all_sectors,
  g.public_school_enrollment,
  g.population_enrollment_gap,
  CAST(g.population_enrollment_gap AS DOUBLE) / NULLIF(g.school_age_population, 0) AS gap_share,
  CAST(g.public_school_enrollment AS DOUBLE) / NULLIF(g.enrollment_all_sectors, 0) AS public_school_share,
  CASE WHEN g.reference_year = 2024 AND g.member_type = 'regular' THEN g.population_enrollment_gap - g2020.population_enrollment_gap
  END AS gap_change_2020_2024,
  COALESCE(g.member_type = 'regular' AND g.is_2020_2024_geography_comparable, FALSE) AS is_2020_2024_geography_comparable,
  g.schools_counted,
  g.schools_incomplete,
  'Public, Private and SUC/LUC schools, Philippine Schools Overseas excluded' AS enrollment_scope,
  'Arithmetic difference between residents aged 5 to 17 and learners enrolled in schools located here, '
    || 'not an out-of-school count or an enrollment rate. Population is counted where people live and '
    || 'enrollment where the school is, so a negative gap usually marks a school hub.' AS interpretation_note
FROM gaps AS g
JOIN periods AS p ON p.reference_year = g.reference_year
LEFT JOIN gaps AS g2020 ON g2020.city_mun_psgc_code = g.city_mun_psgc_code AND g2020.reference_year = 2020;

COMMENT ON TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate IS 'Unpublished build for the Analytics gate, which may have failed. Do not read: use ap4_school_age_enrollment_gap.';
ALTER TABLE edu_access.`06-analytics`.ap4_school_age_enrollment_gap_candidate OWNER TO `reached-hq`;
