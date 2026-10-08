# Evidence: DepEd enrollment Silver builds and passes its gate on Databricks, and a second run rebuilds identical rows

Issue #85 · Databricks `dev` · 2026-10-09 · checked by @hyenalouise

## The claim

The two Silver SQL tasks of `edu_access_pipeline`, run by Spark on the SQL warehouse, build `deped_enrollment_clean` and `deped_enrollment_quarantine` from the current Bronze batches with the same result as the local runs: 180,500 clean rows, 0 quarantined, learner totals equal to Bronze in every school year, and every gate check PASS. A second run rebuilds rows identical to the first, apart from the run stamp, and records a second `succeeded` run.

## What was run

The job `[dev ina_magno] edu_access_pipeline` (job `651937364323543`), deployed with `databricks bundle deploy --target dev --profile reached-hq` from a clean checkout of the pushed commit `7d93d8ee51efd82a714b3b07ed6c985c5aecede8`. Read back from the job before running: `git_source.git_commit` and the `code_revision` parameter both equal that commit, and the two Silver tasks are enabled. No other job run was active and the SQL warehouse was stopped. The job was then run twice with `databricks bundle run edu_access_pipeline --target dev --profile reached-hq`. Times are Manila (UTC+8).

| | Run 1 | Run 2 |
|---|---|---|
| Job run (`run_id` of the Silver rows) | `938255750884504` | `366050291737676` |
| Whole job | 01:25:04 to 01:30:27 (17:25:04 to 17:30:27 UTC, 2026-10-08), 5 min 22 s, `SUCCESS` | 01:31:20 to 01:35:05 (17:31:20 to 17:35:05 UTC), 3 min 45 s, `SUCCESS` |
| Tasks | 20 `SUCCESS` on the first attempt, 43 disabled | same |
| `add_control_columns` | 49 s | 16 s |
| `bronze_deped_enrollment` | skip ×3, 0 inserted, 116 s | skip ×3, 0 inserted, 89 s |
| `90_validate_deped_enrollment_raw` | 17 s | 6 s |
| `01_clean_deped_enrollment` | 42 s | 30 s |
| `90_validate_deped_enrollment_clean` | 50 s | 44 s |

No task waited in a queue, and only the Python tasks had setup time (at most 3 s). The Silver build is about one second of work locally; on the warehouse it takes 30 to 42 s, which is the cost of its statements, not of the data.

## Results

The one-query verification from [Silver, Running on Databricks](../../docs/operations/silver.md#running-on-databricks), run on the SQL warehouse after run 2, with the commit above:

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

`dev` holds two more succeeded `silver_build` runs, at `e9b3a47` (below), so the check counts the runs of the commit that ran.

Also checked on the warehouse:

| Check | Result |
|---|---|
| Gate results of the two runs | 232 Silver results (116 per run) and 24 Bronze results, all PASS; the new `counts_within_plausible_max` and `quarantine_reason_count_above_plausible_max` checks ran once per school year |
| Bronze rerun | Every load of run 2 `succeeded` with 0 batches loaded: enrollment skipped 3, facilities, PSA Poverty Stat and PSGC 1 each |
| Column types in Unity Catalog | The 66 count columns are `INT` |
| Owners | `deped_enrollment_clean` and `deped_enrollment_quarantine` are owned by `reached-hq` (D-009) |
| Identical rebuild | Delta versions 3 (run 1) and 4 (run 2) of `deped_enrollment_clean`, without `run_id`, `cleaned_at_utc`, and `code_revision`: 0 rows in either `EXCEPT ALL` direction |
| No real row changed by the last fixes | Version 2 (built at `e9b3a47`, before the BIGINT sums and the plausible maximum) and version 4: 0 rows in either direction |

What these runs confirm that the local runs could not (D-017): Spark runs the generated SQL as DuckDB does, including session variables read by a temporary view, `translate` with `chr(160)`, `regexp_like`, `regexp_replace`, the CTE inside `INSERT`, `MERGE` with session variables, job parameters reaching both SQL file tasks, and `CREATE OR REPLACE TABLE` with ownership handed to the group on existing Unity Catalog tables.

## Earlier runs at `e9b3a47`

Before the BIGINT sums, the plausible maximum, and finding S-4, the job was deployed at `e9b3a474a7c47c19681beeb033cc0da634079362` and run twice (`264658514180258`, `429750819114716`, 2026-10-09 00:49 to 01:12 Manila). Both runs `SUCCESS`; the same verification gave every check OK with 110 gate checks (the two new checks did not exist yet), and versions 1 and 2 were identical. In the first of those runs `add_control_columns` took 730 s instead of 16 to 49 s, all of it counted as execution with no queue; the next run took 16 s. It was serverless start-up on Free Edition, not this change, which does not touch that task.

## Limitations

- No real row is quarantined, so quarantine on Databricks is shown only by the build and gate running with an empty quarantine table; the made-up rows of `tests/test_silver.py` show the rest locally.
- A failing Silver gate was not exercised on Databricks, to keep the shared `dev` tables at a good build.
- `dev` still holds a `silver_build` run of 2026-10-07 (commit `d2f0c62`, the earlier skip design) with status `running`, and Delta version 0 of `deped_enrollment_clean` from it. Readers take the latest run, so it is never read; removing it is an open question in [Silver](../../docs/operations/silver.md#open-questions).

## How to reproduce

From a clean checkout of the commit above: `databricks bundle validate` and `databricks bundle deploy --target dev --profile reached-hq`, confirm the deployed commit, then `databricks bundle run edu_access_pipeline --target dev --profile reached-hq` twice. Run the verification query from [Silver](../../docs/operations/silver.md#running-on-databricks) on the SQL warehouse with the commit filled in, then compare the last two versions of `deped_enrollment_clean`:

```sql
SELECT COUNT(*) FROM (
  SELECT * EXCEPT (run_id, cleaned_at_utc, code_revision) FROM edu_access.`03-silver`.deped_enrollment_clean VERSION AS OF 3
  EXCEPT ALL
  SELECT * EXCEPT (run_id, cleaned_at_utc, code_revision) FROM edu_access.`03-silver`.deped_enrollment_clean VERSION AS OF 4
);
```

``DESCRIBE HISTORY edu_access.`03-silver`.deped_enrollment_clean`` gives the version numbers of the two runs.
