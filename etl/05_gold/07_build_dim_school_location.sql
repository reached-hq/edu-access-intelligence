-- Gold build for dim_school_location (#217, docs/architecture/data-model.md).
--
-- One row per public school with a published location: every row of deped_psgc_coordinates_clean (the
-- public-only DepEd workbook, SY 2023-24; coordinates from NSBI as of 2025-07-07). It joins dim_school on
-- school_id, one to zero or one, and carries no PSGC code: a school's city and barangay come only from
-- deped_school_psgc_map through the facts (D-049), so there is one path from a school to its LGU.
--
-- Reads published tables only: deped_psgc_coordinates_clean (Silver), deped_school_psgc_map, hdx_adm3_psgc_map
-- (Integration) and hdx_adm3_clean (Silver). Writes dim_school_location_candidate; the gate (the next task)
-- checks it and publishes dim_school_location only if no check fails. It rebuilds on every run.
--
-- Rules:
--   - longitude, latitude and coordinate_flag are Silver's, unchanged. Nothing is corrected or geocoded.
--   - boundary_status is the boundary test S-1 at city or municipality level: is the school's point inside
--     the HDX ADM3 boundary of the city or municipality the reviewed map assigns it for SY 2023-24?
--       inside           inside (any of) its city's boundaries
--       outside          a boundary exists and the point is not inside it (a point on the edge is outside)
--       no_usable_point  coordinate_flag is set (missing, zero, outside_philippines): nothing to test
--       no_matched_city  the map has no matched city or municipality for the school in SY 2023-24
--       no_boundary      the city is matched but has no matched, valid HDX boundary in the latest release
--     Only inside is fit for a map (D-061, proposed); the status is a check, never a correction.
--
-- Cost: the scope (SY 2023-24, city level, matched, unflagged points) is applied before the spatial join;
-- each boundary is parsed once per city, not per school; one st_contains per school and boundary; the
-- result is reduced to one row per school before the final join, so nothing multiplies.

CREATE SCHEMA IF NOT EXISTS edu_access.`05-gold`;
ALTER SCHEMA edu_access.`05-gold` OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`05-gold`.dim_school_location_candidate USING DELTA AS
WITH location AS (
  SELECT school_id, longitude, latitude, coordinate_flag
  FROM edu_access.`03-silver`.deped_psgc_coordinates_clean
),
city AS (
  SELECT school_id, psgc_code AS city_mun_psgc_code
  FROM edu_access.`04-integration`.deped_school_psgc_map
  WHERE school_year = '2023-24' AND geographic_level = 'city_mun' AND match_status = 'matched'
),
hdx_release AS (
  SELECT MAX(source_reference_date) AS source_reference_date
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map
),
boundary AS (
  -- One parsed shape per matched, valid ADM3 feature of the latest release.
  SELECT m.psgc_code AS city_mun_psgc_code, try_to_geometry(h.geometry) AS shape
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map AS m
  JOIN hdx_release AS r ON r.source_reference_date = m.source_reference_date
  JOIN edu_access.`03-silver`.hdx_adm3_clean AS h
    ON h.adm3_pcode = m.adm3_pcode AND h.valid_on = m.source_reference_date
  WHERE m.match_status = 'matched' AND h.geometry_is_valid
),
tested AS (
  -- Unflagged points of schools with a matched city that has a boundary: one row per school.
  SELECT l.school_id,
         MAX(CASE WHEN st_contains(b.shape, try_to_geometry(concat('{"type": "Point", "coordinates": [',
                       CAST(l.longitude AS STRING), ', ', CAST(l.latitude AS STRING), ']}'))) THEN 1 ELSE 0 END) AS is_inside
  FROM location AS l
  JOIN city AS c ON c.school_id = l.school_id
  JOIN boundary AS b ON b.city_mun_psgc_code = c.city_mun_psgc_code
  WHERE l.coordinate_flag IS NULL AND b.shape IS NOT NULL   -- an unparsed shape is no boundary, never 'outside'
  GROUP BY l.school_id
)
SELECT
  l.school_id,
  l.longitude,
  l.latitude,
  l.coordinate_flag,
  CASE
    WHEN l.coordinate_flag IS NOT NULL THEN 'no_usable_point'
    WHEN c.school_id IS NULL THEN 'no_matched_city'
    WHEN t.school_id IS NULL THEN 'no_boundary'
    WHEN t.is_inside = 1 THEN 'inside'
    ELSE 'outside'
  END AS boundary_status
FROM location AS l
LEFT JOIN city AS c ON c.school_id = l.school_id
LEFT JOIN tested AS t ON t.school_id = l.school_id;

ALTER TABLE edu_access.`05-gold`.dim_school_location_candidate OWNER TO `reached-hq`;
