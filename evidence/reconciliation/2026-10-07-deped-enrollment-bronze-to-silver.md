# Evidence: DepEd enrollment Silver reconciles with Bronze, and a second run skips

Issue #85 · local run (DuckDB), not Databricks · 2026-10-07 · checked by @hyenalouise

## The claim

Silver built from the real Bronze data of all three school years keeps every current Bronze row (clean + quarantined = Bronze, per school year), moves no learner (totals equal Bronze and the profile's O-3), passes every gate check, and a second run with the same Bronze batches skips without touching the tables. A forced rebuild gives identical content.

## What was run

Commit `fe859549a99394adc3030c460ff92e637ccd49e5`, clean checkout (no `-dirty`), macOS 26.3.1, Python 3.12.14, DuckDB 1.4.5, a fresh database file in a scratch folder. The three approved zips were read from `raw-data/deped/original/` (checksums verified by the loader, as on the source card).

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.ingestion.cli ingest --source deped_enrollment --db <scratch>.duckdb
```

```bash
python -m src.silver.cli build --source deped_enrollment --db <scratch>.duckdb
```

The Silver command was run twice, then `python -m pytest tests -q` (261 passed). In a second fresh database the same sequence was followed by `build --force` to compare content.

| Step | Result | Pipeline time |
|---|---|---:|
| Bronze load | 60,167 + 60,129 + 60,204 rows loaded, `succeeded` | 7.9 s |
| Silver run 1 | `build (first_build)`: 180,500 Bronze rows → 180,500 clean, 0 quarantined, `succeeded` | 1.7 s (build 1.1 s, checks 0.6 s) |
| Silver run 2 | `skip (unchanged)`, `succeeded`; no Silver statement ran, no check written | 0.01 s |
| Bronze rerun | all three files `skip`, 0 rows inserted | 0.2 s wall |
| Silver `--force` | `build (forced)`: same counts, `succeeded` | 1.8 s |

## Results

The one-query verification from [Silver, Running on Databricks](../../docs/operations/silver.md#running-on-databricks), run through the local store after run 2:

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
| checks in the build run | 111 | 111 | OK |
| checks in the build run not PASS | 0 | 0 | OK |
| rows from the build run | 180500 | 180500 | OK |
| rows from another commit | 0 | 0 | OK |
| builds then skips | 1 build, 1 skip | 1 build, 1 skip | OK |
| silver runs succeeded | 2 | 2 | OK |

The learner totals equal the profile's O-3 (27,081,292; 26,400,182; 25,935,863). Every rule's affected rows per school year, recorded by the gate, are in [Silver, Cleaning rules](../../docs/operations/silver.md#cleaning-rules); each matches the profile finding it comes from (for example overseas 33 / 35 / 36, truncated barangays 24 / 25 / 25, blank barangays 70 / 65 / 7, placeholder addresses 0 / 0 / 3,555).

Idempotency: the MD5 of all 180,500 clean rows, ordered by school year and row number and excluding `run_id`, `cleaned_at_utc`, and `code_revision`, was `5d9ecaf14baac697071e884851af3161` after the first build, after the skip, and after the forced rebuild.

## Why it holds

Links point to the code at the commit above; Silver has since become two SQL tasks that rebuild on every run (D-025).

1. Silver reads Bronze only through `current_batches`, and each row goes to exactly one of the two tables by a reasons string that is never NULL ([build SQL](https://github.com/reached-hq/edu-access-intelligence/blob/fe859549a99394adc3030c460ff92e637ccd49e5/etl/03_silver/01_create_deped_enrollment_clean.sql)).
2. The gate recomputes rows, learners, blank cells, labels, and lineage from Bronze and compares them with Silver per school year ([gate](https://github.com/reached-hq/edu-access-intelligence/blob/fe859549a99394adc3030c460ff92e637ccd49e5/etl/03_silver/90_validate_deped_enrollment_clean.sql)).
3. A run skips only when the current batches and the SHA-256 of the build and gate SQL equal those of the last successful build and the previous run finished ([run.py](https://github.com/reached-hq/edu-access-intelligence/blob/fe859549a99394adc3030c460ff92e637ccd49e5/src/silver/run.py)).

## Also shown by tests

`tests/test_silver.py` (made-up deliveries through the real Bronze pipeline): blank stays NULL, absent columns, label and boolean mapping, whitespace and repairs, flags, NULL-safe filters, quarantine of negative, non-whole, duplicated, blank, NULL, and malformed values with their reasons, the 1% FAIL, an unmapped label failing the gate, a blank turned into 0 caught by the gate, a revised delivery replacing its year, skip, rebuild on new data or changed rules, recovery after a crash, and a forced rerun with identical content.

## What this does not prove

- Anything on Databricks: Spark has not run this SQL, so `regexp_like`, `translate`, `chr(160)`, the CTE inside `INSERT`, `CREATE OR REPLACE TABLE` on Unity Catalog, and ownership are unconfirmed, and so is the cost of a build and of a skip on Free Edition.
- Quarantine on real data: no real row is quarantined; quarantine is shown only with made-up rows.
- A real publisher revision; shown only by tests.

## How to reproduce

From a clean checkout of the commit above, with `RAW_DATA_DIR` set, run the two commands above against a new database file and run the Silver command again. Then run the verification query from [Silver](../../docs/operations/silver.md#running-on-databricks) through the local store, which translates it for DuckDB: `DuckDBStore("<scratch>.duckdb").query(sql)` from `src.ingestion.store`, with the commit filled in.
