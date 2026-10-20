# Evidence: the public-school scope of the EMISD workbook is complete in Bronze, with its PSGC codes and coordinates as published, and a rerun adds nothing

Issue: not yet opened · local run (DuckDB) only; nothing has run on Databricks · 2026-10-21 · checked by @catweyine

## The claim

`deped_enrollment_psgc_raw` holds every SY 2023-24 public school of the EMISD workbook *SY 2023-2024 School Level Data on Enrollment with PSGC, Longitude and Latitude.xlsx*, one Bronze row per sheet row, with the workbook's PSGC codes, longitude, and latitude exactly as published and complete provenance. The public scope is `sector = 'Public'` on rows of kind `unit`. Bronze keeps every sector (D-015). The public filter is applied where it already is: in Gold and Analytics (D-022: "Gold filters public schools on `sector`"; AP1 to AP3). AP4 also counts private and SUC/LUC learners. The scope's counts equal the source card and profile, and its main block equals `deped_enrollment` SY 2023-24 public learners exactly. A second ingestion inserts nothing.

**Not claimed:** anything on Databricks. The `dev` load of this workbook is recorded in [2026-10-16-deped-enrollment-psgc-databricks-idempotency.md](../pipeline-runs/2026-10-16-deped-enrollment-psgc-databricks-idempotency.md), but the public-scope counts below were not queried there. Not claimed either: anything about whether the codes or coordinates are *correct*. Bronze only keeps them. Padding, the Sulu recode, and coordinate flags are Silver's (D-049), and the boundary test is still open (profile S-1).

## What was run

Commit `c98cacfbc8c6fe1f7d02378aacbb83390234f57b` on `feat/deped-psgc-coordinates`, clean worktree (the batch's `code_revision` has no `-dirty`). The verification program was committed next, at `577aa0c51db9fe43d63c69e7c1cf7bb9994e1a28`; it only reads. macOS 26.4.1, Python 3.12.14, DuckDB 1.4.5. A new, empty DuckDB file in a scratch folder outside the repository.

The workbook is read from `$RAW_DATA_DIR/deped/original/`. The loader hashed it and matched the approved SHA-256 `746d69530d228d2324590be10abbe6d75a94176c1745ef74335a4d6db550acd5` ([source card](../../docs/data/source-inventory/deped_enrollment_psgc/README.md#files)). The file was only read.

```bash
python -m src.ingestion.cli ingest --source deped_enrollment_psgc --db <scratch>/emisd.duckdb   # twice
python analysis/verification/deped-psgc-coordinates.py --db <scratch>/emisd.duckdb
```

| | Run 1 | Run 2 |
|---|---|---|
| `run_id` | `6c2dfed6-1783-4c06-8ba3-721872bb77b5` | `9dc42528-051d-47eb-8e6b-91299cb669b8` |
| Batch | `deped_enrollment_psgc__2023-24__746d69530d22` | same |
| Action, outcome | `load`, `initial`, `succeeded` | `skip`, `skipped` ("already loaded; same SHA-256") |
| Rows inserted | 60,285 | 0 |
| Exit code | 0 | 0 |

After both runs: one `ingestion_batches` row (`succeeded`, expected = source = Bronze = 60,285), and 39 `data_quality_results`, all PASS (0 WARN, 0 FAIL), the same count as the [2026-10-16 local run](../pipeline-runs/2026-10-16-deped-enrollment-psgc-local-idempotency.md).

## Results

### 1. Rows and the public filter

| Check | Source card / profile | Bronze |
|---|---|---|
| Rows below the header; `unit` / `blank` / `no_identifier` | 60,285; 60,275 / 9 / 1 (O-1, O-2) | 60,285; 60,275 / 9 / 1 |
| `unit` rows by `sector`, exactly as stored | Public 47,831, Private 12,207, SUC/LUC 204, PSO 33 (card, Coverage) | `Public` 47,831, `Private` 12,207, `SUCsLUCs` 204, `PSO` 33 |
| Labels equal to `public` after trimming and lower-casing but not exactly `Public` | none expected | 0 |
| Public rows: distinct `school_id`; not 6 digits; extra rows of a repeated ID | the repeated ID `404520` and the 7-digit ID are private (O-3) | 47,831; 0; 0 |
| Public rows in the main block (rows 9–60175) / appended block (from 60181) | 47,818 (X-3) / 13 (O-2) | 47,818 / 13 |

The filter value is the workbook's own label. `Public` is the only spelling present, so `sector = 'Public'` selects the whole scope and nothing else.

### 2. PSGC codes and coordinates, as published (public rows)

| Column | 9 digits (leading zero lost, O-5) | 10 digits | `#N/A` (O-6) | blank (appended block, O-2) |
|---|---:|---:|---:|---:|
| `psgc_city_municipality` | 28,811 | 18,803 | 204 | 13 |
| `psgc_barangay` | 28,811 | 18,803 | 204 | 13 |

The 204 `#N/A` equal the profile's public count (O-6). No code is padded in Bronze.

| Coordinate pair (Silver's number pattern and box, `config/mappings/deped_enrollment_psgc.json`) | Public rows |
|---|---:|
| Numeric, inside lon 116–127, lat 4–21.5 | 38,688 |
| `#N/A` | 9,079 (profile O-10: public 9,079) |
| Numeric, outside the box | 46 |
| (0, 0) | 5 |
| Blank (appended block) | 13 |

38,736 public rows have both a numeric barangay code and numeric coordinates. The other 3 with numeric coordinates have `#N/A` codes. Inside the box does not mean correct: profile O-11 finds 2,275 schools (all sectors) over 100 km from their own city or municipality.

### 3. Enrollment counts (public rows)

The 58 count columns hold 0 blank cells and 0 cells that are not a whole number. Learners sum to 23,228,221. That is 23,225,427 in the main block, equal to `deped_enrollment` SY 2023-24 public learners ([profile O-3](../../docs/data/source-inventory/deped_enrollment/profile.md)), plus 2,794 in the appended block (profile S-3: public 2,794).

### 4. Lineage

On public rows: 0 NULLs in the 13 provenance columns checked, 0 repeated `(source_sha256, source_row_number)`, and one `school_year` (`2023-24`).

## Tests

`tests/test_ingestion_report.py` gained seven tests on made-up workbooks. They cover: every sector kept, with the public rows selected by `sector`; a school the publisher did not locate (`#N/A` or blank codes and coordinates) kept with its markers; two schools sharing a place and a point staying one row each; a blank count staying `''` and a zero staying `0`; a repeated school keeping both rows and being counted; a changed workbook for a loaded year blocked as a `revision` with Bronze unchanged; and an approved `delivery_version` 2 kept beside version 1, with only version 2 current.

## Not checked here

- Databricks: the public-scope counts above were not queried on `dev`.
- Correctness of codes or coordinates (S-1, S-5), and the 108 appended schools' status (S-3).
- Silver, Integration, and Gold, which this record does not touch.
