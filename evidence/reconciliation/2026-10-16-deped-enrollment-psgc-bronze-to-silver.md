# Evidence: the DepEd school-to-PSGC crosswalk reconciles from Bronze to Silver locally, and a rebuild gives the same rows

Issue #163 · local DuckDB (D-017) · 2026-10-16, Manila time (UTC+8) · run by @maeveylain

## The claim

The Silver build and gate for `deped_enrollment_psgc` (D-049), run on the real SY 2023-24 Bronze batch, put every Bronze row of kind `unit` either in `deped_enrollment_psgc_clean` or in `deped_enrollment_psgc_quarantine`, with no FAIL. Every profiled count the rules file states is met. A second build gives identical content.

**Not claimed:** anything about Databricks. The two `dev` runs the issue asks for are still to be done.

## What was run

- Code: branch `feat/163-silver-deped-enrollment-psgc` at `0398ade0ae6b43394282047b5d10e6815d967809` (clean), with `code_revision` set to that commit.
- Data: a fresh copy of the local Bronze database from the [Bronze evidence](../pipeline-runs/2026-10-16-deped-enrollment-psgc-local-idempotency.md): batch `deped_enrollment_psgc__2023-24__746d69530d22`, workbook SHA-256 `746d6953…acd5`, 60,285 rows (60,275 `unit`, 9 `blank`, 1 `no_identifier`).
- The generated files, run in order by `DuckDBStore.run_file`, twice: `etl/03_silver/07_clean_deped_enrollment_psgc.sql`, then `etl/03_silver/90_validate_deped_enrollment_psgc_clean.sql`.

| | Run 1 | Run 2 |
|---|---|---|
| `run_id` | `4a49cd37-7e27-4556-8976-3c066bbda36f` | `cc5ad40b-f6fd-4cac-b36b-2c37ae386034` |
| Build, gate | 7.2 s, 1.1 s | 1.4 s, 1.0 s |
| `pipeline_runs` (`silver_build`) | `succeeded` | `succeeded` |
| Checks | 27 PASS, 1 WARN (`quarantine_rate`), 0 FAIL | 27 PASS, 1 WARN, 0 FAIL |
| Clean / quarantine rows | 60,273 / 2 | 60,273 / 2 |
| SHA-256 of both tables' content, ordered by `school_id`, without `run_id` and `cleaned_at_utc` | `dbf4fa1e…5379e5` | `dbf4fa1e…5379e5` (identical) |

After run 2, the published tables hold only run 2's rows (one `run_id`), all stamped `0398ade…7809`, from the one batch.

## Results

### 1. Reconciliation

| | Rows |
|---|---|
| Bronze, kind `unit` | 60,275 |
| Silver clean | 60,273 |
| Silver quarantine | 2: `1406363` `school_id_malformed` (Excel row 60181); `404520` `school_id_identical_copy` (row 60267; its first copy, row 60263, is in clean) |
| Bronze, other kinds (counted, not carried) | 10: 9 `blank`, 1 `no_identifier` |

### 2. Every rule, against its profiled count

| Check (gate) | Rules file | Silver |
|---|---|---|
| Barangay codes padded from 9 digits | 36,010 | 36,010 |
| City null, `source_na` / `not_in_workbook` | 663 / 106 | 663 / 106 |
| Barangay null, `source_na` / `not_in_workbook` | 667 / 106 | 667 / 106 |
| Sulu recoded (`19066…` → `09066…`, region `0900000000`) | 467 | 467 |
| `barangay_outside_city` | 3 | 3 |
| `coordinate_flag` missing / zero / outside the Philippines | 13,899 / 6 / 54 | 13,899 / 6 / 54 (46,314 not flagged) |

All 12 FAIL checks are 0: rows reconcile, `school_id` unique and 6 digits, every code 10 digits, no unrecognized code or coordinate text, null reasons match the codes, region and province null exactly with the city, coordinates in pairs, lineage complete, all rows from this run. `quarantine_rate` is WARN (2 rows; FAIL only above 1% of 60,275).

### 3. Outside the gate: the codes against PSGC 2Q 2026

Not a Silver check (the match is Integration's, #44), but it tests the padding and the recode: of the clean rows, all 59,500 non-null barangay codes and all 59,504 non-null city codes exist in `PSGC-2Q-2026-Publication-Datafile.xlsx` (psa_psgc).

## Not checked here

- The Databricks `dev` runs (Spark SQL on the warehouse, Delta tables, ownership). To be recorded in `evidence/pipeline-runs/` before the pull request closes #163.
- The three rules still to be confirmed by @hyenalouise on #163.
