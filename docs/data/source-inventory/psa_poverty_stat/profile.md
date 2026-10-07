# psa_poverty_stat: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-09-29 |
| Profiled by | @maeveylain |
| Tool | DuckDB 1.4.5 (Python), run locally: [`analysis/profiling/profile_psa_poverty.py`](../../../../analysis/profiling/profile_psa_poverty.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if the file's checksum differs |
| How files were read | Sheet `2023_NoHUC_Maguindanao grouped` of the original xlsx, read with the standard library and loaded into DuckDB with every column as text (`all_varchar`), strict CSV parsing. The 18 column names are built from the merged header (rows 2 to 5) |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/profiling/profile_psa_poverty.py
```

The file must be at `$RAW_DATA_DIR/psa/original/2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx`. Check X-1 also needs the PSGC 2Q 2026 workbook (`PSGC-2Q-2026-Publication-Datafile.xlsx`) in the same folder; without it the script prints "skipped" for X-1. The column statistics in [data_dictionary.md](data_dictionary.md) come from `analysis/profiling/dictionary_psa_poverty.py`.

## Summary

Usable as the poverty layer for city and municipality joins, with care. The ID is unique and maps one-to-one to the PSGC 2Q 2026 `Correspondence Code` for all 1,612 units, but only after left-padding it to 6 digits. Every unit has 15 values for the three years except Kalayaan. Watch for the missing highly urbanized cities, unit labels that are wrong in places, a 2021 standard error problem in CALABARZON, wide uncertainty in many small units, and a definition and method that the workbook does not state (the PSA press release 2026-43 supplies them in part). The 2023 values reproduce the press release's figures exactly (X-2).

## Observed findings

Each check prints under its ID when the script runs.

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | One sheet, wide by year, with a 5-row merged header and a footer | Sheet `2023_NoHUC_Maguindanao grouped`, range A1:S1641, 5 header rows, data rows 6 to 1635, footer rows 1636 to 1641 (3 footnotes and a source line). No hidden rows, no formulas. Column S has values 0 but sits in the filter range | The sheet cannot be read as a plain table | Read rows 6 to before `Notes:`; build column names from the header levels; ignore column S |
| O-2 | `PSGC ID` is unique but lost its leading zeros | 1,612 unit rows: 0 blank, 0 non-numeric, 0 duplicates (also 0 after padding). Length 5 digits: 1,073, 6 digits: 539. All 1,612 ID cells are stored as numbers, so a leading zero cannot be kept. The padded 6-digit form is the intended code: it matches the PSGC `Correspondence Code` for 1,612 of 1,612 rows (X-1). 5-digit IDs cover regions 01 to 09 (for example Region I 125, Region III 128) | A text join or a join to a 6-digit prefix fails for 2 of 3 rows | Read as text and left-pad to 6 digits with zeros; assert length 6 |
| O-3 | Region banner rows and province labels are inconsistent | 18 region banner rows (no ID). Province label on 85 unit rows (84 distinct). One label is `(Continued)` (row 1551, ID `153623`, Pualas). `Lanao del Sur` appears as two consecutive groups. Rows 1491 to 1497 (Barobo to Carrascal, codes `1668xx`) sit under `Surigao del Norte`; PSGC names province `1668` as Surigao del Sur (X-1). Maguindanao del Norte and del Sur share code `1538` | Province from the labels is wrong for at least 8 rows | Derive the province from the padded ID prefix and PSGC, not from the labels |
| O-3 | Negros Island Region has two region prefixes | Region label to first two digits of the ID: Negros Island Region 06: 31 rows and 07: 31 rows. Also NCR is `13` (14 rows), CAR `14`, BARMM `15`, Caraga `16`, MIMAROPA `17` | Region cannot be taken from the ID for these rows | Use the banner label, or map ID prefixes to regions by table |
| O-4 | Units by region and province code | 1,612 unit rows: NCR 14, CAR 76, Region I 125, II 93, III 128, IV-A 141, IV-B 72, V 114, VI 100, Negros Island Region 62, VII 98, VIII 142, IX 70, X 91, XI 48, XII 48, Caraga 72, BARMM 118. 82 distinct province codes | Counts to assert on each reload | Assert 1,612 unit rows and 18 banner rows |
| O-5 | One unit has no estimates | Row 641, ID `175321`, Kalayaan (Palawan): all 15 value columns blank, footnote 3 explains that it was excluded in 2018 because it was a government-regulated island. The other 1,611 rows have all 15 filled and 0 non-numeric values. Banner rows have no values | Null must not become zero | Keep null with a reason code `no_estimate` |
| O-6 | Precision differs between years and measures | 2018: poverty incidence has 2 decimals for all 1,611, CV 1,563 with 2 decimals. 2021 and 2023: poverty incidence has 4 decimals (0 with 2 decimals), CV, SE and limits mostly full precision (for example lower limit 2023 `-2.4063453271442992E-2`). 2018 standard error: 794 of 1,611 with 2 decimals | Extra digits do not add information; equality checks on values differ by year | Do not round on load; round only for display |
| O-7 | Three lower limits are zero or negative | 2018 `12801` Adams: 0 (estimate 5.62, CV 80.25). 2021 `133913` Port Area: 0. 2023 `20903` Ivana: -0.0241. No estimate outside its interval, no upper limit over 100 | Percent cannot be below 0. Zero is probably a floor and the negative value is not | Clip or flag; keep the raw value in Bronze |
| O-8 | Standard error, CV and interval do not agree in some rows | Tolerance 0.05. 2018: 6 rows where SE differs from incidence x CV / 100, 3 where interval half-width / 1.645 differs from SE, and 11 where it differs from incidence x CV / 100. 2021: 133 rows where SE differs from incidence x CV / 100 and 133 where the interval differs from SE, all in Region IV-A (CALABARZON): 133 of 141 rows, in provinces 0410, 0421, 0434, 0456, 0458. 2023: 1 row (`45635` Plaridel, difference 1.20). In 2021 the interval agrees with incidence x CV in every row | The 2021 standard error column is not reliable for CALABARZON. Users who use SE for tests get different answers | Use CV and interval for 2021; flag the 133 rows. Ask the publisher |
| O-9 | Many estimates are imprecise | CV over 20: 2018 171 (10.6%), 2021 84 (5.2%), 2023 156 (9.7%) of 1,611. CV over 30: 35, 17, 36. CV over 50: 3, 3, 4 | Ranking or thresholding small units on poverty alone is unsafe | Carry the interval and CV with every estimate; flag CV over 20 |
| O-10 | Names are not keys and have quirks | 1,397 distinct names in 1,612 unit rows; 114 names on more than one row (`San Isidro` 9, `San Jose` 9, `San Miguel` 8). 37 names carry a former name in parentheses, 16 have non-ASCII characters, 0 with leading, trailing or double spaces. Footnote 2 says Bumbaran was renamed Amai Manabilang, but row `153637` still says Bumbaran | Name joins are ambiguous | Join by ID only; use names for display and for review |

### Cross-check against PSGC 2Q 2026

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| X-1 | The ID is the first six digits of the old 9-digit PSGC | ID padded to 6 digits + `000` matches the PSGC `Correspondence Code` for 1,612 of 1,612 unit rows, none to more than one, none unmatched. Matched levels: Mun 1,484, City 114, SubMun 14. Without padding only 539 match | The join to PSGC works through the `Correspondence Code`, not the 10-digit code | Pad, append `000`, join on `Correspondence Code`, then take the 10-digit PSGC |
| X-1 | Coverage gap against PSGC | Not in this file: 33 highly urbanized cities (`City/HUC`), City of Isabela (`CC`), City of Cotabato (`ICC`), Pateros (correspondence code `137606000`), and 8 Special Geographic Area municipalities (no code). Total 35 cities and 9 municipalities. PSGC has 149 cities (114 in file) and 1,493 municipalities (1,484 in file) | No poverty value for these places; they are often large and urban | Mark as `not_in_source`. Do not impute |
| X-1 | Names differ from PSGC | 61 unit rows differ after trimming and upper-casing. Examples: `Tondo` vs `Tondo I/II`; `Licuan-Baay (Licuan)` vs `Licuan-Baay`; `Sanchez-Mira` vs `Sanchez Mira`; `City of Baliuag` vs `City of Baliwag`; `San Idelfonso` vs `San Ildefonso`; `Santo Tomas` vs `Sto. Tomas`. The `153637` row is `Bumbaran` in this file and `Amai Manabilang` in PSGC | Confirms names cannot be the join key | Use the PSGC name in the model |

### Cross-check against the PSA press release 2026-43

The release "881 Cities and Municipalities Recorded Poverty Incidence of 20 Percent or Lower in 2023" (released 6 February 2026) publishes summary figures for these estimates. The script compares them with the workbook.

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| X-2 | The workbook reproduces the press release figures | 1,611 units with a 2023 estimate (14 sub-municipalities, 114 cities, 1,483 municipalities). 2023 classes by poverty incidence (Levels 1 to 5): 881, 603, 119, 8, 0, the same as Table 1. Level 1 in 2018: 783. Units above 60 percent: 22 (2021) and 8 (2023), in Zamboanga del Norte 3, Tawi-Tawi 2, Maguindanao 2, Abra 1. Highest 2023 value: Siayan, 67.8. Share with a CV of 20 or less: 89.39%, 94.79%, 90.32% (release: 89.4, 94.7, 90.3; the 2021 figure differs by 0.1 in the second decimal) | The file is the data behind that release, and `Poverty Incidence` is on a percent scale | Cite the release for definitions; rerun X-2 when the file is replaced |

## Suspected findings

Hypotheses still to test.

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The 2021 CALABARZON standard errors were computed on a different basis than the other regions and years | Ask the publisher; compare the SE to the interval half-width / 1.645 in the CALABARZON rows | open |
| S-2 | The missing cities and municipalities are published elsewhere, not left out by mistake (`noHUC` in the file name) | Press release 2026-43 says the highly urbanized cities and the Cities of Isabela and Cotabato are excluded because their estimates are in the 2023 Official Poverty Statistics (direct estimation). That covers the 35 missing cities. For the 9 municipalities the release is silent. Suspected reason for the **8 Special Geographic Area municipalities**: they are new units with no history in the model inputs (2020 census, FIES). **Pateros:** the explanation is unverified. Test by reading the PSA methodology and the 2018 SAE release, or ask the publisher | confirmed for the 35 cities; the reasons for the 9 municipalities are suspected, not confirmed |
| S-3 | The three years are not fully comparable (method or geography may differ between rounds) | Press release 2026-43 compares 2018, 2021, and 2023 side by side (Figure 1, Table 2), but describes the 2023 method and inputs only. Ask the publisher whether 2018 and 2021 used the same method. The Technical Notes page linked from the release was not read | open |
| S-4 | The values are percent of persons (population basis), not of families | Press release 2026-43, section B: "the proportion of the population with an income below the poverty threshold" | confirmed |
| S-5 | The zero lower limits (2018, 2021) were floored at 0, while the 2023 value (-0.0241) was not | Compare rows with the smallest incidence and highest CV; ask the publisher | open |
| S-7 | The "standard deviation of an estimate" in footnote 1 is the standard error, and the 90% interval is the estimate plus or minus 1.645 standard errors | Ask the publisher for the interval method. The data supports it: half the interval width divided by 1.645 matches the standard error in all but 3 (2018), 133 (2021), and 0 (2023) rows (O-8) | open |

## Changes across files or years

Only one workbook was acquired. It holds three estimate years in wide columns, but nothing shows how the method or geography changed between them. UNVERIFIED. Observed: precision differs by year (O-6). The region structure in the file looks like current geography (Negros Island Region and the Maguindanao split appear as one table for all three years), which suggests earlier years were mapped to it; that is suspected, not confirmed, and no mapping is documented.

## Questions for the publisher or mentor

Answered by press release 2026-43 (released 6 February 2026): poverty incidence is the proportion of the population below the poverty threshold, the 2023 estimates use Small Area Estimation (Census Empirical Best/Bayes) with the 2020 census and the 2023 FIES and January 2024 LFS, and the highly urbanized cities, Isabela, and Cotabato are in the 2023 Official Poverty Statistics. The questions below are still open. Technical inquiries go to PSA's Poverty and Human Development Statistics Division, as listed on the press release.

- What is the poverty threshold value for each year (footnote 3 of the press release)?
- Are the 2018, 2021 and 2023 estimates produced with the same method, and are they comparable?
- What method produces the 90% confidence interval and the standard error?
- Are the 2021 standard errors for CALABARZON correct?
- Why are Pateros and the 8 Special Geographic Area municipalities not in the file?
- Which PSGC version is the `PSGC ID` based on? (It matches the 2Q 2026 `Correspondence Code` for all 1,612 rows, X-1.)
- Are there later revisions of this file?
