-- One row per invocation of an ingestion pipeline: who ran which code, when,
-- and how it ended. Written at start (status 'running') and updated at the end.
-- A run that is still 'running' with no finished_at_utc was interrupted.
CREATE SCHEMA IF NOT EXISTS edu_access.`01-control`;

CREATE TABLE IF NOT EXISTS edu_access.`01-control`.pipeline_runs (
  run_id STRING NOT NULL,              -- UUID, one per invocation
  pipeline_name STRING NOT NULL,       -- e.g. 'bronze_ingest'
  source_id STRING NOT NULL,
  environment STRING NOT NULL,         -- local | dev | prod (deploy target, not a branch)
  status STRING NOT NULL,              -- running | succeeded | failed
  started_at_utc TIMESTAMP NOT NULL,
  finished_at_utc TIMESTAMP,
  duration_seconds DOUBLE,
  deliveries_found INT,                -- distinct archives discovered in the landing folder
  batches_loaded INT,                  -- loaded and reconciled in this run
  batches_skipped INT,                 -- already loaded, or a re-zipped copy of a loaded file
  batches_failed INT,                  -- validation, load, or reconciliation failed
  batches_blocked INT,                 -- not approved: unknown file or changed checksum
  failure_stage STRING,
  error_message STRING,
  code_revision STRING NOT NULL        -- commit that ran; 'UNSET' if unknown
);
