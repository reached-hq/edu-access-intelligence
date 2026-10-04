# bpda_barmm_education: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-04 |
| Profiled by | @hyenalouise, with AI-assisted checks reviewed by the author |
| Tool | `notebooks/profiling/profile_bpda_barmm_education.py`, standard-library XLSX reader |
| Files profiled (SHA-256) | `BARMM_Education.xlsx` — `5f08cb21ab1abaa2e13277eea429293782c3984447f7217bacce08c1eb44eeca` |
| How files were read | All cells read as stored text from XLSX XML; checksum and exact shape checked first |

## Summary

Conditionally usable for historical division-level access and progression context in BARMM. The 10-row workbook is structurally clean, but it is old, lacks methodology and denominators, has eight Cotabato City blanks, and cannot join directly to current PSGC geography. It should be supporting context, not the primary modeling table.

## Observed findings

| ID | Finding | Evidence (query or check, counts) | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | Reporting-area label is unique | 10 rows; 10 distinct `Province / School Division` values; 0 duplicate keys and 0 fully duplicated rows | Supports one row per published area | Preserve raw label as key until a dated school-division bridge exists |
| O-2 | Rate cells are mostly complete numeric fractions | 200 expected rate cells; 192 numeric and 8 blank; numeric range 0.0362 to 1.0786; median 0.55915 | Values can be normalized to long-form percentages | Cast numeric fractions to decimal rates; keep raw value |
| O-3 | Every blank is in Cotabato City | Completion and cohort-survival fields are blank for elementary and secondary in both SY 2019-2020 and 2020-2021; its 12 net-enrolment cells are filled | Cotabato City cannot be compared on two indicator families | Keep null; do not impute or treat as zero |
| O-4 | Three net-enrolment rates exceed 100% | Lamitan City elementary NER: 107.02% (2018-19), 107.86% (2019-20), 101.52% (2020-21) | Values may reflect denominator or coverage mismatch; clipping would hide the issue | Retain and flag; obtain publisher explanation |
| O-5 | Labels reflect historical reporting geography | Values include `Lanao Del Sur I/II`, `Maguindanao I/II`, city divisions, Sulu, and Cotabato City | Direct current-PSGC joins would be wrong or ambiguous | Build a dated school-division bridge and preserve source geography |
| O-6 | Provenance and methodology are absent from the file | No title row, source note, definitions, formula, PSGC, denominators, region total, release date, or workbook core properties | Indicator semantics and re-aggregation cannot be verified | Treat as conditional/contextual until MBHTE or BPDA supplies documentation |
| O-7 | Two cohort-survival rates are exactly 100% | Marawi City cohort survival SY 2019-2020: elementary 1.0 and secondary 1.0; no other rate cell equals 1.0 | A perfect rate at both levels in the same year may be a cap or placeholder rather than a measured value | Retain and flag; do not rank Marawi City on cohort survival for SY 2019-2020 without a publisher explanation |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The Lamitan City values above 100% may arise from numerator/denominator timing, cross-boundary enrolment, or a mislabeled gross rate | Request the indicator formula and underlying numerator/denominator from BPDA/MBHTE and compare with PSA OpenSTAT / DepEd regional tables | open |
| S-2 | The numbered division labels correspond to historical MBHTE schools-division jurisdictions rather than province boundaries | Obtain the school-division master list and jurisdiction table for each school year | open |
| S-3 | Public and private education coverage may differ by indicator | Obtain the source-system note and coverage definition | open |
| S-4 | The Marawi City SY 2019-2020 cohort-survival values of exactly 100% may be capped or placeholder values rather than measured rates | Request the underlying enrolment counts by grade from BPDA/MBHTE and recompute the rate | open |

## Changes across files or years

- One workbook contains all periods in a stable wide layout.
- Net enrolment has three school years (2018-2019 to 2020-2021); completion and cohort survival have two (2019-2020 to 2020-2021).
- The file provides no release history, so revisions and collection changes cannot be assessed.
- SY 2019-2020 and 2020-2021 overlap the COVID-19 disruption period.

## Questions for the publisher or mentor

- Which agency and source system produced each indicator: MBHTE/BEIS, PSA, or another source?
- What are the exact formulas, numerators, denominators, coverage, and cut-off dates?
- Does `Secondary` mean JHS, SHS, or both for completion and cohort survival?
- Why are Cotabato City completion and cohort-survival values blank?
- Why do Lamitan City elementary net-enrolment values exceed 100%?
- Are the Marawi City SY 2019-2020 cohort-survival values of exactly 100% measured, capped, or placeholders?
- What school-division codes and boundary definitions apply to each row and school year?
- What is the dataset's publication/revision date and reuse license?
