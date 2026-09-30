# psa_poverty_stat: PSA city- and municipal-level poverty estimates (small area estimates), 2018, 2021, 2023

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Annex 1. Statistical Table on 2018, 2021 and 2023 City- and Municipal-Level Poverty Estimates (file `2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx`) |
| Publisher / agency | Philippine Statistics Authority (PSA) |
| Source system (as stated by the publisher) | "Source: Philippine Statistics Authority, through a national government-funded project on the generation of the small area estimates of poverty" (footer of the sheet) |
| Source URL or acquisition method | Manual download from https://psa.gov.ph/statistics/poverty-sae/stat-tables |
| Licensing or access restrictions | UNVERIFIED. The PSA page returned HTTP 403 to an automated fetch, so terms of use were not read. The workbook states none |
| Owner (team member) | @maeveylain |
| Date acquired | 2026-09-29 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx` | xlsx (1 sheet) | n/a (binary workbook; text is Unicode) | 369,977 | 1,630 data rows on sheet `2023_NoHUC_Maguindanao grouped` (rows 6 to 1635 of range A1:S1641; 5 header rows, 6 footer rows): 1,612 city or municipality rows and 18 region banner rows | `303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026` | Local |

The file name carries `06Feb2026`, which is probably the date the file was prepared. UNVERIFIED: the publication date on the PSA page was not read.

## Publisher documentation

The workbook has no data dictionary or metadata sheet. Its only documentation is the title, three footnotes, and a source line. No separate document was downloaded; the PSA methodology page was not read (HTTP 403).

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Title, footnotes and source line on the sheet | inside the workbook above | same as the file | Footnote 1 (standard deviation = poverty incidence x coefficient of variation / 100), footnote 2 (Bumbaran renamed Amai Manabilang), footnote 3 (no estimate for Kalayaan, Palawan) |

UNVERIFIED (not in the workbook): the definition of poverty incidence (population or family basis), the poverty threshold, the survey and census inputs, the method behind the confidence interval, and whether the estimates for the three years use the same method.

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, 18 region banner rows (includes Negros Island Region) |
| Geographic level | City or municipality, one row each, under region and province labels. 14 rows are Manila sub-municipalities. Highly urbanized cities are not in the file (`noHUC` in the file name) |
| Time coverage | 2018, 2021 and 2023 estimates in one wide table |
| Time basis | UNVERIFIED. The workbook does not say whether these are calendar years or survey reference periods |
| Update frequency | UNVERIFIED. Three estimate years so far |
| Population covered | 1,611 of 1,612 listed units have values. 35 cities and 9 municipalities in PSGC 2Q 2026 are not in the file (see `profile.md`, X-1) |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per city or municipality (wide: five measures for each of three years). Region banner rows carry only a region name |
| Candidate primary key | `PSGC ID` (1,612 unit rows, 1,612 unique). Stored as a number, so leading zeros are lost |
| Candidate join keys | `PSGC ID` left-padded to 6 digits, plus `000`, equals the PSGC 2Q 2026 `Correspondence Code` for all 1,612 rows (checked in `profile.md`, X-1). Names are not usable: 1,397 distinct in 1,612 rows, and 61 differ from the PSGC spelling |
| PSGC available? | Yes, but as a 5- or 6-digit ID, not the 10-digit PSGC. It equals the first six digits of the older 9-digit PSGC, so it identifies the city or municipality only. Province, region and city are derived from the padded ID prefix. The PSGC version is not stated |
| Personally identifiable or sensitive fields | None. Area-level estimates |
| Provenance fields in the source | Title, three footnotes and a source line. No per-row provenance |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected | Actual | Notes |
|---|---|---|---|
| `PSGC ID` | identifier (text) | number | 1,073 of 1,612 IDs have 5 digits because the leading zero was dropped. Blank on region banner rows |
| `Region/Province` | text | text | Region name on banner rows; province or district label on the first row of each group. One `(Continued)` label and one misplaced label (see below) |
| `Municipality/City` | text | text | 37 names carry a former name in parentheses. Footer says Bumbaran was renamed, but the row still reads Bumbaran |
| `Poverty Incidence <year>` | decimal (percent) | number | Percent scale (1 to 90). 2018 has 2 decimals; 2021 and 2023 have 4 |
| `Coefficient of Variation <year>` | decimal | number | 2018 mostly 2 decimals; 2021 and 2023 full precision |
| `Standard Error <year>` | decimal | number | Full precision, except 2018 (about half are 2 decimals) |
| `90% Confidence Interval Lower/Upper Limit <year>` | decimal (percent) | number | 2023 has a lower limit below zero |
| (column S) | none | empty | Inside the filter range but has no values |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** `PSGC ID` lost its leading zeros. 1,073 IDs have 5 digits and must be padded to 6.
- **Observed:** the file is wide by year, and only one row is missing all values (Kalayaan, Palawan, footnote 3).
- **Observed:** province labels appear on the first row of each group only, and some are wrong: one `(Continued)` label (row 1551, Pualas), and seven rows (Barobo to Carrascal) sit under `Surigao del Norte` although their codes are Surigao del Sur.
- **Observed:** `Lanao del Sur` appears as a label twice in a row, and Maguindanao del Norte and del Sur share province code `1538` because the workbook groups Maguindanao (sheet name).
- **Observed:** Negros Island Region rows carry two region prefixes in the ID (06 and 07, 31 rows each), so region cannot be derived from the ID alone.
- **Observed:** 2021 standard error disagrees with the coefficient of variation and interval for 133 rows, all in CALABARZON.
- **Observed:** three lower limits are zero or negative (Adams 2018, Port Area 2021, Ivana 2023).
- **Observed:** coverage gap: 33 highly urbanized cities, City of Isabela, City of Cotabato, Pateros, and 8 Special Geographic Area municipalities are not in the file.
- **Observed:** 61 names differ from PSGC spelling (for example `Tondo` vs `Tondo I/II`, `City of Baliuag` vs `City of Baliwag`).
- **Suspected:** the 2021 standard errors for CALABARZON were computed differently from the other regions. To test with the publisher.

## Limitations for analysis

- Estimates are model-based small-area estimates with wide uncertainty. Between 5% and 11% of estimates have a coefficient of variation above 20 in each year (10.6% in 2018, 5.2% in 2021, 9.7% in 2023). Compare units only with their intervals.
- Three time points, and UNVERIFIED whether they are comparable across years (method, definition, and geography may differ).
- Highly urbanized cities are missing, so school-level joins for those cities will have no poverty value.
- The ID is the city or municipality only, and it needs the padding rule and the PSGC version check before joining to the 10-digit PSGC.
- Names, labels and the hierarchy inside the sheet are not reliable keys. Use the ID.
- Cell values in 2021 and 2023 carry more decimals than the estimates justify. Do not treat the extra digits as precision.
