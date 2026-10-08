# Evidence: PSA Poverty Stat ingestion is idempotent and incremental (local: made-up workbooks and the real workbook)

Issue #83 · local only (DuckDB) · 2026-10-07, Manila time (UTC+8) · run by Claude for @catweyine, to be rerun by a reviewer

> **Scope of this evidence.** Two local runs on DuckDB: (1) made-up workbooks shaped like the real one (`tests/factories/psa_workbooks.py`) for the scenarios a single file cannot show (new year, backfill, changed file, crash); (2) the real workbook, loaded twice. It is **not** a Databricks run (see "What this does not prove").

## The claim

When a PSA Poverty Stat workbook arrives, the pipeline loads it once, skips it on every later run, loads a workbook with a new estimate year (or an older one) without touching earlier rows, refuses a changed file under an approved name without overwriting anything, and recovers from a crash after the Bronze write without duplicates. Every Bronze row points to its workbook, sheet, and Excel row.

## What was run

Code on branch `feat/83-psa-poverty-bronze`, rebased onto `main` at `49703b9` (after the repository reorganization, #105), from a clean checkout; the commit SHA is the pull request's head. DuckDB 1.4.5 built from the `duckdb-python` v1.4.5 source, because the package index was not reachable from the workspace used; the same suite on untouched `main` passed 203 of 203 with that build, as a baseline.

```bash
python -m pytest tests -q
```

Result: `279 passed` (203 existing plus 76 new; 72 of the new tests in `tests/test_ingestion_psa.py`). No existing test changed behavior; `tests/test_ingestion_validate.py` gained a workbook branch in the card-consistency test.

```bash
python analysis/demo/psa_ingestion_demo.py
```

Output (exit code 0). Run IDs are random per execution. Each fixture workbook has 19 sheet rows, all loaded: 1 title, 4 header, 8 body (6 units, 2 region banners), 6 footer:

```text
== Run 1, first delivery: run cda63045 SUCCEEDED
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  load   initial     succeeded inserted=19

-- batch manifest
   ('psa_poverty_stat__2018-2021-2023__84e221518598', '2018,2021,2023', 'initial', 'succeeded', 19, 19, 19)

-- every sheet row lands in Bronze, by kind (title, header, units, banners, footer reconciled separately)
   ('footer', 6)
   ('header', 4)
   ('region_banner', 2)
   ('title', 1)
   ('unit', 6)

== Run 2, same files: run de131da7 SUCCEEDED
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  skip   initial     skipped   inserted=0

-- attempts log
   ('cda63045', 'load', 'succeeded', 19)
   ('de131da7', 'skip', 'skipped', 0)

-- pipeline duplicates (expect 0)
   (0,)

== Run 3, new year 2025: run 71ebc82e SUCCEEDED
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  skip   initial     skipped   inserted=0
   2_2025 SAE_with PSGC_noHUC_01Feb2028.xlsx    years=2025            load   incremental succeeded inserted=19

-- rows per delivery, and the run that inserted them (2018-2023 untouched)
   ('2018,2021,2023', 19, 1)
   ('2025', 19, 1)

== Run 4, changed workbook under the approved name: run 5a80af37 FAILED
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  block  revision    blocked   inserted=0
      reason: 2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx has SHA-256 03d3b89d74e0585745b1a67f69fce33be5d0e53f32b6275d4cb736d533252342, which is not approved (approved: sae_cit
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  skip   initial     skipped   inserted=0
   2_2025 SAE_with PSGC_noHUC_01Feb2028.xlsx    years=2025            skip   incremental skipped   inserted=0

-- nothing overwritten
   ('2018,2021,2023', 1, 19)
   ('2025', 1, 19)

-- the blocked file
   ('psa_poverty_stat__2018-2021-2023__03d3b89d74e0', 'blocked', 'revision', 'checksum_mismatch')

== Run 5 crashed after writing Bronze, before marking the batch succeeded

-- the 2015 batch is stuck in 'loading', and downstream cannot see it
   ('2015', 'loading', False)
   ('2018,2021,2023', 'succeeded', True)
   ('2018,2021,2023', 'blocked', False)
   ('2025', 'succeeded', True)

== Run 6, the same command again: run 5d1f707a SUCCEEDED
   2_2015 SAE_with PSGC_noHUC_01Jan2017.xlsx    years=2015            retry  backfill    succeeded inserted=0
   2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx    years=2018,2021,2023  skip   initial     skipped   inserted=0
   2_2025 SAE_with PSGC_noHUC_01Feb2028.xlsx    years=2025            skip   incremental skipped   inserted=0

-- recovered without duplicates
   ('2015', 19, 19)
   ('2018,2021,2023', 19, 19)
   ('2025', 19, 19)

-- row from Excel line 9 of the first workbook (a unit with no estimates: blank, not 0)
   ('2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx', '84e221518598', '2023_NoHUC_Maguindanao grouped', 9, 'unit', '99103', 'No Estimate Town', '', 'psa_poverty_stat__2018-2021-2023__84e221', 'cda63045')

-- known publisher issues recorded as WARN (not corrected)
   ('known_issue_cv_over_20_2018', '1', '0 (profiled: 171, O-9)')
   ('known_issue_lower_limit_zero_or_negative', '1', '0 (profiled: 3, O-7)')
   ('known_issue_province_label_continued', '1', '0 (profiled: 1, O-3)')
   ('known_issue_psgc_id_leading_zero_lost', '3', '0 (profiled: 1073, O-2)')
   ('known_issue_se_disagrees_with_cv_2018', '2', '0 (profiled: 6, O-8)')
   ('known_issue_se_disagrees_with_cv_2023', '1', '0 (profiled: 1, O-8)')
   ('known_issue_unit_rows_without_estimates', '1', '0 (profiled: 1, O-5 (Kalayaan, footnote 3))')
```

## Why the claim holds

| Step | Evidence above |
|---|---|
| Load once | Run 1: `load initial`, 19 inserted (the whole sheet); manifest `expected = source = bronze = 19`; title, header, units, banners and footer reconciled separately |
| Same file again inserts nothing | Run 2: `skip`, 0 inserted; attempts log `load` then `skip`; pipeline duplicates 0 |
| New estimate year is incremental | Run 3: 2025 workbook `load incremental`; 2018-2023 rows still from 1 run |
| Changed bytes under the approved name | Run 4: `block revision`, `checksum_mismatch`; Bronze still one version per dataset; run `FAILED` (exit 1 on the command line) |
| Crash after the Bronze write | Run 5: 2015 batch stuck in `loading`, not visible in `current_batches` |
| Recovery | Run 6: same command, `retry backfill`, 0 inserted (rows already there), 19 rows and 19 distinct Excel rows per delivery |
| Provenance | The traced row gives file, workbook SHA-256, sheet, Excel row 9, row kind, batch, run; its blank estimate stays `''` |
| Known issues kept, not fixed | WARN results with the profiled count beside each |

## Real workbook (local DuckDB)

On 2026-10-07 the real workbook was loaded twice with the command line, at commit `1fdb7ae` (recorded as `code_revision` on every row). The branch was later rewritten to remove commit-message trailers only; its counterpart `5a80a8a` has the identical tree, into a fresh local DuckDB file. The file was a copy of the team's workbook under another name (`2_2023_SAE_with_PSGC_noHUC_06Feb2026_1.xlsx`); its SHA-256 is `303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026` and its size 369,977 bytes, both equal to the source card, so the pipeline identified it as the approved delivery by checksum.

```bash
python -m src.ingestion.cli ingest --source psa_poverty_stat --landing <raw root>
```

```text
===== RUN 1
  psa_poverty_stat__2018-2021-2023__303fb0e87bff       load   initial     succeeded inserted=  1641 bronze=  1641
status: succeeded          (exit 0)
===== RUN 2
  psa_poverty_stat__2018-2021-2023__303fb0e87bff       skip   initial     skipped   inserted=     0 bronze=  1641
      already loaded; same SHA-256
status: succeeded          (exit 0)
```

| Check | Expected (profile, card) | Bronze |
|---|---|---|
| Rows by kind | unit 1,612, region_banner 18, title 1, header 4, footer 6 | 1,612 / 18 / 1 / 4 / 6 |
| Excel rows; pipeline duplicates; rows missing provenance | 1..1641; 0; 0 | 1..1641; 0; 0 |
| Body and footer boundaries (O-1) | body rows 6 to 1635; footer from 1636 | 6 to 1635; 1636 |
| `PSGC ID` 5 digits / 6 digits / distinct (O-2) | 1,073 / 539 / 1,612 | 1,073 / 539 / 1,612 |
| Kalayaan, Excel row 641 (O-5) | ID `175321`, estimates blank | `175321`, `''` |
| Zero or negative lower limits (O-7) | Adams 2018 `0`, Port Area 2021 `0`, Ivana 2023 negative | `0`, `0`, `-2.4063453271442992E-2` (as stored) |
| Units with a 2023 estimate; highest 2023 (X-2) | 1,611; Siayan 67.8 | 1,611; Siayan 67.829368 |
| Title and footer rows | title, 3 notes, source line | rows 1 and 1636 to 1641 kept as received |
| Checks recorded for the load run | no FAIL | 31 PASS, 10 WARN, 0 FAIL |
| Attempts log | load, then skip | `load` 1,641 inserted, then `skip` 0 |

Known-issue WARNs, actual against profiled: `psgc_id_leading_zero_lost` 1,073 / 1,073; `unit_rows_without_estimates` 1 / 1; `province_label_continued` 1 / 1; `lower_limit_zero_or_negative` 3 / 3; `se_disagrees_with_cv` 2018 6 / 6, 2021 133 / 133, 2023 1 / 1; `cv_over_20` 2018 171 / 171, 2021 84 / 84, 2023 156 / 156.

## What this does not prove

- Databricks behavior: `ALTER TABLE … ADD COLUMN` on the existing control tables, the replaced `current_batches` view, Delta column names with `%` and `/`, and reading the workbook from `/Volumes/`. These are confirmed only by the `dev` job run (`docs/operations/ingestion.md`, PSA section).
- **Update after #113 (2026-10-08):** the job is now `edu_access_pipeline` (D-020), and PSA Poverty Stat runs as its own lane in it. Its `dev` runs ([evidence](2026-10-08-pipeline-dag-databricks-idempotency.md)) all skipped the workbook: they show the replaced `current_batches` view, the Bronze table with its `%` and `/` column names (1,641 rows), the workbook found and hashed on `/Volumes/`, and the gate passing as its own task. They do not show the workbook parsed and loaded on Databricks. The D-018 columns are now added by the job's `add_control_columns` task, not by the load; on `dev` they already existed, so adding them to older Delta tables is shown only locally.

## How to reproduce

From the repository root, in VS Code's terminal with the virtual environment active, run the commands above. The tests and the demo need no raw data or credentials; the real-workbook run needs the workbook under `$RAW_DATA_DIR/psa/` (or `--landing`).
