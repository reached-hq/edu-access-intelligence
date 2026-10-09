# Evidence: DepEd enrollment Silver reconciles with Bronze, and every run rebuilds the same rows

Issue #85 · local run (DuckDB); the Databricks runs are in [their own record](../pipeline-runs/2026-10-09-deped-enrollment-silver.md) · 2026-10-09 · checked by @hyenalouise

Replaces [the 2026-10-07 record](2026-10-07-deped-enrollment-bronze-to-silver.md), which ran the earlier design that skipped Silver when Bronze was unchanged. Silver now runs as two SQL tasks of the job and rebuilds on every run (D-025).

## The claim

Silver built from the real Bronze data of all three school years keeps every current Bronze row (clean + quarantined = Bronze, per school year), moves no learner (totals equal Bronze and the profile's O-3), and passes every gate check. A second job run with the same Bronze batches rebuilds both tables with identical content and records a second `succeeded` run.

## What was run

Commit `7d93d8ee51efd82a714b3b07ed6c985c5aecede8`, clean checkout (no `-dirty`), macOS 26.3.1, Python 3.12.14, DuckDB 1.4.5, a fresh database file in a scratch folder. The approved deliveries were read from `raw-data/` (checksums verified by the loader, as on the source card). The whole job ran twice, in the order of the Databricks DAG:

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.job.local_run --db <scratch>.duckdb
```

Then `python -m pytest tests -q` (469 passed).

| Step | Result | Task time |
|---|---|---:|
| Run 1: `bronze_deped_enrollment` | 60,167 + 60,129 + 60,204 rows loaded, `succeeded` | 7.6 s |
| Run 1: `01_clean_deped_enrollment` | 180,500 Bronze rows → 180,500 clean, 0 quarantined | 1.3 s |
| Run 1: `90_validate_deped_enrollment_clean` | 116 checks, all PASS; run `succeeded` | 0.7 s |
| Run 2: `bronze_deped_enrollment` | all three files `skip`, 0 rows inserted | 0.1 s |
| Run 2: `01_clean_deped_enrollment` | rebuilt: 180,500 clean, 0 quarantined | 1.2 s |
| Run 2: `90_validate_deped_enrollment_clean` | 116 checks, all PASS; run `succeeded` | 0.7 s |

Both job runs exited 0 with every enabled task `succeeded`.

## Results

The one-query verification from [Silver, Running on Databricks](../../docs/operations/silver.md#running-on-databricks), run through the local store after run 2 with the commit above:

| Check | Expected | Actual | Result |
|---|---|---|---|
| clean rows SY 2023-24 | 60167 | 60167 | OK |
| clean rows SY 2024-25 | 60129 | 60129 | OK |
| clean rows SY 2025-26 | 60204 | 60204 | OK |
| quarantined rows | 0 | 0 | OK |
| repeated keys | 0 | 0 | OK |
| learners SY 2023-24 / 2024-25 / 2025-26 | 27081292 / 26400182 / 25935863 | 27081292 / 26400182 / 25935863 | OK |
| blank SHS counts kept NULL, SY 2025-26 | 47352 | 47352 | OK |
| absent v2 column NULL in v1 rows | 120296 | 120296 | OK |
| standard labels, school_management, SY 2025-26 | 9 | 9 | OK |
| mangled Ã‘ left | 0 | 0 | OK |
| overseas flagged | 104 | 104 | OK |
| no counts published, SY 2025-26 | 46 | 46 | OK |
| checks in the last run | 116 | 116 | OK |
| checks in the last run not PASS | 0 | 0 | OK |
| rows from the last run | 180500 | 180500 | OK |
| rows from another commit | 0 | 0 | OK |
| last silver run | succeeded | succeeded | OK |
| silver runs succeeded at this commit | 2 | 2 | OK |

The learner totals equal the profile's O-3 (27,081,292; 26,400,182; 25,935,863). The `rule_*` and `flag_*` results of run 2, per school year, equal the table in [Silver, Cleaning rules](../../docs/operations/silver.md#cleaning-rules): for example overseas 33 / 35 / 36, truncated barangays 24 / 25 / 25, blank barangays 70 / 65 / 7, placeholder addresses 0 / 0 / 3,555, labels standardized 0 / 0 / 60,204.

Idempotency: the content hash below was `311b445851533467fd7e669d3cf6e537` over 180,500 rows after run 1 and after run 2. It covers every column except the run stamp (`run_id`, `cleaned_at_utc`, `code_revision`), in school year and row order (DuckDB):

```sql
SELECT COUNT(*), md5(string_agg(CAST(t AS VARCHAR), chr(10) ORDER BY school_year, source_row_number))
FROM (SELECT * EXCLUDE (run_id, cleaned_at_utc, code_revision) FROM edu_access."03-silver".deped_enrollment_clean) AS t;
```

The 2026-10-07 hash was computed differently, so the two values are not comparable. The hash is the same as at `44840ad`, before the BIGINT sums and the plausible maximum: neither changes a real row.

## Why it holds

1. Silver reads Bronze only through `current_batches`, and each row goes to exactly one of the two tables by a reasons string that is never NULL ([build SQL](https://github.com/reached-hq/edu-access-intelligence/blob/7d93d8ee51efd82a714b3b07ed6c985c5aecede8/etl/03_silver/01_clean_deped_enrollment.sql)).
2. Both tables are rebuilt with `CREATE OR REPLACE TABLE ... AS SELECT` from the same current batches, so the same Bronze gives the same rows; only the run stamp changes.
3. The gate recomputes rows, learners, blank cells, labels, and lineage from Bronze and compares them with Silver per school year, then records the run `succeeded` or `failed` from its own execution's results ([gate](https://github.com/reached-hq/edu-access-intelligence/blob/7d93d8ee51efd82a714b3b07ed6c985c5aecede8/etl/03_silver/90_validate_deped_enrollment_clean.sql)).

## Also shown by tests

`tests/test_silver.py` (made-up deliveries through the real Bronze pipeline): blank stays NULL, absent columns, label and boolean mapping, whitespace and repairs, flags, NULL-safe filters, quarantine of negative, non-whole, above-maximum, duplicated, blank, NULL, and malformed values with their reasons, a count of exactly 10,000 kept, nine-digit counts that no longer overflow the build or the gate, the 1% FAIL, an unmapped label failing the gate, on a clean or a quarantined row, a blank turned into 0 caught by the gate, a lost or stale row caught, each check the cleaning rules cannot trip failing a build that breaks it, a revised delivery replacing its year, every run rebuilding the same tables, a run marked `succeeded` only after its gate, and a repaired run judged by its own checks. `tests/test_local_job.py`: Silver is skipped when its Bronze gate fails.

## What this does not prove

- Anything on Databricks: shown by [the Databricks record](../pipeline-runs/2026-10-09-deped-enrollment-silver.md) of the same commit.
- Quarantine on real data: no real row is quarantined; quarantine is shown only with made-up rows.
- A real publisher revision; shown only by tests.

## How to reproduce

From a clean checkout of the commit above, with `RAW_DATA_DIR` set, run the job command above twice against a new database file. Then run the verification query from [Silver](../../docs/operations/silver.md#running-on-databricks) through the local store, which translates it for DuckDB: `DuckDBStore("<scratch>.duckdb").query(sql)` from `src.ingestion.store`, with the commit filled in. Run the hash query in the DuckDB CLI after `ATTACH '<scratch>.duckdb' AS edu_access;`.
