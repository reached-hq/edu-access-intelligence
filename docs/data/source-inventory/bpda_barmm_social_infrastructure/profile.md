# bpda_barmm_social_infrastructure: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-04 |
| Profiled by | @hyenalouise |
| Tool | `analysis/profiling/profile_bpda_barmm_social_infrastructure.py`, standard-library XLSX reader |
| Files profiled (SHA-256) | `BARMM_Social_Infrastructure.xlsx` — `6af9c99e33d820f99eb554326eb126cf6a2cdb30945e8f11088a0b26197391d3` |
| How files were read | All cells read as stored text from XLSX XML; checksum and exact non-empty shape checked first |

## Summary

Conditionally usable for broad historical counts of schools, madaris, classroom buildings, and selected facilities across nine BARMM reporting areas. It adds infrastructure detail absent from the other profiled sources, but mixed dates, undocumented dash markers, historic geography, and building-level rather than classroom-level measures make it unsuitable for crowding, distance, or teacher-load calculations.

## Observed findings

| ID | Finding | Evidence (query or check, counts) | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | Reporting-area label is unique | 9 rows; 9 distinct `Province/City` values; 0 duplicate keys and 0 fully duplicated rows | Supports one row per published reporting area | Preserve raw label until a dated geography bridge exists |
| O-2 | The file uses three different missing/format states | 288 measure cells: 200 numeric, 87 `-`, 1 physical blank; 3 numeric cells contain a leading non-breaking space; no other non-numbers | Naive casting or treating dash as zero will corrupt counts | Retain raw text; trim Unicode whitespace; map dash and blank to distinct null-reason states |
| O-3 | Numeric measures are whole, nonnegative counts | 200 numeric cells; 0 non-integers; 4 explicit zeroes; range 0 to 2,052; median 18 | Type is consistent where values exist | Cast only verified numeric text to integer; preserve zero |
| O-4 | Madrasah component counts reconcile where all components are numeric | `Private Madrasah Elementary = with PTO + Traditional` in 7 of 7 complete rows | Provides a limited internal consistency check | Validate this relation when all three values are present; do not assume dash equals zero in the two incomplete rows |
| O-5 | Geography is mixed and historical | Labels are 5 provinces, 3 cities, and SGA; Maguindanao is unsplit and Sulu is included | Current-PSGC joins and region attribution would be wrong without a bridge | Use a dated, explicit reporting-area bridge |
| O-6 | Education measures have mixed or absent dates | 21 education columns; 4 state a period and 17 do not. Private and public elementary school counts state 2019-2021, permanent elementary classroom buildings state `as of 2022`, and semi-permanent elementary classroom buildings state `as of 20222` | Same-row values are not proven contemporaneous | Store reference period per measure; keep unknown where absent |
| O-7 | Classroom fields count buildings, not capacity | Four headers explicitly say classroom building; no fields contain classroom rooms, seats, learners, utilization, or condition | Cannot calculate crowding or learner-to-classroom ratio | Use as descriptive building inventory only |
| O-8 | Provenance and methodology are absent from the file | No title row, source note, definitions, PSGC, dash semantics, region total, release date, or workbook core properties | Source and measure semantics remain incomplete | Treat as conditional/contextual until BPDA supplies documentation |
| O-9 | Worksheet contains extensive empty formatting | 1,000 physical rows; only 10 non-empty rows (header plus 9 records) | A row-count based on worksheet extent would be wrong | Drop only wholly empty rows and assert 9 data records |
| O-10 | Private elementary and private secondary school counts look copied | `Number of Private Elementary Schools, by Province/City, 2019-2021` equals `Number of Private Secondary Schools` in 5 of 9 rows: Maguindanao 88, Lanao del Sur 57, Basilan 13, Sulu 15, Tawi-Tawi 18. The other four rows differ: Cotabato City 39 vs 6, SGA 5 vs 49, Lamitan City 5 vs 39, Marawi City 49 vs 5 | At least one of the two columns is probably wrong, so private school counts cannot be trusted at either level | Retain both raw columns; exclude both from analysis until BPDA confirms the values |
| O-11 | Four permanent classroom-building counts are far out of line with school counts | Permanent buildings per public school are 2.7 to 5.0 for elementary and 1.2 to 5.7 for secondary in most rows, but Cotabato City elementary is 34.2 (959 / 28), SGA elementary 16.3 (1,383 / 85), Lamitan City secondary 70.1 (491 / 7), and Marawi City secondary 38.4 (269 / 7) | Ranking or comparing areas on these columns would be driven by four suspect values | Retain and flag; do not rank areas on classroom-building counts until BPDA explains the four values |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | Some `-` markers may mean zero, especially where a total equals the only numeric component. In both incomplete madrasah rows the total equals the one filled component: Basilan 11 = 11 with PTO + `-` traditional; Lamitan City 3 = 3 with PTO + `-` traditional (O-4) | Obtain BPDA's codebook or source worksheet and compare with the originating ministry table | open |
| S-2 | `as of 20222` is a typographical error for 2022 | Confirm with BPDA/MBHTE or an archived source table; do not silently correct before confirmation | open |
| S-3 | `Number of SUCs and Elementary Schools` may be a malformed combined header | Ask BPDA for the original data dictionary and originating field name | open |
| S-4 | Different columns may originate from different ministries and reporting years | Obtain column-level provenance from BPDA | open |
| S-5 | The private secondary column may have been pasted from the private elementary column, with the last four rows reordered or partly re-entered | Ask BPDA for the originating MBHTE table for both columns and compare row by row | open |
| S-6 | The four outlying classroom-building counts may be misplaced values, a different counting unit, or schools and buildings counted under different geographies (for example SGA versus Cotabato City) | Ask BPDA for the originating MBHTE facilities table and school list per area | open |

## Changes across files or years

- One workbook contains all measures; it is not a time series.
- A few headers name periods or as-of dates, while most do not.
- The file provides no release history, so revisions cannot be assessed.

## Questions for the publisher or mentor

- What does `-` mean in each column: zero, not applicable, not available, or not reported?
- What is the exact reference date/year and originating ministry/system for every education measure?
- Does a classroom-building count represent buildings, rooms, or another inventory unit?
- Why are permanent classroom buildings per public school so high for Cotabato City and SGA (elementary) and Lamitan City and Marawi City (secondary)?
- What does `Number of SUCs and Elementary Schools` mean?
- Why are private elementary and private secondary school counts identical for Maguindanao, Lanao del Sur, Basilan, Sulu, and Tawi-Tawi? Which column is correct?
- Is `as of 20222` intended to be 2022?
- Which geography vintage defines Maguindanao, SGA, Cotabato City, and Sulu in this table?
- Can BPDA/MBHTE provide school-level IDs, addresses/coordinates, classroom counts, learner counts, teacher counts, and capacity?
- What is the dataset's publication/revision date and reuse license?
