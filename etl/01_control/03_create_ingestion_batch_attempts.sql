-- Append-only audit log: one row per batch per run, including skips and
-- blocks. ingestion_batches holds the current state; this table holds what
-- happened, so a skipped rerun leaves evidence.
CREATE TABLE IF NOT EXISTS edu_access.`01-control`.ingestion_batch_attempts (
  run_id STRING NOT NULL,
  batch_id STRING NOT NULL,
  source_id STRING NOT NULL,
  school_year STRING,
  archive_name STRING NOT NULL,
  archive_sha256 STRING NOT NULL,
  action STRING NOT NULL,              -- load | retry | rerun | skip | block
  load_type STRING,                    -- initial | incremental | backfill | revision
  outcome STRING NOT NULL,             -- succeeded | failed | skipped | blocked
  started_at_utc TIMESTAMP NOT NULL,
  finished_at_utc TIMESTAMP NOT NULL,
  duration_seconds DOUBLE NOT NULL,
  source_rows BIGINT,
  rows_inserted BIGINT,
  bronze_rows BIGINT,
  failure_stage STRING,
  error_code STRING,
  error_message STRING,
  environment STRING NOT NULL,
  code_revision STRING NOT NULL
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`01-control`.ingestion_batch_attempts OWNER TO `reached-hq`;
