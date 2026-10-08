-- Bronze table for psa_poverty_stat. Generated from config/ingestion/psa_poverty_stat.json:
--   python -m src.ingestion.cli ddl --source psa_poverty_stat
-- Do not edit by hand; tests/test_ingestion_pipeline.py fails if it differs.
--
-- Provenance columns first, then every publisher column of every schema
-- version as text. NULL means the column is not in that year's file; ''
-- means the publisher left it blank.
CREATE SCHEMA IF NOT EXISTS edu_access.`02-bronze`;
ALTER SCHEMA edu_access.`02-bronze` OWNER TO `reached-hq`;

CREATE TABLE IF NOT EXISTS edu_access.`02-bronze`.psa_poverty_stat_raw (
  `source_id` STRING NOT NULL,
  `source_system` STRING NOT NULL,
  `source_url` STRING NOT NULL,
  `logical_dataset` STRING NOT NULL,
  `estimate_years_covered` STRING NOT NULL,
  `delivery_version` INT NOT NULL,
  `source_file` STRING NOT NULL,
  `source_sha256` STRING NOT NULL,
  `source_sheet` STRING NOT NULL,
  `source_row_number` BIGINT NOT NULL,
  `source_row_kind` STRING NOT NULL,
  `schema_version` STRING NOT NULL,
  `schema_fingerprint` STRING NOT NULL,
  `batch_id` STRING NOT NULL,
  `run_id` STRING NOT NULL,
  `ingested_at_utc` TIMESTAMP NOT NULL,
  `code_revision` STRING NOT NULL,
  `PSGC ID` STRING,
  `Region/Province` STRING,
  `Municipality/City` STRING,
  `Poverty Incidence 2018` STRING,
  `Poverty Incidence 2021` STRING,
  `Poverty Incidence 2023` STRING,
  `Coefficient of Variation 2018` STRING,
  `Coefficient of Variation 2021` STRING,
  `Coefficient of Variation 2023` STRING,
  `Standard Error 2018` STRING,
  `Standard Error 2021` STRING,
  `Standard Error 2023` STRING,
  `90% Confidence Interval Lower Limit 2018` STRING,
  `90% Confidence Interval Upper Limit 2018` STRING,
  `90% Confidence Interval Lower Limit 2021` STRING,
  `90% Confidence Interval Upper Limit 2021` STRING,
  `90% Confidence Interval Lower Limit 2023` STRING,
  `90% Confidence Interval Upper Limit 2023` STRING
)
USING DELTA
TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5'
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`02-bronze`.psa_poverty_stat_raw OWNER TO `reached-hq`;
