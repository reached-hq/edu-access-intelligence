# Evidence: PSA Poverty Stat Silver reconciles with Bronze per estimate year, and every run rebuilds the same rows

Issue #89 · local runs only (DuckDB); **not run on Databricks** · 2026-10-09 · checked by @Catweyine

## The claim

Silver built from the real Bronze rows of the approved workbook keeps every current Bronze unit row once per estimate year (clean + quarantined = units, for 2018, 2021 and 2023), accounts for every structural row, keeps every published value exactly (each Silver measure equals its own Bronze cell), keeps Kalayaan's missing estimates NULL, flags the statistical warnings at the profiled counts, and passes every FAIL-type gate check. A second run of the same lane, with Bronze skipping the already-loaded workbook, rebuilds both tables with identical business content and records a second `succeeded` run.

## What was run

Commit `e53dd8b6ac395a51dc7538ecb3f31267b72fc98c` (clean: no `-dirty`; the column names of D-034 as revised after review), macOS 26.4.1 (arm64), Python 3.12.14, DuckDB 1.4.5, a fresh database file under `local_state/`. The approved workbook `2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx` (SHA-256 `303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026`, verified by the loader) was read from `raw-data/psa/original/`.

```bash
python -m pytest tests -q
```

558 passed.

```bash
RAW_DATA_DIR=~/Documents/GitHub/raw-data python analysis/verification/psa_poverty_stat_silver.py
```

It runs the PSA Poverty Stat lane of `edu_access_pipeline` twice through `src.job.local_run`'s task runner (the shared control bootstrap, then the five PSA tasks; the other source lanes are not run), then queries the result. Task times (seconds, local):

| Task | Run 1 | Run 2 |
|---|---:|---:|
| `bronze_psa_poverty_stat` | 0.18 (`load`, 1,641 rows inserted) | 0.03 (`skip`, 0 inserted: same SHA-256) |
| `90_validate_psa_poverty_stat_raw` | 0.01 | 0.02 |
| `05_clean_psa_poverty_stat` | 0.05 | 0.05 |
| `90_validate_psa_poverty_stat_clean` | 0.05 | 0.05 |

Every task `succeeded` in both runs. The control bootstrap tasks took 0.01 s each (`add_control_columns` 0.24 s in run 1, when it created the columns).

## Results

After run 2:

| Check | Expected | Actual | Result |
|---|---|---|---|
| Current Bronze rows | 1,641 | 1,641 | OK |
| unit / structural | 1,612 / 29 | 1,612 / 29 | OK |
| structural: title / header / region_banner / blank / footer | 1 / 4 / 18 / 0 / 6 | 1 / 4 / 18 / 0 / 6 | OK |
| Candidates = clean + quarantined, 2018 / 2021 / 2023 | 1,612 each | 1,612 + 0 each | OK |
| Clean rows in all | 4,836 | 4,836 | OK |
| `estimated` per year | 1,611 | 1,611 | OK |
| `no_estimate` per year (Kalayaan, ID `175321`, Excel row 641) | 1 | 1 | OK |
| `partial_estimate` | 0 | 0 | OK |
| NULL measure cells per year (Kalayaan's five) | 5 | 5 | OK |
| `cv_over_20` 2018 / 2021 / 2023 | 171 / 84 / 156 | 171 / 84 / 156 | OK |
| `se_cv_inconsistent` 2018 / 2021 / 2023 | 6 / 133 / 1 | 6 / 133 / 1 | OK |
| `lower_limit_not_positive`, all years | 3 | 3 (1 per year) | OK |
| IDs padded from 5 digits, per year | 1,073 | 1,073 | OK |
| Clean rows that join their current Bronze unit row | 4,836 | 4,836 | OK |
| Repeated keys (`psgc_id`, `estimate_year`) | 0 | 0 | OK |
| Distinct `cleaned_at_utc` across both tables | 1 | 1 | OK |

Expected values are the profile's baselines (O-2, O-5, O-7 to O-9) and the contract's row counts. They were also recomputed before this run by an independent Python reading of the workbook (the Bronze reader `prepare_workbook`, then the rules written again in Python, without the SQL), which gave the same numbers.

**Silver gate, run 2:** 115 results: 106 PASS, 9 WARN, 0 FAIL. The 9 WARN are the three statistical flags in each year (`flag_cv_over_20_<year>`, `flag_se_cv_inconsistent_<year>`, `flag_lower_limit_not_positive_<year>`), at the counts above. Every `<measure>_matches_bronze_<year>` check (5 measures × 3 years) found 0 mismatches; `missing_measures_stay_null_<year>` 5 = 5; `rows_reconcile_<year>` 1,612 = 1,612; `bronze_rows_accounted` 1,641 = 1,641; `quarantine_rate_<year>` 0; `rule_text_whitespace_normalized` 0 (no label needed it).

**Repeated full rebuild:** SHA-256 of all clean rows without the run stamp (`run_id`, `cleaned_at_utc`, `code_revision`), in a fixed order: `417b652a17bee933c5a3cf55cde0029cb8fd9aad93c366eb7c8f62d8a7fe97de` after both runs; the empty quarantine: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` after both. The published `run_id` moved from run 1's to run 2's.

**Run record:** two `silver_build` rows in `pipeline_runs`, both `succeeded`, both `code_revision` `e53dd8b`: `e5af450a-…` and `1c5991a5-…`.

## What this does not show

- **Databricks.** Nothing here ran on Databricks. Spark's behavior for the PSA SQL (`split`/`array_contains`, `TRY_CAST` of scientific notation to DOUBLE, `lpad`, the banner window, `VALUES` with column aliases, `IS NOT DISTINCT FROM`), job parameters, ownership, and warehouse timings are pending the confirmation run ([Silver, Running on Databricks (PSA)](../../docs/operations/silver.md#running-on-databricks-psa)).
- A quarantined row, a failing gate, a revised delivery and a new estimate year are shown only by the made-up workbooks in `tests/test_silver_psa.py`, not on the real data (the workbook quarantines nothing).
- Cross-year comparability of 2018, 2021 and 2023 (profile S-3) is not tested by any of this.

Raw output: written by the script to `local_state/psa_poverty_stat_silver_verification.md` (git-ignored, not committed).

## Earlier run

The same lane was first run at `39129af` (before the columns were renamed and trimmed after review, D-034): every count above was identical, and its own two builds had identical content (SHA-256 `3fdbce79…a1ea5`, a different value because the columns differ). That run is superseded by this one.
