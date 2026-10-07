# Silver: Bronze → clean, typed, standardized

How the Bronze rows of each source's current deliveries become one clean, typed, validated table, what each rule changes, what is set aside, and how each run is recorded. The first source built this way is `deped_enrollment` (#85).

**Status:** two SQL tasks of the job `edu_access_pipeline`, built and tested locally, and run on the real Bronze data of all three school years (2026-10-08). **Not yet run on Databricks**; the steps are under [Running on Databricks](#running-on-databricks).

## The flow

```
bronze_deped_enrollment             Python: check and load the deliveries          (serverless)
90_validate_deped_enrollment_raw    SQL: the Bronze gate                            (SQL warehouse)
   │  only if it passed
   ▼
01_clean_deped_enrollment           SQL: run stamp in session variables; pipeline_runs 'running';
   │                                     rebuild from 01-control.current_batches only:
   │                                       deped_enrollment_clean       one row per school per school year
   │                                       deped_enrollment_quarantine  rows that cannot be trusted, with reasons
   │  only if it succeeded
   ▼
90_validate_deped_enrollment_clean  SQL: one row per check in data_quality_results;
                                         pipeline_runs 'succeeded' or 'failed'; any FAIL fails the task
   │
   ▼  this source lane is complete; other source lanes run independently in parallel
      90_validate_control is the fan-in; Integration and Gold read Silver only when the
      latest silver_build run of the source succeeded
```

Code: `src/silver/` ([module list](../../src/silver/README.md)). SQL: `etl/03_silver/` ([files](../../etl/03_silver/README.md)), generated from the Bronze contract and the [Silver mapping](../../config/mappings/deped_enrollment.json). Columns: [data dictionary](../data/silver/deped-enrollment-clean.md). The job: D-020; Silver: D-021 to D-025 in [decisions.md](../governance/decisions.md).

## The question Silver answers

> When a planner reads a number built from Silver, can the team say exactly which Bronze row it came from, what was changed, why, and what was set aside, without rerunning everything or spending compute it does not need?

| Part | How |
|---|---|
| Which Bronze row | Every clean and quarantined row carries `batch_id`, `delivery_version`, `schema_version`, `source_sha256`, and `source_row_number`; the last two identify the Bronze row exactly. The gate checks that every Silver row resolves to a current Bronze row |
| What was changed | Each rule is one generated SQL expression from a reviewed file. Every build records how many rows each rule changed or flagged (`rule_*`, `flag_*` in `data_quality_results`), and the published value is always one join away in Bronze |
| Why | The rule table below, the evidence for every label in the mapping, and decisions D-021 to D-025 |
| What was set aside | `deped_enrollment_quarantine`, with the reasons; `rows_reconcile` proves Bronze rows = clean + quarantined, per school year |
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
| Blank count stays NULL, not 0 (rows with a blank count) | O-16, Bronze | transform | Never invent a value; in SY 2025-26 blank means "not published" | 60,167 | 0 | 48,709 | None |
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

`deped_enrollment_quarantine` holds `school_year`, `school_id` as published, `quarantine_reasons` (every reason that applies), the Bronze lineage, and the run stamp. Read the published values from Bronze by `source_sha256` and `source_row_number`. Reasons: `school_id_blank`, `school_id_malformed`, `school_id_duplicated`, `count_negative`, `count_uncastable` (D-024). The three acquired years quarantine nothing.

A row's reasons are decided with explicit NULL handling (`school_id IS NULL OR school_id = ''`), and the reasons string is never NULL, so the split into the two tables cannot lose a row whose `school_id` is NULL; `tests/test_silver.py` proves it with such a row.

## The gate

`etl/03_silver/90_validate_deped_enrollment_clean.sql` is the job task after every build, reading Bronze, both Silver tables, and `current_batches`. It writes one row per check to `` `01-control`.data_quality_results `` with `layer = 'silver'`, `:run_id`, and `:code_revision`; records the run as `succeeded` or `failed` in `pipeline_runs`; then fails the task if this execution recorded any FAIL. Only this execution's results count, so a repaired job run (same `run_id`) is judged on its own. Column types are fixed by the build itself (every count through `TRY_CAST(... AS INT)`); `tests/test_silver.py` checks them locally, and the Databricks check below checks them in Unity Catalog.

| Check | Per | FAIL when |
|---|---|---|
| `rows_reconcile` | school year | Bronze current rows ≠ clean + quarantined |
| `school_id_unique`, `school_id_valid` | school year | A key repeats, is NULL, or is not six digits in the clean table |
| `counts_non_negative` | school year | A count is negative |
| `learners_reconcile` | school year | Clean learners ≠ Bronze learners of the same rows |
| `missing_counts_stay_null` | school year | NULL count cells in clean ≠ blank or absent cells in Bronze (catches blank → 0) |
| `absent_columns_stay_null` | school year | A column the year's schema lacks is filled |
| `labels_mapped_<column>` (9 columns) | school year | A published label is not in the reviewed mapping |
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
| WARN | Rows were quarantined (at most 1% of a year) | Recorded; the build stands; the source owner reviews the reasons |
| FAIL | The Silver tables cannot be trusted | The gate task fails and `pipeline_runs` says `failed`; the tables hold that build until the next run rebuilds them, and Gold must not read them. Other source lanes are independent and keep running |

The local run on the real data recorded 110 results, all PASS.

## Every run rebuilds, and every run is recorded

Silver rebuilds both tables on every job run with `CREATE OR REPLACE TABLE ... AS SELECT` from the current batches (D-025): the same Bronze gives the same rows, so a rerun changes nothing but the run stamp, and a revised delivery (`delivery_version` 2) replaces its school year because `current_batches` points to it. On the real data, the MD5 of all 180,500 clean rows (without the run stamp) was `5d9ecaf14baac697071e884851af3161` on every run.

Each table is one Delta commit; the pair is not, so the run row is the commit marker, as `ingestion_batches` is for Bronze:

| `pipeline_runs.status` (`pipeline_name = 'silver_build'`) | Written by | Meaning |
|---|---|---|
| `running` | the build task, first | The build started; with no later status it never finished, or its gate never ran |
| `succeeded` | the gate task, after its checks | Every check passed or warned: Gold may read Silver |
| `failed` | the gate task, after its checks | At least one FAIL: Gold must not read Silver |

## Compute

Free Edition's serverless capacity is shared; in the Bronze runs most time was spent waiting for it, and each small control-table statement took 3 to 13 seconds.

- **Two SQL tasks on the warehouse.** The Bronze gate before them has already started it, so Silver adds two tasks' statements, not a new start-up. No notebook.
- **No skip.** A file cannot decide to skip itself, and the rebuild is cheap (about a second for 180,500 rows locally), so every run rebuilds (D-025). The saving given up is that work, not a warehouse start.
- **A build** is about 15 statements: the run stamp (6), the run row, the schema and its owner, the classification view, two `CREATE OR REPLACE` and two owner statements. **The gate** is 5: its start time (2), the checks, the run row, the final check. Locally: about 1.1 s and 0.6 s.
- **Parallel source lanes.** Tasks within this source stay ordered, while unrelated sources may run at the same time. There is no schedule, and `max_concurrent_runs: 1` prevents two whole job runs from overlapping.

Databricks timings will be recorded with the first run (open).

## Running locally

From the repository root, with the virtual environment active, run the whole job on DuckDB in a deterministic dependency order equivalent to the Databricks DAG:

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.job.local_run
```

The tables go to `local_state/edu_access.duckdb` (`--db <path>` for another file). Bronze loads only new files; Silver rebuilds every time. Exit code 0 when every task succeeded, 1 otherwise, with the failed tasks named.

## Changing a rule or approving a label

1. Edit `config/mappings/deped_enrollment.json`: a new label goes under its column with the standard value and the evidence (how many of the same schools carried the old label). A new column in a new schema version must be classified there too, or the generator stops.
2. Regenerate the three generated files (a test fails until you do):

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

**Not yet run.** The deliberate confirmation run (D-008), after the branch is pushed:

1. From a clean checkout of the pushed commit, announce the run, detach notebooks, leave the SQL warehouse stopped (the job starts it).
2. `databricks bundle validate --target dev --profile reached-hq`, then `databricks bundle deploy --target dev --profile reached-hq`; confirm in `databricks bundle summary` that `git_commit` and `code_revision` both equal `git rev-parse HEAD`.
3. `databricks bundle run edu_access_pipeline --target dev --profile reached-hq` twice. In both runs the Bronze loads skip (already loaded), the gates pass, and Silver rebuilds.
4. Check with the queries below, then record the evidence in `evidence/pipeline-runs/<date>-deped-enrollment-silver.md` in the layout of the Bronze evidence, with per-task timings (job start, task start and end, queue and setup time) so waiting for compute is told apart from work.

What only Databricks can show: Spark's behavior for the shared SQL (`regexp_like`, `translate`, `chr(160)`, session variables, the CTE inside `INSERT`, `MERGE` with variables), job parameters reaching SQL file tasks, `CREATE OR REPLACE TABLE` and ownership on existing Unity Catalog tables, and the real cost of the warehouse tasks.

All checks in one query, each marked `OK` or `CHECK`, for the three approved deliveries after two runs. Replace the commit with the one that ran:

```sql
WITH c AS (SELECT * FROM edu_access.`03-silver`.deped_enrollment_clean),
     q AS (SELECT * FROM edu_access.`03-silver`.deped_enrollment_quarantine),
     pr AS (SELECT * FROM edu_access.`01-control`.pipeline_runs WHERE pipeline_name = 'silver_build' AND source_id = 'deped_enrollment'),
     last_run AS (SELECT MAX_BY(run_id, started_at_utc) AS run_id FROM pr),
     d AS (SELECT * FROM edu_access.`01-control`.data_quality_results WHERE layer = 'silver' AND run_id = (SELECT run_id FROM last_run)),
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
  UNION ALL SELECT 'checks in the last run', '110', CAST(COUNT(*) AS STRING) FROM d
  UNION ALL SELECT 'checks in the last run not PASS', '0', CAST(COUNT_IF(status <> 'PASS') AS STRING) FROM d
  UNION ALL SELECT 'rows from the last run', '180500', CAST(COUNT_IF(run_id = (SELECT run_id FROM last_run)) AS STRING) FROM c
  UNION ALL SELECT 'rows from another commit', '0', CAST(COUNT_IF(code_revision <> '<commit that ran>') AS STRING) FROM c
  UNION ALL SELECT 'last silver run', 'succeeded', MAX(status) FROM pr WHERE run_id = (SELECT run_id FROM last_run)
  UNION ALL SELECT 'silver runs succeeded', '2', CAST(COUNT_IF(status = 'succeeded') AS STRING) FROM pr
)
SELECT check_name, expected, actual, CASE WHEN expected = actual THEN 'OK' ELSE 'CHECK' END AS result FROM checks;
```

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

- Read Silver only when the latest `silver_build` run of the source in `pipeline_runs` succeeded (its rows carry that `run_id`).
- `is_overseas`: exclude from any geographic analysis; their place names are placeholders in SY 2025-26.
- `enrollment_status`: `all_zero` and `no_counts` schools are kept in Silver; decide per measure whether they count as schools (S-1).
- `barangay_possibly_truncated` and NULL `barangay`: barangay-level results for these schools are uncertain.
- NULL counts: "not published"; in SY 2025-26 usually "level not offered". Use `schema_version` to tell a column the year lacks from a blank, and NULL-safe filters (`IS NOT TRUE`) on nullable booleans.
- Region is as published: NIR exists from SY 2024-25 (O-10); compare regions across years only through PSGC (D-012).
- School IDs change between years (O-12): a missing ID is not a closed school.
- Unpivot grade, sex, and strand there (D-021), and decide how `g11_sshs_*` relates to the older strand columns.

What Integration still has to do: match `province`, `municipality`, and `barangay` to PSGC 2Q 2026 (D-012) using the names as Silver keeps them (spacing normalized, `Ñ` repaired, `(Capital)` and other suffixes kept), apply the 40-character prefix rule to truncated barangays (O-18), and report unmatched names ([generated list](../data/cross-source/generated/deped_psgc_unmatched.md)).

## Limitations

- Not yet run on Databricks: Spark has not executed this SQL.
- `region` and the other categories are gated, so any new label stops Silver until it is reviewed, by design.
- Every run rebuilds every school year, and starts the SQL warehouse; fine at 180,000 rows, revisit for larger sources.
- After a failed gate the Silver tables hold the failed build until the next run; Gold must check the run status first.
- Only `deped_enrollment` has Silver; facilities and the other sources follow with their own mapping (#86 to #90).

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
