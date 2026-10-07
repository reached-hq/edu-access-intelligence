# Evidence: DepEd facilities loads into Bronze once, and a second run inserts nothing

Issue #11 · Databricks `dev` · 2026-10-06, Manila time (UTC+8) · checked by @hyenalouise

## The claim

DepEd facilities, the second source, loads through the same pipeline as enrollment with only its own contract and generated SQL. Running the job again with the same files inserts nothing, and loading facilities does not change enrollment's Bronze table.

## What was run

The job `bronze_ingest` at commit `acec94d5546e9b8043da4e21065e45de1f4337f4` (`code_revision` and `git_source.git_commit`), with two tasks in order: `bronze_deped_enrollment`, then `bronze_deped_facilities` (`run_if: ALL_DONE`: it runs even if enrollment fails). The tasks are connected only for order; they share no data, only the control tables. Before the runs, the SQL warehouse was stopped and notebooks detached.

The stored revision remains the exact commit Databricks ran. After the branch was rebased, its counterpart in the current pull request is `9bcdb126545aa69cf5d33a10d664bd9730ab7c74`.

```bash
databricks bundle deploy --target dev --profile reached-hq
```

```bash
databricks bundle run bronze_ingest --target dev --profile reached-hq
```

The second command was run twice. The landing folder `/Volumes/edu_access/00-source/raw/deped/` was the same both times.

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `588715548188592` | `75917129933986` |
| Facilities pipeline `run_id` | `46e9f03a-c249-46f6-a84a-6521a7373f87` | `a2c64867-315e-43da-8030-9de8cd89e5f5` |
| Enrollment task | 04:14:41 to 04:16:41, skipped 3 files | 04:18:49 to 04:19:51, skipped 3 files |
| Facilities task | 04:16:41 to 04:18:14, **loaded 60,167 rows** | 04:19:52 to 04:20:39, **skipped, 0 inserted** |
| Whole job | 3 min 41 s, `SUCCESS` | 1 min 52 s, `SUCCESS` |

<img width="1140" height="313" alt="image" src="https://github.com/user-attachments/assets/e3fca7b7-6d39-44f8-a0f1-ddf55f3fcc14" />

With no other serverless compute running, the job did not wait for capacity. Compare enrollment's first run, which waited 35.5 minutes for 3.5 minutes of work ([enrollment evidence](2026-10-06-deped-enrollment-idempotency.md)).

## Results

### 1. The job's own output

Run 1, facilities task:

<img width="1143" height="388" alt="image" src="https://github.com/user-attachments/assets/7d81bf34-b074-41a7-bdee-ddc94097af30" />

Run 2, facilities task:

<img width="1149" height="382" alt="image" src="https://github.com/user-attachments/assets/ab4614a1-66f0-44c0-af05-8175bfbc381d" />

In both runs the enrollment task skipped all three of its files and inserted 0.

### 2. What each run did, for both sources

```sql
SELECT r.started_at_utc, a.source_id, a.batch_id, a.action, a.outcome, a.rows_inserted
FROM edu_access.`01-control`.ingestion_batch_attempts AS a
JOIN edu_access.`01-control`.pipeline_runs AS r USING (run_id)
WHERE r.code_revision = 'acec94d5546e9b8043da4e21065e45de1f4337f4'
ORDER BY r.started_at_utc, a.source_id, a.batch_id
```
<img width="919" height="270" alt="image" src="https://github.com/user-attachments/assets/91615e51-5336-4477-bbf2-5c53588a05d6" />


### 3. Two sources, two Bronze tables, nothing doubled

```sql
SELECT 'deped_enrollment_raw' AS bronze_table, COUNT(*) AS bronze_rows,
       COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) AS duplicates,
       COUNT(DISTINCT run_id) AS runs_that_inserted_rows
FROM edu_access.`02-bronze`.deped_enrollment_raw
UNION ALL
SELECT 'deped_facilities_raw', COUNT(*),
       COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number),
       COUNT(DISTINCT run_id)
FROM edu_access.`02-bronze`.deped_facilities_raw
```

<img width="911" height="202" alt="image" src="https://github.com/user-attachments/assets/c36876d8-f39e-4266-88a8-8f6a53587cde" />


### 4. The Bronze table's write history

```sql
DESCRIBE HISTORY edu_access.`02-bronze`.deped_facilities_raw
```
<img width="912" height="204" alt="image" src="https://github.com/user-attachments/assets/ab8ab61e-73de-4db5-9ae7-4413ee7fd062" />


### 5. Every check, in one query (checked 04:34)

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

All fourteen checks matched:

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

<img width="917" height="395" alt="image" src="https://github.com/user-attachments/assets/5f8f6bab-124f-4274-bde6-8adccd29c27f" />

### 6. The new table

```sql
SHOW TBLPROPERTIES edu_access.`02-bronze`.deped_facilities_raw ('delta.columnMapping.mode')
```

<img width="920" height="267" alt="image" src="https://github.com/user-attachments/assets/4a92cc30-e8f0-484e-814b-ef71c93459c9" />

## Why it holds

The same three reasons as for enrollment:

1. A delivery's identity is its archive SHA-256. Run 2 found facilities' checksum already `succeeded` and skipped it.
2. Bronze is loaded with an insert-only MERGE on `(source_sha256, source_row_number)`, so even a forced rerun cannot double a row.
3. A batch is marked `succeeded` only after its rows reconcile with the file.

Facilities added no ingestion code: only `config/ingestion/deped_facilities.json`, its generated table and gate, and a job task.

## What this does not prove

- Recovery from a real failure, backfill, or a revised file on Databricks (shown only by local tests).
- That facilities is ready for analysis: blanks in facility counts are ambiguous (profile O-4, O-5) and are for Silver to handle.

## How to reproduce

With notebooks detached and the SQL warehouse stopped, from a clean checkout of a pushed commit, run the two commands under "What was run", the second one twice. Then run the queries in sections 2 to 6, replacing the commit `acec94d…` with the one deployed. Every result should match its expected values.
