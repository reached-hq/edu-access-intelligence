-- The processed-file manifest: one row per distinct archive (by SHA-256) ever
-- seen, holding its current state. Upserted with MERGE on batch_id.
--
-- Bronze has no cross-table transaction with this table, so this row is the
-- commit marker: downstream reads only Bronze rows whose batch has
-- status = 'succeeded' (see 05_create_current_batches.sql).
CREATE TABLE IF NOT EXISTS edu_access.`01-control`.ingestion_batches (
  batch_id STRING NOT NULL,            -- <source_id>__<school_year>__<archive_sha256[:12]>; same file, same id
  source_id STRING NOT NULL,
  school_year STRING,                  -- from the file names; NULL if they could not be read
  delivery_version INT,                -- 1 for a school year's first delivery, 2+ for revisions
  supersedes_archive_sha256 STRING,    -- the delivery a revision replaces; both stay in Bronze
  load_type STRING,                    -- initial | incremental | backfill | revision
  status STRING NOT NULL,              -- validating | loading | succeeded | failed | blocked | skipped
  archive_path STRING NOT NULL,        -- relative to the landing folder
  archive_name STRING NOT NULL,
  archive_sha256 STRING NOT NULL,
  source_file STRING,                  -- data file inside the archive
  source_sha256 STRING,
  encoding STRING,
  schema_version STRING,
  schema_fingerprint STRING,
  expected_rows BIGINT,                -- row_count approved in the source contract
  source_rows BIGINT,                  -- data rows read from the file
  rows_inserted BIGINT,                -- Bronze rows inserted by the latest attempt
  bronze_rows BIGINT,                  -- Bronze rows for this file after the latest attempt
  rejected_rows BIGINT,                -- always 0: Bronze rejects whole batches, never single rows
  attempt_count INT NOT NULL,
  first_run_id STRING NOT NULL,
  last_run_id STRING NOT NULL,
  first_attempt_at_utc TIMESTAMP NOT NULL,
  last_attempt_at_utc TIMESTAMP NOT NULL,
  succeeded_at_utc TIMESTAMP,
  failure_stage STRING,
  error_code STRING,
  error_message STRING,
  environment STRING NOT NULL,
  code_revision STRING NOT NULL        -- commit of the latest attempt
);
