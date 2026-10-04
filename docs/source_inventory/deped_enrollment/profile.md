# deped_enrollment: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-09-29 |
| Profiled by | @hyenalouise |
| Tool | DuckDB 1.4.5 (Python), run locally: [`notebooks/profiling/profile_deped.py`](../../../notebooks/profiling/profile_deped.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if a zip's checksum differs |
| How files were read | Straight from the original zips, all columns as text (`all_varchar`), strict CSV parsing. SY 2025-26 is decoded from Windows-1252 in memory; raw files are never modified |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_deped.py
```

`RAW_DATA_DIR` must contain `deped/original/` with the zips listed in the script. Every result prints under its finding ID below.

## Summary

Clean and usable at school level: `school_id` is a reliable key within each year, and every enrollment count is a valid whole number. The main work before analysis is matching place names to PSGC and harmonizing SY 2025-26, which changed encoding, columns, and category labels.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | `school_id` is clean in every year | 0 blank, 0 non-numeric, 0 not 6 digits, 0 duplicates, 0 fully duplicated rows in each of the three files | Safe primary key within a year | Assert uniqueness in Bronze validation |
| O-2 | Enrollment counts are valid | 0 non-integer and 0 negative values across all count columns; 0 schools with elementary learners that do not offer elementary | Counts can be typed as integers without loss | Type in Silver; keep a range check |
| O-3 | Total learners per file | 27,081,292 (2023-24); 26,400,182 (2024-25); 25,935,863 (2025-26) | Baseline for reconciliation | Reconcile against DepEd's published totals (not yet done) |
| O-4 | No PSGC codes | Location columns are names only | Joining to PSA data requires name matching | Match names to PSGC in integration; count and list unmatched. Done for SY 2023-24 in [deped_dataset_research.md](../../cross_source/deped_dataset_research.md): 96.9% of schools match to barangay |
| O-5 | Place names are not standardized | 5,450 rows (2023-24) have a "(Capital)" suffix in municipality, e.g. "CEBU CITY (Capital)" (269). Provinces are ALL CAPS; divisions are never ALL CAPS. In 2025-26, 220 rows have double spaces in municipality (e.g. "CITY OF MALOLOS  (Capital)"), 275 rows have leading or trailing spaces, and NCR district province names gained extra spaces (e.g. "NCR   SECOND DISTRICT"). Of 255 schools whose municipality text changed from 2024-25 to 2025-26, 213 differ only by spacing | Direct name joins will miss | Documented normalization rules in Silver, with affected counts |
| O-6 | SY 2025-26 encoding differs | Windows-1252 with CRLF line endings; 1,892 lines fail UTF-8 decoding (e.g. `Do\xf1a`). Earlier years are UTF-8 with LF | A loader that assumes UTF-8 fails or corrupts names | Declare encoding per file in the source contract; fail loudly on mismatch |
| O-7 | SY 2025-26 adds columns | Undocumented `Modified Curricular Offering Classification` (values: Purely ES 42,118; JHS with SHS 7,901; All Offering 3,692; ES and JHS 3,384; Purely JHS 1,730; Purely SHS 1,347; ES with SHS 32), plus four documented `g11_sshs_*` columns | Schema drift between years | Schema-drift check in Bronze; map new columns explicitly |
| O-8 | SY 2025-26 relabels categories | `DepEd` → `DepED Managed`; `Non-Sectarian` → `Non-Sectarian ` (trailing space); `PSO` → `SCHOOL ABROAD`; `SUC/LUC` → `SUCsLUCs`; `True/False` → `Yes/No`; annex labels reworded (e.g. `Standalone School` → `School with no Annexes`) | Category comparisons across years break | Mapping table from each year's labels to one standard set |
| O-9 | README labels match no year exactly | README lists `DepEd Managed`; data has `DepEd` (2023-24, 2024-25) and `DepED Managed` (2025-26) | Documentation cannot be used as the accepted-values list | Build accepted values from observed data, per year |
| O-10 | New region NIR from SY 2024-25 | 2,704 schools in NIR in 2024-25 were in Region VI (1,586) or VII (1,118) in 2023-24; no other region changes | Region-level trends are not comparable without adjustment | Compare at province or municipality level, or map to a fixed region set |
| O-11 | Province values change between years | Distinct province values (including `PSO`): 88 (2023-24), 89 (2024-25), 88 (2025-26). `(SGA - North Cotabato)` appears from 2024-25. In 2025-26, `PSO` is no longer used as a province and the NCR district names change spacing (see O-5) | Province matching must handle it | Include in PSGC matching |
| O-12 | School ID churn | 2023-24 → 2024-25: 59,537 kept, 630 dropped, 592 new. 2024-25 → 2025-26: 59,653 kept, 476 dropped, 551 new | School-level history is incomplete for about 1% of schools per year | Report churn; do not treat a dropped ID as a closed school |
| O-13 | Overseas schools included | 33 rows with region `PSO` (2023-24). In 2025-26 their municipality is `CITY OF PASIG` | Would be wrongly placed in Pasig if matched by name | Exclude PSO from geographic analysis by rule |
| O-14 | Placeholder street addresses | 2023-24: 5,203 blank. 2025-26: 0 blank, but `-` (2,234), `n/a` (685), `N/A` (636) | Blank and placeholder mean the same thing | Standardize placeholders to NULL in Silver (not used for analysis) |
| O-15 | Barangay blanks | 70 (2023-24), 65 (2024-25), 7 (2025-26) | Barangay-level placement incomplete for a few schools | Flag; analysis above barangay level is unaffected |
| O-16 | Entirely blank columns | `g11_unique_*` and `g12_unique_*` are blank in 2023-24, as the README says ("only has values starting SY 2024-25") | None | Expected |
| O-17 | Place names contain mangled characters | `Ã‘` appears where `Ñ` belongs (e.g. `ALMEÃ‘ANA`, `AGUSAN PEQUEÃ‘O`): 260 rows and 173 distinct places in 2023-24, 261 and 173 in 2024-25, 263 and 173 in 2025-26; also 11, 11, and 10 school names. Present in all three years, including the Windows-1252 file, so it is in the published data, not caused by decoding | Exact name matching fails for these places | Repair by re-reading the text as UTF-8 before matching; keep the raw value ([cross-source A-10](../../cross_source/deped_dataset_research.md#data-problems-in-depeds-place-names-a-10)) |
| O-18 | Barangay names appear to be capped at 40 characters | The longest barangay value in every year is exactly 40 characters, and 40 is far more common than 38 or 39 (2023-24: 8, 6, 24 rows). 13 distinct 40-character names per year; some end mid-word or with an open bracket (e.g. `AURORA HILL PROPER (MALVAR-SGT. FLORESCA`), while others are complete | Longer barangay names are probably cut off | Match a 40-character name only to the one PSGC barangay in its city or municipality that starts with it; otherwise list it as unmatched |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | Zero-enrollment schools are closed or non-reporting. 2023-24: 115 (Private 103, PSO 7, Public 4, SUC/LUC 1); 2024-25: 24; 2025-26: 46 | Check whether their IDs appear in the next year and in facilities | open |
| S-2 | Some municipality changes between years are corrections, others real moves (e.g. LORETO → LA PAZ, SITANGKAI → SIBUTU) | Compare against PSGC and the school's barangay | open |
| S-3 | File totals match DepEd's official published enrollment | Find DepEd's official national totals per school year and compare | open |

## Changes across files or years

- SY 2023-24 and 2024-25: identical columns and column order (78 columns).
- SY 2025-26: 83 columns, Windows-1252 encoding, CRLF line endings, relabeled categories (O-6 to O-8).

## Questions for the publisher or mentor

- Is the SY 2025-26 encoding change intentional, and will earlier years be republished the same way?
- Is a school ID mapping file (mentioned in the README) planned, and when?
