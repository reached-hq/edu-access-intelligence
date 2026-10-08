-- Bronze table for psa_psgc. Generated from config/ingestion/psa_psgc.json:
--   python -m src.ingestion.cli ddl --source psa_psgc
-- Do not edit by hand; tests/test_ingestion_pipeline.py fails if it differs.
--
-- Provenance columns first, then every publisher column of every schema
-- version as text. NULL means the column is not in that year's file; ''
-- means the publisher left it blank.
CREATE SCHEMA IF NOT EXISTS edu_access.`02-bronze`;
ALTER SCHEMA edu_access.`02-bronze` OWNER TO `reached-hq`;

CREATE TABLE IF NOT EXISTS edu_access.`02-bronze`.psa_psgc_raw (
  `source_id` STRING NOT NULL,
  `source_system` STRING NOT NULL,
  `source_url` STRING NOT NULL,
  `publication_period` STRING NOT NULL,
  `publication_date` STRING NOT NULL,
  `delivery_version` INT NOT NULL,
  `source_file` STRING NOT NULL,
  `source_sha256` STRING NOT NULL,
  `source_sheet` STRING NOT NULL,
  `source_row_number` BIGINT NOT NULL,
  `schema_version` STRING NOT NULL,
  `schema_fingerprint` STRING NOT NULL,
  `batch_id` STRING NOT NULL,
  `run_id` STRING NOT NULL,
  `ingested_at_utc` TIMESTAMP NOT NULL,
  `code_revision` STRING NOT NULL,
  `psgc_code` STRING,
  `name` STRING,
  `correspondence_code` STRING,
  `geographic_level` STRING,
  `old_names` STRING,
  `city_class` STRING,
  `income_classification` STRING,
  `urban_rural` STRING,
  `population` STRING,
  `column_j_footnote` STRING,
  `status` STRING
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5'
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`02-bronze`.psa_psgc_raw OWNER TO `reached-hq`;
