-- ap1 school-provision context, the DepEd Order 40, s. 2014 school-presence and spacing screens, and the RA 12321
-- next-level 3 km screen (D-061).
-- grain: one regular city or municipality for SY 2023-24.
-- measures: learners per public school and 2024 school-age population (5-17) per active public school, descriptive:
-- no published source gives a ratio for either. coverage gate: at least 90% of active public schools have complete
-- all-level enrollment. a school that offers a level but has every offered count blank is not active, but it is
-- missing data, so it joins the denominator.
-- screen, like AP2 and AP3 a published reference turned into a status (config/analytics_benchmarks.json, ap1):
-- DO 40 expects at least one K-6 school in every barangay and one Grades 7-10 school in every city or municipality.
-- a regular barangay is served when an active public school that offers ES is matched to it; a school matched only
-- to the city or municipality ('-UNKNOWN' barangay) is counted, so the barangay count is then an upper bound.
-- spacing: DO 40 says a new school should not be within 2 km of a public school in a rural area or 1 km in an urban
-- area. an active public ES with a usable point (dim_school_location: inside its own city or municipality) is
-- isolated when no other such school is within that distance of it, by its barangay's PSGC urban or rural class.
-- straight-line (haversine) km between published points; pairs are found through a 0.02-degree grid, wider than
-- 2 km at Philippine latitudes, so no pair within 2 km is missed. spacing is assessed when at least 90% of the
-- LGU's active public ES schools have a usable point and an urban or rural class.
-- next level within 3 km (RA 12321, s. 5(a): a basic education school within a walkable 3 km of the residence): we have
-- no residences, so each active public ES with a usable point is tested for an active public JHS with a usable point
-- within 3 km, itself included, and each such JHS for an active public SHS. straight-line km, so over 3 km is certain
-- (a walk is never shorter) and within 3 km is only possible. pairs come from a 0.03-degree grid, wider than 3 km at
-- Philippine latitudes. assessed when at least 90% of the LGU's active public ES (or JHS) schools have a usable point.
-- the screen is for review, never a rank, a school shortage or a construction need: a nearby school may serve the
-- barangay, straight-line distance is not travel time, and the order's demand and feasibility criteria cannot be
-- tested with current data.

CREATE SCHEMA IF NOT EXISTS edu_access.`06-analytics`;
ALTER SCHEMA edu_access.`06-analytics` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`06-analytics`.ap1_school_provision_candidate USING DELTA AS
WITH lgus AS (
  SELECT city_mun_psgc_code, city_mun_name, lgu_type, province_psgc_code, province_name,
         region_psgc_code, region_name
  FROM edu_access.`05-gold`.dim_city_municipality
  WHERE member_type = 'regular'
), school_rows AS (
  SELECT school_id, city_mun_psgc_code, barangay_psgc_code,
         MAX(CASE WHEN is_offered AND learner_count > 0 THEN 1 ELSE 0 END) AS is_active,
         MAX(CASE WHEN education_level_code = 'ES' AND is_offered THEN 1 ELSE 0 END) AS offers_es,
         MAX(CASE WHEN education_level_code = 'JHS' AND is_offered THEN 1 ELSE 0 END) AS offers_jhs,
         MAX(CASE WHEN education_level_code = 'SHS' AND is_offered THEN 1 ELSE 0 END) AS offers_shs,
         SUM(CASE WHEN education_level_code = 'ES' AND is_offered AND learner_count IS NOT NULL THEN learner_count
             ELSE 0 END) AS es_learners,
         SUM(CASE WHEN education_level_code = 'JHS' AND is_offered AND learner_count IS NOT NULL THEN learner_count
             ELSE 0 END) AS jhs_learners,
         COUNT_IF(is_offered AND learner_count IS NULL) AS incomplete_offered_levels,
         COUNT_IF(is_offered) > 0 AND COUNT_IF(is_offered AND learner_count IS NOT NULL) = 0 AS is_blank,
         MAX(CASE WHEN annex_status = 'Annex/Extension School' THEN 1 ELSE 0 END) AS is_annex,
         SUM(CASE WHEN is_offered AND learner_count IS NOT NULL THEN learner_count ELSE 0 END) AS complete_level_learners
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id, city_mun_psgc_code, barangay_psgc_code
), served_barangays AS (
  SELECT DISTINCT barangay_psgc_code
  FROM school_rows
  WHERE is_active = 1 AND offers_es = 1
), barangays AS (
  SELECT b.city_mun_psgc_code,
         COUNT(*) AS regular_barangay_count,
         COUNT(s.barangay_psgc_code) AS barangays_with_public_es
  FROM edu_access.`05-gold`.dim_barangay AS b
  LEFT JOIN served_barangays AS s ON s.barangay_psgc_code = b.barangay_psgc_code
  WHERE b.member_type = 'regular'
  GROUP BY b.city_mun_psgc_code
), presence AS (
  SELECT city_mun_psgc_code,
         COUNT_IF(is_active = 1 AND offers_es = 1 AND barangay_psgc_code = city_mun_psgc_code || '-UNKNOWN')
           AS unknown_barangay_es_school_count,
         COUNT_IF(is_active = 1 AND offers_jhs = 1) AS public_jhs_school_count,
         COUNT_IF(is_active = 1 AND offers_es = 1) AS active_public_es_school_count
  FROM school_rows
  GROUP BY city_mun_psgc_code
), es_points AS (
  SELECT s.school_id, s.city_mun_psgc_code, s.complete_level_learners, l.latitude, l.longitude,
         CASE l.urban_rural WHEN 'R' THEN 2.0 WHEN 'U' THEN 1.0 END AS spacing_km,
         CAST(FLOOR(l.latitude / 0.02) AS BIGINT) AS cell_y,
         CAST(FLOOR(l.longitude / 0.02) AS BIGINT) AS cell_x
  FROM school_rows AS s
  JOIN edu_access.`05-gold`.dim_school_location AS l USING (school_id)
  WHERE s.is_active = 1 AND s.offers_es = 1 AND l.is_location_usable
), nearest AS (
  SELECT a.school_id,
         MIN(6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
           + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude))
             * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2)))) AS nearest_other_es_km
  FROM es_points AS a
  CROSS JOIN (VALUES (-1), (0), (1)) AS dy(d)
  CROSS JOIN (VALUES (-1), (0), (1)) AS dx(d)
  JOIN es_points AS b
    ON b.cell_y = a.cell_y + dy.d AND b.cell_x = a.cell_x + dx.d AND b.school_id <> a.school_id
  GROUP BY a.school_id
), spacing AS (
  SELECT p.city_mun_psgc_code,
         COUNT_IF(p.spacing_km IS NOT NULL) AS spacing_tested_es_school_count,
         COUNT_IF(p.spacing_km IS NOT NULL AND COALESCE(n.nearest_other_es_km > p.spacing_km, TRUE))
           AS isolated_es_school_count,
         SUM(CASE WHEN p.spacing_km IS NOT NULL AND COALESCE(n.nearest_other_es_km > p.spacing_km, TRUE)
             THEN p.complete_level_learners ELSE 0 END) AS learners_in_isolated_es_schools
  FROM es_points AS p
  LEFT JOIN nearest AS n USING (school_id)
  GROUP BY p.city_mun_psgc_code
), located AS (
  SELECT s.school_id, s.city_mun_psgc_code, s.offers_es, s.offers_jhs, s.offers_shs, s.es_learners, s.jhs_learners,
         l.latitude, l.longitude,
         CAST(FLOOR(l.latitude / 0.03) AS BIGINT) AS cell_y,
         CAST(FLOOR(l.longitude / 0.03) AS BIGINT) AS cell_x
  FROM school_rows AS s
  JOIN edu_access.`05-gold`.dim_school_location AS l USING (school_id)
  WHERE s.is_active = 1 AND l.is_location_usable
), reach AS (
  SELECT a.school_id,
         MAX(CASE WHEN b.offers_jhs = 1 AND 6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
           + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude))
             * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2))) <= 3.0 THEN 1 ELSE 0 END) AS jhs_within_3km,
         MAX(CASE WHEN b.offers_shs = 1 AND 6371.0088 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(b.latitude - a.latitude) / 2), 2)
           + COS(RADIANS(a.latitude)) * COS(RADIANS(b.latitude))
             * POWER(SIN(RADIANS(b.longitude - a.longitude) / 2), 2))) <= 3.0 THEN 1 ELSE 0 END) AS shs_within_3km
  FROM located AS a
  CROSS JOIN (VALUES (-1), (0), (1)) AS dy(d)
  CROSS JOIN (VALUES (-1), (0), (1)) AS dx(d)
  JOIN located AS b ON b.cell_y = a.cell_y + dy.d AND b.cell_x = a.cell_x + dx.d
  WHERE a.offers_es = 1 OR a.offers_jhs = 1
  GROUP BY a.school_id
), next_level AS (
  SELECT a.city_mun_psgc_code,
         COUNT_IF(a.offers_es = 1) AS next_level_tested_es_school_count,
         COUNT_IF(a.offers_es = 1 AND r.jhs_within_3km = 0) AS es_schools_without_jhs_within_3km,
         SUM(CASE WHEN a.offers_es = 1 AND r.jhs_within_3km = 0 THEN a.es_learners ELSE 0 END)
           AS es_learners_without_jhs_within_3km,
         COUNT_IF(a.offers_jhs = 1) AS next_level_tested_jhs_school_count,
         COUNT_IF(a.offers_jhs = 1 AND r.shs_within_3km = 0) AS jhs_schools_without_shs_within_3km,
         SUM(CASE WHEN a.offers_jhs = 1 AND r.shs_within_3km = 0 THEN a.jhs_learners ELSE 0 END)
           AS jhs_learners_without_shs_within_3km
  FROM located AS a
  JOIN reach AS r USING (school_id)
  GROUP BY a.city_mun_psgc_code
), schools AS (
  SELECT city_mun_psgc_code,
         COUNT_IF(is_active = 1) AS active_public_school_count,
         COUNT_IF(is_active = 1 AND is_annex = 1) AS annex_school_count,
         COUNT_IF(is_active = 1 AND incomplete_offered_levels = 0) AS complete_enrollment_school_count,
         COUNT_IF(is_active = 1 AND incomplete_offered_levels > 0) AS incomplete_enrollment_school_count,
         COUNT_IF(is_blank) AS blank_enrollment_school_count,
         SUM(CASE WHEN is_active = 1 AND incomplete_offered_levels = 0 THEN complete_level_learners ELSE 0 END)
           AS public_school_enrollment
  FROM school_rows
  GROUP BY city_mun_psgc_code
), population AS (
  SELECT city_mun_psgc_code, CAST(SUM(population) AS BIGINT) AS school_age_population
  FROM edu_access.`05-gold`.fact_city_school_age_population
  WHERE reference_year = 2024 AND sex IN ('male', 'female') AND age BETWEEN 5 AND 17
    AND psgc_match_status = 'matched'
  GROUP BY city_mun_psgc_code
), metrics AS (
  SELECT l.*, CAST('2023-24' AS STRING) AS school_year, CAST(2024 AS INT) AS population_reference_year,
         COALESCE(s.active_public_school_count, 0) AS active_public_school_count,
         COALESCE(s.annex_school_count, 0) AS annex_school_count,
         COALESCE(s.complete_enrollment_school_count, 0) AS complete_enrollment_school_count,
         COALESCE(s.incomplete_enrollment_school_count, 0) AS incomplete_enrollment_school_count,
         COALESCE(s.blank_enrollment_school_count, 0) AS blank_enrollment_school_count,
         CAST(COALESCE(s.public_school_enrollment, 0) AS BIGINT) AS public_school_enrollment,
         p.school_age_population,
         COALESCE(b.regular_barangay_count, 0) AS regular_barangay_count,
         COALESCE(b.barangays_with_public_es, 0) AS barangays_with_public_es,
         COALESCE(b.regular_barangay_count, 0) - COALESCE(b.barangays_with_public_es, 0) AS barangays_without_public_es,
         COALESCE(r.unknown_barangay_es_school_count, 0) AS unknown_barangay_es_school_count,
         COALESCE(r.public_jhs_school_count, 0) AS public_jhs_school_count,
         COALESCE(r.active_public_es_school_count, 0) AS active_public_es_school_count,
         COALESCE(x.spacing_tested_es_school_count, 0) AS spacing_tested_es_school_count,
         COALESCE(x.isolated_es_school_count, 0) AS isolated_es_school_count,
         CAST(COALESCE(x.learners_in_isolated_es_schools, 0) AS BIGINT) AS learners_in_isolated_es_schools,
         COALESCE(n.next_level_tested_es_school_count, 0) AS next_level_tested_es_school_count,
         COALESCE(n.es_schools_without_jhs_within_3km, 0) AS es_schools_without_jhs_within_3km,
         CAST(COALESCE(n.es_learners_without_jhs_within_3km, 0) AS BIGINT) AS es_learners_without_jhs_within_3km,
         COALESCE(n.next_level_tested_jhs_school_count, 0) AS next_level_tested_jhs_school_count,
         COALESCE(n.jhs_schools_without_shs_within_3km, 0) AS jhs_schools_without_shs_within_3km,
         CAST(COALESCE(n.jhs_learners_without_shs_within_3km, 0) AS BIGINT) AS jhs_learners_without_shs_within_3km
  FROM lgus AS l
  LEFT JOIN schools AS s USING (city_mun_psgc_code)
  LEFT JOIN population AS p USING (city_mun_psgc_code)
  LEFT JOIN barangays AS b USING (city_mun_psgc_code)
  LEFT JOIN presence AS r USING (city_mun_psgc_code)
  LEFT JOIN spacing AS x USING (city_mun_psgc_code)
  LEFT JOIN next_level AS n USING (city_mun_psgc_code)
), ratios AS (
  SELECT *,
         CAST(public_school_enrollment AS DOUBLE) / NULLIF(complete_enrollment_school_count, 0)
           AS learners_per_public_school,
         CAST(school_age_population AS DOUBLE) / NULLIF(active_public_school_count, 0)
           AS school_age_population_per_public_school,
         CAST(100.0 * complete_enrollment_school_count
           / NULLIF(active_public_school_count + blank_enrollment_school_count, 0) AS DOUBLE) AS coverage_pct,
         CAST(100.0 * barangays_without_public_es / NULLIF(regular_barangay_count, 0) AS DOUBLE)
           AS barangays_without_public_es_pct,
         barangays_without_public_es > 0 AND unknown_barangay_es_school_count > 0 AS es_count_is_upper_bound,
         CAST(100.0 * spacing_tested_es_school_count / NULLIF(active_public_es_school_count, 0) AS DOUBLE)
           AS spacing_coverage_pct,
         CAST(100.0 * next_level_tested_es_school_count / NULLIF(active_public_es_school_count, 0) AS DOUBLE)
           AS es_to_jhs_coverage_pct,
         CAST(100.0 * next_level_tested_jhs_school_count / NULLIF(public_jhs_school_count, 0) AS DOUBLE)
           AS jhs_to_shs_coverage_pct
  FROM metrics
), gated AS (
  SELECT *,
         CASE WHEN active_public_school_count = 0 THEN 'no active public school'
              WHEN learners_per_public_school IS NULL THEN 'no school with complete enrollment'
              WHEN coverage_pct < 90 THEN 'coverage below 90%'
         END AS not_assessed_reason
  FROM ratios
)
SELECT g.*,
       g.not_assessed_reason IS NULL AS is_assessed,
       'descriptive learners per public school, not a school-establishment or priority measure' AS measure_label,
       'deped_do_2014_40' AS reference_id,
       CAST(1 AS INT) AS es_reference_min_schools_per_barangay,
       CAST(1 AS INT) AS jhs_reference_min_schools_per_lgu,
       CASE WHEN g.regular_barangay_count = 0 THEN 'not assessed'
            WHEN g.barangays_without_public_es > 0 THEN 'barangay without public ES'
            ELSE 'every barangay has a public ES' END AS es_benchmark_status,
       CASE WHEN g.public_jhs_school_count = 0 THEN 'no public JHS' ELSE 'public JHS present' END AS jhs_benchmark_status,
       CAST(2.0 AS DOUBLE) AS spacing_km_rural_reference,
       CAST(1.0 AS DOUBLE) AS spacing_km_urban_reference,
       CASE WHEN g.active_public_es_school_count = 0 OR g.spacing_coverage_pct < 90 THEN 'not assessed'
            WHEN g.isolated_es_school_count > 0 THEN 'isolated public ES identified'
            ELSE 'no isolated public ES' END AS spacing_benchmark_status,
       'ra_12321_2026' AS access_reference_id,
       CAST(3.0 AS DOUBLE) AS access_km_reference,
       CASE WHEN g.active_public_es_school_count = 0 OR g.es_to_jhs_coverage_pct < 90 THEN 'not assessed'
            WHEN g.es_schools_without_jhs_within_3km > 0 THEN 'ES without public JHS within 3 km'
            ELSE 'every ES has a public JHS within 3 km' END AS es_to_jhs_3km_status,
       CASE WHEN g.public_jhs_school_count = 0 OR g.jhs_to_shs_coverage_pct < 90 THEN 'not assessed'
            WHEN g.jhs_schools_without_shs_within_3km > 0 THEN 'JHS without public SHS within 3 km'
            ELSE 'every JHS has a public SHS within 3 km' END AS jhs_to_shs_3km_status,
       CASE WHEN g.regular_barangay_count = 0 THEN 'not assessed'
            WHEN g.barangays_without_public_es > 0 OR g.public_jhs_school_count = 0 THEN 'school-presence gap identified'
            ELSE 'no school-presence gap identified' END AS benchmark_status,
       :code_revision AS code_revision
FROM gated AS g;

COMMENT ON TABLE edu_access.`06-analytics`.ap1_school_provision_candidate IS 'Unpublished AP1 build. Do not read: use ap1_school_provision.';
ALTER TABLE edu_access.`06-analytics`.ap1_school_provision_candidate OWNER TO `reached-hq`;
