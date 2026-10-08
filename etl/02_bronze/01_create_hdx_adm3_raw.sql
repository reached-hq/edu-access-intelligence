-- Bronze table for hdx_boundaries. Generated from config/ingestion/hdx_boundaries.json:
--   python -m src.ingestion.cli ddl --source hdx_boundaries
-- Do not edit by hand; tests/test_ingestion_pipeline.py fails if it differs.
--
-- Provenance columns first, then every publisher column of every schema
-- version as text. NULL means the column is not in that year's file; ''
-- means the publisher left it blank.
CREATE SCHEMA IF NOT EXISTS edu_access.`02-bronze`;
ALTER SCHEMA edu_access.`02-bronze` OWNER TO `reached-hq`;

CREATE TABLE IF NOT EXISTS edu_access.`02-bronze`.hdx_adm3_raw (
  `source_id` STRING NOT NULL,
  `source_system` STRING NOT NULL,
  `source_url` STRING NOT NULL,
  `school_year` STRING NOT NULL,
  `delivery_version` INT NOT NULL,
  `source_archive` STRING NOT NULL,
  `source_archive_sha256` STRING NOT NULL,
  `source_file` STRING NOT NULL,
  `source_sha256` STRING NOT NULL,
  `source_row_number` BIGINT NOT NULL,
  `schema_version` STRING NOT NULL,
  `schema_fingerprint` STRING NOT NULL,
  `batch_id` STRING NOT NULL,
  `run_id` STRING NOT NULL,
  `ingested_at_utc` TIMESTAMP NOT NULL,
  `code_revision` STRING NOT NULL,
  `adm3_name` STRING,
  `adm3_name1` STRING,
  `adm3_name2` STRING,
  `adm3_name3` STRING,
  `adm3_pcode` STRING,
  `adm2_name` STRING,
  `adm2_name1` STRING,
  `adm2_name2` STRING,
  `adm2_name3` STRING,
  `adm2_pcode` STRING,
  `adm1_name` STRING,
  `adm1_name1` STRING,
  `adm1_name2` STRING,
  `adm1_name3` STRING,
  `adm1_pcode` STRING,
  `adm0_name` STRING,
  `adm0_name1` STRING,
  `adm0_name2` STRING,
  `adm0_name3` STRING,
  `adm0_pcode` STRING,
  `valid_on` STRING,
  `valid_to` STRING,
  `area_sqkm` STRING,
  `version` STRING,
  `lang` STRING,
  `lang1` STRING,
  `lang2` STRING,
  `lang3` STRING,
  `adm3_ref_name` STRING,
  `center_lat` STRING,
  `center_lon` STRING,
  `geometry` STRING
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5'
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`02-bronze`.hdx_adm3_raw OWNER TO `reached-hq`;
