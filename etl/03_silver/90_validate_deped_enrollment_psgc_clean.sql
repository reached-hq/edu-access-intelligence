-- Silver gate for deped_enrollment_psgc. Generated from config/ingestion/deped_enrollment_psgc.json
-- and config/mappings/deped_enrollment_psgc.json:
--   python -m src.silver.cli gate --source deped_enrollment_psgc > etl/03_silver/90_validate_deped_enrollment_psgc_clean.sql
-- Do not edit by hand; tests/test_silver.py fails if it differs.
-- Records every rule count, stops before publishing on FAIL, then publishes quarantine before clean.

DECLARE OR REPLACE VARIABLE silver_gate_started_at_utc TIMESTAMP;
SET VARIABLE silver_gate_started_at_utc = current_timestamp();

-- Materialize the aggregates once so every check reads the same one-row result.
CREATE OR REPLACE TABLE edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate USING DELTA AS
WITH cur AS (
  SELECT batch_id FROM edu_access.`01-control`.current_batches WHERE source_id = 'deped_enrollment_psgc'
), bronze AS (
  SELECT b.* FROM edu_access.`02-bronze`.deped_enrollment_psgc_raw AS b JOIN cur ON b.batch_id = cur.batch_id
), c AS (
  SELECT * FROM edu_access.`03-silver`.deped_enrollment_psgc_clean_candidate
), q AS (
  SELECT * FROM edu_access.`03-silver`.deped_enrollment_psgc_quarantine_candidate
), counts AS (
  SELECT
    (SELECT COUNT(*) FROM cur) AS current_batches,
    (SELECT COUNT_IF(source_row_kind = 'unit') FROM bronze) AS bronze_unit_rows,
    (SELECT COUNT_IF(source_row_kind <> 'unit') FROM bronze) AS bronze_other_rows,
    (SELECT COUNT(*) FROM c) AS clean_rows,
    (SELECT COUNT(*) FROM q) AS quarantine_rows,
    (SELECT COUNT(*) - COUNT(DISTINCT (school_year, school_id)) FROM c) AS duplicate_clean_ids,
    (SELECT COUNT_IF(NOT regexp_like(school_id, '^[0-9]{6}$')) FROM c) AS malformed_clean_ids,
    (SELECT COUNT_IF((psgc_region IS NOT NULL AND NOT regexp_like(psgc_region, '^[0-9]{10}$')) OR (psgc_province IS NOT NULL AND NOT regexp_like(psgc_province, '^[0-9]{10}$')) OR (psgc_city_municipality IS NOT NULL AND NOT regexp_like(psgc_city_municipality, '^[0-9]{10}$')) OR (psgc_barangay IS NOT NULL AND NOT regexp_like(psgc_barangay, '^[0-9]{10}$'))) FROM c) AS codes_not_ten_digits,
    (SELECT COUNT_IF(psgc_city_municipality_null_reason = 'unrecognized' OR psgc_barangay_null_reason = 'unrecognized') FROM c) AS unrecognized_code_values,
    (SELECT COUNT_IF((psgc_city_municipality IS NULL) <> (psgc_city_municipality_null_reason IS NOT NULL) OR (psgc_barangay IS NULL) <> (psgc_barangay_null_reason IS NOT NULL)) FROM c) AS null_reason_mismatches,
    (SELECT COUNT_IF((psgc_region IS NULL) <> (psgc_city_municipality IS NULL) OR (psgc_province IS NULL) <> (psgc_city_municipality IS NULL)) FROM c) AS levels_not_null_together,
    (SELECT COUNT_IF((longitude IS NULL) <> (latitude IS NULL)) FROM c) AS coordinates_not_in_pairs,
    (SELECT COUNT_IF(source_row_kind = 'unit' AND ((b.longitude NOT IN ('#N/A', '') AND NOT regexp_like(b.longitude, '^-?[0-9]+([.][0-9]+)?([eE]-?[0-9]+)?$')) OR (b.latitude NOT IN ('#N/A', '') AND NOT regexp_like(b.latitude, '^-?[0-9]+([.][0-9]+)?([eE]-?[0-9]+)?$')))) FROM bronze AS b) AS unrecognized_coordinates,
    (SELECT COALESCE(COUNT_IF(x.batch_id IS NULL OR x.delivery_version IS NULL OR x.schema_version IS NULL OR x.source_sha256 IS NULL OR x.source_row_number IS NULL OR x.run_id IS NULL OR x.cleaned_at_utc IS NULL OR x.code_revision IS NULL), 0) FROM c AS x) + (SELECT COALESCE(COUNT_IF(x.batch_id IS NULL OR x.delivery_version IS NULL OR x.schema_version IS NULL OR x.source_sha256 IS NULL OR x.source_row_number IS NULL OR x.run_id IS NULL OR x.cleaned_at_utc IS NULL OR x.code_revision IS NULL), 0) FROM q AS x) AS missing_lineage,
    (SELECT COALESCE(COUNT_IF(run_id <> :run_id), 0) FROM c) + (SELECT COALESCE(COUNT_IF(run_id <> :run_id), 0) FROM q) AS other_run_rows,
    (SELECT COUNT_IF(source_row_kind = 'unit' AND regexp_like(b.psgc_barangay, '^[0-9]{9,10}$') AND length(b.psgc_barangay) < 10) FROM bronze AS b) AS codes_padded,
    (SELECT COUNT_IF(psgc_city_municipality_null_reason = 'source_na') FROM c) AS city_source_na,
    (SELECT COUNT_IF(psgc_city_municipality_null_reason = 'not_in_workbook') FROM c) AS city_not_in_workbook,
    (SELECT COUNT_IF(psgc_barangay_null_reason = 'source_na') FROM c) AS barangay_source_na,
    (SELECT COUNT_IF(psgc_barangay_null_reason = 'not_in_workbook') FROM c) AS barangay_not_in_workbook,
    (SELECT COUNT_IF(psgc_recoded) FROM c) AS recoded,
    (SELECT COUNT_IF(barangay_outside_city) FROM c) AS barangay_outside_city,
    (SELECT COUNT_IF(coordinate_flag = 'missing') FROM c) AS coordinate_missing,
    (SELECT COUNT_IF(coordinate_flag = 'zero') FROM c) AS coordinate_zero,
    (SELECT COUNT_IF(coordinate_flag = 'outside_philippines') FROM c) AS coordinate_outside_philippines,
    (SELECT COUNT_IF(array_contains(quarantine_reasons, 'school_id_malformed')) FROM q) AS quarantine_school_id_malformed,
    (SELECT COUNT_IF(array_contains(quarantine_reasons, 'school_id_duplicated')) FROM q) AS quarantine_school_id_duplicated,
    (SELECT COUNT_IF(array_contains(quarantine_reasons, 'school_id_identical_copy')) FROM q) AS quarantine_school_id_identical_copy
)
SELECT cur.batch_id, counts.* FROM cur CROSS JOIN counts;

ALTER TABLE edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate OWNER TO `reached-hq`;

INSERT INTO edu_access.`01-control`.data_quality_results (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, batch_id, 'deped_enrollment_psgc', 'silver', table_name, check_name, status, expected, actual, current_timestamp(), :code_revision FROM (
SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'current_batch_present' AS check_name, CASE WHEN current_batches > 0 THEN 'PASS' ELSE 'FAIL' END AS status, '> 0' AS expected, CAST(current_batches AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'rows_reconcile' AS check_name, CASE WHEN clean_rows + quarantine_rows = bronze_unit_rows THEN 'PASS' ELSE 'FAIL' END AS status, '= bronze_unit_rows' AS expected, CAST(clean_rows + quarantine_rows AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'school_id_unique' AS check_name, CASE WHEN duplicate_clean_ids = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(duplicate_clean_ids AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'school_id_format' AS check_name, CASE WHEN malformed_clean_ids = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(malformed_clean_ids AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'codes_ten_digits' AS check_name, CASE WHEN codes_not_ten_digits = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(codes_not_ten_digits AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'code_values_recognized' AS check_name, CASE WHEN unrecognized_code_values = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(unrecognized_code_values AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'null_reason_matches_code' AS check_name, CASE WHEN null_reason_mismatches = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(null_reason_mismatches AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'levels_null_together' AS check_name, CASE WHEN levels_not_null_together = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(levels_not_null_together AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'coordinates_in_pairs' AS check_name, CASE WHEN coordinates_not_in_pairs = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(coordinates_not_in_pairs AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'coordinate_values_recognized' AS check_name, CASE WHEN unrecognized_coordinates = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(unrecognized_coordinates AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'lineage_complete' AS check_name, CASE WHEN missing_lineage = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(missing_lineage AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'rows_built_by_this_run' AS check_name, CASE WHEN other_run_rows = 0 THEN 'PASS' ELSE 'FAIL' END AS status, '= 0' AS expected, CAST(other_run_rows AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_bronze_unit_rows' AS check_name, CASE WHEN bronze_unit_rows = 60275 THEN 'PASS' ELSE 'WARN' END AS status, '60275' AS expected, CAST(bronze_unit_rows AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_bronze_other_rows' AS check_name, CASE WHEN bronze_other_rows = 10 THEN 'PASS' ELSE 'WARN' END AS status, '10' AS expected, CAST(bronze_other_rows AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_codes_padded' AS check_name, CASE WHEN codes_padded = 36010 THEN 'PASS' ELSE 'WARN' END AS status, '36010' AS expected, CAST(codes_padded AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_city_source_na' AS check_name, CASE WHEN city_source_na = 663 THEN 'PASS' ELSE 'WARN' END AS status, '663' AS expected, CAST(city_source_na AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_city_not_in_workbook' AS check_name, CASE WHEN city_not_in_workbook = 106 THEN 'PASS' ELSE 'WARN' END AS status, '106' AS expected, CAST(city_not_in_workbook AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_barangay_source_na' AS check_name, CASE WHEN barangay_source_na = 667 THEN 'PASS' ELSE 'WARN' END AS status, '667' AS expected, CAST(barangay_source_na AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_barangay_not_in_workbook' AS check_name, CASE WHEN barangay_not_in_workbook = 106 THEN 'PASS' ELSE 'WARN' END AS status, '106' AS expected, CAST(barangay_not_in_workbook AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_recoded' AS check_name, CASE WHEN recoded = 467 THEN 'PASS' ELSE 'WARN' END AS status, '467' AS expected, CAST(recoded AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_barangay_outside_city' AS check_name, CASE WHEN barangay_outside_city = 3 THEN 'PASS' ELSE 'WARN' END AS status, '3' AS expected, CAST(barangay_outside_city AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_coordinate_missing' AS check_name, CASE WHEN coordinate_missing = 13899 THEN 'PASS' ELSE 'WARN' END AS status, '13899' AS expected, CAST(coordinate_missing AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_coordinate_zero' AS check_name, CASE WHEN coordinate_zero = 6 THEN 'PASS' ELSE 'WARN' END AS status, '6' AS expected, CAST(coordinate_zero AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_clean_candidate' AS table_name, 'profiled_coordinate_outside_philippines' AS check_name, CASE WHEN coordinate_outside_philippines = 54 THEN 'PASS' ELSE 'WARN' END AS status, '54' AS expected, CAST(coordinate_outside_philippines AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_quarantine_candidate' AS table_name, 'profiled_quarantine_school_id_malformed' AS check_name, CASE WHEN quarantine_school_id_malformed = 1 THEN 'PASS' ELSE 'WARN' END AS status, '1' AS expected, CAST(quarantine_school_id_malformed AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_quarantine_candidate' AS table_name, 'profiled_quarantine_school_id_duplicated' AS check_name, CASE WHEN quarantine_school_id_duplicated = 0 THEN 'PASS' ELSE 'WARN' END AS status, '0' AS expected, CAST(quarantine_school_id_duplicated AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_quarantine_candidate' AS table_name, 'profiled_quarantine_school_id_identical_copy' AS check_name, CASE WHEN quarantine_school_id_identical_copy = 1 THEN 'PASS' ELSE 'WARN' END AS status, '1' AS expected, CAST(quarantine_school_id_identical_copy AS STRING) AS actual FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
  UNION ALL SELECT batch_id, 'edu_access.03-silver.deped_enrollment_psgc_quarantine_candidate', 'quarantine_rate', CASE WHEN quarantine_rows = 0 THEN 'PASS' WHEN quarantine_rows * 100 > bronze_unit_rows * 1 THEN 'FAIL' ELSE 'WARN' END, '0 (FAIL above 1% of ' || CAST(bronze_unit_rows AS STRING) || ')', CAST(quarantine_rows AS STRING) FROM edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate
) AS results;

MERGE INTO edu_access.`01-control`.pipeline_runs AS t USING (SELECT :run_id AS run_id, COUNT_IF(status = 'FAIL') AS fails FROM edu_access.`01-control`.data_quality_results WHERE run_id = :run_id AND source_id = 'deped_enrollment_psgc' AND layer = 'silver' AND checked_at_utc >= session.silver_gate_started_at_utc) AS s
ON t.run_id = s.run_id AND t.pipeline_name = 'silver_build' AND t.source_id = 'deped_enrollment_psgc' WHEN MATCHED AND s.fails > 0 THEN UPDATE SET status = 'failed', finished_at_utc = current_timestamp(), failure_stage = 'gate', error_message = CAST(s.fails AS STRING) || ' FAIL result(s) in data_quality_results';

SELECT CASE WHEN COUNT(*) > 0 THEN raise_error('Silver gate failed for deped_enrollment_psgc: ' || CAST(COUNT(*) AS STRING) || ' FAIL result(s)') END FROM edu_access.`01-control`.data_quality_results WHERE run_id = :run_id AND source_id = 'deped_enrollment_psgc' AND layer = 'silver' AND status = 'FAIL' AND checked_at_utc >= session.silver_gate_started_at_utc;

CREATE OR REPLACE TABLE edu_access.`03-silver`.deped_enrollment_psgc_quarantine USING DELTA AS SELECT * FROM edu_access.`03-silver`.deped_enrollment_psgc_quarantine_candidate;
ALTER TABLE edu_access.`03-silver`.deped_enrollment_psgc_quarantine OWNER TO `reached-hq`;

CREATE OR REPLACE TABLE edu_access.`03-silver`.deped_enrollment_psgc_clean USING DELTA AS SELECT * FROM edu_access.`03-silver`.deped_enrollment_psgc_clean_candidate;
ALTER TABLE edu_access.`03-silver`.deped_enrollment_psgc_clean OWNER TO `reached-hq`;

MERGE INTO edu_access.`01-control`.pipeline_runs AS t USING (SELECT :run_id AS run_id) AS s ON t.run_id = s.run_id AND t.pipeline_name = 'silver_build' AND t.source_id = 'deped_enrollment_psgc' WHEN MATCHED THEN UPDATE SET status = 'succeeded', finished_at_utc = current_timestamp(), failure_stage = NULL, error_message = NULL;

DROP TABLE IF EXISTS edu_access.`03-silver`.deped_enrollment_psgc_gate_summary_candidate;
