-- Gold gate for dim_school_location (#217). Checks dim_school_location_candidate against the tables it was
-- built from, writes every result to data_quality_results (layer 'gold'), stops on any FAIL, and only then
-- publishes dim_school_location. A FAIL keeps the last good build and stops nothing else: no other task
-- waits for this one.
--
-- FAIL: a repeated or NULL key; a row count other than deped_psgc_coordinates_clean's; a school not in
-- dim_school; a longitude, latitude or coordinate_flag that differs from Silver; a boundary_status outside
-- the five values, or one that does not follow its inputs (no_usable_point exactly when coordinate_flag is
-- set; no_matched_city exactly when an unflagged school has no matched SY 2023-24 city; inside or outside
-- only when that city has a boundary, no_boundary only when it has none); an upstream run that did not
-- succeed.
-- Counts only (PASS): schools per boundary_status.
--
-- The point-in-boundary result itself is not recomputed here, to run the spatial work once per refresh;
-- tests/test_gold_dim_school_location.py checks it on known shapes.

DECLARE OR REPLACE VARIABLE gold_gate_started_at_utc TIMESTAMP;
SET VARIABLE gold_gate_started_at_utc = current_timestamp();
DECLARE OR REPLACE VARIABLE gold_gate_summary STRING;
SET VARIABLE gold_gate_summary = '`edu_access`.`05-gold`.`dim_school_location_gate_summary_r_' || sha2(:run_id, 256) || '`';
DECLARE OR REPLACE VARIABLE gold_gate_owner_sql STRING;

-- COUNT_IF is wrapped in COALESCE: over no rows DuckDB returns NULL, Databricks 0.
-- The one-row summary the checks read is written to a table, once, as the other Gold gates do (read many
-- times as a temporary view, Databricks SQL's optimizer failed; dim_barangay, 2026-10-20). The table is this
-- run's own (its name holds a hash of run_id) and is dropped once the checks are recorded.
CREATE OR REPLACE TABLE IDENTIFIER(session.gold_gate_summary) USING DELTA COMMENT 'Internal unpublished one-row summary for one dim_school_location gate. The gate drops it once its checks are recorded in data_quality_results.' AS
WITH dimension AS (
  SELECT * FROM edu_access.`05-gold`.dim_school_location_candidate
),
location AS (
  SELECT school_id, longitude, latitude, coordinate_flag FROM edu_access.`03-silver`.deped_psgc_coordinates_clean
),
city AS (
  SELECT school_id, psgc_code AS city_mun_psgc_code
  FROM edu_access.`04-integration`.deped_school_psgc_map
  WHERE school_year = '2023-24' AND geographic_level = 'city_mun' AND match_status = 'matched'
),
hdx_release AS (
  SELECT MAX(source_reference_date) AS source_reference_date FROM edu_access.`04-integration`.hdx_adm3_psgc_map
),
bounded_city AS (
  SELECT DISTINCT m.psgc_code AS city_mun_psgc_code
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map AS m
  JOIN hdx_release AS r ON r.source_reference_date = m.source_reference_date
  JOIN edu_access.`03-silver`.hdx_adm3_clean AS h ON h.adm3_pcode = m.adm3_pcode AND h.valid_on = m.source_reference_date
  WHERE m.match_status = 'matched' AND h.geometry_is_valid
),
inputs AS (
  SELECT d.school_id, d.coordinate_flag, d.boundary_status,
         c.school_id IS NOT NULL AS has_city, bc.city_mun_psgc_code IS NOT NULL AS has_boundary
  FROM dimension AS d
  LEFT JOIN city AS c ON c.school_id = d.school_id
  LEFT JOIN bounded_city AS bc ON bc.city_mun_psgc_code = c.city_mun_psgc_code
)
SELECT
  (SELECT COUNT(*) FROM dimension) AS dimension_rows,
  (SELECT COUNT(*) FROM location) AS source_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT school_id) FROM dimension) AS duplicate_keys,
  (SELECT COALESCE(COUNT_IF(school_id IS NULL), 0) FROM dimension) AS null_keys,
  (SELECT COUNT(*) FROM dimension AS d LEFT JOIN edu_access.`05-gold`.dim_school AS s ON s.school_id = d.school_id
    WHERE s.school_id IS NULL) AS schools_not_in_dim_school,
  (SELECT COUNT(*) FROM location AS l LEFT JOIN dimension AS d ON d.school_id = l.school_id
    WHERE d.school_id IS NULL OR d.longitude IS DISTINCT FROM l.longitude OR d.latitude IS DISTINCT FROM l.latitude
       OR d.coordinate_flag IS DISTINCT FROM l.coordinate_flag) AS rows_not_matching_source,
  (SELECT COALESCE(COUNT_IF(boundary_status IS NULL OR boundary_status NOT IN ('inside', 'outside', 'no_usable_point', 'no_matched_city', 'no_boundary')), 0) FROM dimension) AS bad_boundary_status,
  (SELECT COALESCE(COUNT_IF((coordinate_flag IS NOT NULL) <> (boundary_status = 'no_usable_point')), 0) FROM inputs) AS usable_point_mismatches,
  (SELECT COALESCE(COUNT_IF(coordinate_flag IS NULL AND (NOT has_city) <> (boundary_status = 'no_matched_city')), 0) FROM inputs) AS matched_city_mismatches,
  (SELECT COALESCE(COUNT_IF(coordinate_flag IS NULL AND has_city
                   AND (boundary_status IN ('inside', 'outside')) <> has_boundary), 0) FROM inputs) AS boundary_mismatches,
  (SELECT COALESCE(COUNT_IF(boundary_status = 'inside'), 0) FROM dimension) AS status_inside,
  (SELECT COALESCE(COUNT_IF(boundary_status = 'outside'), 0) FROM dimension) AS status_outside,
  (SELECT COALESCE(COUNT_IF(boundary_status = 'no_usable_point'), 0) FROM dimension) AS status_no_usable_point,
  (SELECT COALESCE(COUNT_IF(boundary_status = 'no_matched_city'), 0) FROM dimension) AS status_no_matched_city,
  (SELECT COALESCE(COUNT_IF(boundary_status = 'no_boundary'), 0) FROM dimension) AS status_no_boundary;
SET VARIABLE gold_gate_owner_sql = 'ALTER TABLE ' || session.gold_gate_summary || ' OWNER TO `reached-hq`';
EXECUTE IMMEDIATE gold_gate_owner_sql;

INSERT INTO edu_access.`01-control`.data_quality_results (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'dim_school_location', 'gold', 'edu_access.05-gold.dim_school_location', check_name, status, expected, actual, current_timestamp(), :code_revision
FROM (
  SELECT 'rows_reconcile' AS check_name, CASE WHEN dimension_rows = source_rows THEN 'PASS' ELSE 'FAIL' END AS status, CAST(source_rows AS STRING) AS expected, CAST(dimension_rows AS STRING) AS actual FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'key_unique', CASE WHEN duplicate_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(duplicate_keys AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'key_not_null', CASE WHEN null_keys = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(null_keys AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'school_in_dim_school', CASE WHEN schools_not_in_dim_school = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(schools_not_in_dim_school AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'values_match_source', CASE WHEN rows_not_matching_source = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(rows_not_matching_source AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'boundary_status_allowed', CASE WHEN bad_boundary_status = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(bad_boundary_status AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'boundary_status_follows_inputs', CASE WHEN usable_point_mismatches + matched_city_mismatches + boundary_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END, '0',
                   CAST(usable_point_mismatches + matched_city_mismatches + boundary_mismatches AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_inside_boundary', 'PASS', CAST(NULL AS STRING), CAST(status_inside AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_outside_boundary', 'PASS', CAST(NULL AS STRING), CAST(status_outside AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_no_usable_point', 'PASS', CAST(NULL AS STRING), CAST(status_no_usable_point AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_no_matched_city', 'PASS', CAST(NULL AS STRING), CAST(status_no_matched_city AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
  UNION ALL SELECT 'schools_no_boundary', 'PASS', CAST(NULL AS STRING), CAST(status_no_boundary AS STRING) FROM IDENTIFIER(session.gold_gate_summary)
) AS results;

-- Integrity rule 1 of the metric specification: one result per distinct upstream run_id read, PASS only
-- when that run succeeded in pipeline_runs (D-025), so the build never trusts a run that did not publish.
INSERT INTO edu_access.`01-control`.data_quality_results (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, 'dim_school_location', 'gold', 'edu_access.05-gold.dim_school_location', 'upstream_run_' || u.input_table,
       CASE WHEN p.run_id IS NULL THEN 'FAIL' ELSE 'PASS' END, 'succeeded ' || u.pipeline_name, u.upstream_run_id,
       current_timestamp(), :code_revision
FROM (
  SELECT DISTINCT 'deped_psgc_coordinates_clean' AS input_table, 'silver_build' AS pipeline_name, 'deped_psgc_coordinates' AS source_id, run_id AS upstream_run_id
  FROM edu_access.`03-silver`.deped_psgc_coordinates_clean
  UNION ALL
  SELECT DISTINCT 'deped_school_psgc_map', 'integration_build', 'deped_enrollment', run_id
  FROM edu_access.`04-integration`.deped_school_psgc_map WHERE school_year = '2023-24'
  UNION ALL
  SELECT DISTINCT 'hdx_adm3_psgc_map', 'integration_build', 'hdx_boundaries', run_id
  FROM edu_access.`04-integration`.hdx_adm3_psgc_map
) AS u
LEFT JOIN (
  SELECT DISTINCT run_id, pipeline_name, source_id
  FROM edu_access.`01-control`.pipeline_runs
  WHERE status = 'succeeded'
) AS p ON p.run_id = u.upstream_run_id AND p.pipeline_name = u.pipeline_name AND p.source_id = u.source_id;

-- Every check is recorded, so the summary is no longer needed, whether the gate passes or fails.
DROP TABLE IF EXISTS IDENTIFIER(session.gold_gate_summary);

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Gold gate failed for dim_school_location: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s) in data_quality_results for run ' || :run_id) END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = 'dim_school_location' AND layer = 'gold' AND status = 'FAIL'
  AND checked_at_utc >= session.gold_gate_started_at_utc;

-- Every check passed: publish.
CREATE OR REPLACE TABLE edu_access.`05-gold`.dim_school_location USING DELTA AS
SELECT * FROM edu_access.`05-gold`.dim_school_location_candidate;

COMMENT ON TABLE edu_access.`05-gold`.dim_school_location IS 'One public school with a published location (SY 2023-24, NSBI as of 2025-07-07): its point, coordinate_flag, and boundary_status (S-1 at city level). Joins dim_school on school_id and carries no PSGC code (#217).';
ALTER TABLE edu_access.`05-gold`.dim_school_location OWNER TO `reached-hq`;
