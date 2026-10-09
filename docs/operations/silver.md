# Silver: Bronze → clean, typed, standardized

How the Bronze rows of each source's current deliveries become one clean, typed, validated table, what each rule changes, what is set aside, and how each run is recorded. The first source built this way is `deped_enrollment` (#85).

**Status:** two SQL tasks of the job `edu_access_pipeline`, built and tested locally, and run by the job on the real Bronze data of all three school years (2026-10-09, [evidence](../../evidence/reconciliation/2026-10-09-deped-enrollment-bronze-to-silver.md)). Run on Databricks `dev` on 2026-10-09 at `7d93d8e`: two job runs, every check OK, identical rows ([evidence](../../evidence/pipeline-runs/2026-10-09-deped-enrollment-silver.md)); and with publishing after the gate at `acd6416`, with the same rows ([evidence](../../evidence/pipeline-runs/2026-10-09-silver-publish-after-gate.md)).

## The flow

```
bronze_deped_enrollment             Python: check and load the deliveries          (serverless)
90_validate_deped_enrollment_raw    SQL: the Bronze gate                            (SQL warehouse)
   │  only if it passed
   ▼
01_clean_deped_enrollment           SQL: run stamp in session variables; pipeline_runs 'running';
   │                                     rebuild the candidates from 01-control.current_batches only:
   │                                       deped_enrollment_clean_candidate       one row per school per school year
   │                                       deped_enrollment_quarantine_candidate  rows that cannot be trusted, with reasons
   │  only if it succeeded
   ▼
90_validate_deped_enrollment_clean  SQL: check the candidates, one row per check in data_quality_results
                                         any FAIL: pipeline_runs 'failed', the task stops, nothing published
                                         all PASS or WARN: publish quarantine, then clean:
                                           deped_enrollment_quarantine, deped_enrollment_clean
                                         then pipeline_runs 'succeeded'
   │
   ▼  this source lane is complete; other source lanes run independently in parallel
      90_validate_control is the fan-in; Integration and Gold read a Silver table only when
      the run its rows carry succeeded
```

Code: `src/silver/` ([module list](../../src/silver/README.md)). SQL: `etl/03_silver/` ([files](../../etl/03_silver/README.md)), generated from the Bronze contract and the [Silver mapping](../../config/mappings/deped_enrollment.json). Columns: [data dictionary](../data/silver/deped-enrollment-clean.md). The job: D-020; Silver: D-021 to D-025 in [decisions.md](../governance/decisions.md).

## The question Silver answers

> When a planner reads a number built from Silver, can the team say exactly which Bronze row it came from, what was changed, why, and what was set aside, without rerunning everything or spending compute it does not need?

| Part | How |
|---|---|
| Which Bronze row | Every clean and quarantined row carries `batch_id`, `delivery_version`, `schema_version`, `source_sha256`, and `source_row_number`; the last two identify the Bronze row exactly. The gate checks that every Silver row resolves to a current Bronze row |
| What was changed | Each rule is one generated SQL expression from a reviewed file. Every build records how many rows each rule changed or flagged (`rule_*`, `flag_*` in `data_quality_results`), and the published value is always one join away in Bronze |
| Why | The rule table below, the evidence for every label in the mapping, and decisions D-021 to D-025 |
| What was set aside | `deped_enrollment_quarantine`, with the reasons; `rows_reconcile` proves Bronze rows = clean + quarantined, per school year. A build that fails its gate is never published; it waits in the candidate tables for review |
| Which run and code | `run_id` (the job run), `cleaned_at_utc` (one value per build), and `code_revision` on every row and every check; the run itself in `pipeline_runs` |
| Compute | Silver runs only after its Bronze gate passed, as two SQL tasks on the warehouse the Bronze gate already started. Rebuilding 180,000 rows takes about a second locally (D-025) |

## Grain and shape

One row per school per school year, key (`school_id`, `school_year`), wide as published: the 66 grade × sex × strand count columns stay columns (D-021). Gold unpivots them when its grain is agreed. Column names are snake_case; the one publisher column that is not, `Modified Curricular Offering Classification` (SY 2025-26 only, undocumented), is renamed `modified_curricular_offering_classification`.

## Cleaning rules

Counts are from the local run on the real Bronze data, current batches only (version 1 of each school year), on 2026-10-07. Every build records the same numbers in `data_quality_results`. Action: **transform** changes a value, **flag** adds a column and keeps the row, **quarantine** sets the row aside, **fail** stops the run.

| Rule | Finding | Action | Why | SY 2023-24 | SY 2024-25 | SY 2025-26 | Information that may be lost (all of it stays in Bronze) |
|---|---|---|---|---:|---:|---:|---|
| Read only the current batch of each school year | D-015 | transform | Older versions stay in Bronze, never in Silver | 60,167 rows | 60,129 | 60,204 | Superseded versions (none yet) |
| `school_id` kept as text, exactly six digits, unique per year | O-1 | quarantine | A key that is blank, malformed, or repeated cannot be trusted | 0 | 0 | 0 | The quarantined rows, until resolved |
| Counts to INT when 1–9 digits | O-2 | transform | Whole numbers type without loss | 0 not castable | 0 | 0 | None |
| Negative or non-whole count | O-2 | quarantine | A count cannot be negative or fractional | 0 | 0 | 0 | The quarantined rows |
| Count above 10,000 (`plausible_max`) | O-2 | quarantine | The largest published count is 4,097; above 10,000 is a count with an extra digit, which reconciliation cannot see | 0 | 0 | 0 | The quarantined rows |
| Blank count stays NULL, not 0 (rows with a blank count) | O-16, Bronze | transform | Never invent a value; in SY 2025-26 blank means "not published". In SY 2023-24 the four unique-strand columns (`g11_unique_*`, `g12_unique_*`) are blank in every row and no other count is blank, so that year publishes no unique-strand enrollment: NULL, not 0 | 60,167 | 0 | 48,709 | None |
| Column absent from the year's file stays NULL (rows) | O-7 | transform | Told apart from a blank by `schema_version` (`v1`) | 60,167 | 60,129 | 0 | None |
| Learners unchanged by cleaning (`learners_reconcile`) | O-3 | fail if not | Cleaning must move no learner | 27,081,292 | 26,400,182 | 25,935,863 | — |
| Labels mapped to one standard set (rows with any relabel) | O-8, O-9 | transform; unmapped **fails** | One label per category across years | 0 | 0 | 60,204 | The year's own wording |
| `True`/`Yes` → TRUE, `False`/`No` → FALSE, blank → NULL | O-8 | transform; unmapped **fails** | One boolean representation | 0 unmapped | 0 | 0 | None |
| Trim, collapse spaces, tabs, no-break spaces (rows) | O-5 | transform | Spacing differences break joins (`NCR   SECOND DISTRICT`, `Non-Sectarian `) | 6 | 4 | 13,958 | Exact spacing |
| Repair `Ã‘` → `Ñ` and `Ã±` → `ñ` in free text (rows) | O-17 | transform | Mangled in the published data, every year | 273 | 274 | 274 | The mangled bytes |
| Blank text → NULL (rows; `street_address` 5,203 / 5,038 / 0 and `barangay` 70 / 65 / 7) | O-14, O-15 | transform | Make missingness explicit | 5,266 | 5,096 | 7 | None |
| `street_address` `-`, `n/a`, `N/A` → NULL | O-14 | transform | Placeholders mean no address | 0 | 0 | 3,555 | The placeholder spelling |
| `is_overseas` (PSO, SCHOOL ABROAD) | O-13 | flag | Placed in Pasig City in SY 2025-26; Gold excludes from geography | 33 | 35 | 36 | None |
| `enrollment_status = 'all_zero'` | S-1 | flag | Possibly closed or non-reporting; never dropped | 115 | 24 | 0 | None |
| `enrollment_status = 'no_counts'` | S-1, Bronze | flag | No count published at all | 0 | 0 | 46 | None |
| `barangay_possibly_truncated` (published length exactly 40) | O-18 | flag | Cannot be repaired | 24 | 25 | 25 | None |
| Blank `barangay` (NULL) | O-15 | flag (NULL) | Placement below the municipality is unknown | 70 | 65 | 7 | None |
| Region and province changes, `(Capital)` and other place-name spelling | O-10, O-11, O-5 | none | Comparability and matching belong to Integration and Gold (D-012) | kept | kept | kept | — |
| School ID churn | O-12 | none | Not a data error; Gold reports it | — | — | — | — |

Silver keeps "(Capital)" on 5,450 / 5,454 / 5,446 rows and every other place spelling, so Integration can match them to PSGC.

### What the Bronze data showed beyond the profile

Profiling Bronze rather than the raw files confirmed every count above, and found three things the profile does not say (to add to [profile.md](../data/source-inventory/deped_enrollment/profile.md) with the profiling script, D-007):

- **SY 2025-26 leaves counts blank where earlier years publish 0.** All 47,232 schools with `offers_shs = No` have blank senior-high columns, where SY 2024-25 publishes 0 for such schools, and 1,403 schools have blank kindergarten-to-grade-10 columns. Sums are unaffected; a school-level comparison across years must not read NULL as 0.
- **S-1 for SY 2025-26 is 46 schools with no count at all**, not 46 schools with zero counts (Private 35, PSO 8, Public 3). No SY 2025-26 school publishes all zeros.
- **O-17's "11, 11, 10 school names" are lowercase `Ã±`**, not `Ã‘`. Three to four school names and addresses per year also contain a tab or a no-break space.

## Quarantine

`deped_enrollment_quarantine` holds `school_year`, `school_id` as published, `quarantine_reasons` (every reason that applies), the Bronze lineage, and the run stamp. Read the published values from Bronze by `source_sha256` and `source_row_number`. Reasons: `school_id_blank`, `school_id_malformed`, `school_id_duplicated`, `count_negative`, `count_uncastable`, `count_above_plausible_max` (D-024). The three acquired years quarantine nothing.

A row's reasons are decided with explicit NULL handling (`school_id IS NULL OR school_id = ''`), and the reasons string is never NULL, so the split into the two tables cannot lose a row whose `school_id` is NULL; `tests/test_silver.py` proves it with such a row.

## The gate

`etl/03_silver/90_validate_deped_enrollment_clean.sql` is the job task after every build, reading Bronze, the two candidate tables, and `current_batches`. It writes one row per check to `` `01-control`.data_quality_results `` with `layer = 'silver'`, `:run_id`, `:code_revision`, and the candidate table checked as `table_name`. If this execution recorded any FAIL it records the run `failed` and fails the task before publishing anything. Otherwise it publishes the candidates (quarantine first, then clean) and records the run `succeeded`. Only this execution's results count, so a repaired job run (same `run_id`) is judged on its own. Column types are fixed by the build itself (every count through `TRY_CAST(... AS INT)`); `tests/test_silver.py` checks them locally, and the Databricks check below checks them in Unity Catalog.

| Check | Per | FAIL when |
|---|---|---|
| `rows_reconcile` | school year | Bronze current rows ≠ clean + quarantined |
| `school_id_unique`, `school_id_valid` | school year | A key repeats, is NULL, or is not six digits in the clean table |
| `counts_non_negative` | school year | A count is negative |
| `counts_within_plausible_max` | school year | A count is above 10,000 in the clean table |
| `learners_reconcile` | school year | Clean learners ≠ Bronze learners of the same rows |
| `missing_counts_stay_null` | school year | NULL count cells in clean ≠ blank or absent cells in Bronze (catches blank → 0) |
| `absent_columns_stay_null` | school year | A column the year's schema lacks is filled |
| `labels_mapped_<column>` (9 columns) | school year | A published label is not in the reviewed mapping, on a clean or a quarantined row |
| `enrollment_status_valid` | school year | A status outside the three values |
| `current_batches_present` | table | Bronze has no current batch for the source, so Silver would be empty |
| `lineage_complete`, `rows_resolve_to_current_bronze` | table | A lineage column is NULL, or a Silver row is not a current Bronze row |
| `rows_built_by_this_run`, `one_timestamp_per_run` | table | A row is left from another run, or the tables disagree on `cleaned_at_utc` |
| `quarantine_rate` | school year | WARN above 0; **FAIL above 1%** of the year's Bronze rows |
| `quarantine_reason_<reason>` | school year | WARN above 0 |
| `rule_*`, `flag_*` | school year | Never: records of how many rows each rule changed or flagged (expected is NULL) |

| Status | Meaning | Action |
|---|---|---|
| PASS | As expected | None |
| WARN | Rows were quarantined (at most 1% of a year) | Recorded; the build is published; the source owner reviews the reasons |
| FAIL | The candidate build cannot be trusted | The gate task fails before publishing and `pipeline_runs` says `failed`; the Silver tables keep the last build that passed, and the failed one waits in the candidate tables until the next run. Other source lanes are independent and keep running |

The local run on the real data recorded 116 results, all PASS.

## Every run rebuilds, and every run is recorded

Silver rebuilds both candidate tables on every job run with `CREATE OR REPLACE TABLE ... AS SELECT` from the current batches, and publishes them when the gate passes (D-025): the same Bronze gives the same rows, so a rerun changes nothing but the run stamp, and a revised delivery (`delivery_version` 2) replaces its school year because `current_batches` points to it. On the real data, the MD5 of all 180,500 clean rows (without the run stamp) was `311b445851533467fd7e669d3cf6e537` after both of two job runs ([evidence](../../evidence/reconciliation/2026-10-09-deped-enrollment-bronze-to-silver.md), with the query).

Each published table is one Delta commit; the pair is not, so the run row is the commit marker, as `ingestion_batches` is for Bronze. Its `run_id` is the job run id, which every source's build in that job run shares, so the row is keyed by `run_id`, `pipeline_name`, and `source_id`, and `job_run_id` holds the same id, so filtering `pipeline_runs` on `job_run_id` finds a job run's Bronze loads and Silver builds together (D-020):

| `pipeline_runs.status` (`pipeline_name = 'silver_build'`) | Written by | Meaning |
|---|---|---|
| `running` | the build task, first | The build started; with no later status it never finished, its gate never ran, or the task died while publishing |
| `succeeded` | the gate task, after publishing | Every check passed or warned, and both tables were published: Silver rows carrying this `run_id` may be read |
| `failed` | the gate task, after its checks | At least one FAIL: nothing was published; the build is in the candidate tables |

Gold's rule follows: a Silver table is trusted when the `run_id` its rows carry is a `silver_build` run that `succeeded`. After a failed run the published tables still carry the last good run, so they stay readable; the rule also covers a task that dies between the two copies, which leaves the Silver quarantine from a `running` run and the Silver clean table from the last good one. A task that dies after both copies but before the `succeeded` row (only the clean table's owner statement and that row come between) leaves both tables carrying a `running` run, so Gold has no trusted Silver for the source until the next run passes and republishes. That is the safe side: Gold never reads a build whose run was not confirmed.

## Compute

Free Edition's serverless capacity is shared; in the Bronze runs most time was spent waiting for it, and each small control-table statement took 3 to 13 seconds.

- **Two SQL tasks on the warehouse.** The Bronze gate before them has already started it, so Silver adds two tasks' statements, not a new start-up. No notebook.
- **No skip.** A file cannot decide to skip itself, and the rebuild is cheap (about a second for 180,500 rows locally), so every run rebuilds (D-025). The saving given up is that work, not a warehouse start.
- **A build** is about 17 statements: the run stamp (6), the run row, the schema and its owner, the classification view, two `CREATE OR REPLACE`, two comments, and two owner statements, all on the candidate tables. Each candidate's comment says it is unpublished and names the Silver table to read instead; the published copies carry no comment. **The gate** is 10: its start time (2), the checks, the `failed` run row, the stop, two copies and two owner statements to publish, and the `succeeded` run row. Locally: about 1.1 s and 0.7 s.
- **Parallel source lanes.** Tasks within this source stay ordered, while unrelated sources may run at the same time. There is no schedule, and `max_concurrent_runs: 1` prevents two whole job runs from overlapping.

On Databricks `dev` the build took 30 to 56 s and the gate 44 to 50 s before it published, 47 to 63 s since, with no queue or setup time ([evidence](../../evidence/pipeline-runs/2026-10-09-deped-enrollment-silver.md), [with publishing](../../evidence/pipeline-runs/2026-10-09-silver-publish-after-gate.md)): the warehouse's time per statement, not the 180,500 rows.

## Running locally

From the repository root, with the virtual environment active, run the whole job on DuckDB in a deterministic dependency order equivalent to the Databricks DAG:

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.job.local_run
```

The tables go to `local_state/edu_access.duckdb` (`--db <path>` for another file). Bronze loads only new files; Silver rebuilds every time. Exit code 0 when every task succeeded, 1 otherwise, with the failed tasks named.

## Changing a rule or approving a label

1. Edit `config/mappings/deped_enrollment.json`: a new label goes under its column with the standard value and the evidence (how many of the same schools carried the old label). A new column in a new schema version must be classified there too, or the generator stops.
2. Regenerate the three generated files (a test fails until you do):

   On Windows, set `PYTHONUTF8=1` first (in PowerShell, `$env:PYTHONUTF8 = "1"`). Without it Python writes the redirected file in cp1252, the `Ñ` repair becomes an invalid byte, and the build fails with `'utf-8' codec can't decode byte 0xd1`.

   ```bash
   python -m src.silver.cli sql --source deped_enrollment > etl/03_silver/01_clean_deped_enrollment.sql
   ```

   ```bash
   python -m src.silver.cli gate --source deped_enrollment > etl/03_silver/90_validate_deped_enrollment_clean.sql
   ```

   ```bash
   python -m src.silver.cli dictionary --source deped_enrollment > docs/data/silver/deped-enrollment-clean.md
   ```

3. Run the tests and the job locally on the real data; compare the `rule_*` counts with the table above. The source owner approves the pull request. The next job run builds with the new rules.

## Running on Databricks

**Run on `dev` on 2026-10-09** at `be5ee73`, with Silver publishing only after its gate passes ([evidence](../../evidence/pipeline-runs/2026-10-09-silver-publish-after-gate.md#re-run-at-the-head-commit-be5ee73)); first at `7d93d8e` ([evidence](../../evidence/pipeline-runs/2026-10-09-deped-enrollment-silver.md)). The deliberate confirmation run (D-008), repeated after any change to the Silver SQL, after the branch is pushed:

1. From a clean checkout of the pushed commit, announce the run, detach notebooks, leave the SQL warehouse stopped (the job starts it).
2. `databricks bundle validate --target dev --profile reached-hq`, then `databricks bundle deploy --target dev --profile reached-hq`; confirm in `databricks bundle summary` that `git_commit` and `code_revision` both equal `git rev-parse HEAD`.
3. `databricks bundle run edu_access_pipeline --target dev --profile reached-hq` twice. In both runs the Bronze loads skip (already loaded), the gates pass, and Silver rebuilds.
4. Check with the queries below, then record the evidence in `evidence/pipeline-runs/<date>-deped-enrollment-silver.md` in the layout of the Bronze evidence, with per-task timings (job start, task start and end, queue and setup time) so waiting for compute is told apart from work.

What only Databricks can show, all confirmed by the 2026-10-09 runs: Spark's behavior for the shared SQL (`regexp_like`, `translate`, `chr(160)`, session variables, the CTE inside `INSERT`, `MERGE` with variables), job parameters reaching SQL file tasks, `CREATE OR REPLACE TABLE` and ownership on existing Unity Catalog tables, and the real cost of the warehouse tasks.

All checks in one query, each marked `OK` or `CHECK`, for the three approved deliveries after two runs. Replace the commit with the one that ran:

```sql
WITH c AS (SELECT * FROM edu_access.`03-silver`.deped_enrollment_clean),
     q AS (SELECT * FROM edu_access.`03-silver`.deped_enrollment_quarantine),
     pr AS (SELECT * FROM edu_access.`01-control`.pipeline_runs WHERE pipeline_name = 'silver_build' AND source_id = 'deped_enrollment'),
     last_run AS (SELECT MAX_BY(run_id, started_at_utc) AS run_id FROM pr),
     d AS (SELECT * FROM edu_access.`01-control`.data_quality_results
           WHERE layer = 'silver' AND source_id = 'deped_enrollment' AND run_id = (SELECT run_id FROM last_run)),
checks AS (
  SELECT 'clean rows SY 2023-24' AS check_name, '60167' AS expected, CAST(COUNT_IF(school_year = '2023-24') AS STRING) AS actual FROM c
  UNION ALL SELECT 'clean rows SY 2024-25', '60129', CAST(COUNT_IF(school_year = '2024-25') AS STRING) FROM c
  UNION ALL SELECT 'clean rows SY 2025-26', '60204', CAST(COUNT_IF(school_year = '2025-26') AS STRING) FROM c
  UNION ALL SELECT 'quarantined rows', '0', CAST(COUNT(*) AS STRING) FROM q
  UNION ALL SELECT 'repeated keys', '0', CAST(COUNT(*) - COUNT(DISTINCT school_id || school_year) AS STRING) FROM c
  UNION ALL SELECT 'learners SY 2023-24 / 2024-25 / 2025-26', '27081292 / 26400182 / 25935863',
    MAX(CASE WHEN batch_id LIKE '%2023-24%' THEN actual END) || ' / ' || MAX(CASE WHEN batch_id LIKE '%2024-25%' THEN actual END)
    || ' / ' || MAX(CASE WHEN batch_id LIKE '%2025-26%' THEN actual END) FROM d WHERE check_name = 'learners_reconcile'
  UNION ALL SELECT 'blank SHS counts kept NULL, SY 2025-26', '47352', CAST(COUNT_IF(school_year = '2025-26' AND g11_stem_male IS NULL) AS STRING) FROM c
  UNION ALL SELECT 'absent v2 column NULL in v1 rows', '120296', CAST(COUNT_IF(schema_version = 'v1' AND g11_sshs_acad_male IS NULL) AS STRING) FROM c
  UNION ALL SELECT 'standard labels, school_management, SY 2025-26', '9', CAST(COUNT(DISTINCT CASE WHEN school_year = '2025-26' THEN school_management END) AS STRING) FROM c
  UNION ALL SELECT 'mangled Ã‘ left', '0', CAST(COUNT_IF(barangay LIKE '%Ã‘%' OR street_address LIKE '%Ã‘%') AS STRING) FROM c
  UNION ALL SELECT 'overseas flagged', '104', CAST(COUNT_IF(is_overseas) AS STRING) FROM c
  UNION ALL SELECT 'no counts published, SY 2025-26', '46', CAST(COUNT_IF(enrollment_status = 'no_counts') AS STRING) FROM c
  UNION ALL SELECT 'checks in the last run', '116', CAST(COUNT(*) AS STRING) FROM d
  UNION ALL SELECT 'checks in the last run not PASS', '0', CAST(COUNT_IF(status <> 'PASS') AS STRING) FROM d
  UNION ALL SELECT 'rows from the last run', '180500', CAST(COUNT_IF(run_id = (SELECT run_id FROM last_run)) AS STRING) FROM c
  UNION ALL SELECT 'rows from another commit', '0', CAST(COUNT_IF(code_revision <> '<commit that ran>') AS STRING) FROM c
  UNION ALL SELECT 'last silver run', 'succeeded', MAX(status) FROM pr WHERE run_id = (SELECT run_id FROM last_run)
  UNION ALL SELECT 'silver runs succeeded at this commit', '2', CAST(COUNT_IF(status = 'succeeded' AND code_revision = '<commit that ran>') AS STRING) FROM pr
  UNION ALL SELECT 'published rows from a succeeded run', '180500', CAST(COUNT(*) AS STRING)
    FROM c JOIN pr ON pr.run_id = c.run_id AND pr.status = 'succeeded'
  UNION ALL SELECT 'candidate rows not published', '0', CAST(COUNT(*) AS STRING) FROM (
    SELECT * FROM edu_access.`03-silver`.deped_enrollment_clean_candidate EXCEPT ALL SELECT * FROM c)
)
SELECT check_name, expected, actual, CASE WHEN expected = actual THEN 'OK' ELSE 'CHECK' END AS result FROM checks;
```

After a run that failed its gate, four rows show `CHECK` by design, because they describe that latest run: `checks in the last run not PASS` (its FAIL results), `rows from the last run` (0: nothing of it was published), `last silver run` (`failed`), and `candidate rows not published` (the failed build waits in the candidate table). `published rows from a succeeded run` stays OK: the Silver tables still hold the last good build. To check that build instead, read `data_quality_results` for its `run_id`.

Column types, in Unity Catalog only (expect `INT` 66):

```sql
SELECT data_type, COUNT(*) AS columns
FROM edu_access.information_schema.columns
WHERE table_schema = '03-silver' AND table_name = 'deped_enrollment_clean' AND column_name LIKE '%male'
GROUP BY data_type;
```

## Handoff to Integration and Gold

What Silver guarantees, per run that ended `succeeded`:

- One row per (`school_id`, `school_year`) for the current delivery of every school year; Bronze rows = clean + quarantined; learner totals equal Bronze's.
- Counts are INT or NULL; NULL is never 0. Booleans are TRUE, FALSE, or NULL. Every category value is in the reviewed standard set.
- Every row names its Bronze row, delivery, schema version, Silver run, timestamp, and commit.

What Gold must respect:

- Read a Silver table only when the `run_id` its rows carry is a `silver_build` run that `succeeded` in `pipeline_runs`. A later failed run does not change what is published, so the last good build stays readable. Never read the `_candidate` tables.
- `is_overseas`: exclude from any geographic analysis; their place names are placeholders in SY 2025-26.
- Suspected over-reporting (profile S-4): schools 410978, 410977, and 410472 report Grade 11 strands that grow 5 to 23 times in a year, to the largest counts in the data. Silver keeps them as published; decide whether strand- and school-level results include them.
- `enrollment_status`: `all_zero` and `no_counts` schools are kept in Silver; decide per measure whether they count as schools (S-1).
- `barangay_possibly_truncated` and NULL `barangay`: barangay-level results for these schools are uncertain.
- NULL counts: "not published"; in SY 2025-26 usually "level not offered". Use `schema_version` to tell a column the year lacks from a blank, and NULL-safe filters (`IS NOT TRUE`) on nullable booleans.
- Region is as published: NIR exists from SY 2024-25 (O-10); compare regions across years only through PSGC (D-012).
- School IDs change between years (O-12): a missing ID is not a closed school.
- Unpivot grade, sex, and strand there (D-021), and decide how `g11_sshs_*` relates to the older strand columns.

What Integration still has to do: match `province`, `municipality`, and `barangay` to PSGC 2Q 2026 (D-012) using the names as Silver keeps them (spacing normalized, `Ñ` repaired, `(Capital)` and other suffixes kept), apply the 40-character prefix rule to truncated barangays (O-18), and report unmatched names ([generated list](../data/cross-source/generated/deped_psgc_unmatched.md)).

## Limitations

- On Databricks only `dev` has run it, and only with nothing to quarantine: a quarantined row and a failing gate are shown by the local tests, not on Databricks.
- `region` and the other categories are gated, so any new label stops Silver until it is reviewed, by design.
- Every run rebuilds every school year, and starts the SQL warehouse; fine at 180,000 rows, revisit for larger sources.
- The two Silver tables are published one after the other: a task that dies between them leaves them from different runs until the next run. Gold's rule (the run each table's rows carry) keeps the clean table readable; a reader comparing the two tables must check both runs. A task that dies after both copies but before recording `succeeded` leaves nothing trusted for the source until the next run passes.
- `deped_enrollment` and `hdx_boundaries` (#90) have Silver; facilities and the other sources follow with their own mapping (#86 to #89).

## Open questions

| Question | Default until decided | Where |
|---|---|---|
| Should `Ã±` → `ñ` be repaired with `Ã‘` → `Ñ`, or left for Integration? | Repaired (exact pattern, counted) | D-023 |
| Should more address placeholders become NULL (`none` 709, `not applicable` about 300 a year, `NA`/`na` 44, `0` 104 in SY 2025-26)? | Only `-`, `n/a`, `N/A` | D-023 |
| Is 1% the right FAIL threshold for quarantine? | 1% of a school year's Bronze rows | D-024 |
| Should a school with two conflicting rows keep one copy if the rows are identical? | Every copy quarantined | D-024 |
| Should Gold treat `no_counts` like `all_zero`? | Gold decides per measure | D-024 |
| Should Silver skip when Bronze is unchanged, with a condition task in the job? | Rebuild every run | D-025 |
| Should the Bronze gate also count only its own execution's results, so a repaired job run is judged on its own, as the Silver gate does? Changing it means regenerating every source's Bronze gate | Start a new run instead of repairing a failed one | D-020 |
| Drop `01-control.layer_builds` on dev, created by the cancelled run of 2026-10-08 and no longer used? | Left in place | Team |
| Should profile.md record the three Bronze findings above (and S-1's correction)? | Recorded here only | D-007 |

## HDX ADM3 boundaries

`hdx_boundaries` uses the design above (two SQL tasks, candidates, publish after the gate, `pipeline_runs`; D-020, D-025) with its own rules (D-035). Its SQL and dictionary are generated by `src/silver/hdx_boundaries.py` from the Bronze contract and the [Silver rules](../../config/mappings/hdx_boundaries.json); columns: [data dictionary](../data/silver/hdx-adm3-clean.md).

**Status:** implemented and tested locally on made-up GeoJSON (`tests/test_silver_hdx.py`, with DuckDB's spatial extension); every geometry function the SQL uses was checked read-only on Databricks `dev` on 2026-10-09. Run by the job on Databricks `dev` on 2026-10-09 at `853be19`, twice: 1,642 clean rows, 0 quarantined, all 38 checks PASS in both runs ([evidence](../../evidence/pipeline-runs/2026-10-09-hdx-adm3-silver-databricks.md)).

### The flow (HDX)

```
06_create_hdx_adm3_raw        SQL: Bronze DDL
bronze_hdx_boundaries         Python: check and load the GeoJSON file (skip when already loaded)
90_validate_hdx_adm3_raw      SQL: the Bronze gate
   │  only if it passed
   ▼
06_clean_hdx_adm3             SQL: run stamp; pipeline_runs 'running'; from current_batches only:
   │                               hdx_adm3_clean_candidate       one row per ADM3 unit
   │                               hdx_adm3_quarantine_candidate  features that cannot be trusted
   │  only if it succeeded
   ▼
90_validate_hdx_adm3_clean    SQL: 38 checks (5 whole build, 33 per batch); any FAIL: 'failed', stop,
                                   nothing published; else publish quarantine, then clean, then 'succeeded'
```

### Grain and shape (HDX)

One row per COD-AB ADM3 feature (city or municipality) of each current batch, key (`adm3_pcode`, `valid_on`), all 32 published columns in file order, then three flags, the lineage, and the run stamp. The geometry is the published GeoJSON text (D-035): parse it with `try_to_geometry` on Databricks or `ST_GeomFromGeoJSON` in DuckDB spatial.

### Cleaning rules (HDX)

| Rule | Action | Why | Real file (2026-10-09 checks) |
|---|---|---|---|
| Current batches only | transform | D-015 | 1,642 features |
| `adm3_pcode` and parent codes kept exactly as published | none | Not PSGC codes (#74, HB-2) | |
| Blank, malformed (`^PH[0-9]{7}$`) or repeated `adm3_pcode` | quarantine | A key that cannot be trusted | 0 / 0 / 0 |
| Names trimmed, spaces collapsed, blank → NULL | transform | Joins | 0 with extra spaces |
| Region, country, version, language mapped to reviewed labels | transform; unmapped **fails** | One label per category | 17 / 1 / 1 / 1 labels |
| `valid_on`, `valid_to` → DATE when `YYYY-MM-DD` | transform; else quarantine | | 0 failures; `valid_to` blank in all rows |
| `area_sqkm` → DECIMAL(20,14), `center_lat`/`center_lon` → DECIMAL(18,14), only when the text fits exactly | transform; else quarantine | No digit rounded (D-023) | up to 4+14 digits; 0 failures |
| `area_sqkm` zero or negative | quarantine | Impossible | min 0.399814 |
| Geometry does not parse, is empty, or is not Polygon/MultiPolygon | quarantine | | 0 / 0 / 0 (1,273 Polygon, 369 MultiPolygon) |
| Geometry parses but is not valid | flag `geometry_is_valid` | Never repaired | 0 |
| Published centre outside its shape | flag `center_inside_geometry` | | 0 |
| adm3 → adm2 → adm1 code chain broken | flag `hierarchy_consistent` | | 0 |

### The gate (HDX)

Besides the shared whole-build checks (`current_batches_present`, `lineage_complete`, `rows_resolve_to_current_bronze`, `rows_built_by_this_run`, `one_timestamp_per_run`), per batch: `rows_reconcile`, `adm3_pcode_unique`, `adm3_pcode_valid`, `codes_as_published`, `geometry_as_published`, `values_kept` (a clean value is NULL only where Bronze is blank), `valid_on_is_reference_date`, `geometry_parsed`, `geometry_type_allowed`, `geometry_not_empty`, `area_positive`, `flags_consistent` (the gate re-parses every shape and recomputes the flags), and `labels_mapped_*` (FAIL); `geometry_valid`, `center_inside_geometry`, `hierarchy_consistent`, and `quarantine_reason_*` (WARN); `quarantine_rate` (WARN above 0, FAIL above 1%); and two `rule_*` records. `hdx_boundaries.gate_checks()` lists them.

### Running locally (HDX)

`python -m src.job.local_run` runs the lane with the rest of the job. The first statement that uses a geometry function makes DuckDB install and load its spatial extension (downloaded once from duckdb.org).

### Handoff to Integration and Gold (HDX)

- `adm3_pcode` is a COD-AB P-code, not a PSGC code; match by code and name together (`03_map_hdx_adm3_psgc`), and relate the 8 Special Geographic Area units spatially ([limitations](../governance/limitations.md)).
- Regions are COD-AB's 17, before the Negros Island Region; take regions from PSGC.
- Parse `geometry` where a spatial type is needed; never write a repaired shape back to Silver.

