# Evidence: DepEd facilities loads into Bronze once, and a second run inserts nothing

Issue #11 · Databricks `dev` · 2026-10-06, Manila time (UTC+8) · checked by @hyenalouise

## The claim

DepEd facilities, the second source, loads through the same pipeline as enrollment with only its own contract and generated SQL. Running the job again with the same files inserts nothing, and loading facilities does not change enrollment's Bronze table.

## What was run

The job `bronze_ingest` at commit `acec94d5546e9b8043da4e21065e45de1f4337f4` (`code_revision` and `git_source.git_commit`), with two tasks in order: `bronze_deped_enrollment`, then `bronze_deped_facilities` (`run_if: ALL_DONE`). Deployed with `databricks bundle deploy --target dev --profile reached-hq` and started twice with `databricks bundle run bronze_ingest --target dev --profile reached-hq`. The landing folder `/Volumes/edu_access/00-source/raw/deped/` was the same both times. Before the runs, the SQL warehouse was stopped and notebooks detached.

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `588715548188592` | `75917129933986` |
| Facilities pipeline `run_id` | `46e9f03a-c249-46f6-a84a-6521a7373f87` | `a2c64867-315e-43da-8030-9de8cd89e5f5` |
| Enrollment task | 04:14:41 to 04:16:41, skipped 3 files | 04:18:49 to 04:19:51, skipped 3 files |
| Facilities task | 04:16:41 to 04:18:14, **loaded 60,167 rows** | 04:19:52 to 04:20:39, **skipped, 0 inserted** |
| Whole job | 3 min 41 s, `SUCCESS` | 1 min 52 s, `SUCCESS` |
<img width="1140" height="313" alt="image" src="https://github.com/user-attachments/assets/e3fca7b7-6d39-44f8-a0f1-ddf55f3fcc14" />


With no other serverless compute running, the job did not wait for capacity: compare enrollment's first run, which waited 35.5 minutes for 3.5 minutes of work ([enrollment evidence](2026-10-06-deped-enrollment-idempotency.md)).

## Results

### The job's own output

Run 1, facilities task: <br>
<img width="1143" height="388" alt="image" src="https://github.com/user-attachments/assets/7d81bf34-b074-41a7-bdee-ddc94097af30" />

<br>
Run 2, facilities task:<br>
<img width="1149" height="382" alt="image" src="https://github.com/user-attachments/assets/ab4614a1-66f0-44c0-af05-8175bfbc381d" />


In both runs the enrollment task skipped all three of its files and inserted 0.

### Verification in the tables (checked 04:34)

All fourteen checks matched, run in a notebook after run 2:

| Check | Expected | Actual |
|---|---|---|
| Facilities rows | 60,167 | 60,167 |
| Facilities pipeline duplicates | 0 | 0 |
| Facilities rows missing provenance | 0 | 0 |
| Facilities runs that inserted rows | 1 | 1 |
| Facilities rows from another commit | 0 | 0 |
| Public elementary schools with a blank classroom count, kept blank (profile O-4) | 669 | 669 |
| Rows with zero elementary classrooms (profile O-5) | 0 | 0 |
| Facilities schools also in SY 2023-24 enrollment (profile O-2) | 60,167 | 60,167 |
| Facilities loads / skips in the attempts log | 1 / 1 | 1 / 1 |
| Facilities batch succeeded and reconciled | 1 | 1 |
| Facilities runs succeeded | 2 | 2 |
| Enrollment rows unchanged | 180,500 | 180,500 |
| Enrollment runs that inserted rows (still only its first) | 1 | 1 |
| Checks that are not PASS, both sources | 0 | 0 |

The query is the one-query facilities verification below. The new table `edu_access.`02-bronze`.deped_facilities_raw` was owned by `reached-hq` from the moment it was created, has 103 columns (16 provenance and 87 from the publisher), and has `delta.columnMapping.mode = name` (checked with `databricks tables get`).

## Why it holds

The same three reasons as for enrollment: a delivery's identity is its archive SHA-256, so run 2 found facilities' checksum already `succeeded` and skipped it; Bronze is loaded with an insert-only MERGE on `(source_sha256, source_row_number)`; and a batch is marked `succeeded` only after its rows reconcile. Facilities added no ingestion code, only `config/ingestion/deped_facilities.json`, its generated table and gate, and a job task.

## What this does not prove

- Recovery from a real failure, backfill, or a revised file on Databricks (shown only by local tests).
- That facilities is ready for analysis: blanks in facility counts are ambiguous (profile O-4, O-5) and are for Silver to handle.

## How to reproduce

With notebooks detached and the SQL warehouse stopped, from a clean checkout of a pushed commit:

```bash
databricks bundle deploy --target dev --profile reached-hq
```

```bash
databricks bundle run bronze_ingest --target dev --profile reached-hq
```

Run the second command again, then run this in a notebook; every line should show `OK` (replace the commit with the one deployed):

```sql
WITH f AS (SELECT * FROM edu_access.`02-bronze`.deped_facilities_raw),
     e AS (SELECT * FROM edu_access.`02-bronze`.deped_enrollment_raw),
     a AS (SELECT * FROM edu_access.`01-control`.ingestion_batch_attempts WHERE source_id = 'deped_facilities'),
     b AS (SELECT * FROM edu_access.`01-control`.ingestion_batches WHERE source_id = 'deped_facilities'),
     p AS (SELECT * FROM edu_access.`01-control`.pipeline_runs WHERE source_id = 'deped_facilities'),
     q AS (SELECT * FROM edu_access.`01-control`.data_quality_results),
checks AS (
  SELECT 'facilities rows' AS check_name, '60167' AS expected, CAST(COUNT(*) AS STRING) AS actual FROM f
  UNION ALL SELECT 'facilities pipeline duplicates', '0', CAST(COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) AS STRING) FROM f
  UNION ALL SELECT 'facilities rows missing provenance', '0', CAST(COUNT_IF(source_sha256 IS NULL OR source_row_number IS NULL OR batch_id IS NULL OR run_id IS NULL OR code_revision IS NULL) AS STRING) FROM f
  UNION ALL SELECT 'facilities runs that inserted rows', '1', CAST(COUNT(DISTINCT run_id) AS STRING) FROM f
  UNION ALL SELECT 'facilities rows from another commit', '0', CAST(COUNT_IF(code_revision <> 'acec94d5546e9b8043da4e21065e45de1f4337f4') AS STRING) FROM f
  UNION ALL SELECT 'blank classroom count kept blank (profile O-4)', '669', CAST(COUNT_IF(sector = 'Public' AND offers_es = 'True' AND es_classrooms_instructional = '') AS STRING) FROM f
  UNION ALL SELECT 'zero elementary classrooms (profile O-5)', '0', CAST(COUNT_IF(es_classrooms_instructional = '0') AS STRING) FROM f
  UNION ALL SELECT 'facilities schools also in SY 2023-24 enrollment', '60167', CAST(COUNT(*) AS STRING) FROM f JOIN e ON e.school_id = f.school_id AND e.school_year = '2023-24'
  UNION ALL SELECT 'facilities loads / skips', '1 / 1', CONCAT(CAST(COUNT_IF(action = 'load' AND outcome = 'succeeded') AS STRING), ' / ', CAST(COUNT_IF(action = 'skip' AND rows_inserted = 0) AS STRING)) FROM a
  UNION ALL SELECT 'facilities batch succeeded and reconciled', '1', CAST(COUNT_IF(status = 'succeeded' AND source_rows = expected_rows AND bronze_rows = source_rows) AS STRING) FROM b
  UNION ALL SELECT 'facilities runs succeeded', '2', CAST(COUNT_IF(status = 'succeeded') AS STRING) FROM p
  UNION ALL SELECT 'enrollment rows unchanged', '180500', CAST(COUNT(*) AS STRING) FROM e
  UNION ALL SELECT 'enrollment runs that inserted rows (still only its first)', '1', CAST(COUNT(DISTINCT run_id) AS STRING) FROM e
  UNION ALL SELECT 'checks that are not PASS (both sources)', '0', CAST(COUNT_IF(status <> 'PASS') AS STRING) FROM q
)
SELECT check_name, expected, actual, CASE WHEN expected = actual THEN 'OK' ELSE 'CHECK' END AS result FROM checks;
```
