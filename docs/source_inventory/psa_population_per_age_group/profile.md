# psa_population_per_age_group: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-02 |
| Profiled by | @mafelisilda |
| Tool | DuckDB and Python: [`notebooks/profiling/profile_psa_population_per_age_group.py`](../../../notebooks/profiling/profile_psa_population_per_age_group.py) |
| Files profiled (SHA-256) | `ce797046a055f870c30f5a2ce6d42b4bdc8f14f4dd8145269f450372c6c93ad6` |
| How files were read | Title validated as UTF-8 text; five delivered columns loaded into DuckDB as text; header validated; population cells converted to integers only after parsing; source row retained in memory for traceability |

## How to rerun

```powershell
$env:RAW_DATA_DIR = "C:\path\to\raw-data"
python notebooks\profiling\profile_psa_population_per_age_group.py
```

Place the inventoried CSV directly in `$env:RAW_DATA_DIR\psa\original\`.

## Summary

Usable for national and regional 2024 household-population analysis by age group and sex, subject to preserving the published definitions and geography. Lower-level `Both Sexes` analysis for ages 80 and older is not audit-ready because 38 rows fail sex reconciliation and 19 geographies fail age-band reconciliation. The file is otherwise complete and unique, with 2,603 rows, no blanks, no duplicate rows or candidate keys, and no negative or zero population values.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | File identity and schema are reproducible | SHA-256 matches the inventory; 1 title record, 1 header record, 2,603 data rows, and 5 columns | Supports immutable raw lineage | Stop on checksum, title, or header mismatch |
| O-2 | Candidate keys and full rows are unique | 0 duplicate `(Age Group, Geographic Location)` keys and 0 duplicate full rows | Safe source grain | Enforce uniqueness before loading |
| O-3 | Required values are complete and numeric | 0 blank cells across 13,015 data cells; 7,809 of 7,809 population cells parse as integers; 0 negatives and 0 zeros | No null imputation is needed | Reject blanks, non-integers, and negatives; retain valid zeros if later releases contain them |
| O-4 | Every geography has the complete age roster | 19 age categories each contain 137 rows; all 137 geographic labels occur exactly 19 times | No missing geography-by-age combinations | Assert the complete 19 by 137 matrix |
| O-5 | Display prefixes encode three geographic levels | 19 country rows, 342 region rows, and 2,242 lower-level rows, equal to 1, 18, and 118 labels across 19 ages | Prefix stripping without level retention would lose hierarchy | Derive level before cleaning; preserve raw label |
| O-6 | National totals reconcile to region totals | 57 of 57 national age-by-sex values equal the sum of the 18 region values | National and regional aggregation is internally consistent | Keep as a blocking refresh control |
| O-7 | Thirty-eight lower-level sex totals do not reconcile | `Both Sexes != Male + Female` for 38 of 2,603 rows: 19 in `80 - 84` and 19 in `85 and over`; Regions V: 12, X: 14, XI: 12; no country or region rows fail | Affected lower-level both-sex counts are unreliable | Quarantine these cells and obtain PSA confirmation, if possible; do not silently recalculate |
| O-8 | Nineteen both-sex all-age totals do not equal summed age bands | 19 of 137 geographies fail only for `Both Sexes`; each excess in the band sum equals that geography's published `85 and over` value. Male and female reconcile for all 137 geographies | The oldest lower-level age bands cannot be safely aggregated using `Both Sexes` | Block affected age-by-place analysis and retain raw values for audit |
| O-9 | Six region-child checks fail | Lower-level `Both Sexes` sums fail for Regions V, X, and XI in both `80 - 84` and `85 and over`; all other region-child age-sex checks reconcile | Confirms the defect is localized below region level | Make region-child reconciliation mandatory and publish exceptions |
| O-10 | Geographic text contains irreversible replacement characters | 38 rows and 2 distinct labels contain `U+FFFD`: `City of Las Piñas` and `City of Parañaque` are damaged in every age group | Exact name matching and presentation are impaired | Recover labels and codes from API metadata, while preserving raw CSV text |
| O-11 | Geographic codes are lost in CSV export | API metadata supplies one 10-digit code for each of 137 geographic labels; the CSV contains labels only | Name-only joins are less stable and footnote markers complicate matching | Ingest API codes or maintain a checksum-versioned crosswalk |
| O-12 | The asterisk denotes province counts that exclude separately reported HUCs, but the marker is inconsistently applied | 25 labels contain `*`, `**`, or numbered slash markers. A companion official PSA 2024 table defines `*` as "Population counts for the provinces exclude the counts of Highly Urbanized Cities." The age-group file has 14 labels with one asterisk. `Agusan del Norte` has no asterisk even though `City of Butuan` is a separate row | Marker-only parsing could incorrectly treat Agusan del Norte as including Butuan or create double counting in PSGC joins | Treat every separately listed HUC as outside its province row regardless of marker presence; preserve raw labels and join using API codes and hierarchy |
| O-13 | No direct personal information is present | Columns contain aggregate age group, geography, and population counts only | Low privacy risk | Classify as Public |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The 38 sex-total failures result from a PSA table-generation or export alignment defect | Compare the CSV with a fresh API JSON-stat or CSV response, PSA publication tables, and any correction notice; request publisher confirmation | open |
| S-2 | The `Both Sexes` values for `80 - 84` in the 19 affected geographies may include a broader oldest-age grouping | Obtain the underlying crosstab or methodology and compare its age-bin definitions; do not infer a correction from arithmetic alone | open |
| S-3 | The API's 10-digit geographic codes correspond to a specific PSGC edition | Compare all 137 codes and labels with dated PSGC releases and confirm the effective date with PSA | open |

## Changes across files or years

Only the supplied 2024 CSV was downloaded and profiled, so the observations and quality metrics in this document do not describe the historical tables. The [PSA OpenSTAT population catalog](https://openstat.psa.gov.ph/Database/Demographic-and-Social-Statistics/Population-and-Vital-Statistics) and API expose related census tables for 2010 and 2020, but their schemas and population concepts are not fully equivalent to the 2024 source.

| Census table | Population concept | Age categories | Sex categories | Geographic categories | Comparability with 2024 |
|---|---|---:|---|---:|---|
| [2010 table `0091A6DTPR0.px`](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/PO_2010/0091A6DTPR0.px) | Total population | 17; youngest label `Below 5`; oldest band `80 and over` | Male, Female; no `Both Sexes` category | 134 | Not directly equivalent. It reports total rather than household population, combines all ages 80 and older, and requires calculating both-sex totals from male and female values |
| 2015 catalog | Total population by geographic location | No age dimension in the table listed by the API | No sex dimension in the table listed by the API | Not assessed | Not a directly comparable age-by-sex source based on the current catalog listing |
| [2020 table `0031A6DPAG0.px`](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/PO_2020/0031A6DPAG0.px) | Selectable `Total Population` or `Household Population` | 18; includes `All Ages`; oldest band `80 years old and over` | Both Sexes, Male, Female | 135 | Partially comparable when `Household Population` is selected. Ages 80 and older cannot be separated into the 2024 `80 - 84` and `85 and over` bands |
| [2024 table `0201A6DPAG0.px`](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/PO_2024/0201A6DPAG0.px) | Household population | 19; includes `All Ages`; separate `80 - 84` and `85 and over` bands | Both Sexes, Male, Female | 137 | Profiled source |

Geographic categories also changed from 134 in 2010 to 135 in 2020 and 137 in 2024. Labels, regional assignments, province and HUC treatment, and footnote conventions differ, including ARMM versus BARMM and the appearance of NIR in 2024. Cross-year analysis therefore requires a dated geographic crosswalk and a harmonized age scheme. The safest common age grouping is subject to further validation, but ages 80 and older must be combined for comparison with 2010 and 2020.

The 2024 OpenSTAT API metadata showed the table updated on 2026-09-22, seven days before the recorded download. Future refreshes should record the API update timestamp and compare checksums, categories, geographic codes, footnotes, and all reconciliation metrics. A separate profiling run is required before the 2010 or 2020 tables are used analytically.

## Questions for the publisher or mentor

- Can PSA confirm or correct the 38 lower-level `Both Sexes` values in the two oldest age groups?
- Can PSA confirm why the age-group table omits `*` from Agusan del Norte even though Butuan is reported separately?
- Which PSGC edition or geographic effective date governs the API's 10-digit codes?
- What exact census reference date and household-population definition should accompany this table?
- Is there a revision history or correction-notice endpoint for OpenSTAT table `0201A6DPAG0.px`?
- What license or reuse terms apply to downloaded OpenSTAT data?
