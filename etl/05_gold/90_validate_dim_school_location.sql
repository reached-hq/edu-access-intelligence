-- Gold gate for dim_school_location (D-061). Checks dim_school_location_candidate against
-- deped_psgc_coordinates_clean, fact_school_enrollment, dim_barangay and the HDX boundaries, writes every result
-- to data_quality_results (layer 'gold'), stops on any FAIL, and only then publishes dim_school_location. A
-- FAIL keeps the last good build.
--
-- FAIL: rows that differ from the Silver schools of SY 2023-24, a repeated or NULL key, a point or flag that
-- differs from Silver, a city, barangay or urban_rural that differs from fact_school_enrollment and
-- dim_barangay, a boundary_test_status outside the five allowed values or out of order (no_point exactly when
-- coordinate_flag is set, no_city_match exactly when there is no matched city), a boundary result that differs
-- from st_contains recomputed here, or is_location_usable other than boundary_test_status = 'inside'.
-- WARN: schools with no matched city or municipality, and cities or municipalities of located schools with no matched
-- HDX feature. Count only (PASS, outlier_schools): points outside their own city or municipality (S-1).
-- The checks use names already in config/quality_attributes.yml, so the data-quality dashboard is not regenerated.

DECLARE OR REPLACE VARIABLE gold_gate_started_at_utc TIMESTAMP;
SET VARIABLE gold_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE gold_gate_summary STRING;
SET VARIABLE gold_gate_summary = '`edu_access`.`05-gold`.`dim_school_location_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE gold_gate_owner_sql STRING;

CREATE OR REPLACE TABLE IDENTIFIER(session.gold_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one dim_school_location gate. The gate drops it once its checks are recorded in data_quality_results.' AS
WITH dimension AS (
  SELECT * FROM edu_access.`05-gold`.dim_school_location_candidate
), source AS (
  SELECT * FROM edu_access.`03-silver`.deped_psgc_coordinates_clean WHERE school_year = '2023-24'
), geography AS (
  SELECT school_id, MIN(city_mun_psgc_code) AS city, MIN(barangay_psgc_code) AS barangay
  FROM edu_access.`05-gold`.fact_school_enrollment
  WHERE school_year = '2023-24' AND sector = 'Public' AND psgc_match_status = 'matched'
  GROUP BY school_id
), latest AS (
  SELECT MAX(source_reference_date) AS d FROM edu_access.`04-integration`.hdx_adm3_psgc_map
), shapes AS (
  SELECT m.psgc_code, h.geometry
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map m
  JOIN latest ON latest.d = m.source_reference_date
  JOIN edu_access.`03-silver`.hdx_adm3_clean h ON h.adm3_pcode = m.adm3_pcode AND h.valid_on = m.source_reference_date
  WHERE m.match_status = 'matched'
), recomputed AS (
  SELECT d.school_id, COUNT(s.psgc_code) AS shapes,
         COUNT_IF(st_contains(try_to_geometry(s.geometry),
           try_to_geometry('{"type": "Point", "coordinates": [' || CAST(d.longitude AS STRING) || ', '
             || CAST(d.latitude AS STRING) || ']}'))) AS containing
  FROM dimension d
  JOIN shapes s ON s.psgc_code = d.city_mun_psgc_code
  WHERE d.coordinate_flag IS NULL
  GROUP BY d.school_id
)
SELECT
  (SELECT COUNT(*) FROM source) AS source_rows,
  (SELECT COUNT(*) FROM dimension) AS dimension_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT school_id) FROM dimension) AS duplicate_keys,
  (SELECT COUNT_IF(school_id IS NULL) FROM dimension) AS null_keys,
  (SELECT COUNT(*) FROM dimension d FULL OUTER JOIN source s USING (school_id)
    WHERE d.school_id IS NULL OR s.school_id IS NULL
       OR d.longitude IS DISTINCT FROM s.longitude OR d.latitude IS DISTINCT FROM s.latitude
       OR d.coordinate_flag IS DISTINCT FROM s.coordinate_flag) AS point_mismatch,
  (SELECT COUNT(*) FROM dimension d LEFT JOIN geography g USING (school_id)
    LEFT JOIN edu_access.`05-gold`.dim_barangay b ON b.barangay_psgc_code = g.barangay
    WHERE d.city_mun_psgc_code IS DISTINCT FROM g.city OR d.barangay_psgc_code IS DISTINCT FROM g.barangay
       OR d.urban_rural IS DISTINCT FROM b.urban_rural) AS geography_mismatch,
  (SELECT COUNT_IF(boundary_test_status IS NULL
      OR boundary_test_status NOT IN ('no_point', 'no_city_match', 'no_boundary', 'inside', 'outside')
      OR (boundary_test_status = 'no_point') <> (coordinate_flag IS NOT NULL)
      OR (boundary_test_status = 'no_city_match') <> (coordinate_flag IS NULL AND city_mun_psgc_code IS NULL)
      OR is_location_usable IS DISTINCT FROM (boundary_test_status = 'inside')) FROM dimension) AS status_invalid,
  (SELECT COUNT(*) FROM dimension d LEFT JOIN recomputed r USING (school_id)
    WHERE d.boundary_test_status IN ('no_boundary', 'inside', 'outside')
      AND d.boundary_test_status IS DISTINCT FROM CASE WHEN COALESCE(r.shapes, 0) = 0 THEN 'no_boundary'
        WHEN r.containing > 0 THEN 'inside' ELSE 'outside' END) AS boundary_mismatch,
  (SELECT COUNT_IF(boundary_test_status = 'outside') FROM dimension) AS outside_rows,
  (SELECT COUNT(DISTINCT CASE WHEN boundary_test_status = 'no_boundary' THEN city_mun_psgc_code END) FROM dimension)
    AS cities_without_boundary,
  (SELECT COUNT_IF(boundary_test_status = 'no_city_match') FROM dimension) AS no_city_match_rows;
SET VARIABLE gold_gate_owner_sql = 'ALTER TABLE ' || session.gold_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE gold_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'dim_school_location', 'gold', 'edu_access.05-gold.dim_school_location', check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_reconcile' AS check_name, CASE WHEN dimension_rows = source_rows THEN 'PASS' ELSE 'FAIL' END AS status, CAST(source_rows AS STRING) AS expected, CAST(dimension_rows AS STRING) AS actual FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'key_not_null', CASE WHEN null_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_keys AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'coordinates_reconcile', CASE WHEN point_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(point_mismatch AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'values_match_source', CASE WHEN geography_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(geography_mismatch AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'status_valid', CASE WHEN status_invalid = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(status_invalid AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'derived_values_reconcile', CASE WHEN boundary_mismatch = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(boundary_mismatch AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_city_unknown', CASE WHEN no_city_match_rows = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(no_city_match_rows AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'psgc_units_without_feature', CASE WHEN cities_without_boundary = 0 THEN 'PASS' ELSE 'WARN' END, '0', CAST(cities_without_boundary AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'outlier_schools', 'PASS', CAST(NULL AS STRING), CAST(outside_rows AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
) AS results;

-- Every check is recorded, so the summary is no longer needed, whether the gate passes or fails.
DROP TABLE IF EXISTS IDENTIFIER(session.gold_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Gold gate failed for dim_school_location: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'dim_school_location' AND layer = 'gold' AND status = 'FAIL' AND checked_at_utc >= session.gold_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`05-gold`.dim_school_location USING DELTA AS
SELECT * FROM edu_access.`05-gold`.dim_school_location_candidate;
COMMENT ON TABLE edu_access.`05-gold`.dim_school_location IS 'One public school in the public-only DepEd workbook, SY 2023-24: its published point, PSGC geography, urban or rural class, and the boundary test S-1 (D-061).';
ALTER TABLE edu_access.`05-gold`.dim_school_location OWNER TO `reached-hq`;
