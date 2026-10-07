# Evidence: loading DepEd enrollment into Bronze twice inserts nothing the second time

Issue #11 · Databricks `dev` · 2026-10-06, Manila time (UTC+8; UTC in brackets where it helps) · checked by @hyenalouise

## The claim

Running the same ingestion again, with the same files, leaves Bronze unchanged: every file is recognized as already loaded by its SHA-256 and skipped, no row is inserted twice, and the control tables record what each run did and which commit did it.

## What was run

The job `bronze_ingest`, deployed with `databricks bundle deploy --target dev --profile reached-hq` and started twice with `databricks bundle run bronze_ingest --target dev --profile reached-hq`. Nothing changed between the runs except the code commit (documentation and table-ownership fixes); the landing folder `/Volumes/edu_access/00-source/raw/deped/` held the same three enrollment zips both times.

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `738752819100453` | `1088383272500634` |
| Pipeline `run_id` | `67a608ec-7f00-4597-890c-962f638d372c` | `2661793a-31c2-4143-a621-5040b9dc7546` |
| Commit (`code_revision`, `git_source.git_commit`) | `e681c5bb62374e4ec5501f63c54c087f60e2651b` | `d9311127f94c9d7cb585d63855bb1938ee92fdde` |
| Job started | 01:21:37 (17:21:37 UTC, 2026-10-05) | 02:30:25 (18:30:25 UTC) |
| Serverless cluster started | 01:57:05 (`1005-175705-vuoxhqzb-v2n`) | 02:38:04 (`1005-183804-p73g3729-v2n`) |
| Job ended | 02:00:42 | 02:39:53 |
| Waiting for compute / working | 35.5 min / 3.6 min | 7.6 min / 1.8 min |
| Task result | `SUCCESS` | `SUCCESS` |

The stored `code_revision` values above remain the exact commits Databricks ran and are preserved by tags `run/2026-10-06-enrollment-1` and `run/2026-10-06-enrollment-2`. After the branch was rebased, their counterparts in the current pull request are `51eaccc58aeeab2493126c72ce5feb2582ffb7d7` for run 1 and `3bfb3d1f61a62699243fd965946fbc65c3f56fb2` for run 2. Those counterparts contain the same PR-specific changes, but their snapshots also include later changes from the updated #69 base, including the `discover()` hashing fix; they are not the exact code that ran.

<img width="1070" height="557" alt="image" src="https://github.com/user-attachments/assets/f8b378f5-dc25-4040-9581-e82074f8de43" />

The waiting time was Free Edition serverless capacity in use elsewhere, not the pipeline: the cluster ID encodes its start time, and `DESCRIBE HISTORY` shows `pipeline_runs` created at 01:57:34, 29 seconds after the cluster started.

## Results

### The job's own output

Run 1: <br>
<img width="924" height="212" alt="image" src="https://github.com/user-attachments/assets/0389ace7-995e-40a9-bf3a-f5b4759a141f" />

<br>
Run 2:<br>
<img width="930" height="275" alt="image" src="https://github.com/user-attachments/assets/101e3eb2-3f85-4fd9-ac99-46d1c813a1a3" />


### The audit history (checked 02:43)

```sql
SELECT r.started_at_utc, r.code_revision, a.batch_id, a.action, a.outcome, a.rows_inserted
FROM edu_access.`01-control`.ingestion_batch_attempts AS a
JOIN edu_access.`01-control`.pipeline_runs AS r USING (run_id)
ORDER BY r.started_at_utc, a.batch_id
```

<img width="1090" height="241" alt="image" src="https://github.com/user-attachments/assets/e8dc440c-fce9-4c7d-a665-7632762f0b1e" />


The same three `batch_id`s appear in both runs: identical bytes get an identical identity.

### Nothing doubled (checked 02:43)

```sql
SELECT
  (SELECT COUNT(*) FROM edu_access.`02-bronze`.deped_enrollment_raw) AS bronze_rows,
  (SELECT COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) FROM edu_access.`02-bronze`.deped_enrollment_raw) AS duplicates,
  (SELECT COUNT(DISTINCT run_id) FROM edu_access.`02-bronze`.deped_enrollment_raw) AS runs_that_inserted_rows,
  (SELECT COUNT(*) FROM edu_access.`01-control`.pipeline_runs WHERE status = 'succeeded') AS succeeded_runs,
  (SELECT COUNT_IF(status <> 'PASS') FROM edu_access.`01-control`.data_quality_results) AS checks_not_pass
```

<img width="1093" height="131" alt="image" src="https://github.com/user-attachments/assets/19a04bdc-9905-4ef2-b6c3-fa4a7d225b52" />


180,500 is 60,167 + 60,129 + 60,204, the row counts on the source card. Every Bronze row was inserted by run 1; run 2 inserted none.

### Run 1 was correct before it was repeated (checked 02:23)

All thirteen checks of the one-query verification in [ingestion.md](../ingestion.md#validation-queries-databricks-sql-editor) matched:

| Check | Expected | Actual |
|---|---|---|
| Rows SY 2023-24 / 2024-25 / 2025-26 | 60,167 / 60,129 / 60,204 | same |
| Pipeline duplicates | 0 | 0 |
| Rows missing provenance | 0 | 0 |
| Rows from another commit | 0 | 0 |
| Blank `street_address` kept blank, SY 2023-24 | 5,203 | 5,203 |
| v2-only column NULL in v1 years | 120,296 | 120,296 |
| SY 2025-26 rows with "ñ" (Windows-1252 decoded) | 595 | 595 |
| Batches succeeded and reconciled | 3 | 3 |
| Checks not PASS / checks recorded | 0 / 37 | 0 / 37 |
| Runs succeeded in `dev` with 3 loads | 1 | 1 |

`delta.columnMapping.mode` on the Bronze table is `name`, so `Modified Curricular Offering Classification` is stored under its own name.

After run 2, the Bronze table, the four control tables, the `current_batches` view, and both schemas are owned by `reached-hq` (checked with `databricks tables get` and `databricks schemas get`).

## Why it holds

1. A delivery's identity is its archive SHA-256. Run 2 found each zip's checksum in `ingestion_batches` with status `succeeded`, so it skipped the file and wrote an attempt row saying so ([batch.py](../../src/ingestion/batch.py)).
2. Even a forced rerun cannot double rows: Bronze is loaded with an insert-only MERGE on `(source_sha256, source_row_number)`, the CSV's checksum and the row's position in it ([bronze.py](../../src/ingestion/bronze.py)).
3. A batch is marked `succeeded` only after its Bronze rows reconcile with the file, and downstream reads only succeeded batches, so an interrupted load is retried, not half-read ([pipeline.py](../../src/ingestion/pipeline.py)).

## Also shown locally

- `tests/test_ingestion_pipeline.py` (made-up files, DuckDB): `test_idempotency_demonstration` (load, rerun skipped, audit history, a second school year loaded without touching the first, a changed file under the same name blocked), `test_rerun_validates_again_and_adds_nothing`, `test_interrupted_load_is_recovered`, `test_partial_write_is_completed_without_duplicates`, `test_batch_is_invisible_downstream_until_its_last_write`.
- The real files loaded into two separate fresh local databases gave identical Bronze content: 180,500 rows, 97 columns compared (all but `run_id` and `ingested_at_utc`), the same MD5 `89fbfdc65df11eee0bc26eecc03c2f05`, and the same batch IDs.

## What this does not prove

- Recovery from a real failure on Databricks. Nothing failed in either run; crash and partial-write recovery are shown only by the local tests (D-017, item 2).
- Backfill, a revised file, or a blocked file on Databricks; these are shown only locally.
- Anything about the other DepEd sources; only `deped_enrollment` is loaded.

## How to reproduce

From a clean checkout of a pushed commit, with notebooks detached and the SQL warehouse stopped (a running job waits for Free Edition serverless capacity):

```bash
databricks bundle deploy --target dev --profile reached-hq
```

```bash
databricks bundle run bronze_ingest --target dev --profile reached-hq
```

Run the second command again, then run the two queries above. The attempts log gains three `skip` rows with `rows_inserted = 0`, and the other numbers stay the same, except `succeeded_runs`, which goes up by one.
