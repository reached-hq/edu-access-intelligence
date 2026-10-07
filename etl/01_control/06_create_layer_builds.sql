-- Append-only: one row per Silver (later Gold) run per source, saying whether it
-- rebuilt the source's tables or skipped, from which Bronze batches, and with
-- which rules. It answers "what did Silver last build?", so a run whose inputs
-- and rules are unchanged since the last successful build can skip the work.
-- The run itself is in pipeline_runs (pipeline_name 'silver_build'), whose
-- status 'succeeded' is written last and marks the build as committed.
CREATE TABLE IF NOT EXISTS edu_access.`01-control`.layer_builds (
  run_id STRING NOT NULL,              -- the Silver run; stamped on every row it built
  layer STRING NOT NULL,               -- silver
  source_id STRING NOT NULL,
  target_table STRING NOT NULL,        -- e.g. edu_access.03-silver.deped_enrollment_clean
  quarantine_table STRING,
  action STRING NOT NULL,              -- build | skip
  reason STRING NOT NULL,              -- first_build | bronze_changed | rules_changed | previous_run_incomplete | tables_missing | forced | unchanged
  outcome STRING NOT NULL,             -- succeeded | failed | skipped
  input_batch_ids STRING NOT NULL,     -- current_batches read, sorted, comma-separated
  rules_fingerprint STRING NOT NULL,   -- SHA-256 of the build and gate SQL that ran
  bronze_rows BIGINT,                  -- current Bronze rows read (NULL on skip)
  clean_rows BIGINT,
  quarantined_rows BIGINT,
  cleaned_at_utc TIMESTAMP,            -- the one timestamp on every row built (NULL on skip)
  build_seconds DOUBLE,                -- building both tables
  gate_seconds DOUBLE,                 -- the column-type checks and the gate
  started_at_utc TIMESTAMP NOT NULL,
  finished_at_utc TIMESTAMP NOT NULL,
  duration_seconds DOUBLE NOT NULL,
  failure_stage STRING,
  error_message STRING,                -- counts and identifiers only, never row values
  environment STRING NOT NULL,
  code_revision STRING NOT NULL
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`01-control`.layer_builds OWNER TO `reached-hq`;
