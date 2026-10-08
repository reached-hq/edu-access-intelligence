# Evidence: the edu_access_pipeline DAG runs every Bronze lane and gate on Databricks, a second run inserts nothing, and each load joins to its gate

Issue #47 · PR #113 · Databricks `dev` · 2026-10-08, Manila time (UTC+8; UTC in brackets) · run by @hyenalouise

## The claim

On Databricks `dev`, the job `edu_access_pipeline` (D-020) runs the control setup once, then the four delivered sources as independent lanes (raw-table DDL → Python load with `--no-gate --no-setup` → Bronze gate as its own SQL task), with every placeholder task disabled. Running it twice inserts no Bronze rows, every Bronze gate passes, and every load's `pipeline_runs` row joins to its gate task's rows in `data_quality_results` through the new `job_run_id` column, which the first run added to the existing shared table.

## What was run

The job `[dev ina_magno] edu_access_pipeline` (job ID `651937364323543`), deployed from branch `feat/47-gate-sql-tasks` at commit `819a2489f95c322477c99858a236a2aa5687a8ae`, after merging `main` (#109, #111). The deployed job's `git_source.git_commit` was that commit, read back from the job; every load recorded it as `code_revision`. 62 tasks: 17 enabled (5 control DDL, 4 raw-table DDL, 4 loads, 4 Bronze gates), 45 disabled placeholders. The run was announced to the team beforehand.

```bash
databricks bundle validate --target dev --profile reached-hq
```

```bash
databricks bundle deploy --target dev --profile reached-hq
```

```bash
databricks bundle run edu_access_pipeline --target dev --profile reached-hq
```

The last command was run twice. The landing folder held the same approved deliveries both times, all loaded by earlier runs (#11, #109, #111).

| | Run 1 | Run 2 |
|---|---|---|
| Job run (`job_run_id`) | `129683751826546` | `871133851621812` |
| Whole job | 17:25:17 to 17:29:47 (09:25:17 to 09:29:47 UTC), 4 min 30 s, `SUCCESS` | 17:30:44 to 17:32:46 (09:30:44 to 09:32:46 UTC), 2 min 2 s, `SUCCESS` |
| Tasks | 17 `SUCCESS` on the first attempt, 45 disabled | same |
| DepEd enrollment | skip ×3, 0 inserted (Bronze 60,167 / 60,129 / 60,204) | same |
| DepEd facilities | skip, 0 inserted (Bronze 60,167) | same |
| PSA Poverty Stat | skip, 0 inserted (Bronze 1,641) | same |
| PSA PSGC | skip, 0 inserted (Bronze 43,768) | same |

Every load printed "already loaded; same SHA-256". The four loads ran in parallel after their own raw-table DDL; no lane waited for another: their `pipeline_runs` rows started within 0.61 s of each other in run 1 (09:26:58.133 to 09:26:58.741 UTC) and within 0.25 s in run 2 (09:31:27.673 to 09:31:27.918 UTC).

Run 1 task graph: control setup, then four parallel lanes, every enabled task green
<img width="1470" height="624" alt="image" src="https://github.com/user-attachments/assets/956d0dee-2ee6-4e57-946e-22835651fc97" />
<br>

Run 2 task graph: the same 17 tasks green
<img width="1470" height="619" alt="image" src="https://github.com/user-attachments/assets/a4af5aea-d278-4d33-8326-e1d4dcf512f7" />


## Results

Queried read-only through the SQL warehouse after both runs, on 2026-10-08. The queries are in [docs/operations/ingestion.md](../../docs/operations/ingestion.md#running-on-databricks).

### 1. The new column

`DESCRIBE TABLE edu_access.`01-control`.pipeline_runs` ends with `job_run_id string`. The table predates the column, and the job's `CREATE TABLE IF NOT EXISTS` adds none, so the first run's loads added it (`control.add_missing_columns`). All four loads started in parallel and none failed or retried, so adding the column did not break a parallel lane. Whether two lanes actually raced for it cannot be seen from the run. The 48 `pipeline_runs` rows written before these runs all have `job_run_id` NULL.

<img width="1023" height="397" alt="image" src="https://github.com/user-attachments/assets/4e1df786-8b65-4a0c-89cc-9e3676a05463" />

### 2. Each load joins to its gate

| Source | Run 1: load, gate checks, FAIL | Run 2: load, gate checks, FAIL |
|---|---|---|
| `deped_enrollment` | `succeeded`, 3, 0 | `succeeded`, 3, 0 |
| `deped_facilities` | `succeeded`, 3, 0 | `succeeded`, 3, 0 |
| `psa_poverty_stat` | `succeeded`, 3, 0 | `succeeded`, 3, 0 |
| `psa_psgc` | `succeeded`, 3, 0 | `succeeded`, 3, 0 |

Gate checks are the rows under `job_run_id`; FAIL counts include the load's own checks under its `run_id`. No WARN in either run: a skip checks no batch. For the latest job run the four sources together recorded 4 × PASS for each of `approved_deliveries_present`, `no_pipeline_duplicates`, `rows_have_a_known_batch` and `succeeded_batches_reconcile`. No FAIL was written to `data_quality_results` after 09:00 UTC.

<img width="1023" height="451" alt="image" src="https://github.com/user-attachments/assets/0175287c-c69b-40e4-b31b-23cac20f02b5" />
<br>

A load's true outcome: 8 rows, each with 3 gate checks and 0 FAIL
<img width="1018" height="449" alt="image" src="https://github.com/user-attachments/assets/f25c7cbe-5a4d-4e29-aec4-c4d96d419c38" />
<br>

Checks for the latest job run: 16 rows, all PASS
<img width="1016" height="586" alt="image" src="https://github.com/user-attachments/assets/77b94a89-093e-4f96-83f9-554d31a5d4de" />
<br>

### 3. Nothing inserted (idempotency)

| Bronze table | Rows | Rows ingested after 09:00 UTC |
|---|---|---|
| `deped_enrollment_raw` | 180,500 | 0 |
| `deped_facilities_raw` | 60,167 | 0 |
| `psa_poverty_stat_raw` | 1,641 | 0 |
| `psa_psgc_raw` | 43,768 | 0 |

`ingestion_batch_attempts` for both job runs holds only `skip` / `skipped` attempts with 0 rows inserted: enrollment 3, the other sources 1 each, per run.

Bronze row counts, and 0 rows ingested after 09:00 UTC in every table
<img width="1021" height="388" alt="image" src="https://github.com/user-attachments/assets/77b3b2ab-ad83-4bb4-ac4c-7a3faa80b9b4" />
<br>

Attempts of both job runs: only skip / skipped, 0 inserted
<img width="1023" height="416" alt="image" src="https://github.com/user-attachments/assets/33ac036d-c702-4b2a-979e-9c0fedfcf2ed" />


## The same job, locally, on the real files

`python -m src.job.local_run` ran the same DAG twice on a fresh DuckDB file with the real raw deliveries, at commit `75c3a31` (the code of `819a248`; only documentation changed after it). Every enabled task succeeded both times. Run 1 loaded enrollment 3, facilities 1, poverty 1 and PSGC 1 batches (180,500 / 60,167 / 1,641 / 43,768 rows); run 2 loaded 0 and skipped all six; every Bronze row has run 1's `run_id`. Every lane in both runs joined to 3 gate checks with 0 FAIL; Poverty Stat's loading run showed its 10 profiled WARNs next to its gate checks.

## Limitations

- On Databricks both runs skipped: the load path itself (validate, MERGE, reconcile) is not re-run on Databricks at this commit. It is shown by the local runs above and by the earlier Databricks runs of each source.
- Silver and later stages are placeholders and stayed disabled; `90_validate_control`, the source-lane fan-in, is disabled with them, because it depends on the Silver gates, so the control-table checks did not run.
- A real gate failure was not provoked on Databricks; that a failed gate fails its own task and leaves the other lanes running is shown locally (`tests/test_local_job.py`).

## How to reproduce

From a clean checkout of `819a248` (or later on this branch), with the `reached-hq` profile signed in, notebooks detached and the run announced: the three commands above, the last one twice. Then the queries in [docs/operations/ingestion.md](../../docs/operations/ingestion.md#running-on-databricks).

## Repeated after adding control columns before the view (`bb040a9`)

Review found that `05_create_current_batches` reads `logical_dataset`, but only a load added the D-018 columns, and loads run after the view task: on control tables created before #109 the view task failed, all 12 lane tasks were `upstream_failed`, and rerunning could not fix it. Commit `4026bfe` adds one Python task, `add_control_columns` (`cli.py columns`), between `04_create_data_quality_results` and `05_create_current_batches`; it also adds `job_run_id`, so loads no longer add columns.

**Locally**, control tables were created from the SQL at `d9dd28b` (before #109) and the job run on them with the real files. Before the fix: `Binder Error: Referenced column "logical_dataset" not found` in `05_create_current_batches`, 12 tasks `upstream_failed`, and the same on a rerun. After the fix: both runs succeeded with 0 failed tasks.

**On Databricks `dev`**, the job was redeployed at `bb040a9b1eaec564ffa5e3c5184d6ae6349c2` (read back from the job: 63 tasks, 18 enabled, `05_create_current_batches` after `add_control_columns`) and run twice. Dev's tables already had every column, so this shows the task runs on Databricks without changing the result; the old-table case is shown only locally.

| | Run 3 | Run 4 |
|---|---|---|
| Job run (`job_run_id`) | `471206277550325` | `374205222997457` |
| Whole job | 21:39:10 to 21:42:40 (13:39:10 to 13:42:40 UTC), 3 min 31 s, `SUCCESS` | 21:43:13 to 21:45:15 (13:43:13 to 13:45:15 UTC), 2 min 1 s, `SUCCESS` |
| Tasks | 18 `SUCCESS` on the first attempt, 45 disabled | same |
| `add_control_columns` | 47 s (mostly serverless start-up) | 19 s |
| Loads | all skipped: enrollment 3, the others 1; 0 inserted | same |
| Each load joined to its gate | 4 of 4: 3 gate checks, 0 FAIL, 0 WARN | same |

Bronze still has 180,500 / 60,167 / 1,641 / 43,768 rows, none ingested after 13:39 UTC, and no FAIL was written to `data_quality_results` after it.
