-- Gold build for dim_school_location (D-061, docs/architecture/data-model.md: school_location).
--
-- One row per public school in the public-only DepEd workbook for SY 2023-24 (deped_psgc_coordinates_clean,
-- #217, #218): its published point, its city or municipality and barangay from fact_school_enrollment (the
-- reviewed school-to-PSGC match, D-049), the barangay's PSGC urban or rural class, and the boundary test S-1.
--
-- Reads published tables only: deped_psgc_coordinates_clean, fact_school_enrollment, dim_barangay,
-- hdx_adm3_psgc_map and hdx_adm3_clean. Writes dim_school_location_candidate; the gate (the next task) checks
-- it and publishes dim_school_location only if no check fails. It rebuilds on every run.
--
-- Rules:
--   - boundary_test_status, in this order:
--       no_point        coordinate_flag is set (missing, zero, or outside the Philippines); nothing is tested
--       no_city_match   the school has no matched city or municipality in fact_school_enrollment SY 2023-24
--       no_boundary     the city or municipality has no matched HDX ADM3 feature in the latest HDX release
--                       (today the 8 Special Geographic Area municipalities)
--       inside          the point is inside a matched feature of its own city or municipality (st_contains)
--       outside         it is not
--   - is_location_usable is TRUE only for inside. A point is kept and flagged, never moved or corrected.
--   - The 2 km / 1 km spacing of DepEd Order 40, s. 2014 is applied in Analytics (AP1), not here.

CREATE SCHEMA IF NOT EXISTS edu_access.`05-gold`;
ALTER SCHEMA edu_access.`05-gold` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`05-gold`.dim_school_location_candidate USING DELTA AS
WITH points AS (
  SELECT school_id, school_year, longitude, latitude, coordinate_flag
  FROM edu_access.`03-silver`.deped_psgc_coordinates_clean
  WHERE school_year = '2023-24'
), geography AS (
  SELECT school_id, MIN(city_mun_psgc_code) AS city_mun_psgc_code, MIN(barangay_psgc_code) AS barangay_psgc_code
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id
), hdx_release AS (
  SELECT MAX(source_reference_date) AS source_reference_date
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map
), boundaries AS (
  SELECT m.psgc_code AS city_mun_psgc_code, try_to_geometry(h.geometry) AS geo
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map AS m
  JOIN hdx_release AS r ON r.source_reference_date = m.source_reference_date
  JOIN edu_access.`03-silver`.hdx_adm3_clean AS h
    ON h.adm3_pcode = m.adm3_pcode AND h.valid_on = m.source_reference_date
  WHERE m.match_status = 'matched'
), tested AS (
  SELECT p.school_id,
         COUNT(b.city_mun_psgc_code) AS boundary_count,
         MAX(CASE WHEN st_contains(b.geo, try_to_geometry(concat('{"type": "Point", "coordinates": [',
           CAST(p.longitude AS STRING), ', ', CAST(p.latitude AS STRING), ']}'))) THEN 1 ELSE 0 END) AS inside
  FROM points AS p
  JOIN geography AS g USING (school_id)
  JOIN boundaries AS b ON b.city_mun_psgc_code = g.city_mun_psgc_code
  WHERE p.coordinate_flag IS NULL
  GROUP BY p.school_id
), located AS (
  SELECT p.school_id, p.school_year, g.city_mun_psgc_code, g.barangay_psgc_code, d.urban_rural,
         p.longitude, p.latitude, p.coordinate_flag,
         CASE WHEN p.coordinate_flag IS NOT NULL THEN 'no_point'
              WHEN g.city_mun_psgc_code IS NULL THEN 'no_city_match'
              WHEN COALESCE(t.boundary_count, 0) = 0 THEN 'no_boundary'
              WHEN t.inside = 1 THEN 'inside'
              ELSE 'outside' END AS boundary_test_status
  FROM points AS p
  LEFT JOIN geography AS g USING (school_id)
  LEFT JOIN edu_access.`05-gold`.dim_barangay AS d ON d.barangay_psgc_code = g.barangay_psgc_code
  LEFT JOIN tested AS t USING (school_id)
)
SELECT school_id, school_year, city_mun_psgc_code, barangay_psgc_code, urban_rural, longitude, latitude,
       coordinate_flag, boundary_test_status, boundary_test_status = 'inside' AS is_location_usable,
       'deped_psgc_coordinates' AS location_source
FROM located;

COMMENT ON TABLE edu_access.`05-gold`.dim_school_location_candidate IS 'Unpublished build for the Gold gate, which may have failed. Do not read: use dim_school_location.';
ALTER TABLE edu_access.`05-gold`.dim_school_location_candidate OWNER TO `reached-hq`;
