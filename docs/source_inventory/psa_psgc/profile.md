# psa_psgc: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-09-29 |
| Profiled by | @maeveylain |
| Tool | DuckDB 1.4.5 (Python), run locally: [`notebooks/profiling/profile_psgc.py`](../../../notebooks/profiling/profile_psgc.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if the file's checksum differs |
| How files were read | Sheet `PSGC` of the original xlsx, read with the standard library and loaded into DuckDB with every column as text (`all_varchar`), strict CSV parsing. Sheets `National Summary` and `Notes` were read for cross-checks |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_psgc.py
```

The file must be at `$RAW_DATA_DIR/psa/original/PSGC-2Q-2026-Publication-Datafile.xlsx`. The column statistics in [data_dictionary.md](data_dictionary.md) come from `notebooks/profiling/dictionary_psgc.py`.

## Summary

Usable as the geographic reference for the project. `10-digit PSGC` is a clean, unique key, every barangay and municipality has its parent in the file, and unit counts and regional populations reconcile with the workbook's own `National Summary`. Watch for a small set of special rows (Special Geographic Area, City of Isabela) that lack a level or code, several undocumented columns, and codes that must be read as text to keep leading zeros.

## Observed findings

Each check prints under its ID when the script runs.

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | `10-digit PSGC` is clean and unique | 43,768 rows: 0 blank, 0 not 10 characters, 0 non-numeric, 0 duplicates, 0 fully duplicated rows. 29,620 ids start with `0` (e.g. Region IX is `0900000000`) | Safe primary key, but only as text | Read as string everywhere; assert uniqueness and length 10 in Bronze validation |
| O-2 | 2 rows have a blank `Geographic Level` | `0990100000` City of Isabela (Not a Province), population `#N/A`; `1999900000` Special Geographic Area, population 214,703, no correspondence code | Level counts and level-based filters skip these rows | Flag both; assign an explicit level only with a documented rule |
| O-2 | `Notes` legend does not match the data | Legend lists `Reg, Prov, Mun, Bgy, Dist, SubMun`. `Dist` has 0 rows; `City` (149 rows) is not in the legend | Level list must come from the data, not the legend | Use the observed six values plus blank; record in the mapping |
| O-3 | `Correspondence Code` is blank for 50 rows | By level: Bgy 38, Mun 8, Prov 2, blank level 1, Reg 1. Provinces: Maguindanao del Norte and del Sur; region: Negros Island Region. All 43,718 filled values are unique and 9 digits | Cannot be used as a complete key. Code is not explained in the `Notes` sheet | Do not join on it; ask the publisher what it means (see Questions) |
| O-4 | One population cell is not a number, and 12 barangays have 0 | `0990100000` City of Isabela: `#N/A`. Zero population: 12 rows, all barangays | `#N/A` breaks numeric typing | Cast with a safe cast, keep `#N/A` rows flagged, treat 0 as a value to review, not a missing value |
| O-4 | Regional populations reconcile with the national total | Sum of 18 regions 112,727,776; `National Summary` 112,729,484; difference 1,708, which is the count of Filipinos abroad stated in `Notes` D.2 | Population does not add up to national by design | Never compare a sum of units to the national figure without this adjustment |
| O-5 | Unit counts match the `National Summary` sheet | Provinces 82, cities 149, municipalities 1,493, barangays 42,010: all four match | The file is complete relative to its own summary | Assert these counts after each quarterly load |
| O-6 | Column J has no header and holds footnotes | 19 rows: provinces 16, regions 2, barangays 1. Text such as "(excluding CITY OF BAGUIO) " and markers `1/`, `2/`, `3/` | Looks like data but is annotation. Provincial population excludes component cities | Exclude from the model; keep a note that province populations exclude some cities |
| O-7 | `Income Classification` has non-class values | 8 municipalities in the Special Geographic Area are `-`; 6 municipalities have a starred class (`2nd*` 2, `3rd*` 2, `4th*` 2), e.g. Mankayan, Arteche, Lugait. Filled only on provinces, cities, municipalities (0 elsewhere) | A category with 9 spellings for 5 classes | Split into `class` and `retained_after_downgrade`; map `-` to unknown |
| O-8 | `Urban / Rural` is `-` for 38 barangays, and all 38 have no correspondence code | Values: R 34,054, U 7,918, `-` 38. The 38 with `-` are exactly the 38 barangays with a blank `Correspondence Code` (0 others). `-` includes 6 Caloocan barangays, so not every NCR barangay is `U` despite `Notes` C | Urban share must state its denominator | Report unknown separately; do not fold into rural |
| O-9 | Names are not keys and have trailing spaces | 27,391 distinct names in 43,768 rows; 4,041 barangay names occur more than once (e.g. `Poblacion` 607 times). 2,855 names end in a space, 2,846 of them on rows with a `Status` value; no leading or double spaces | Name joins are ambiguous and space-sensitive | Trim names in Silver; match only within a parent code |
| O-10 | The hierarchy is complete in the file | 0 barangays without their city or municipality (first 7 digits + `000`); 0 provinces, cities, or municipalities without their region; 0 non-NCR municipalities without their province | Parent lookups by code prefix are safe | Derive region, province, and city or municipality from the code and assert it; handle NCR (no provinces) and the special rows explicitly |
| O-11 | `Old names` is sparse | 1,699 rows filled (barangays 1,618, municipalities 75, cities 3, provinces 3), 1,439 distinct | Only a partial record of past names | Use for name matching to older sources, not as a full history |
| O-12 | `Status` marks capitals and poblaciones | `Pob.` 2,773 (all barangays); `Capital` 82 (cities 45, municipalities 37) | Only these two values exist | Keep as category; leave blank as blank |
| O-13 | Two header cells contain line breaks | Headers of `Income Classification` and `Urban / Rural` include `\n` | Column names break naive parsers | Normalize header whitespace when loading |

## Suspected findings

Hypotheses still to test.

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The 38 barangays with `-` urban/rural and no correspondence code are new or split barangays created after the 2020 census (9 of 38 record an old name, e.g. `Muzon` split into East, South, West) | Compare with the previous PSGC quarter and the RA creating each barangay; check the other 29 for creation notes | open |
| S-2 | `Correspondence Code` is the older 9-digit PSGC code kept for continuity | Compare with the PSA page or the prior PSGC publication; ask the publisher | open |
| S-3 | The Special Geographic Area rows (`19999...`, 8 municipalities) are not in a province, which is why they have no income class or correspondence code | Read the PSA notes on the Special Geographic Area and the Bangsamoro transfer | open |
| S-4 | DepEd place names will match PSGC names only after trimming, case changes, and parent scoping | Match rates in `docs/profiling/` (cross-source work) | open |

## Changes across files or years

Only the 2Q 2026 publication was acquired, so no comparison across quarters is possible. Codes and names change when local government units are created, merged, or renamed, so each quarterly file should be compared with the last before replacing it.

## Questions for the publisher or mentor

- What is the `Correspondence Code` and why is it blank for new units?
- Should the Special Geographic Area rows be treated as provinces, municipalities, or excluded from level counts?
- Is there an official list of changes between quarterly publications (new, renamed, and merged units)?
- Which PSGC quarter do the DepEd 2023-24 to 2025-26 files use for place names?
