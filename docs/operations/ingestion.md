# Ingestion: Source → Control → Bronze

How raw files become Bronze rows, how to add the next delivery, and how to check that it worked. The first source built this way is `deped_enrollment`; `deped_facilities` is the second, and needed only its own contract and generated SQL. Other sources reuse the same code with their own contract. `psa_poverty_stat` is the first workbook source: same pipeline, a second delivery format ([PSA Poverty Stat](#psa-poverty-stat-xlsx-workbook) below).

**Status:** built and tested locally, then verified on Databricks `dev` for both `deped_enrollment` and `deped_facilities`. The source cards and evidence files linked below record the uploaded files, tables, and runs. `psa_poverty_stat`: built and tested locally with made-up workbooks, and loaded locally from the real workbook (1,641 rows, then a skip); **not yet run on Databricks** (see its section).

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

Code: `src/ingestion/` ([module list](../../src/ingestion/README.md)). SQL: `etl/01_control/`, `etl/02_bronze/`. Contract: `config/ingestion/` ([how to approve a delivery](../../config/ingestion/README.md)). Decisions: D-014 to D-017 in [decisions.md](../governance/decisions.md).

## The nine questions, for `deped_enrollment`

| Question | Answer |
|---|---|
| What is ingested? | Every row of sheet `2023_NoHUC_Maguindanao grouped` (used range A1:S1641, 1,641 rows), so no worksheet row is dropped: the title (row 1), the 4 header rows, the 1,630 body rows (Excel rows 6 to 1635: 1,612 city/municipality rows and 18 region banner rows), and the 6 footer rows (notes and source line). Each row is labelled by `source_row_kind`; only `unit` rows are data. Column S is in the used range but empty, and checked, not loaded |
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

The SY 2025-26 changes are expected because they are documented in the [profile](../data/source-inventory/deped_enrollment/profile.md) (O-6 to O-8). Any other header stops the batch. To accept a real change, add a schema version to the contract in a pull request; Bronze then gains the new columns (`ALTER TABLE ... ADD COLUMN`), never from a file directly.

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

See [etl/01_control/README.md](../../etl/01_control/README.md). Batch statuses: `validating` → `loading` → `succeeded`; or `failed`, `blocked`, `skipped`. **`succeeded` is written last.** Delta commits one table at a time, so Bronze and the batch status cannot change together; instead, downstream reads only batches in `current_batches`, and a batch reaches that view only after its rows are reconciled.

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

From the repository root, with the virtual environment active ([terminal_setup.md](../getting-started/terminal-setup.md)):

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

After changing a schema version in the contract, regenerate the Bronze DDL and gate (a test fails until you do):

```bash
python -m src.ingestion.cli ddl --source deped_enrollment > etl/02_bronze/01_create_deped_enrollment_raw.sql
```

```bash
python -m src.ingestion.cli gate --source deped_enrollment > etl/02_bronze/90_validate_deped_enrollment_raw.sql
```

### Adding another source shaped like these (a zip with one CSV and a README)

1. Write `config/ingestion/<source_id>.json`: file-name patterns, the column list as a schema version, and the approved deliveries copied from the source card ([config/ingestion/README.md](../../config/ingestion/README.md)).
2. Generate `etl/02_bronze/01_create_<source_id>_raw.sql` and `90_validate_<source_id>_raw.sql` with the two commands above.
3. Add the publisher's file names to `NAMES` in `tests/factories/deped_deliveries.py` and a test that loads a made-up delivery (see `tests/test_ingestion_facilities.py`).
4. Add a task to `bronze_ingest` in `databricks.yml`, after the last one, with `run_if: ALL_DONE` (`tests/test_bundle.py` checks both).
5. Load the real file locally and compare with the source card, then open the pull request, run the job twice on `dev`, and record the evidence.

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

Evidence for both runs, with the queries and their results: [evidence/2026-10-06-deped-enrollment-idempotency.md](../../evidence/pipeline-runs/2026-10-06-deped-enrollment-idempotency.md).

Facilities, the second source, was loaded and rerun the same day at commit `acec94d` (rebased counterpart `9bcdb12`): 60,167 rows, then a skip, with enrollment untouched ([evidence](../../evidence/pipeline-runs/2026-10-06-deped-facilities-idempotency.md)). With the SQL warehouse stopped and notebooks detached, the whole job took 3 min 41 s, then 1 min 52 s: it did not wait for capacity.

Times here are Manila time (UTC+8), with UTC in brackets where it helps. Timestamps in the tables are stored in UTC (`*_utc` columns); convert them for display with `from_utc_timestamp(col, 'Asia/Manila')`.

Run 1: 2026-10-06 Manila (2026-10-05 UTC), `dev`, job `[dev cheimlouise] bronze_ingest`, run `738752819100453`, commit `e681c5b` (rebased counterpart `a55e6e9`):

- Loaded 60,167 + 60,129 + 60,204 rows (initial, incremental, incremental), as reported by the job; the task ended `SUCCESS`. This confirms behavior 4 below (zips read from `/Volumes/`) and that the job runs without `__file__` and exits cleanly.
- It took 39 minutes (2,327 s), against about 7 seconds locally. The run's own timestamps show where: the job started at 01:21:37 Manila (17:21:37 UTC), the pipeline wrote its run row at 01:57:46, and the job ended at 02:00:42. The job was waiting for compute: the serverless cluster's ID (`1005-175705-…`) shows it started at 01:57:05 Manila (17:57:05 UTC), 35.5 minutes after the job, and `DESCRIBE HISTORY` shows `pipeline_runs` created at 01:57:34. Free Edition's serverless capacity was in use elsewhere (the SQL warehouse reported `RESOURCE_EXHAUSTED` at the time), most likely by a notebook. Once it had compute, discovery, loading all 180,500 rows, reconciliation, and the gate took about 3.5 minutes; each small control-table write took 3 to 13 seconds.
- Two problems found and fixed: the first deploy was rejected until the task declared `source: GIT`; and the tables were owned by the account that deployed the job, so nobody else could read them. Ownership of the six objects was moved to `reached-hq`, and every `CREATE` in `etl/` is now followed by `OWNER TO `reached-hq`` (D-009).
- Verified the same day in a notebook, by a different account in the `reached-hq` group (the SQL warehouse could not start while other serverless compute was running: Free Edition's limit). Every check matched: rows 60,167 / 60,129 / 60,204; 0 pipeline duplicates; 0 rows missing provenance; 0 rows from another commit; 5,203 blank street addresses kept blank in SY 2023-24; the v2-only column NULL in all 120,296 v1-year rows; 595 SY 2025-26 rows with "ñ"; 3 batches succeeded and reconciled; 37 checks recorded, none other than PASS; 1 run succeeded in `dev`. `delta.columnMapping.mode` is `name`. The same numbers as the local load.
- Run 2, 2026-10-06 02:30 Manila (18:30 UTC), `1088383272500634`, commit `d931112` (rebased counterpart `96b27f0`), the same files: all three batches `skip`, 0 rows inserted, run `succeeded`, task `SUCCESS`, 9.5 minutes, of which 7.6 waiting for compute (cluster started 02:38:04 Manila) and 1.8 working. Verified in the tables: the attempts log shows `load` for each file in run 1 and `skip` in run 2; Bronze still has 180,500 rows, 0 pipeline duplicates, and every row from run 1; 2 succeeded runs; no check other than PASS. Every object, and both schemas, still belongs to `reached-hq` after the run re-applied ownership.

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

Rebasing or squash-merging a branch does not change a stored `code_revision`, and it can make that exact commit unreachable from the rewritten branch. Before rewriting a branch used for a Databricks run, either tag the run commit so it remains reachable or record the run SHA and its rebased or squashed counterpart in the evidence file. Never rewrite the stored revision: it identifies the code that actually ran.

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

## PSA Poverty Stat (xlsx workbook)

`psa_poverty_stat` loads through the same pipeline as DepEd, from its own contract, `config/ingestion/psa_poverty_stat.json` (`format: xlsx_sheet`). What differs is in `src/ingestion/workbook.py` (reading and checking the workbook) and `src/ingestion/formats.py` (period, versions, load type). Decision: D-018.

**Status:** implemented and tested locally with made-up workbooks (`tests/test_ingestion_psa.py`), and **verified locally on the real workbook** on 2026-10-07: every layout check passed, 1,641 rows loaded (1,612 unit, 18 region_banner, 1 title, 4 header, 6 footer), every known-issue count equal to the profile, and a second run skipped it ([evidence](../../evidence/pipeline-runs/2026-10-07-psa-poverty-stat-local-idempotency.md#real-workbook-local-duckdb)). **Not run on Databricks.** The source stays `profiled`.

### The flow

```
psa.gov.ph stat-tables page                (official xlsx; no API, no scraping)
   │  download by hand; never modify, never re-save in Excel
   ▼
00 Source   /Volumes/edu_access/00-source/raw/psa/[<download date>/]2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx
   │  discover *SAE*.xlsx → SHA-256 → approved?   (config/ingestion/psa_poverty_stat.json)
   ▼
   │  open safely → expected sheet only → header names from the merged header → schema version
   │  → estimate years from the header → footer 'Notes:' → every row 1..1641 labelled title / header /
   │    unit / region_banner / footer
01 Control  pipeline_runs · ingestion_batches (+ logical_dataset, estimate_years_covered, source_sheet)
   │        · ingestion_batch_attempts · data_quality_results
   │  checks (FAIL blocks; WARN records) → MERGE → reconcile (rows, units, banners) → succeeded → gate
   ▼
02 Bronze   edu_access.`02-bronze`.psa_poverty_stat_raw   (1,641 rows per delivery: the whole sheet, text, with provenance)
   │
   ▼  Silver reads only batches in `01-control`.current_batches
```

### The nine questions

| Question | Answer |
|---|---|
| What is ingested? | Sheet `2023_NoHUC_Maguindanao grouped` of the approved workbook: the 1,630 body rows (Excel rows 6 to 1635), both the 1,612 city/municipality rows and the 18 region banner rows. The title, header rows and footer stay in Source; they are checked, not loaded |
| How often does it arrive? | UNVERIFIED. One workbook so far, covering 2018, 2021 and 2023 (released 2026-02-06). Treated as an irregular batch, never as a stream |
| What identifies a new delivery? | A workbook SHA-256 not seen before |
| What shows a delivery changed? | The same file name (or estimate years already loaded) with a different SHA-256. There is no `updated_at` in the workbook, and none is invented |
| Has this exact file been processed? | `ingestion_batches.status = 'succeeded'` for its `archive_sha256` (the workbook's) |
| Are previous versions kept? | Yes: in Source (no overwrite, D-016) and in Bronze (`delivery_version` per `logical_dataset`, D-015, D-018) |
| Is the delivery valid? | The checks under [PSA validation](#psa-validation) |
| Can it be rerun safely? | Yes: a succeeded workbook is skipped; a forced rerun inserts nothing |
| Where did each row come from? | `source_file`, `source_sha256`, `source_sheet`, `source_row_number` (the Excel row), plus `batch_id`, `run_id`, `code_revision` |

### Identity

| Level | Identified by | Why |
|---|---|---|
| Delivery (batch) | Workbook SHA-256; `batch_id` = `psa_poverty_stat__2018-2021-2023__<sha[:12]>` | Same bytes, same batch, wherever the file sits |
| Logical period | `logical_dataset` + `delivery_version` (e.g. `sae_city_municipal_2018_2021_2023` v1) | One workbook covers three estimate years, so versions are counted per dataset, not per year |
| Estimate years | `estimate_years_covered` = `2018,2021,2023`, read from the header and checked against the approval | Delivery metadata. A wide row holds all three years; no row is given a single year |
| Bronze row | `source_sha256` + `source_row_number` (Excel row) | A rerun inserts nothing; repeated publisher rows (different Excel rows) are all kept. One sheet per approved workbook keeps the pair unique; loading a second sheet would need `source_sheet` in the key |
| Schema | `schema_version` + `schema_fingerprint` of the 18 built column names | Any renamed, added, or reordered header changes it |

Why not a hash of the row's content? Two identical publisher rows would merge into one, which is silent deduplication. Why not the file name? PSA can replace the file at the same URL and name.

### Layout as a versioned contract

Schema `v1` pins the layout the profile found (O-1), and anything else stops the batch:

| Element | Contract | On anything else |
|---|---|---|
| Sheets | Only `2023_NoHUC_Maguindanao grouped` | `missing_sheet` / `unexpected_sheet` (a new sheet may hold data) |
| Header | Rows 2 (group, merged across its columns), 4 (ID; Lower/Upper Limit), 5 (year) build 18 names that must equal `v1` exactly | `unknown_schema_drift`; groups not merged as profiled: `unexpected_header_layout` |
| Estimate years | From the column names: 2018, 2021, 2023, equal to the approval | `estimate_years_mismatch` |
| Used range | `A1:S1641`, as declared in the sheet | FAIL |
| Body | Row 6 to the row before `Notes:` in column A: 1,630 rows | `footer_not_found`; count FAIL |
| Row kinds | `unit` (has `PSGC ID`), `region_banner` (only `Region/Province`), `blank`, `unclassified` | Units 1,612 and banners 18 each reconciled; any `unclassified` row FAILs |
| Footer | 6 rows (1636 to 1641), loaded as `footer` | FAIL |
| Title and header | Row 1 (`title`) and rows 2 to 5 (`header`), loaded as received | Header drift stops the batch (above) |
| Column S | Empty and ignored; nothing right of it | FAIL |

### PSA validation

Before Bronze, in addition to the layout above:

| Check | Status |
|---|---|
| Workbook exists, approved by SHA-256 | `blocked` (`unregistered_delivery`; `checksum_mismatch` for an approved name with other bytes) |
| Opens as a zip without `..`, absolute, linked or encrypted parts, under 50 MB expanded; no XML DTD or entities | `failed` (`corrupt_archive`, `corrupt_workbook`, `unsafe_member`, `unsafe_workbook`, `archive_too_large`) |
| `PSGC ID` matches `[0-9]{5,6}` on every unit row (banners exempt) | FAIL |
| Units, banners, blank rows, body rows, footer rows equal the approval | FAIL |
| `PSGC ID` unique; no fully repeated rows | WARN, rows kept (source duplicates) |
| Non-numeric values in estimate columns; formula cells; error cells | WARN, rows kept |
| Known publisher issues (below) | WARN with the profiled count beside the actual count |

Known issues are flagged, never corrected, in Bronze:

| Check (`known_issue_…`) | Profiled | Finding | Bronze keeps |
|---|---|---|---|
| `psgc_id_leading_zero_lost` (ID shorter than 6 digits) | 1,073 | O-2 | `12801`, not `012801` |
| `unit_rows_without_estimates` (Kalayaan) | 1 | O-5 | 15 blanks `''`; never 0. Missing is not zero poverty |
| `province_label_continued` | 1 | O-3 | `(Continued)` as written |
| `lower_limit_zero_or_negative` | 3 | O-7 | `-2.4063453271442992E-2`, not clipped |
| `se_disagrees_with_cv_2018` / `_2021` / `_2023` (tolerance 0.05) | 6 / 133 / 1 | O-8 (2021: CALABARZON) | SE as published |
| `cv_over_20_2018` / `_2021` / `_2023` | 171 / 84 / 156 | O-9 | CV as published |

Values are the text stored in the file: numbers keep every stored digit (no rounding, no added precision), text keeps its Unicode, and labels and names are not standardized (61 differ from PSGC, O-10/X-1). Results hold counts only, never values.

After the MERGE: Bronze rows for the workbook equal the sheet's rows (1,641), Excel row numbers run 1..1641 with no repeats, every provenance column is filled, and the counts by `source_row_kind` equal the file's (`bronze_row_kinds_match_source`: title 1, header 4, unit 1,612, region_banner 18, footer 6). Then the generated gate (`etl/02_bronze/90_validate_psa_poverty_stat_raw.sql`) checks the whole table.

### Bronze table

`edu_access.`02-bronze`.psa_poverty_stat_raw` (generated: `etl/02_bronze/01_create_psa_poverty_stat_raw.sql`): 17 provenance columns, then the 18 publisher columns as text. Poverty incidence is the percentage of **persons** below the poverty threshold (press release 2026-43), not of families or students. Each year's estimate keeps its CV, standard error, and both 90% limits in the same row.

| Provenance column | Meaning |
|---|---|
| `source_id`, `source_system`, `source_url` | From the registry |
| `logical_dataset`, `estimate_years_covered`, `delivery_version` | Which delivery, of which dataset, covering which years |
| `source_file`, `source_sha256`, `source_sheet`, `source_row_number` | The workbook, its checksum, the sheet, the Excel row |
| `source_row_kind` | `title`, `header`, `unit`, `region_banner`, `blank`, or `footer`, from the layout; changes no source column. Silver reads only `unit` rows as data |
| `schema_version`, `schema_fingerprint` | Which header it had |
| `batch_id`, `run_id`, `ingested_at_utc`, `code_revision` | The batch, the run, when, and the commit |

### Retry, rerun, backfill, revision (workbooks)

| Term | Example | What happens |
|---|---|---|
| Skip | The same workbook again | Attempt logged `skip`; 0 rows |
| Retry | A batch that failed (for example an approval with a wrong count, later fixed) or was interrupted | Picked up automatically; MERGE adds only missing rows |
| Rerun | `--rerun psa_poverty_stat__2018-2021-2023__303fb0e87bff` | Validated and merged again; 0 rows |
| Incremental | A workbook with only later years (e.g. 2025) | New `logical_dataset`, `load_type = incremental`; earlier rows untouched |
| Backfill | A workbook with only earlier years (e.g. 2015) | New `logical_dataset`, `load_type = backfill`; nothing rebuilt |
| Revised delivery | A changed workbook for years already loaded (same name, or overlapping years) | Before approval: `blocked`, `load_type = revision`, run fails, nothing overwritten. After approval as `delivery_version: 2` of the same `logical_dataset` with `supersedes`: loaded beside v1; `current_batches` points to v2 |

The contract refuses two logical datasets that share an estimate year, so a workbook that republishes 2023 can only enter as a reviewed revision, never as a silent second copy of 2023. Whether a later release that adds a year (2018 to 2025, say) is a revision of the existing dataset or a new dataset is a team decision when it happens (open question below); until then the contract forces the question.

<a id="psa-running-locally"></a>
### Running locally

In VS Code's terminal, from the repository root, with the virtual environment active:

```bash
python -m pytest tests -q
```

```bash
python -m src.ingestion.cli ingest --source psa_poverty_stat
```

```bash
python -m src.ingestion.cli status --source psa_poverty_stat
```

`RAW_DATA_DIR` must be set in that terminal first ([terminal setup, Part 8](../getting-started/terminal-setup.md#part-8-raw-data-and-raw_data_dir)), or given with `--landing <raw root>`. The workbook must be under `$RAW_DATA_DIR/psa/` (for example `psa/original/`). Expected on the real file: one batch `load initial`, `inserted=1641 bronze=1641`, status `succeeded`, every FAIL-type check PASS and the known-issue WARNs at their profiled counts; the second run `skip`, `inserted=0`. If the first run reports `unexpected_header_layout`, `footer_rows_match_approved` or another layout FAIL, the profile's description of the layout and the real file differ: do not change the data, record what was found and adjust the contract in review.

After changing the contract's schema, regenerate the SQL (a test fails until you do):

```bash
python -m src.ingestion.cli ddl --source psa_poverty_stat > etl/02_bronze/01_create_psa_poverty_stat_raw.sql
```

```bash
python -m src.ingestion.cli gate --source psa_poverty_stat > etl/02_bronze/90_validate_psa_poverty_stat_raw.sql
```

### Databricks confirmation (not yet done)

`databricks.yml` has a third task, `bronze_psa_poverty_stat`, after facilities (`run_if: ALL_DONE`). Before running it: the change is reviewed and merged, the run is announced to the team (it touches the shared control tables), and the CLI profile `reached-hq` works. The workbook is already on the volume (card: uploaded 2026-09-30, checksum verified). Then the same steps as for DepEd ([Running on Databricks](#running-on-databricks)): `databricks bundle validate`, `deploy`, `summary`, `run` twice.

The first run after this change also adds three nullable columns to `ingestion_batches` and two to `ingestion_batch_attempts` (`ALTER TABLE … ADD COLUMN`, only if missing) and replaces `current_batches`. DepEd rows are unaffected (the new columns are NULL for them), but the run should be announced, and `ALTER TABLE ADD COLUMN` on the existing Delta tables is confirmed only by that run.

Validation queries (Databricks SQL editor):

```sql
-- The batch and its counts: expect 1 succeeded, expected = source = bronze = 1641 (the whole sheet)
SELECT batch_id, logical_dataset, estimate_years_covered, source_sheet, delivery_version, load_type, status,
       expected_rows, source_rows, bronze_rows, error_code
FROM edu_access.`01-control`.ingestion_batches WHERE source_id = 'psa_poverty_stat';

-- Every sheet row by kind: expect footer 6, header 4, region_banner 18, title 1, unit 1612
SELECT source_row_kind, COUNT(*) FROM edu_access.`02-bronze`.psa_poverty_stat_raw GROUP BY ALL ORDER BY 1;

-- Load then skip: expect 'load' in run 1 and 'skip' with 0 rows in run 2
SELECT r.started_at_utc, a.action, a.outcome, a.rows_inserted, a.estimate_years_covered
FROM edu_access.`01-control`.ingestion_batch_attempts AS a JOIN edu_access.`01-control`.pipeline_runs AS r USING (run_id)
WHERE a.source_id = 'psa_poverty_stat' ORDER BY r.started_at_utc;

-- No pipeline duplicates: expect 0
SELECT COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number) FROM edu_access.`02-bronze`.psa_poverty_stat_raw;

-- Excel rows: expect 1 and 1641
SELECT MIN(source_row_number), MAX(source_row_number) FROM edu_access.`02-bronze`.psa_poverty_stat_raw;

-- Known issues kept as received: expect 1073 five-digit IDs, 1 unit with a blank 2023 estimate
SELECT COUNT_IF(source_row_kind = 'unit' AND length(`PSGC ID`) = 5) AS five_digit_ids,
       COUNT_IF(source_row_kind = 'unit' AND `Poverty Incidence 2023` = '') AS blank_2023
FROM edu_access.`02-bronze`.psa_poverty_stat_raw;

-- Checks for the PSA batch: expect no FAIL, and WARNs at the profiled counts
SELECT check_name, status, expected, actual FROM edu_access.`01-control`.data_quality_results
WHERE source_id = 'psa_poverty_stat' AND run_id = (SELECT MAX_BY(run_id, started_at_utc) FROM edu_access.`01-control`.pipeline_runs
                                                  WHERE source_id = 'psa_poverty_stat') ORDER BY status, check_name;

-- Where one row came from
SELECT source_file, source_sha256, source_sheet, source_row_number, source_row_kind, batch_id, run_id, code_revision
FROM edu_access.`02-bronze`.psa_poverty_stat_raw WHERE source_row_number = 641;
```

### Handoff to Silver (not built here)

Silver should:

- read only rows whose `batch_id` is in `current_batches`, and only `source_row_kind = 'unit'`; use the banner rows to carry the region label down (O-3), never as places;
- keep `PSGC ID` raw, and add a padded 6-digit code (`lpad(…, 6, '0')`) and the PSGC Correspondence Code (padded code + `000`); the geographic join to PSGC belongs in Integration (X-1, D-012);
- unpivot to one row per unit and estimate year, typing estimates, CV, SE and limits as decimals without rounding; blanks become NULL with a reason (`no_estimate` for Kalayaan), never 0;
- flag, not fix: CV over 20, the 2021 CALABARZON standard errors, zero or negative lower limits (clip only in a documented, reversible column if a rule is approved);
- take province from the ID prefix, not the labels (`(Continued)`, Surigao rows, O-3), and region from the banner for Negros Island Region (two ID prefixes);
- record that 33 highly urbanized cities, Isabela, Cotabato, Pateros and 8 SGA municipalities are `not_in_source`, not zero poverty;
- keep `batch_id` and `source_row_number` on every row.

Cross-year comparability (S-3) and update frequency remain unverified; a trend across 2018, 2021 and 2023 needs the team's decision first.

### Runbook (PSA)

**1. How do I add a new PSA Poverty Stat workbook delivery?**
Download it from the stat-tables page; do not rename it, open-and-save it, or convert it. Upload it to `raw/psa/<download date>/` (never over an existing file) with that folder's `SHA256SUMS.txt`. Profile it (`analysis/profiling/profile_psa_poverty.py`, adjusted for its name and checksum), update the card, and add the delivery to `config/ingestion/psa_poverty_stat.json` in a pull request: `logical_dataset`, `estimate_years`, `workbook`, `workbook_sha256`, `sheet`, `schema_version`, `body_rows`, `unit_rows`, `banner_rows`, `footer_rows`, `retrieved_at_utc`. If the header has other years or columns, add a schema version (and regenerate the DDL). Then run the job.

**2. How do I know whether it was already processed?**
`python -m src.ingestion.cli status --source psa_poverty_stat`, or the first validation query: `succeeded` for its SHA-256 means processed.

**3. What happens if the publisher replaces a file?**
The new bytes do not match the approved SHA-256: the batch is `blocked` (`checksum_mismatch`, `load_type = revision` when its header names years already loaded) and the run fails. Nothing is overwritten. If the change is real, approve it as `delivery_version: 2` of the same `logical_dataset` with `supersedes` set to v1's `workbook_sha256`. Both versions stay in Bronze.

**4. How do I inspect a failed batch?**

```sql
SELECT batch_id, status, failure_stage, error_code, error_message, attempt_count, last_run_id
FROM edu_access.`01-control`.ingestion_batches
WHERE source_id = 'psa_poverty_stat' AND status IN ('failed', 'blocked', 'loading');
```

Then its checks: `SELECT check_name, status, expected, actual FROM edu_access.`01-control`.data_quality_results WHERE batch_id = '<batch_id>'`.

**5. How do I safely rerun it?**
Fix the cause and run again: a `failed` or `loading` batch is retried and the MERGE adds only missing rows. To repeat a succeeded batch on purpose: `--rerun <batch_id>` (adds 0 rows).

**6. How do I verify the Bronze output?**
1,641 rows for the workbook (1 `title`, 4 `header`, 1,612 `unit`, 18 `region_banner`, 6 `footer`), Excel rows 1 to 1641, no FAIL, the known-issue WARNs at their profiled counts, and one row traced to its sheet line with the last query above (row 641 is Kalayaan, blank estimates).

**7. How do I prove the same batch did not create duplicates?**
Run twice. The attempts query shows `load` then `skip` with 0 rows, Bronze still has 1,641 rows, and the duplicate query returns 0. Locally, `tests/test_ingestion_psa.py::test_psa_idempotency_demonstration` proves the same with made-up workbooks, and `analysis/demo/psa_ingestion_demo.py` prints the whole story (load, skip, a new year, a changed file blocked, a crash and its recovery, one row traced to its Excel line) for a presentation: run it cell by cell in VS Code, or `python analysis/demo/psa_ingestion_demo.py`. It uses no raw data and no Databricks.

### Limitations and open questions (PSA)

- Verified on made-up workbooks and on the real workbook locally (DuckDB); the Databricks run is pending.
- The merged-header check expects each group in row 2 to be merged across its columns, as in the real workbook; a future file laid out differently stops the batch, and the contract is corrected in review, not the file.
- `known_issue` checks compare against counts from one profile run; they warn, they never block.
- Update frequency, cross-year comparability (S-3), and the PSGC version of the ID are unverified.

| Question | Default until decided | Where |
|---|---|---|
| Is a later release that adds a year (and may revise old ones) a revision of the current dataset, or a new dataset? | The contract refuses overlap across datasets, so the reviewer must choose; both versions are kept either way | D-018 |
| Should the latest version always be current after a revision? | Latest succeeded version | D-015 |
| Does `psa_poverty_stat` move from `profiled` to `accepted`? | Stays `profiled`; loads to `local` and `dev` only | Team (owner @maeveylain) |
| How long are superseded versions kept? | Forever | Not yet logged |
| Should Silver clip negative lower limits, or only flag them? | Flag only | Silver issue |
