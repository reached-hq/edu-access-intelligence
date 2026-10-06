# DepEd enrollment across SY 2023-24, 2024-25, and 2025-26

**Research date:** 2026-10-06 · Part of #8

## Purpose and method

This memo compares the three acquired enrollment files: their columns, category labels, school IDs, and place names, and how each year matches PSGC 2Q 2026. Every number below is printed by [`notebooks/profiling/cross_source_deped_years.py`](../../notebooks/profiling/cross_source_deped_years.py) under the finding ID shown, from checksum-verified raw files.

- Category labels are compared on the same schools: a school's value in one year is cross-tabulated against its value the next year, so a relabel shows up as one pair that holds for nearly every school.
- Place names are compared after the normalization the PSGC match already uses (capitals, collapsed spaces, repaired encoding, no trailing "(Capital)"), so that a spacing change is not counted as a move.
- The PSGC match reuses the SY 2023-24 rules from [deped_dataset_research.md](deped_dataset_research.md#rules) unchanged. SY 2023-24 reproduces that memo's numbers exactly.

The lists behind the counts (dropped and new school IDs, changed place names, newly unmatched names) are in [deped_year_changes.md](deped_year_changes.md).

The [deped_enrollment profile](../source_inventory/deped_enrollment/profile.md) already records the column, encoding, and label changes for SY 2025-26 (O-6 to O-8), the Negros Island Region move (O-10), and the school ID churn (O-12). This memo adds what those findings leave out: which labels map to which, the lists, blank counts, the Sulu move, and the PSGC match for the later years.

## Summary

1. **The later years match PSGC as well as SY 2023-24.** 97.1% of schools reach a PSGC barangay in both SY 2024-25 and 2025-26, against 96.9% in SY 2023-24, with the same rules. Across the two later years, only 23 unmatched names were matched or absent in SY 2023-24.
2. **Every category label in SY 2025-26 is renamed, but one to one.** `sector`, `school_management`, `annex_status`, and the three `offers_*` columns each have a clean old-to-new mapping on the same schools. A small number of schools also really change category every year.
3. **SY 2025-26 leaves counts blank instead of 0** for levels a school does not offer: the Senior High School columns for 47,352 schools and the Kinder to Grade 10 columns for 1,403. Earlier years write 0.
4. **Regions move twice.** 2,704 kept schools move from Regions VI and VII to the Negros Island Region in SY 2024-25, and 477 Sulu schools move from BARMM to Region IX in SY 2025-26. DepEd's own region is therefore a different map in each year.
5. **School IDs churn by about 1% a year,** and 29 IDs skip SY 2024-25 and come back in 2025-26. All are listed.
6. **Some place changes are real transfers.** 31 schools move from Makati to Taguig in SY 2024-25, and their barangays are the ones PSGC 2Q 2026 lists under Taguig. In SY 2023-24 those 31 are unmatched only because DepEd still filed them under Makati.

## Y-1: rows and columns

| School year | Schools | Columns |
|---|---:|---:|
| 2023-24 | 60,167 | 78 |
| 2024-25 | 60,129 | 78 |
| 2025-26 | 60,204 | 83 |

SY 2024-25 has the same columns as 2023-24. SY 2025-26 adds `Modified Curricular Offering Classification` and four `g11_sshs_*` columns, and removes none.

## Y-2: category labels

From SY 2024-25 to 2025-26, on the 59,653 schools in both files:

| Column | SY 2024-25 label | SY 2025-26 label | Schools |
|---|---|---|---:|
| `sector` | `SUC/LUC` | `SUCsLUCs` | 171 |
| `school_management` | `DepEd` | `DepED Managed` | 47,786 |
| | `Non-Sectarian` | `Non-Sectarian ` (trailing space) | 8,114 |
| | `Sectarian` | `Sectarian ` (trailing space) | 3,490 |
| | `SUC` | `SUC Managed` | 163 |
| | `PSO` | `SCHOOL ABROAD` | 35 |
| | `DOST` | `DOST Managed` | 15 |
| | `International School` | `Local International School` | 6 |
| | `Other GA` | `Other GA Managed` | 1 |
| | `LUC` | `LUC` (unchanged) | 8 |
| `annex_status` | `Standalone School` | `School with no Annexes` | 56,908 |
| | `Mother School` | `Mother school` | 1,933 |
| | `Annex/Extension School` | `Annex or Extension school(s)` | 722 |
| | `Mobile School/Center` | `Mobile School(s)/Center(s)` | 14 |
| `offers_es`, `offers_jhs`, `offers_shs` | `True`, `False` | `Yes`, `No` | all |
| `legislative_district` | `PSO` | `Lone District` | 35 |

The rest are schools whose category really changes, every year and in every column. From SY 2024-25 to 2025-26, for example: 25 schools from non-sectarian to sectarian and 9 back; 33 mother schools and 25 annexes become schools with no annexes; 232 schools start offering Senior High School and 141 stop. From SY 2023-24 to 2024-25 the labels do not change, except that `NIR` (region) and `No Legislative District` appear, and the same kind of reclassification happens on a similar scale.

**For Silver:** one mapping table per column, from each year's label to one standard set, built from these pairs. Trim the trailing spaces first.

## Y-3: blank count cells

| School year | Count columns | Every SHS column blank | Of those, offering SHS | Every Kinder to Grade 10 column blank | Every count blank |
|---|---:|---:|---:|---:|---:|
| 2023-24 | 62 | 0 | 0 | 0 | 0 |
| 2024-25 | 62 | 0 | 0 | 0 | 0 |
| 2025-26 | 66 | 47,352 | 120 | 1,403 | 46 |

In SY 2023-24 the only blanks are the four `g11_unique_*` and `g12_unique_*` columns, which the README says start in SY 2024-25 (profile O-16). In SY 2025-26 a blank mostly means "level not offered", where earlier years wrote 0. No school in any year has SHS learners while not offering SHS. The exceptions are the 120 schools that offer SHS but have every SHS column blank, and the 46 schools with every count blank. Those are missing counts, not zeros.

**For Silver:** do not read every blank as 0. Read it as 0 only where the school does not offer that level, and keep the 120 and the 46 as missing, flagged.

## Y-4: school IDs

| Years | Kept | Dropped | New |
|---|---:|---:|---:|
| 2023-24 to 2024-25 | 59,537 | 630 (private 404, public 204, SUC/LUC 22) | 592 (public 358, private 230, overseas 2, SUC/LUC 2) |
| 2024-25 to 2025-26 | 59,653 | 476 (private 295, public 169, SUC/LUC 12) | 551 (public 326, private 224, overseas 1) |

59,072 school IDs are in all three years. 29 are in SY 2023-24 and 2025-26 but not 2024-25, so a missing year is not always a closure. All dropped and new IDs are listed with their name, sector, and place.

## Y-5: place names for the same school

Changes that remain after normalization, on schools in both years:

| Field | 2023-24 to 2024-25 | 2024-25 to 2025-26 |
|---|---:|---:|
| Region | 2,704 (Negros Occidental 1,586 and Negros Oriental 1,027 to NIR; Siquijor 91 to NIR) | 477 (all Sulu, BARMM to Region IX) |
| Division | 63 | 64 |
| Province | 2 (`NORTH COTABATO` to `(SGA - North Cotabato)`) | 36 (35 overseas schools from `PSO` to `NCR SECOND DISTRICT`; 1 from Davao Occidental to Davao del Sur) |
| City or municipality | 47 | 42 |
| Barangay | 70 | 123 |

As published, SY 2025-26 differs far more (2,514 province values and 576 barangay values), but almost all of that is extra spaces (profile O-5).

The city and municipality changes are of three kinds:

- **Transfers:** 31 schools from `CITY OF MAKATI` to `TAGUIG CITY` in SY 2024-25. Their barangays (Cembo, Comembo, East Rembo, Pembo, Pitogo, Rizal, South Cembo, West Rembo) are under the City of Taguig in PSGC 2Q 2026.
- **Labels:** 35 overseas schools get `CITY OF PASIG` in SY 2025-26 (profile O-13), and 2 Special Geographic Area schools get `(SGA - North Cotabato)` as their municipality in SY 2024-25.
- **Single schools** moving to a neighbouring municipality, such as `SITANGKAI` to `SIBUTU` or `SANTA CRUZ` to `BOAC`. These read as corrections of where the school is, not renamed places.

## Y-6: PSGC 2Q 2026 match by year

| School year | Schools (overseas excluded) | Matched to barangay | City or municipality unmatched | Barangay unmatched | Ambiguous | No barangay given |
|---|---:|---:|---:|---:|---:|---:|
| 2023-24 | 60,134 | 58,289 (96.9%) | 1,022 | 726 | 60 | 37 |
| 2024-25 | 60,094 | 58,364 (97.1%) | 964 | 678 | 58 | 30 |
| 2025-26 | 60,168 | 58,449 (97.1%) | 971 | 681 | 60 | 7 |

Names that are unmatched in a later year but were matched or absent in SY 2023-24 (23, all listed):

- **The new Special Geographic Area label.** From SY 2024-25 DepEd files some Special Geographic Area schools (7, then 8) under province `(SGA - North Cotabato)`, often with the same text as their municipality. It matches no PSGC unit. The other 110 stay under `NORTH COTABATO`, as in SY 2023-24.
- **`MALITA` under `DAVAO DEL SUR`** in SY 2025-26: Malita is in Davao Occidental, so the province looks wrong in DepEd's file.
- **16 barangay rows (12 distinct names),** for example `LIGAS II`, `P.F. ESPIRITU III`, and `ZAPOTE I` in Bacoor and `POBLACION` in Taguig. Four of them are unmatched in both later years.

For the same school in consecutive years, the matched barangay code is the same for 57,696 schools (2023-24 to 2024-25) and 57,843 (2024-25 to 2025-26). It differs for 37 and 56 schools.

## What it means for joins

- **School-level trends need a label map and a fixed region map.** Region from DepEd is not one map across these years (NIR from SY 2024-25, Sulu in Region IX from SY 2025-26). Report trends by PSGC 2Q 2026 region, or by province.
- **The PSGC rules carry over.** No new matching rule is needed for the later years. One improvement for every year: a documented rule for transferred barangays would recover the 31 Makati to Taguig schools in SY 2023-24, using DepEd's own SY 2024-25 placement as evidence.
- **The Special Geographic Area needs its own handling in every year.** It has three labels across the files (`NORTH COTABATO`, `(SGA - North Cotabato)`, and division `Special Geographic Area Division`), and none of them matches the eight PSGC municipalities.
- **Blank does not mean zero in SY 2025-26** (Y-3).

## Limits

- Place changes are taken as published. A school moving to a neighbouring municipality may be a correction or a real move; DepEd does not say which.
- The newly unmatched barangays were not checked one by one against PSGC `Old names` or later PSGC releases.
- Only the three acquired years are compared. DepEd publishes enrollment from SY 2017-18.
