# Ingestion: Source → Control → Bronze

How raw files become Bronze rows, how to add the next delivery, and how to check that it worked. The first source built this way is `deped_enrollment`; other sources reuse the same code with their own contract.

**Status:** built and tested locally. **Not yet run on Databricks**: the raw files are not uploaded yet (#10), and the confirmation run is the last step of #11. Nothing in this document claims a Databricks table, job, or run exists until that section says it was done.

## The flow

```
DepEd download page                         (official zip, one per school year)
   │  download by hand; never modify
   ▼
00 Source   /Volumes/edu_access/00-source/raw/deped/[<download date>/]<original name>.zip
   │  discover → checksum → is it an approved delivery?   (config/ingestion/deped_enrollment.json)
   ▼
01 Control  pipeline_runs · ingestion_batches · ingestion_batch_attempts · data_quality_results
   │  validate → MERGE into Bronze → reconcile → mark the batch succeeded → Bronze gate
   ▼
02 Bronze   edu_access.`02-bronze`.deped_enrollment_raw     (all years, all versions, text, with provenance)
   │
   ▼  Silver reads only batches listed in `01-control`.current_batches
```

Code: `src/ingestion/` ([module list](../src/ingestion/README.md)). SQL: `etl/01_control/`, `etl/02_bronze/`. Contract: `config/ingestion/` ([how to approve a delivery](../config/ingestion/README.md)). Decisions: D-014 to D-017 in [decisions.md](decisions.md).

## The nine questions, for `deped_enrollment`

| Question | Answer |
|---|---|
| What is ingested? | The CSV inside each `Enrollment-in-SY-YYYY-YYYY.zip`. The `README.md` inside is checksummed but stays in Source |
| How often does it arrive? | Yearly, one zip per school year (SY 2025-26 was added 2026-07-23). DepEd also re-uploads published years (2025-10-15) |
| What identifies a new delivery? | An archive SHA-256 not seen before |
| What shows a delivery changed? | The same school year (from the file names) with a different SHA-256 |
| Has this exact file been processed? | `ingestion_batches.status = 'succeeded'` for its `archive_sha256` |
| Are previous versions kept? | Yes, in Source (never overwritten; later downloads in dated subfolders, D-016) and in Bronze (`delivery_version`, D-015) |
| Is the delivery valid? | The checks under [Validation](#validation) |
| Can it be rerun safely? | Yes: a succeeded file is skipped, and a forced rerun inserts nothing |
| Where did each row come from? | Its provenance columns, joined to `ingestion_batches` and `pipeline_runs` |

The DepEd files have no `updated_at` or change column, so none is invented: the file checksum is the change signal. The source is an official download, so there is no scraping and no API (official download → API → database → scraping).

## Identity

| Level | Identified by | Why |
|---|---|---|
| Delivery (batch) | `archive_sha256`; `batch_id` = `<source_id>__<school_year>__<archive_sha256[:12]>` | The same bytes always get the same batch, wherever the file sits |
| Logical period | `source_id` + `school_year` + `delivery_version` | A revised file is version 2 of the same school year, never a silent replacement |
| Bronze row | `source_sha256` (the CSV's checksum) + `source_row_number` | A rerun inserts nothing. A re-zipped copy of the same CSV inserts nothing. Publisher duplicates have different row numbers, so all are kept |
| Schema | `schema_version` + `schema_fingerprint` (SHA-256 of the ordered column names) | Any rename, addition, or reorder changes the fingerprint |
| Code | `code_revision` | The commit that ran ([below](#code_revision)) |

The school year is read from both the archive name (`Enrollment-in-SY-2025-2026.zip`) and the CSV name (`enrollment_2025-26.csv`); they must agree with each other and with the approved entry.

## Storage layout

Raw files are kept exactly as downloaded and are never overwritten (D-016, provisional). The first downloads are in the publisher folder; any later download goes into a dated subfolder:

```
/Volumes/edu_access/00-source/raw/
└── deped/
    ├── Enrollment-in-SY-2023-2024.zip      first downloads, uploaded 2026-09-30
    ├── Enrollment-in-SY-2024-2025.zip
    ├── Enrollment-in-SY-2025-2026.zip
    ├── SHA256SUMS.txt                      covers every file in this folder
    ├── ...                                 other DepEd sources
    └── 2027-08-15/                         a later download (example date)
        ├── Enrollment-in-SY-2026-2027.zip
        └── SHA256SUMS.txt
```

A re-download of a published file therefore sits beside the earlier one. The pipeline searches `raw/deped/` at any depth and identifies files by checksum, so the layout does not matter to it, and it also works with the flat local layout used for profiling (`raw-data/deped/original/`).

## Validation

Before anything is written to Bronze (`src/ingestion/validate.py`):

| Check | On failure |
|---|---|
| Archive exists and is an approved delivery (by SHA-256) | `blocked`: `unregistered_delivery`, or `checksum_mismatch` if the name is approved but the bytes are not |
| Archive opens; no `..`, absolute, symbolic-link, or encrypted members; under the size limit | `failed`: `corrupt_archive`, `unsafe_member`, `archive_too_large` |
| Exactly one data file and the expected `README.md`; nothing else | `failed`: `missing_data_member`, `missing_document_member`, `unexpected_member` |
| CSV and README checksums match the approved entry | `failed`: `member_checksum_mismatch`, `document_checksum_mismatch` |
| School year agrees across archive name, CSV name, and approval | `failed`: `school_year_mismatch` |
| CSV decodes strictly with the approved encoding | `failed`: `encoding_mismatch` |
| Every row has as many fields as the header | `failed`: `ragged_row` |
| Header equals a known schema version, and the approved one | `failed`: `unknown_schema_drift`, `schema_version_mismatch` |
| Row count is nonzero and equals the approved count | FAIL → `failed`, nothing loaded |
| `school_id` is never blank | FAIL → `failed`, nothing loaded |
| `school_id` is 6 digits; unique in the file; no fully repeated rows | WARN: recorded, rows loaded as received |

After the MERGE, before the batch is marked succeeded (`bronze.reconcile`): Bronze rows for the file equal the source rows, no row number appears twice, row numbers run 1..n, and no provenance column is NULL. Then the Bronze gate (`etl/02_bronze/90_validate_deped_enrollment_raw.sql`) checks the whole table, and fails the run on any FAIL recorded in it.

Each run also records `approved_deliveries_present`: a WARN naming any approved zip that is not in the landing folder.

### Schema versions

| Version | School years | Columns | Encoding |
|---|---|---|---|
| `v1` | 2023-24, 2024-25 | 78 | UTF-8, LF |
| `v2` | 2025-26 | 83: v1 plus `Modified Curricular Offering Classification` (undocumented) and four `g11_sshs_*` | Windows-1252, CRLF |

The SY 2025-26 changes are expected because they are documented in the [profile](source_inventory/deped_enrollment/profile.md) (O-6 to O-8). Any other header stops the batch. To accept a real change, add a schema version to the contract in a pull request; Bronze then gains the new columns (`ALTER TABLE ... ADD COLUMN`), never from a file directly.

## Bronze

`edu_access.`02-bronze`.deped_enrollment_raw`: one table, all school years and versions.

- Every publisher column, as text, exactly as received. A blank stays `''`; a column the year's file does not have is `NULL`. No trimming, relabeling (`True`/`Yes` stay as they are), typing, or deduplication.
- The column name with spaces is kept as is, which needs Delta column mapping (`delta.columnMapping.mode = 'name'`).

Provenance columns on every row:

| Column | Meaning |
|---|---|
| `source_id`, `source_system`, `source_url` | From the registry (`config/sources.json`) |
| `school_year`, `delivery_version` | The period and which delivery of it |
| `source_archive`, `source_archive_sha256` | The zip |
| `source_file`, `source_sha256`, `source_row_number` | The CSV inside it and the row's position (data rows from 1) |
| `schema_version`, `schema_fingerprint` | Which header it had |
| `batch_id`, `run_id`, `ingested_at_utc` | The batch and the run that inserted the row |
| `code_revision` | The commit that inserted the row |

### Two kinds of duplicate

| Kind | Example | Handling |
|---|---|---|
| Pipeline duplicate | The same file loaded twice | Prevented: the insert-only MERGE on `(source_sha256, source_row_number)`; checked by `no_pipeline_duplicates` |
| Source duplicate | DepEd lists one school twice | Kept: both rows in Bronze as evidence, flagged WARN (`school_id_unique_in_file`, `duplicate_rows_in_file`); Silver decides |

## Control tables

See [etl/01_control/README.md](../etl/01_control/README.md). Batch statuses: `validating` → `loading` → `succeeded`; or `failed`, `blocked`, `skipped`. **`succeeded` is written last.** Delta commits one table at a time, so Bronze and the batch status cannot change together; instead, downstream reads only batches in `current_batches`, and a batch reaches that view only after its rows are reconciled.

## Retry, rerun, backfill, revision

| Term | Meaning | What to do | What happens |
|---|---|---|---|
| **Skip** | Same file, already succeeded | Nothing: any run | Attempt logged `skip`; 0 rows |
| **Retry** | Repeat a failed or interrupted batch | Fix the cause, run again | Batch is picked up automatically; the MERGE adds only missing rows; `attempt_count` goes up |
| **Rerun** | Repeat a succeeded batch on purpose | `--rerun <batch_id>` | Validated, merged (adds 0 rows), reconciled again |
| **Backfill** | An older school year arrives later | Approve it and upload it | `load_type = backfill`; other years untouched |
| **Revision** | A changed file for a loaded school year | Approve it as the next `delivery_version` with `supersedes` | Before approval: `blocked`. After: loaded beside version 1; `current_batches` points to the new version |

## Failure and recovery

| Failure | What the pipeline does | What you do |
|---|---|---|
| Approved zip missing from landing | WARN `approved_deliveries_present`, naming it | Upload it (#10) |
| Checksum differs from approval | `blocked` `checksum_mismatch`; run fails (exit 1) | Damaged: download again. Revised: approve as the next version |
| Unknown zip | `blocked` `unregistered_delivery` | Profile it, approve it |
| Corrupt zip, unsafe path, missing or extra member | `failed`, nothing loaded | Inspect the file; tell the publisher if needed |
| Wrong or unknown encoding | `failed` `encoding_mismatch`, nothing loaded | Re-profile; correct the approved encoding |
| Undocumented schema change | `failed` `unknown_schema_drift`, nothing loaded | Profile it; add a schema version |
| Empty file, wrong row count, blank `school_id` | FAIL check, `failed`, nothing loaded | Check the file against the source card |
| Process dies mid-load | Batch stays `loading`; downstream cannot see it | Run again: it is retried and completed |
| Bronze write incomplete | Reconciliation FAIL; batch `failed`, not current | Run again: the MERGE adds the missing rows only |
| Same file loaded twice | Skipped; nothing inserted | Nothing |
| Not a full commit on Databricks | Exit 2 `code_revision_required` before anything runs | Deploy from a clean, pushed `main` |
| No Spark or workspace | Exit 3 `store_unavailable` | Run locally, or fix the login (`databricks auth login --profile reached-hq`) |
| `prod` with a source that is not `accepted` | Exit 2 `source_not_accepted` | Use `dev` until the team accepts the source |

Exit codes: 0 everything loaded or already loaded; 1 a batch failed or was blocked, or the gate failed; 2 configuration; 3 environment.

## Running locally

From the repository root, with the virtual environment active ([terminal_setup.md](terminal_setup.md)):

```bash
python -m pytest tests -q
```

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.ingestion.cli ingest --source deped_enrollment
```

```bash
python -m src.ingestion.cli status --source deped_enrollment
```

Tables go to `local_state/edu_access.duckdb` (git-ignored); delete the file to start over. Results from 2026-10-06 on the three real files: 60,167 + 60,129 + 60,204 rows loaded in about 7 seconds, all checks PASS; the second run skipped all three and inserted nothing.

After changing a schema version in the contract, regenerate the Bronze DDL (a test fails until you do):

```bash
python -m src.ingestion.cli ddl --source deped_enrollment > etl/02_bronze/01_create_deped_enrollment_raw.sql
```

## Running on Databricks

**Done for `deped_enrollment`.** Run 1 loaded and was verified, and run 2 skipped everything, on 2026-10-06 (see [First Databricks run](#first-databricks-run)). These are the steps for the deliberate confirmation run (D-008). They need: the `reached-hq` CLI profile, the raw files in the volume, the commit pushed to GitHub, and the run announced to the team (workflow, Part 5).

1. Raw files. The three enrollment zips are already in `/Volumes/edu_access/00-source/raw/deped/` (checked 2026-10-06: sizes match the source card, and the folder's `SHA256SUMS.txt` lists the approved checksums). The first run hashes every zip itself, so a damaged upload is blocked, not loaded. For a later download, list the folder first, then upload into a new dated folder, never over an existing file:

   ```bash
   databricks fs ls dbfs:/Volumes/edu_access/00-source/raw/deped/ --profile reached-hq
   ```

   ```bash
   databricks fs cp "$RAW_DATA_DIR/deped/original/Enrollment-in-SY-2026-2027.zip" dbfs:/Volumes/edu_access/00-source/raw/deped/2027-08-15/ --profile reached-hq
   ```

   Then upload that folder's `SHA256SUMS.txt`.

2. Deploy from a clean checkout of a pushed commit: the pull request branch for the confirmation run, `main` afterwards. `${bundle.git.commit}` is `HEAD`, and the job clones that commit from GitHub:

   ```bash
   git switch main && git pull --ff-only && git status --short
   ```

   ```bash
   databricks bundle validate --target dev --profile reached-hq
   ```

   ```bash
   databricks bundle deploy --target dev --profile reached-hq
   ```

3. Confirm what was deployed: in the job (`[dev <user>] bronze_ingest`), `git_source.git_commit` and the `code_revision` parameter must both equal `git rev-parse HEAD`:

   ```bash
   databricks bundle summary --target dev --profile reached-hq
   ```

4. Run it twice. The second run must skip all three files:

   ```bash
   databricks bundle run bronze_ingest --target dev --profile reached-hq
   ```

5. Check the results with the queries below, and record the run in `pipeline_runs` and on #11.

Before step 4, stop other serverless compute: detach notebooks and leave the SQL warehouse stopped, and do not query it while the job runs. On Free Edition a job waits until serverless capacity is free; the first run waited 35 minutes for 3.5 minutes of work. Check the results after the run ends.

`databricks bundle validate` was run on 2026-10-06 and passed; both commit values resolved to the same SHA.

### First Databricks run

Evidence for both runs, with the queries and their results: [evidence/2026-10-06-deped-enrollment-idempotency.md](evidence/2026-10-06-deped-enrollment-idempotency.md).

Times here are Manila time (UTC+8), with UTC in brackets where it helps. Timestamps in the tables are stored in UTC (`*_utc` columns); convert them for display with `from_utc_timestamp(col, 'Asia/Manila')`.

Run 1: 2026-10-06 Manila (2026-10-05 UTC), `dev`, job `[dev cheimlouise] bronze_ingest`, run `738752819100453`, commit `e681c5b`:

- Loaded 60,167 + 60,129 + 60,204 rows (initial, incremental, incremental), as reported by the job; the task ended `SUCCESS`. This confirms behavior 4 below (zips read from `/Volumes/`) and that the job runs without `__file__` and exits cleanly.
- It took 39 minutes (2,327 s), against about 7 seconds locally. The run's own timestamps show where: the job started at 01:21:37 Manila (17:21:37 UTC), the pipeline wrote its run row at 01:57:46, and the job ended at 02:00:42. The job was waiting for compute: the serverless cluster's ID (`1005-175705-…`) shows it started at 01:57:05 Manila (17:57:05 UTC), 35.5 minutes after the job, and `DESCRIBE HISTORY` shows `pipeline_runs` created at 01:57:34. Free Edition's serverless capacity was in use elsewhere (the SQL warehouse reported `RESOURCE_EXHAUSTED` at the time), most likely by a notebook. Once it had compute, discovery, loading all 180,500 rows, reconciliation, and the gate took about 3.5 minutes; each small control-table write took 3 to 13 seconds.
- Two problems found and fixed: the first deploy was rejected until the task declared `source: GIT`; and the tables were owned by the account that deployed the job, so nobody else could read them. Ownership of the six objects was moved to `reached-hq`, and every `CREATE` in `etl/` is now followed by `OWNER TO `reached-hq`` (D-009).
- Verified the same day in a notebook, by a different account in the `reached-hq` group (the SQL warehouse could not start while other serverless compute was running: Free Edition's limit). Every check matched: rows 60,167 / 60,129 / 60,204; 0 pipeline duplicates; 0 rows missing provenance; 0 rows from another commit; 5,203 blank street addresses kept blank in SY 2023-24; the v2-only column NULL in all 120,296 v1-year rows; 595 SY 2025-26 rows with "ñ"; 3 batches succeeded and reconciled; 37 checks recorded, none other than PASS; 1 run succeeded in `dev`. `delta.columnMapping.mode` is `name`. The same numbers as the local load.
- Run 2, 2026-10-06 02:30 Manila (18:30 UTC), `1088383272500634`, commit `d931112`, the same files: all three batches `skip`, 0 rows inserted, run `succeeded`, task `SUCCESS`, 9.5 minutes, of which 7.6 waiting for compute (cluster started 02:38:04 Manila) and 1.8 working. Verified in the tables: the attempts log shows `load` for each file in run 1 and `skip` in run 2; Bronze still has 180,500 rows, 0 pipeline duplicates, and every row from run 1; 2 succeeded runs; no check other than PASS. Every object, and both schemas, still belongs to `reached-hq` after the run re-applied ownership.

### Validation queries (Databricks SQL editor)

```sql
-- Every batch and its state
SELECT batch_id, school_year, delivery_version, load_type, status, attempt_count, expected_rows, source_rows, bronze_rows, error_code
FROM edu_access.`01-control`.ingestion_batches WHERE source_id = 'deped_enrollment' ORDER BY school_year, delivery_version;

-- What happened, run by run (proves skips)
SELECT r.started_at_utc, r.status, a.batch_id, a.action, a.outcome, a.rows_inserted, a.code_revision
FROM edu_access.`01-control`.ingestion_batch_attempts AS a JOIN edu_access.`01-control`.pipeline_runs AS r USING (run_id)
ORDER BY r.started_at_utc, a.batch_id;

-- Row counts reconcile to the approved files: expect 60,167 / 60,129 / 60,204
SELECT school_year, delivery_version, COUNT(*) AS rows FROM edu_access.`02-bronze`.deped_enrollment_raw GROUP BY ALL ORDER BY 1, 2;

-- No pipeline duplicates: expect 0
SELECT COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) FROM edu_access.`02-bronze`.deped_enrollment_raw;

-- Where one row came from
SELECT source_archive, source_file, source_sha256, source_row_number, batch_id, run_id, ingested_at_utc, code_revision
FROM edu_access.`02-bronze`.deped_enrollment_raw WHERE school_year = '2025-26' AND source_row_number = 1;

-- Checks for the latest run: expect no FAIL
SELECT check_name, status, expected, actual FROM edu_access.`01-control`.data_quality_results
WHERE run_id = (SELECT MAX_BY(run_id, started_at_utc) FROM edu_access.`01-control`.pipeline_runs) ORDER BY status, check_name;

-- Column mapping is on (needed for the column name with spaces)
SHOW TBLPROPERTIES edu_access.`02-bronze`.deped_enrollment_raw ('delta.columnMapping.mode');
```

All checks in one query, each marked `OK` or `CHECK`. The expected values are for the three approved deliveries after one loading run; replace the commit with the one that loaded them:

```sql
WITH r AS (SELECT * FROM edu_access.`02-bronze`.deped_enrollment_raw),
     b AS (SELECT * FROM edu_access.`01-control`.ingestion_batches),
     q AS (SELECT * FROM edu_access.`01-control`.data_quality_results),
     p AS (SELECT * FROM edu_access.`01-control`.pipeline_runs),
checks AS (
  SELECT 'rows SY 2023-24' AS check_name, '60167' AS expected, CAST(COUNT_IF(school_year = '2023-24') AS STRING) AS actual FROM r
  UNION ALL SELECT 'rows SY 2024-25', '60129', CAST(COUNT_IF(school_year = '2024-25') AS STRING) FROM r
  UNION ALL SELECT 'rows SY 2025-26', '60204', CAST(COUNT_IF(school_year = '2025-26') AS STRING) FROM r
  UNION ALL SELECT 'pipeline duplicates', '0', CAST(COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) AS STRING) FROM r
  UNION ALL SELECT 'rows missing provenance', '0', CAST(COUNT_IF(source_sha256 IS NULL OR source_row_number IS NULL OR batch_id IS NULL OR run_id IS NULL OR code_revision IS NULL) AS STRING) FROM r
  UNION ALL SELECT 'rows from another commit', '0', CAST(COUNT_IF(code_revision <> 'e681c5bb62374e4ec5501f63c54c087f60e2651b') AS STRING) FROM r
  UNION ALL SELECT 'blank street_address kept blank, SY 2023-24', '5203', CAST(COUNT_IF(school_year = '2023-24' AND street_address = '') AS STRING) FROM r
  UNION ALL SELECT 'v2-only column NULL in v1 years', '120296', CAST(COUNT_IF(`Modified Curricular Offering Classification` IS NULL) AS STRING) FROM r
  UNION ALL SELECT 'SY 2025-26 rows with ñ', '595', CAST(COUNT_IF(school_year = '2025-26' AND (barangay LIKE '%ñ%' OR municipality LIKE '%ñ%' OR school_name LIKE '%ñ%')) AS STRING) FROM r
  UNION ALL SELECT 'batches succeeded and reconciled', '3', CAST(COUNT_IF(status = 'succeeded' AND source_rows = expected_rows AND bronze_rows = source_rows) AS STRING) FROM b
  UNION ALL SELECT 'checks that are not PASS', '0', CAST(COUNT_IF(status <> 'PASS') AS STRING) FROM q
  UNION ALL SELECT 'checks recorded', '37', CAST(COUNT(*) AS STRING) FROM q
  UNION ALL SELECT 'runs succeeded in dev with 3 loads', '1', CAST(COUNT_IF(status = 'succeeded' AND environment = 'dev' AND batches_loaded = 3) AS STRING) FROM p
)
SELECT check_name, expected, actual, CASE WHEN expected = actual THEN 'OK' ELSE 'CHECK' END AS result FROM checks;
```

### What only the Databricks run can prove (D-017)

Status after run 1: items 1, 3 (after handing the tables to the group), and 4 are confirmed; item 2 is not tested, because nothing failed.

1. Delta accepts `Modified Curricular Offering Classification` with column mapping.
2. The MERGE and the control writes behave as single-table commits.
3. The `reached-hq` group's Unity Catalog permissions allow the job to create and write the tables.
4. Python reads the zips from `/Volumes/...` paths on serverless compute.

Also to watch: `createDataFrame` of about 60,000 rows per year on serverless (Spark Connect), whether the job can clone the public repository without a Git credential, and whether the explicit Delta protocol versions in the Bronze DDL are accepted alongside the workspace's default table features.

Unity Catalog makes whoever creates a table its owner, and a `dev` job runs as whoever deployed it, so each object is handed to the team group right after it is created; `tests/test_bundle.py` checks every `CREATE` in `etl/`. Locally the ownership statements are skipped (DuckDB has no owners).

Three runtime differences are imitated locally in `tests/test_databricks_runtime.py`, because each would otherwise surface only on Databricks: a job's Python file runs with `exec` and no `__file__`; it runs inside IPython, which reports even `SystemExit(0)` as a failure, so the command line exits only on failure; and `spark.sql()` runs a `SELECT` only when collected, so the Spark store collects every statement (otherwise the Bronze gate's final check would never run).

## code_revision

Every Bronze row, control row, and check result records the commit that produced it.

- **Databricks:** the job parameter `code_revision` defaults to `${bundle.git.commit}`, the same substitution as `git_source.git_commit`, so the code that runs and the commit recorded cannot differ. The task passes it with `--code-revision`; the gate reads it as `:code_revision`. A job run without a full 40-character SHA stops before doing anything (exit 2).
- **Locally:** read from git; `-dirty` is added when there are uncommitted or untracked changes.
- **Unknown:** `UNSET`, the only spelling.

`tests/test_bundle.py` fails if the job follows a branch, if the parameter or `git_commit` stops being `${bundle.git.commit}`, if a task stops passing it, or if any gate result stops reading `:code_revision`.

## Handoff to Silver

Bronze preserves; Silver cleans. Silver (#43) should:

- read only rows whose `batch_id` is in `` `01-control`.current_batches `` (the latest succeeded version per school year);
- type the counts (all whole numbers, profile O-2) and keep blanks as NULL, never 0;
- map each year's labels to one set (`True`/`Yes`, `DepEd`/`DepED Managed`, trailing spaces; profile O-8), and normalize place names (profile O-5) with affected counts;
- resolve publisher duplicates of `school_id` if any appear (none so far, profile O-1), quarantining rather than dropping;
- keep `batch_id` and `source_row_number` so every Silver row traces back to its Bronze row.

## Runbook

**1. How do I add a new DepEd school year?**
Download the zip from the official page; do not rename or open-and-save it. Profile it and update the source card (checksums, encoding, rows). Add the delivery to `config/ingestion/deped_enrollment.json` (and a schema version if the header changed; then regenerate the DDL), and merge the pull request. Upload the zip to `raw/deped/<download date>/`, never over an existing file. Run the job. An older year loads as `backfill`, a newer one as `incremental`; other years are untouched.

**2. How do I know whether it was already processed?**
`python -m src.ingestion.cli status --source deped_enrollment` locally, or the first validation query on Databricks. Look up the file's SHA-256: `succeeded` means processed.

**3. What happens if the publisher replaces a file?**
The new bytes do not match the approved checksum, so the batch is `blocked` (`checksum_mismatch`, `load_type = revision`) and the run fails; nothing is overwritten. If the change is real, approve it as `delivery_version: 2` with `supersedes` set to version 1's `archive_sha256`. Both versions stay in Bronze, and `current_batches` moves to version 2.

**4. How do I inspect a failed batch?**
`status` shows `error_code`. Then:

```sql
SELECT failure_stage, error_code, error_message, attempt_count, last_run_id
FROM edu_access.`01-control`.ingestion_batches WHERE status IN ('failed', 'blocked', 'loading');
```

and the checks for that batch in `data_quality_results` (`WHERE batch_id = '...'`). Messages hold counts and checksums, never row values.

**5. How do I safely rerun it?**
Fix the cause and run the same command again. A `failed` or `loading` batch is retried automatically and the MERGE adds only missing rows. To repeat a succeeded batch, add `--rerun <batch_id>`; it inserts nothing.

**6. How do I verify the Bronze output?**
Row counts per school year equal the approved `row_count` (third query); the run has no FAIL (sixth query); pick a row and trace it by its provenance columns to the file and line it came from.

**7. How do I prove the same batch did not create duplicates?**
Run the job twice. The attempts query shows `load` then `skip` with `rows_inserted = 0`, the row counts do not change, and the duplicate query returns 0. Locally, `tests/test_ingestion_pipeline.py::test_idempotency_demonstration` proves the same with made-up files.

## Limitations

- Not yet confirmed on Databricks (D-017 lists what only that run proves).
- A file named unlike `Enrollment-in-SY-YYYY-YYYY.zip` and not yet approved is not discovered; a renamed publisher file must be noticed by whoever downloads it.
- Approval is manual by design: a new year needs a profile update and a pull request before it loads.
- A revision reloads all rows of the school year (about 60,000), even if one value changed.
- No `prod` target yet; `dev` is the only deploy target.
- SY 2017-18 to 2022-23 are published but not acquired; their headers are unknown and will likely need new schema versions.

## Open questions

| Question | Default until decided | Where |
|---|---|---|
| Should the latest version of a school year always be current, or do revisions need review first? | Latest succeeded version | D-015 |
| Are per-publisher raw folders enough, given #10 asked for one folder per source? | First downloads flat in `raw/deped/`, later ones in dated subfolders | D-016 |
| When is a `prod` target added, and how is its data kept apart from `dev`? There is one workspace and one catalog, and `edu_access` is hardcoded in the SQL and `store.py` | `dev` only | Before #47 |
| How long are superseded versions kept in Bronze and Source? | Forever | Not yet logged |
| Who can approve a delivery, and does `deped_enrollment` move to `accepted` before a `prod` target exists? | Any reviewer; stays `profiled` | Team |
| Should a blank `school_id` fail the whole year, or be quarantined in Silver? | Fail the batch (none observed) | Profile O-1 |
| Does DepEd publish the promised school ID mapping file, and should it be a delivery member? | Unexpected members fail the batch | Source card |
