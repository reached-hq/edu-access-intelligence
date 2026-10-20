# deped_psgc_coordinates: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-21 |
| Profiled by | @catweyine |
| Tool | Python, run locally: [`analysis/profiling/profile_deped_psgc_coordinates.py`](../../../../analysis/profiling/profile_deped_psgc_coordinates.py). Row counts come from the Bronze contract's own checks (`src/ingestion/xlsx_report.py`) |
| File profiled | See [README.md](README.md#files). The script stops if the file's SHA-256 differs |
| How the file was read | Sheet `DB`, with the standard library (D-007); every cell as stored text; the 88 headers of row 8 must equal schema `v1` |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/profiling/profile_deped_psgc_coordinates.py
```

X-1 and X-2 run when the approved all-sector workbook of deped_enrollment_psgc is also in `deped/original/`; otherwise they print `skipped`. Two runs on the same files give identical output.

## Observed findings

| ID | Finding | Evidence | Proposed handling |
|---|---|---|---|
| O-1 | Same report layout as deped_enrollment_psgc, public only | One sheet `DB`; title rows 1-5 as in deped_enrollment_psgc; row 6 adds `SECTOR: PUBLIC ONLY` in A6 beside the PSGC and coordinate notes; header in row 8, identical to `v1`. 47,818 rows below the header (A1:CJ47826), all with a school ID: 0 blank, 0 without an ID, no appended block. `sector` is `Public` on all 47,818 | Bronze reads it with the `xlsx_report` format and schema `v1`; the A6 note is pinned in the approval, and `dq_sector_not_public` WARNs above 0 |
| O-2 | School ID is clean | 47,818 distinct, all 6 digits, 0 duplicate rows | None |
| O-3 | PSGC codes as in deped_enrollment_psgc | Stored as numbers: 28,811 lost their leading zero (region, province, city, barangay alike). `#N/A` on 204 schools (city and barangay). 0 blank | Pad and treat `#N/A` as missing in Silver, as deped_enrollment_psgc does (D-049) |
| O-4 | Coordinates: few missing | 47,139 numeric pairs; 47,080 inside lon 116-127, lat 4-21.5; 5 at (0, 0); 54 others outside the box. `#N/A` on 679 | Keep and flag in Silver, never correct |
| O-5 | Text as in deped_enrollment_psgc | Mojibake in 239 cells; `barangay` blank 14; income class `1St` 72; urban/rural `-` 29; 3,602 error cells (`#N/A`) | Bronze keeps them; Silver repairs as for deped_enrollment_psgc |

## Cross-source checks

| ID | Check | Evidence | Conclusion |
|---|---|---|---|
| X-1 | Against the all-sector workbook (deped_enrollment_psgc, SHA-256 `746d6953…acd5`), by `school_id` | Its public schools: 47,831, of which 47,818 in its main block. Here and not there: 0. There and not here: 13, all in its appended block. Of the 47,818 shared schools, 282 rows are identical in all 88 columns; the other 47,536 differ in `longitude` and `latitude` only. Coordinates: 8,797 were `#N/A` there and are numbers here; 397 the reverse; of the pairs numeric in both, 30 moved under 1 km, 2,446 1-10 km, 35,866 over 10 km | The same schools, codes and counts. Only the coordinates changed, for nearly every school |
| X-2 | Distance from each school to the median point of its own city or municipality (PSGC code), as in deped_enrollment_psgc O-11, public schools in the box | All-sector workbook, 38,685 schools: < 10 km 21,960; 10-25 7,505; 25-50 4,533; 50-100 2,896; > 100 km 1,791. This workbook, 47,080: < 10 km 40,046; 10-25 5,937; 25-50 675; 50-100 162; > 100 km 260 | This file's points are far more consistent with each school's PSGC place |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | This file's coordinates are a corrected re-issue of deped_enrollment_psgc's, which were misplaced for most schools | Ask the sender; point-in-polygon against the HDX ADM3 and ADM4 boundaries for both files | open (consistent with X-2) |

## Questions for the sender

- Is this file a correction of the all-sector workbook's coordinates, and should it replace them?
- Are there terms on publishing results from it?
- On what date was it sent?
