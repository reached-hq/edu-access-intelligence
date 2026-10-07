-- One row per check per batch per run. PASS: as expected. WARN: recorded,
-- rows still loaded (e.g. publisher duplicates, kept for Silver to resolve).
-- FAIL: the batch is not marked succeeded, so nothing downstream reads it.
-- Results hold counts and rules, never row values. Columns follow #42.
CREATE TABLE IF NOT EXISTS edu_access.`01-control`.data_quality_results (
  run_id STRING NOT NULL,
  batch_id STRING,
  source_id STRING,
  layer STRING NOT NULL,               -- bronze for these checks
  table_name STRING NOT NULL,
  check_name STRING NOT NULL,
  status STRING NOT NULL,              -- PASS | WARN | FAIL
  expected STRING,
  actual STRING,
  checked_at_utc TIMESTAMP NOT NULL,
  code_revision STRING NOT NULL
);

-- Owned by the team group, not by whoever ran the job first (D-009).
ALTER TABLE edu_access.`01-control`.data_quality_results OWNER TO `reached-hq`;
