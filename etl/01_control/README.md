# 01 Control

Tables that record pipeline runs, ingestion batches, and data-quality results. They answer "was this file already loaded?", "what happened in that run?", "which Bronze rows may downstream read?", and "what did Silver last build?".

| File | Object | Holds |
|---|---|---|
| `01_create_pipeline_runs.sql` | `pipeline_runs` | One row per run: source, environment, status, timings, batch counts, failure, `code_revision` |
| `02_create_ingestion_batches.sql` | `ingestion_batches` | The processed-file manifest: one row per distinct archive (by SHA-256) and its current state. Upserted with MERGE |
| `03_create_ingestion_batch_attempts.sql` | `ingestion_batch_attempts` | Append-only: one row per batch per run, including skips and blocks |
| `04_create_data_quality_results.sql` | `data_quality_results` | Append-only: one row per check (PASS, WARN, FAIL), counts only, never row values. Columns follow #42 |
| `05_create_current_batches.sql` | `current_batches` (view) | For each source and school year, the latest succeeded delivery version: what downstream reads (D-015) |
| `06_create_layer_builds.sql` | `layer_builds` | Append-only: one row per Silver run per source, `build` or `skip`, with the batches it read, the rules fingerprint, and row counts. What a run compares with to skip (D-022) |

Batch statuses: `validating` → `loading` → `succeeded`, or `failed` (retried by the next run), `blocked` (not an approved delivery), `skipped` (a re-zipped copy of an approved file). The `succeeded` status is written last, after Bronze is reconciled, so it marks the batch as committed (D-015).

Files follow `NN_<verb>_<object>.sql` (see [File naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)). The Databricks job runs them as explicit bootstrap tasks before its source lanes. Standalone ingestion creates them automatically unless `--no-setup` is passed, so a manual first run needs no separate setup.
