# Evidence: the real PSGC 2Q 2026 workbook loads into Bronze locally once, and a second run inserts nothing

Issue #82 · local DuckDB (D-017) · 2026-10-07, Manila time (UTC+8) · run by @maeveylain

## The claim

The official `PSGC-2Q-2026-Publication-Datafile.xlsx` loads through the shared pipeline (format `xlsx_table`, contract `config/ingestion/psa_psgc.json`) into `psa_psgc_raw` with every data row of sheet `PSGC`, every value as stored, and complete provenance. Its counts equal the source card. Running the same ingestion again skips the workbook and inserts nothing.

**Not claimed:** anything about Databricks. This is a local run on DuckDB; the `dev` confirmation run has not been done.

## What was run

Code: branch `feat/82-psgc-bronze`, uncommitted work on top of `main` at `d9dd28b3bde2b3f39a0410d4a7d86097c70f3a88`, so the stored `code_revision` is `d9dd28b3…f3a88-dirty`. That is the honest value (see [code_revision](../../docs/operations/ingestion.md#code_revision)); the run is to be repeated at the pull request's commit before the pull request leaves draft. Python 3.14.7, DuckDB 1.4.5.

The workbook: `$RAW_DATA_DIR/psa/original/PSGC-2Q-2026-Publication-Datafile.xlsx`, SHA-256 `31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d`, equal to `SHA256SUMS.txt` and the [source card](../../docs/data/source-inventory/psa_psgc/README.md#files). The file was only read.

A fresh, git-ignored database, so no earlier local tables were involved. The command was run twice from Git Bash, with `RAW_DATA_DIR` set to the raw-data root:

```bash
rm -f local_state/psgc_step6.duckdb
```

```bash
.venv/Scripts/python.exe -m src.ingestion.cli ingest --source psa_psgc --db local_state/psgc_step6.duckdb
```

```bash
.venv/Scripts/python.exe -m src.ingestion.cli status --source psa_psgc --db local_state/psgc_step6.duckdb
```

| | Run 1 | Run 2 |
|---|---|---|
| `run_id` | `29a19ac9-c763-4a68-a562-2bfeddaa9ed5` | `12f3aa47-30bd-459e-878f-e80ca5e93288` |
| Started (UTC) | 2026-10-07 15:08:08 | 2026-10-07 15:08:34 |
| Batch | `psa_psgc__2026-Q2__31892bc2bdde` | same |
| Action, outcome | `load`, `initial`, `succeeded` | `skip`, `skipped` ("already loaded; same SHA-256") |
| Rows inserted | **43,768** | **0** |
| Pipeline time (`duration_seconds`) | 15.4 s | 0.4 s |
| Exit code | 0 | 0 |

## Results

### 1. Bronze against the source card

| Check | Source card | Bronze |
|---|---|---|
| Data rows on sheet `PSGC` (A1:K43769) | 43,768 | 43,768, Excel rows 2 to 43,769 |
| Distinct `10-digit PSGC` | 43,768 | 43,768 |
| `Bgy` / `Mun` / `City` / `Prov` / `Reg` / `SubMun` / blank level | 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 | 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 |
| Blank `Correspondence Code` | 50 | 50 |
| `2024 Population` = `#N/A` / = `0` | 1 / 12 | 1 / 12 |
| `Urban / Rural` = `-` | 38 | 38 |
| Names ending in a space | 2,855 | 2,855 (not trimmed) |
| Column J filled | 19 | 19 (as `column_j_footnote`) |
| Codes starting with `0` | 29,620 | 29,620; 0 codes not exactly 10 digits |
| Codes stored as numbers in the workbook | not on the card (found 2026-10-07) | 84, all exactly 10 digits, kept as stored; none padded |
| Names with `ñ`/`Ñ` | n/a | 456, including `Tañong`; 0 mojibake |

### 2. Identity and provenance

```sql
SELECT COUNT(*) - COUNT(DISTINCT source_sha256 || ':' || CAST(source_row_number AS VARCHAR)) FROM edu_access."02-bronze".psa_psgc_raw;
-- 0 pipeline duplicates

SELECT COUNT(*) FROM edu_access."02-bronze".psa_psgc_raw WHERE source_id IS NULL OR publication_period IS NULL OR source_sheet IS NULL
   OR source_sha256 IS NULL OR source_row_number IS NULL OR batch_id IS NULL OR run_id IS NULL OR code_revision IS NULL;  -- (all 16 provenance columns were checked)
-- 0 rows missing provenance
```

One row traced: Excel row 2 of sheet `PSGC` in `PSGC-2Q-2026-Publication-Datafile.xlsx` (`31892bc2bdde…`) is code `1300000000`, `publication_period` `2026-Q2`, `publication_date` `2026-06-30`, batch `psa_psgc__2026-Q2__31892bc2bdde`.

### 3. Control tables

- `ingestion_batch_attempts`, in run order: `load succeeded 43768`, then `skip skipped 0`, both for period `2026-Q2`.
- `pipeline_runs`: two `succeeded` runs (1 loaded, then 1 skipped), no failure stage.
- `current_batches`: `2026-Q2`, version 1, `psa_psgc__2026-Q2__31892bc2bdde`.
- `ingestion_batches` (from `status`): `succeeded`, 1 attempt, source 43,768, Bronze 43,768.

### 4. Checks

Run 1: 30 PASS, 11 WARN, **0 FAIL**. Every WARN is a known publisher characteristic at exactly its profiled count, recorded and loaded as received:

| Check | Expected | Actual |
|---|---|---|
| `dq_blank_geographic_level` | profiled 2 (O-2) | 2 |
| `dq_blank_correspondence_code` | profiled 50 (O-3) | 50 |
| `dq_population_not_whole_number` | profiled 1 (O-4) | 1 |
| `dq_population_zero` | profiled 12 (O-4) | 12 |
| `dq_income_class_dash` | profiled 8 (O-7) | 8 |
| `dq_income_class_starred` | profiled 6 (O-7) | 6 |
| `dq_urban_rural_dash` | profiled 38 (O-8) | 38 |
| `dq_name_trailing_space` | profiled 2,855 (O-9) | 2,855 |
| `dq_column_j_footnote_filled` | profiled 19 (O-6) | 19 |
| `psgc_code_stored_as_number` | profiled 84 | 84 |
| `error_cells` | 0 | 1 (the `#N/A` population cell) |

Among the PASS results: row count and range equal the approval; the sheets equal the contract's six; the code is never blank and always `^[0-9]{10}$`; no mojibake; no formulas; unit counts equal the workbook's own `National Summary` (82 / 149 / 1,493 / 42,010); regional populations are 1,708 below the national total, as `Notes` D.2 documents; the hierarchy by code prefix is complete; the Bronze gate (no pipeline duplicates, every row has a known batch, every succeeded batch reconciles).

Run 2: 4 PASS (the approved workbook is present, and the three gate checks), no other result, because the batch was skipped.

## Limitations

- Local DuckDB stands in for Delta (D-017). Column mapping, Unity Catalog permissions and reading from `/Volumes/` are confirmed only by the Databricks `dev` run, which has not been done.
- The code was uncommitted (`-dirty`); repeat at the pull request's commit.

## How to reproduce

Set `RAW_DATA_DIR` to the folder holding `psa/original/`, then run the commands above with the project's own interpreter (`.venv/Scripts/python.exe`). Expected: run 1 `load initial succeeded inserted=43768`, run 2 `skip`, `inserted=0`, both exit code 0.

## Repeated at the pull request's commit

The runs above used uncommitted code (`-dirty`). They were repeated after the work was committed and pushed (#111), at commit `8f9c893d424bcb7555f948b646f705f7ae8cc65d` (clean working tree, so the stored `code_revision` carries no `-dirty`), on a fresh database, from VS Code's PowerShell terminal with `$env:RAW_DATA_DIR` set to the raw-data root:

```bash
.\.venv\Scripts\python.exe -m src.ingestion.cli ingest --source psa_psgc --db local_state/psgc_commit.duckdb
```

| | Run 1 | Run 2 |
|---|---|---|
| `run_id` | `df5d9835-56a3-4506-adbc-05de7f909048` | `375d6313-939e-4245-85e8-6aacfd8aa4cc` |
| Started (UTC) | 2026-10-07 15:42:33 | 2026-10-07 15:44:46 |
| Action, outcome | `load`, `initial`, `succeeded` | `skip`, `skipped` ("already loaded; same SHA-256") |
| Rows inserted | **43,768** | **0** |
| Pipeline time (`duration_seconds`) | 8.8 s | 0.4 s |
| Checks | 30 PASS, 11 WARN, 0 FAIL | 4 PASS |
| `code_revision` | `8f9c893d…c65d` | `8f9c893d…c65d` |

Checked in the database afterwards, all equal to the first runs and to the source card: 43,768 rows, Excel rows 2 to 43,769, 43,768 distinct codes; levels 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 blank; 50 blank correspondence codes, `#N/A` 1, population `0` 12, `-` urban/rural 38, 2,855 trailing spaces, 19 column-J footnotes, 29,620 leading-zero codes, 0 codes not exactly 10 digits; 0 pipeline duplicates; 0 rows missing provenance; every Bronze row carries the one commit. The 11 WARNs are the same checks at the same counts as the table in [Checks](#4-checks). Attempts: `load succeeded 43768`, then `skip skipped 0`. `current_batches`: `2026-Q2`, version 1, `psa_psgc__2026-Q2__31892bc2bdde`.

This resolves the second limitation above. The Databricks `dev` run is still not done.
