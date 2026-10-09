# Evidence: Silver publishes only a build that passes its gate, and a failed build leaves the last good one in place

Issue #119 · Databricks `dev` and local (DuckDB) · 2026-10-09 · checked by @hyenalouise

## The claim

The DepEd enrollment Silver build writes only the candidate tables (`deped_enrollment_clean_candidate`, `deped_enrollment_quarantine_candidate`). The gate checks them and copies them to the Silver tables only when every check passes, then records the run `succeeded` (D-025). On the real data:

1. On Databricks, two job runs build, check, and publish with the same result as before the change: 180,500 clean rows, 0 quarantined, every check PASS, published rows identical to the build at `7d93d8e`.
2. A build that fails its gate publishes nothing: the Silver tables keep every row of the last good build, still trusted by the rule Gold follows (the `run_id` the rows carry is a succeeded `silver_build` run), and the failed build waits in the candidate tables.

## What was run

### Databricks `dev`

The job `[dev ina_magno] edu_access_pipeline` (job `651937364323543`), deployed with `databricks bundle deploy --target dev --profile reached-hq` from a clean checkout of the pushed commit `acd6416e4b25cbceea60551ff8ca625cbe85f518`. Read back from the job before running: `git_source.git_commit` and the `code_revision` parameter both equal that commit. No other job run was active and the SQL warehouse was stopped. The job was run twice with `databricks bundle run edu_access_pipeline --target dev --profile reached-hq`. Times are Manila (UTC+8).

Job details: Git source at commit acd6416
<img width="1457" height="550" alt="image" src="https://github.com/user-attachments/assets/dc3adf0b-a19d-469c-85e4-eb22a9f2d026" />


| | Run 1 | Run 2 |
|---|---|---|
| Job run (`run_id` of the Silver rows) | `706712982940347` | `22433027021877` |
| Whole job | 02:26:54 to 02:32:52 (18:26:54 to 18:32:52 UTC, 2026-10-08), 5 min 57 s, `SUCCESS` | 02:33:42 to 02:37:13 (18:33:42 to 18:37:13 UTC), 3 min 30 s, `SUCCESS` |
| Tasks | 20 `SUCCESS` on the first attempt, 43 disabled | same |
| `bronze_deped_enrollment` | skip ×3, 0 inserted, 108 s | skip ×3, 0 inserted, 65 s |
| `01_clean_deped_enrollment` (into the candidates) | 56 s | 30 s |
| `90_validate_deped_enrollment_clean` (check, then publish) | 63 s | 47 s |

#### Run 1 task graph: every enabled task green
<img width="1461" height="515" alt="image" src="https://github.com/user-attachments/assets/78b08900-1a4a-43cb-8043-ebe92de0a932" />

#### Run 2 task graph: the same 20 tasks green
<img width="1454" height="496" alt="image" src="https://github.com/user-attachments/assets/b51783b2-4f4d-4457-a347-e4073c9ea314" />

No task waited in a queue. Before this change the gate took 44 to 50 s in four runs ([#85 evidence](2026-10-09-deped-enrollment-silver.md)); publishing (two table copies and two owner statements, plus one more run-row update) adds about 3 to 13 s per run on the warehouse.

### Local, real data

Commit `acd6416` (clean checkout), macOS 26.3.1, Python 3.12.14, DuckDB 1.4.5, a fresh database file in a scratch folder: `RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.job.local_run --db <scratch>.duckdb`, twice; then `python -m pytest tests -q` (476 passed). Both runs succeeded; the gate took 1.3 s and 1.1 s (0.7 s before the change).

Then, in a scratch **copy** of that database only, one SY 2025-26 Bronze row's `sector` was set to `Charter`, a label the mapping does not list, and the build and gate files were run once more with `run_id = 'local-fail'`.

## Results

### Databricks: the verification query

The one-query verification from [Silver, Running on Databricks](../../docs/operations/silver.md#running-on-databricks), run on the SQL warehouse after run 2 with the commit above:

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
| published rows from a succeeded run | 180500 | 180500 | OK |
| candidate rows not published | 0 | 0 | OK |

#### Verification query after run 2: 20 rows, all OK
<img width="1022" height="471" alt="image" src="https://github.com/user-attachments/assets/3ba74370-9657-4e8e-b5de-e05d2d7c40d8" />


### Databricks: the tables

| Check | Result |
|---|---|
| Gate results of the two runs | 232 Silver results (116 per run) and 24 Bronze results, all PASS |
| What the gate checked | Its results name `deped_enrollment_clean_candidate` and `deped_enrollment_quarantine_candidate`, the tables it checks |
| Bronze rerun | Every load of run 2 `succeeded` with 0 batches loaded |
| Tables and owners | `deped_enrollment_clean`, `deped_enrollment_quarantine`, and their two `_candidate` tables, all owned by `reached-hq` (D-009) |
| Column types | The 66 count columns of `deped_enrollment_clean` are `INT` |
| Published as built | After run 2, the candidate and the Silver clean table are identical, run stamp included (0 rows in either `EXCEPT ALL` direction); both quarantine tables are empty |
| Identical rebuild | Delta versions 5 (run 1) and 6 (run 2) of `deped_enrollment_clean`, without the run stamp: 0 rows in either direction |
| No row changed by this change | Version 4 (published at `7d93d8e`, before this change) and version 6: 0 rows in either direction |

#### Gate results of the two runs: bronze PASS 24, silver PASS 232
<img width="1014" height="239" alt="image" src="https://github.com/user-attachments/assets/d21c0750-406c-4ca5-a110-bf24fb83a48b" />

#### The gate's results name the two candidate tables
<img width="1019" height="213" alt="image" src="https://github.com/user-attachments/assets/7842dec3-11d7-410c-af80-4796d1004d69" />

#### Tables in 03-silver: the two Silver tables and their two candidates, all owned by reached-hq
<img width="1017" height="272" alt="image" src="https://github.com/user-attachments/assets/59738868-9ea7-4106-8b4e-ff598a1b3eea" />

#### DESCRIBE HISTORY deped_enrollment_clean: versions 5 and 6 are the two runs
<img width="1014" height="288" alt="image" src="https://github.com/user-attachments/assets/6ef0f0c6-18b3-439e-b73f-9d6176f376fa" />

#### Candidate and published clean table compared: 0 and 0
<img width="1017" height="262" alt="image" src="https://github.com/user-attachments/assets/b36dc83f-db17-4f48-9c27-278a48d6cc85" />

#### Versions 4 and 6 compared: 0 and 0
<img width="1027" height="296" alt="image" src="https://github.com/user-attachments/assets/789f17ed-2519-43f8-802d-96df39bc6dbd" />

### Local: a build that fails its gate

| | Before the failing build | After it |
|---|---|---|
| `deped_enrollment_clean` | 180,500 rows of the last good run | the same 180,500 rows, unchanged |
| Published rows trusted (their `run_id` is a succeeded run) | 180,500 | 180,500 |
| `deped_enrollment_clean_candidate` | the good build | 180,500 rows of run `local-fail`, one with `sector` NULL |
| Gate | | stopped: `labels_mapped_sector` FAIL, 1 row in SY 2025-26 |
| `pipeline_runs` for `local-fail` | | `failed`, stage `gate`, "1 FAIL result(s) in data_quality_results" |

Before this change, the same steps at `7d93d8e` (the Silver SQL of #112) on a scratch copy of a database built by two local job runs at that commit replaced every school year of the published build: all 180,500 rows of `deped_enrollment_clean` then carried the failed run `local-fail-old`, 0 rows of the last good run remained, and 0 published rows came from a succeeded run (#119).

## Why it holds

1. The build creates only the two candidate tables ([build SQL](https://github.com/reached-hq/edu-access-intelligence/blob/acd6416e4b25cbceea60551ff8ca625cbe85f518/etl/03_silver/01_clean_deped_enrollment.sql)).
2. The gate records a failed run and stops the task with `raise_error` before its first `CREATE OR REPLACE TABLE` of a Silver table; a SQL task stops at the first failing statement, so nothing after it runs. It publishes quarantine first and clean last, and writes `succeeded` only after both ([gate](https://github.com/reached-hq/edu-access-intelligence/blob/acd6416e4b25cbceea60551ff8ca625cbe85f518/etl/03_silver/90_validate_deped_enrollment_clean.sql)).
3. Gold trusts a Silver table by the run its rows carry, so a later failed or interrupted run cannot make the last good build unreadable (D-025).

## Also shown by tests

`tests/test_silver.py`: a failed build never replaces the last good one, and the candidates keep it for review; a build that passes is published exactly as built; a run that dies between the two copies is never `succeeded`, and the last good clean table stays trusted; no current batch leaves the published build in place; a repaired run publishes; the generated gate stops before publishing and publishes clean last; every run rebuilds identical published rows.

## Limitations

- A failing gate and a run that dies while publishing are shown locally, not on Databricks, to keep the shared `dev` tables at a good build.
- The two Silver tables are still published one after the other, not in one transaction; the order and the trust rule make a task that dies between them safe for readers of the clean table (D-025).

## How to reproduce

Databricks: from a clean checkout of the commit above, `databricks bundle deploy --target dev --profile reached-hq`, confirm the deployed commit, run the job twice, then run the verification query from [Silver](../../docs/operations/silver.md#running-on-databricks) with the commit filled in, and compare versions of `deped_enrollment_clean` as in the [#85 evidence](2026-10-09-deped-enrollment-silver.md#how-to-reproduce). Locally: the job command above twice against a new database file; for the failing build, copy that file, set one SY 2025-26 Bronze row's `sector` to `Charter`, and run the two Silver files with `DuckDBStore("<copy>.duckdb").run_file(path, params)` from `src.ingestion.store`.
