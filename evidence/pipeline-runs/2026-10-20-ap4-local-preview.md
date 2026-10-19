# Evidence (preview): the AP4 enrollment trend builds on real data, passes its gate, and matches the metric specification's 2024 figures

Issue #147 · D-058 · local DuckDB (D-017) · 2026-10-20, Manila time (UTC+8) · run by @maeveylain · local only, **preview**, not yet run on Databricks

## The claim

At commit `eddda3b`, the AP4 build and gate (`etl/06_analytics/04_answer_ap4.sql`, `90_validate_ap4.sql`) turn the real `fact_school_enrollment` (built with #196's SQL) and `fact_city_school_age_population` (#193) into `ap4_enrollment_trend`. The table has 6,576 rows, one per city or municipality member and school year. The gate gives 20 PASS / 4 WARN / 0 FAIL, and a second run produces identical rows. The census context on SY 2024-25 equals the metric specification's AP4 table: 27,569,038 residents aged 5 to 17, 26,375,327 learners in all sectors except Philippine Schools Overseas, and a national gap of 1,193,711.

## What was run, and what it is not

On Windows 11, Python 3.14 and the project's DuckDB. A throwaway checkout combined this branch with #196 (`feat/46-gold-fact-school-enrollment`), with the enrollment-fact and AP4 tasks switched on there only. `python -m src.job.local_run` ran on a copy of the local database, with a scratch landing folder holding:
- the DepEd and PSA originals
- the approved SY 2020-21 enrollment archive (SHA-256 `65c400aa…`, as in the contract)

The repository's `raw-data` folder was not changed.

**This is a preview, not full evidence.**
- **Two school years are missing.** The SY 2021-22 and 2022-23 enrollment archives are not on this laptop, so the table has 4 of the 6 school years: 2020-21, 2023-24, 2024-25 and 2025-26.
- **The school map gate was bypassed in scratch.** Because those two years are missing, the DepEd school-to-PSGC map gate (#189) failed on exactly its four pinned counts for them (`profiled_2021-22_*`, `profiled_2022-23_*`, "no rows"). Every other map check passed. In the scratch database only, the map candidate was published by hand and its `integration_build` run marked succeeded, with the reason in `error_message`, so that `fact_school_enrollment` and AP4 could run.
- **Effect on the output.** With two years missing, the change from the previous year on SY 2023-24 is NULL (the year before is not in the data) rather than a three-year change.

A full local or `dev` run with all six enrollment years is still needed.

On the same database, the enrollment fact (110 PASS / 5 WARN / 0 FAIL) and then AP4 were each run twice.

| | Run 1 | Run 2 |
|---|---|---|
| AP4 checks: PASS / WARN / FAIL | 20 / 4 / 0 | 20 / 4 / 0 |
| Rows | 6,576 | 6,576 |
| MD5 of every row | `f85199f9…` | `f85199f9…` |

## The trend

Enrollment in all sectors, Philippine Schools Overseas excluded:

| School year | Regular cities and municipalities | `UNKNOWN` | `EXCLUDED` | National | Schools left out (incomplete level) |
|---|---:|---:|---:|---:|---:|
| 2020-21 | 26,193,844 | 12,430 | 638 | 26,206,912 | 0 |
| 2023-24 | 27,049,274 | 4,825 | 3,745 | 27,057,844 | 0 |
| 2024-25 | 26,365,125 | 2,030 | 8,172 | 26,375,327 | 0 |
| 2025-26 | 25,874,902 | 3,043 | 8,235 | 25,886,180 | 162 |

From SY 2020-21 to 2025-26, enrollment decreases in 1,225 regular cities and municipalities and increases in 417; none is unchanged.

The latest year has 162 schools with an offered level left blank. They are left out of that year's sum (counted in `schools_incomplete`, never read as 0). 49 of the 1,225 decreasing members have such a school in SY 2025-26 (75 schools), so their label may partly reflect missing counts rather than fewer learners. The dashboard should show `schools_incomplete` beside the trend.

## Context: school-age population, census school years only

| School year | Population 5–17 (regular) | Enrollment (regular) | Gap (regular) | On `EXCLUDED` |
|---|---:|---:|---:|---|
| 2020-21 (2020 census) | 28,615,370 | 26,193,844 | 2,461,476 | 64,929 people (the 2020 SGA clusters) |
| 2024-25 (2024 census) | 27,569,038 | 26,365,125 | 1,203,913 | — |

National 2024: 27,569,038 − 26,375,327 = 1,193,711, the metric specification's figure. On SY 2023-24 and 2025-26 the census columns are NULL and `census_context` reads "not available: no census in this school year".

## Checks

| Check | Expected | Actual |
|---|---|---|
| Every row equals the row rebuilt from the Gold facts (`rows_match_gold`) | 0 differ | 0 |
| Repeated or NULL keys | 0 | 0 |
| Members without a row for every school year in the fact | 0 | 0 |
| Schools placed in two cities in one school year | 0 | 0 |
| Enrollment per school year and population per census year, AP4 = Gold | equal | equal |
| Census context outside SY 2020-21 and 2024-25 | 0 | 0 |
| Changes, shares, gap and trend follow their rows | 0 errors | 0 |
| A member with two different trends | 0 | 0 |
| Schools left out for an incomplete offered level (WARN) | | 162 |
| Learners in schools on `UNKNOWN` / `EXCLUDED`, all years (WARN) | | 43,118 |
| School-age population on `EXCLUDED` (WARN) | | 64,929 |
| Regular census rows without population (WARN): the 8 SGA municipalities in SY 2020-21, which did not exist in the 2020 census | | 8 |

## Not checked

- A run with all six enrollment years and the school map gate passing (2021-22 and 2022-23 archives are not on this laptop).
- Databricks `dev`: not run; it follows the next batch run once #196 merges.
- Upstream `run_id` checks: AP4 reads Gold, whose rows carry no `run_id`; lineage runs through the Gold gates.
