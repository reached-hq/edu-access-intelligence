# psa_openstat_education: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-04 |
| Profiled by | @hyenalouise |
| Tool | DuckDB (Python), run locally: [`analysis/profiling/profile_psa_openstat.py`](../../../../analysis/profiling/profile_psa_openstat.py) |
| Files profiled (SHA-256) | 13 CSVs and 13 metadata JSON files; see [README.md](README.md#files). The script stops if any checksum differs |
| How files were read | All columns as text (`all_varchar`), strict CSV parsing; each table reshaped to one value per geography, category, group, and year |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/profiling/profile_psa_openstat.py
```

`RAW_DATA_DIR` must contain `psa/original/openstat/` and, for X-1, `deped/original/Enrollment-in-SY-2023-2024.zip`. Every result prints under its finding ID below.

## Summary

Usable as a regional benchmark. The tables are small, complete against their metadata, and internally consistent: totals and regional sums reconcile exactly, and the SY 2023-24 school counts equal DepEd's enrollment file. Before use, the 35 geography labels need one region map, the three undocumented missing markers need to load as null, and each table's own year range has to be respected; most end at SY 2022-23.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | Every table matches its metadata | For all 13 tables, the cells in the CSV equal the product of the metadata's category counts (171 to 1,026 cells), and no row key repeats. The metadata holds only a title and dimensions | The exports are complete; nothing was dropped by the API | Assert cell counts and key uniqueness in Bronze |
| O-2 | Geography labels are inconsistent across tables | 35 distinct labels for 20 keys: the Philippines, 18 regions (17 plus the Negros Island Region), and Unknown. 13 regions have two or three spellings, e.g. `..Ilocos Region` and `..I - Ilocos Region`, and `..CALABARZON`, `..IV-A - CALABARZON`, `..IV-A  CALABARZON` (double space). `NIR` and `Unknown` in NAT Grades 6 and 10 have no `..` prefix | A join on the raw label fails between tables and against DepEd or PSGC | Map every label to one region key; stop on a label not in the map (the script does) |
| O-3 | Three undocumented missing markers | `..`: 216 cells, Senior High School teachers in all 18 rows for SY 2004-05 to 2015-16. `...`: 24 NAT Grade 6 and 28 NAT Grade 10 cells (all `NIR` and `Unknown` cells, plus NCR Grade 10 in SY 2019-20), and 6 cells per literacy table (NIR in 2013 and 2019). `a`: 3 cells per literacy table, Eastern Visayas 2013 | Treating a marker as zero, or failing to parse it, corrupts the values | Load all three as null and keep the raw marker |
| O-4 | Values are in range, with four net enrolment rates above 100% | Counts are non-negative whole numbers (schools 68 to 51,250; teachers 393 to 511,866). Rates and NAT scores are 0 to 100 except four elementary net enrolment rates: Region III total, male, and female in SY 2019-20 (100.02 to 100.03) and Region X male in SY 2019-20 (100.10) | A net enrolment rate cannot exceed 100% by definition, so the denominator or the age data is off for those cells | Keep and flag; do not cap |
| O-5 | Totals reconcile exactly | Table 10.10: Total = Public + Private in 270 of 270 cells. Regions sum to the Philippines in 45 of 45 cells for both Table 10.10 and Table 10.11 | Internally consistent counts | Keep as a Bronze check |
| O-6 | Year ranges differ by table | School counts SY 2019-20 to 2023-24; teachers SY 2004-05 to 2022-23; net enrolment SY 2019-20 (kindergarten, elementary) or 2018-19 (JHS, SHS) to 2022-23; cohort survival SY 2018-19 to 2022-23; NAT Grade 6 SY 2016-17, 2017-18, 2021-22; Grade 10 SY 2017-18, 2019-20, 2022-23; Grade 12 SY 2017-18, 2018-19, 2022-23; literacy 2013, 2019, 2024 | Only the school counts reach SY 2023-24; NAT years are not a series | Store years per table; never assume a shared range |
| O-7 | Literacy levels for the Philippines and BARMM | Basic literacy: Philippines 96.5, 96.5, 90.0; BARMM 86.1, 83.2, 81.0 (2013, 2019, 2024). Functional literacy: Philippines 90.3, 91.6, 70.8; BARMM 72.1, 71.6, 64.7 | BARMM is below the national rate in every year; 2024 is not comparable with 2013 or 2019 because PSA changed the definitions and the test for 2024 (O-9) | Report levels per year; do not report 2019 to 2024 as a change |
| O-8 | The school-year tables use 17 regions | No Negros Island Region in the school, teacher, net enrolment, cohort survival, and NAT Grade 12 tables. NIR appears with values only in the 2024 literacy columns, and as empty rows in NAT Grades 6 and 10 | Regional series are on the pre-NIR map, like DepEd SY 2023-24 | Use the 17-region map for school-year data |
| O-9 | PSA changed the literacy definitions and test for 2024 | FLEMMS 2024 Technical Notes: the revised definitions were approved by PSA Board Resolution No. 13, Series of 2024 (p. 1). Basic literate: 2019 "can read and write", reported by a proxy respondent; 2024 "can read, write, and compute", tested on each person with cue cards and self-administered forms. Functionally literate: 2019 also counted anyone who finished high school (old curriculum) or junior high school; 2024 "can read, write, compute, and comprehend". The sampling frame (2013 master sample to 2023 geo-enabled master sample) and the design domain (regional to provincial/HUC) also changed (p. 3) | The 2019 to 2024 fall in functional literacy (-20.8 points) mostly reflects the new definition, not a measured decline | Report 2024 literacy as a level; never as a change from 2013 or 2019 |

## Cross-checks with other sources

| ID | Check | Evidence | Result |
|---|---|---|---|
| X-1 | Table 10.10 SY 2023-24 school counts against [deped_enrollment](../deped_enrollment/) SY 2023-24 | 108 region, level, and type cells; DepEd public counted as Public plus SUC/LUC, overseas schools excluded, a school counted once for each level it offers | 108 of 108 equal. Philippines: elementary 39,386 public and 9,924 private; JHS 10,723 and 5,620; SHS 7,889 and 4,878. Table 10.10 is built from the same DepEd school list |
| X-2 | Table 10.11 teachers against DepEd personnel ([#40](https://github.com/reached-hq/edu-access-intelligence/pull/40)) | Table 10.11 ends at SY 2022-23; personnel is SY 2023-24 | Not comparable: no shared year |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The 2024 literacy figures were measured differently from 2019 (national functional literacy -20.8 points, basic -6.5) | Confirmed by the FLEMMS 2024 Technical Notes and documentation; see O-9 | confirmed (O-9) |
| S-2 | `a` marks Eastern Visayas 2013 as not collected or not published, and `...` marks a region or year with no data | Find the footnotes on the OpenSTAT web tables or the PSA publication behind each table | open |
| S-3 | The `Unknown` NAT rows hold learners or schools without a region, but no values are published | Ask PSA or DepEd what `Unknown` covers | open |

## Changes across files or years

- One retrieval of 13 tables; no earlier delivery to compare.
- Header style differs by table: school and teacher tables put the year alone in the header, the others combine group and year (`Male 2019-2020`), and NAT Grade 10 adds `Subject Area` before each subject.
- NAT Grade 6 calls its dimension `Subject Area`, Grade 10 calls it `Subject`.

## Questions for the publisher or mentor

- What do `..`, `...`, and `a` mean in these tables?
- Does Table 10.13 use the 10-and-over or the 5-and-over population for 2024? Its title says 10 and over; the Technical Notes compute the 2024 basic literacy rate for 5 and over (p. 1), and the public-use file has literacy levels for both (`llevel10over`, `llevel5over`).
- Which source and reference date does each table use (DepEd LIS, BEIS, NAT)?
- Why do four elementary net enrolment rates exceed 100% in SY 2019-20?
- What does the `Unknown` region in the NAT tables contain?
- What are the reuse terms for OpenSTAT data?
