# deped_enrollment_psgc: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-14 |
| Profiled by | @maeveylain |
| Tool | DuckDB 1.4.5 (Python), run locally: [`analysis/profiling/profile_deped_enrollment_psgc.py`](../../../../analysis/profiling/profile_deped_enrollment_psgc.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if the file's checksum differs |
| How files were read | Sheet `DB` of the original xlsx, read with the standard library (D-007) and loaded into DuckDB with every column as text (`all_varchar`), strict CSV parsing. Columns are mapped by position; the script stops if any of the 88 headers in row 8 differs from the expected one |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/profiling/profile_deped_enrollment_psgc.py
```

The workbook must be at `$RAW_DATA_DIR/deped/original/`. The cross-checks are optional: X-1 runs if `deped/original/Enrollment-in-SY-2023-2024.zip` is present with the SHA-256 on the [deped_enrollment card](../deped_enrollment/README.md#files); X-2 runs if `psa/original/` holds the two PSGC files with the SHA-256 on the [psa_psgc card](../psa_psgc/README.md). Otherwise each prints `skipped`. Each finding below prints under its ID. The column statistics in [data_dictionary.md](data_dictionary.md) come from `analysis/profiling/dictionary_deped_enrollment_psgc.py`. Two runs on the same files give identical output.

## Summary

The SY 2023-24 school enrollment that the team already has (deped_enrollment), plus a PSGC code for each school's barangay and the school's coordinates. Enrollment is identical to deped_enrollment for all 60,167 shared schools (X-1), so this source adds **location, not counts**. The PSGC codes are the main gain: 59,500 schools (98.7%) have a barangay code that PSA knows (X-2). Before joining, codes must be padded to 10 digits (O-5). The coordinates are weak: 23% are missing and at least 2,275 schools are placed over 100 km from their own city or municipality (O-10, O-11). Use them for maps only after a boundary check (S-1), not for distance measures.

## Observed findings

| ID | Finding | Evidence (query or check, counts) | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | A report layout, not a table | One sheet, `DB`. Rows 1-5 are titles (enrollment from LIS as of 2024-01-31; PSGC "based on PSA (4th quarter of 2024 PSGC)"; income class from DOF D.O. 74 s. 2024). Row 6 holds two notes and the grade bands, row 7 the sex, row 8 the column names. Nine sheet rows are absent (blank): 60177-60180, 60195-60197, 60291-60292. Row 60176 has no school and 13 cells, all `#N/A`, in the PSGC and coordinate columns | A generic reader that takes row 1 as the header fails; the `#N/A` row would load as a school | Bronze reads from row 9 and maps columns by position after checking the 88 headers. Row 60176 is rejected with a counted reason |
| O-2 | A main block and an appended block | Rows 9-60175 hold 60,167 schools. After the first gap, rows 60181-60293 hold 108 more: 0 of them have a PSGC code, coordinates, or `URP`. By sector: Private 94, Public 13, SUCsLUCs 1. By region: Region IV-A 43, Region VII 30, Region III 11, NCR 10, others 14 | 108 schools cannot be placed with this file. Their origin is unknown (S-3) | Keep them, flagged as having no location. Locate them by name matching, as for deped_enrollment |
| O-3 | School ID is clean in the main block, not after it | Main block: 0 non-numeric, 0 not 6 digits, 0 duplicates. Appended block: `1406363` (7 digits, The Ermita Catholic School, row 60181), and `404520` (Catherina Cittadini School) on rows 60263 and 60267, which are identical in every column | A 7-digit ID breaks the documented 6-digit format; the duplicate double-counts one school | Bronze: a repeated ID is a WARN with every row kept as evidence (D-015). Silver keeps one of two identical rows and counts it |
| O-4 | Enrollment counts are complete whole numbers | 58 count columns (Kindergarten to Grade 12 by strand, by sex); 0 cells not a whole number, 0 blank. 27,084,335 learners: 27,081,292 in the main block, 3,043 in the appended block. 213 schools have 0 learners | Counts can be summed directly | None needed. See X-1 for the comparison with deped_enrollment |
| O-5 | PSGC codes lost their leading zero | Code cells are stored as numbers. Regions I to IX have 9-digit codes: 36,014 schools in every PSGC code column (36,010 for barangay), e.g. `100000000` for Region I. The other 23,490 have 10 digits | A text join to PSA's 10-digit `0100000000` misses 36,014 of the 59,504 schools with a code (60.5%) | Pad every numeric code to 10 digits with leading zeros. Rule documented in Silver with the count of padded values |
| O-6 | `#N/A` in the PSGC columns | 663 schools have `#N/A` for region, province, and city/municipality; 667 for barangay. The extra 4 are in City of Olongapo, with a blank DepEd barangay. By sector: Private 408, Public 204, PSO 33 (all overseas schools), SUCsLUCs 22. NCR has the most (174). Examples: `100015` ILOCOS NORTE / BACARRA / CABULALAAN | `#N/A` is an Excel error, not a value; 634 domestic schools have no code | Treat `#N/A` as missing and record the reason. Name-match the domestic schools to PSGC (#44). Exclude PSO from geographic analysis, as in deped_enrollment O-13 |
| O-7 | A few codes break the PSGC hierarchy | Barangay outside its city/municipality (first 7 digits): `207519` Damatulan `1999904001` under Kadayangan `1999903000`; `401274` and `500512` San Agustin `0307104008` under Iba `0307105000`. City not under its province: Angeles City (HUC) `0330100000` in Pampanga `0305400000`, 117 schools. Province under its region: 0 exceptions | Joining at different levels gives different places for 3 schools. The Angeles case is expected: a highly urbanized city's code is not under its province | Join on the barangay code, the most specific one. List the 3 schools for Silver. Do not test province-city containment for HUCs |
| O-8 | Two income class columns, one typo | Columns AA and AB share a header. AB adds the LGU kind (`1st Class City`, `1st Class Municipality`) and never disagrees with AA. `1St` on 89 schools. `SGA (No Income Classification)` on 112 schools. `#N/A` on 663, blank on 108 | Duplicate header names break loaders that require unique names; `1St` is a separate category | Name the columns `income_class` and `income_class_long`. Normalize `1St` to `1st`, with the count |
| O-9 | Two different urban/rural classifications | Column Z (PSA, 2020 CPH, by barangay): `R` 39,532, `U` 19,888, `#N/A` 667, `-` 80, blank 108. Column P `URP` (undocumented): `Partially Urban` 47,551, `Urban` 9,684, `Rural` 2,932, blank 108. They disagree: 1,309 `Urban` schools are in `R` barangays and 244 `Rural` schools in `U` barangays | Using the wrong one changes urban/rural results | Use column Z (PSA, documented) for barangay urbanity. Keep `URP` as published until its meaning is known (S-4) |
| O-10 | Coordinates: 23% missing, some impossible | 46,374 schools have numeric coordinates, 13,793 `#N/A` (22.9%), 108 blank. 13,147 of the `#N/A` schools do have a PSGC barangay code. Missing by sector: Public 9,079 of 47,831; Private 4,610 of 12,207; PSO 33 of 33. NCR is worst: 1,879 of 2,697. 6 schools are at (0, 0); 54 others are outside lon 116-127, lat 4-21.5, e.g. `136622` NCR at (112.11, 12.73). None look swapped. 27 longitudes are whole numbers, e.g. (121, 13); 13,536 carry binary-float digits (`5.0999999999999996`). 125 coordinate pairs are shared by 256 schools | Missing coordinates are not random (NCR, private schools). Placeholder-like points (0, 0), (121, 13) would distort maps | Treat `#N/A`, (0, 0), and out-of-country points as missing, each with a count. Round to 7 decimals on load and record it |
| O-11 | Many coordinates far from their own city or municipality | Distance from the median point of the other schools with the same PSGC city/municipality code: within 10 km 25,290; 10-25 km 9,528; 25-50 km 5,582; 50-100 km 3,678; over 100 km 2,275. MIMAROPA has the most over 100 km (505 of 2,306). Examples: `130749` Polomolok at (114.00, 21.00), 2,015 km away. No row shift: shifting one or two rows explains only 60-117 of the 2,275 | At least 2,275 points, and probably more, are in the wrong place. The median is a rough centre for large or island municipalities | Do not compute distances from these coordinates until S-1 is tested. Flag schools over 100 km as suspect, with the count |
| O-12 | DepEd place names next to PSGC names | DepEd `Barangay` equals the PSGC barangay name, ignoring case and spaces, for 52,049 of 59,500 schools. 2,704 schools carry PSGC region Negros Island Region while DepEd still lists them under Region VI (1,586) or VII (1,118) | Barangay names differ for 7,451 schools, and the region differs for all NIR schools, so the DepEd names and the PSGC columns cannot be used interchangeably | Use the PSGC codes for joins. Keep the DepEd names as published for traceability |

## Cross-source checks

| ID | Check | Evidence | Conclusion |
|---|---|---|---|
| X-1 | Against deped_enrollment SY 2023-24 (`enrollment_2023-24.csv`) | Same 60,167 school IDs; 0 only in the CSV; the 108 extra schools are all in the appended block. Each of the 58 count columns equals its CSV column for every school (`ACAD PBM` = `maritime`, Pre-Baccalaureate Maritime). Totals equal: 27,081,292; 0 schools differ. The CSV's four `unique` columns are blank in every row and have no counterpart here | The main block is the same enrollment as deped_enrollment, with location columns added |
| X-2 | PSGC barangay codes (padded to 10 digits) against psa_psgc 2Q 2026 and the Q4_2023 API pull | 59,500 schools with a code: 59,033 are in 2Q 2026, 56,761 in Q4_2023, 0 in neither. Only in 2Q 2026: 2,739, of which 2,704 are Negros Island Region (`18…`). Only in Q4_2023: 467, all Sulu (`19066…`, still under BARMM). All 80 `-` urban/rural schools are in 2Q 2026, 53 in Q4_2023 | Every code is real. The mix, NIR present and Sulu still in BARMM, fits a PSGC version from late 2024, as the title row says; the Q4 2024 file itself is not acquired (S-5) |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | Coordinates far from their city or municipality (O-11) are wrong, not large municipalities | Point-in-polygon of each school against the approved HDX ADM3 and ADM4 boundaries (hdx_boundaries), by PSGC code. Count schools outside their own municipality and barangay | open |
| S-2 | Coordinates for private schools come from a different source than NSBI | NSBI covers public schools only (Technical Notes p. 3, 12, via deped_facilities), but 7,597 of 12,207 private schools have coordinates. Ask the publisher; compare precision and outlier rates of public and private schools | open |
| S-3 | The 108 appended schools (O-2) were added by hand after the main extract | They are not in the deped_enrollment CSV, have no PSGC or coordinates, and follow blank rows. Ask the publisher; check whether they appear in deped_enrollment SY 2024-25 | open |
| S-4 | `URP` is DepEd's own urban/rural classification of the school | Undocumented. Ask the publisher; compare with the DepEd school classification in other DepEd files | open |
| S-5 | PSGC codes are from the PSA Q4 2024 publication, as stated | Acquire the PSA PSGC Q4 2024 file and match all codes; X-2 shows consistency with late 2024 only | open |
| S-6 | The 634 domestic schools with `#N/A` PSGC (O-6) are lookup failures, not schools without a location | `#N/A` is an Excel lookup error and row 60176 holds only `#N/A`. Name-match them to PSGC and count matches | open |

## Changes across files or years

- One file, SY 2023-24 only. Compared with deped_enrollment SY 2023-24, labels follow the SY 2025-26 style (`SUCsLUCs`, `School with no Annexes`, `Modified COC`), and the PBM strand is named differently (X-1).

## Questions for the publisher or mentor

Ask DepEd EMISD by replying to the email that delivered the file (EMISD invites follow-up questions there).

- May results derived from this file be published (licensing, [card](README.md))?
- What are the 108 rows after the blank rows (S-3)?
- What is `URP`, and what does `Partially Urban` mean (S-4)?
- Where do the coordinates of private schools come from, if NSBI covers public schools only (S-2)?
- Is a later version with fewer `#N/A` coordinates available?
