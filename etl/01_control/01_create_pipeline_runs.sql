-- One row per invocation of an ingestion pipeline: who ran which code, when,
-- and how it ended. Written at start (status 'running') and updated at the end.
-- A run that is still 'running' with no finished_at_utc was interrupted.
CREATE SCHEMA IF NOT EXISTS edu_access.`01-control`;
ALTER SCHEMA edu_access.`01-control` OWNER TO `reached-hq`;

CREATE TABLE IF NOT EXISTS edu_access.`01-control`.pipeline_runs (
  run_id STRING NOT NULL,              -- bronze_ingest: UUID, one per load. silver_build: the job run id,
                                       -- shared by every source's build in that job run (D-020)
  pipeline_name STRING NOT NULL,       -- 'bronze_ingest' (a source's Bronze load) or 'silver_build'
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
  code_revision STRING NOT NULL,       -- commit that ran; 'UNSET' if unknown
  job_run_id STRING                    -- Databricks job run that ran this load; its Bronze gate task
                                       -- writes data_quality_results under this run_id. NULL for manual runs.
                                       -- silver_build: the same job run as run_id
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`01-control`.pipeline_runs OWNER TO `reached-hq`;
