# Evidence: PSGC 2Q 2026 Bronze reconciles to Silver, and a rebuild gives the same content

Issue #88 · local DuckDB (D-017) · 2026-10-10, Manila time (UTC+8) · run by @maeveylain

## The claim

At commit `9d2ee0181e597cd6c6fc4357a99c67dcd4889ebb`, the generated PSGC Silver build and gate (`etl/03_silver/04_clean_psa_psgc.sql`, `90_validate_psa_psgc_clean.sql`) turn the real 2Q 2026 Bronze rows into `psa_psgc_clean` with every row accounted for, every value equal to its rule applied to its own Bronze cell, and every gate check PASS. A second build gives identical business content.

**Not claimed:** anything about Databricks. The Silver tasks have not run on `dev`.

## What was run

A clean checkout of `9d2ee01` (a git worktree, no uncommitted change, so `code_revision` carries no `-dirty`), the project's Python 3.14.7 and DuckDB 1.4.5, a fresh git-ignored database, and `RAW_DATA_DIR` set to the raw-data root:

```bash
python -m src.ingestion.cli ingest --source psa_psgc --db local_state/psgc_silver_evidence.duckdb
```

Then the two Silver SQL files, run twice through `DuckDBStore.run_file` with the job's parameters (`run_id`, `code_revision` = `9d2ee01…`, `environment` = `local`), as `src/job/local_run.py` runs them.

| | Bronze | Silver run 1 | Silver run 2 |
|---|---|---|---|
| Run | `bb1b7a91-9961-434e-bd2c-70d2e74a9fbb` | `local-silver-1-256448e7` | `local-silver-2-57ce100d` |
| Started (UTC) | 2026-10-10 | 03:21:07 | 03:21:15 |
| Result | `load initial succeeded`, 43,768 inserted | `succeeded` | `succeeded` |
| Build / gate | | 5.7 s / 3.3 s | 2.0 s / 1.9 s |
| Gate results | | 50 PASS, 0 WARN, 0 FAIL | 50 PASS, 0 WARN, 0 FAIL |
| Clean / quarantined | | 43,768 / 0 | 43,768 / 0 |
| SHA-256 of the business content (every clean column but `run_id`, `cleaned_at_utc`, `code_revision`, ordered by code) | | `2aa69c692ebefc61…` | `2aa69c692ebefc61…` (identical) |

## Results

Queried in the database after run 2.

| Check | Expected (source card, mapping) | Silver |
|---|---|---|
| Rows; distinct codes | 43,768; 43,768 | 43,768; 43,768 |
| Rows flagged as the master quarter (2026-Q2) | 43,768 | 43,768 |
| Codes starting with `0` | 29,620 | 29,620 |
| Levels `Bgy` / `Mun` / `City` / `Prov` / `Reg` / `SubMun` / blank | 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 | the same; the 2 blank levels NULL with `level_blank` |
| Names ending in a space | 2,855 in Bronze | 0 |
| Population NULL / 0 | 1 `#N/A` / 12 | 1 (`publisher_na`) / 12 |
| Sum of the 18 regions' population | 112,727,776 (O-4) | 112,727,776 |
| Correspondence code NULL | 50 | 50 |
| `urban_rural` `-` → NULL `unknown` | 38 | 38 |
| Starred income classes split / `-` → `not_classified` | 6 / 8 | 6 / 8 |
| Rows with a population footnote | 19 | 19 |
| Barangays whose `city_municipality_code` is a municipality / city / sub-municipality | 34,007 / 7,106 / 897 (mapping) | the same; 0 missing |
| Cities / municipalities with no `province_code` | 33 HUCs / 1 (Pateros) | 33 / 1 |
| Distinct `run_id` and `code_revision` on the clean rows | 1 and `9d2ee01…` | 1 and `9d2ee01…` |

Rule records of the gate (always PASS, a count of what each rule did): `rule_text_whitespace_normalized` 2,874 rows (2,855 names, plus old names and footnotes), `rule_population_marker_to_null` 1, `rule_income_class_star_split` 6, `rule_placeholder_to_null` 46 cells (38 `urban_rural`, 8 `income_classification`), `flag_level_blank` 2, `flag_population_is_zero` 12, `flag_has_population_footnote` 19. Every FAIL check (reconciliation, uniqueness, the 18 `*_matches_bronze` checks, the 5 `labels_mapped_*` checks, the 3 parent checks, flags, lineage) recorded 0.

Both Silver runs are `succeeded` in `pipeline_runs`, with `code_revision` `9d2ee01…`.

## Limitations

- Local DuckDB stands in for Spark and Delta (D-017). The SQL features only Databricks can confirm are listed in [Silver, Running on Databricks (PSGC)](../../docs/operations/silver.md#running-on-databricks-psgc).
- One quarter only. Several quarters, a re-issued quarter, a duplicated code, an unmapped label and quarantine above 1% are shown by `tests/test_silver_psgc.py` on made-up workbooks.

## How to reproduce

From a clean checkout of `9d2ee01` (or later), with `RAW_DATA_DIR` set: load Bronze with the command above, then run the whole job with `python -m src.job.local_run --db <fresh file>`, or the two Silver files as described. Expected: 43,768 clean rows, 0 quarantined, 50 PASS.
