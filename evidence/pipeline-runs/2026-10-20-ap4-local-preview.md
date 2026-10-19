# Evidence (preview): AP4 builds on real data, passes its gate, and matches the metric specification's national figures

Issue #147 · local DuckDB (D-017) · 2026-10-20, Manila time (UTC+8) · run by @maeveylain · local only, **preview**, not yet run on Databricks

## The claim

At commit `b060478`, the AP4 build and gate (`etl/06_analytics/04_answer_ap4.sql`, `90_validate_ap4.sql`) turn the real `fact_city_school_age_population` (#193) and `fact_school_enrollment` (built with #196's SQL) into `ap4_school_age_enrollment_gap`: 3,288 rows, one per city or municipality member and AP4 period, 20 PASS / 3 WARN / 0 FAIL, identical on a second run. The 2024 national figures equal the metric specification's AP4 table: 27,569,038 residents aged 5 to 17, 26,375,327 learners in all sectors except Philippine Schools Overseas, and a gap of 1,193,711.

## What was run, and what it is not

On Windows 11, Python 3.14 and the project's DuckDB. A throwaway checkout combined this branch (`b060478`) with #196 (`feat/46-gold-fact-school-enrollment`), with the enrollment-fact and AP4 tasks switched on there only. `python -m src.job.local_run` ran on a copy of the local database with a scratch landing folder holding the DepEd and PSA originals and the approved SY 2020-21 enrollment archive (SHA-256 `65c400aa…`, as in the contract). The repository's `raw-data` folder was not changed.

**Preview, not full evidence.** The SY 2021-22 and 2022-23 enrollment archives are not on this laptop, so the DepEd school-to-PSGC map gate (#189) failed on exactly its four pinned counts for those two years (`profiled_2021-22_*`, `profiled_2022-23_*`, "no rows"); every other map check passed. In the scratch database only, the map candidate was published by hand and its `integration_build` run marked succeeded (the note says so in `error_message`), so `fact_school_enrollment` and AP4 could run. AP4 reads only SY 2020-21 and 2024-25, which were both loaded (60,957 and 60,129 schools). A full local or `dev` run with all six enrollment years is still needed.

Then, twice, on the same database: `10_build_fact_school_enrollment`, `90_validate_fact_school_enrollment` (110 PASS / 5 WARN / 0 FAIL both times), `04_answer_ap4`, `90_validate_ap4`.

| | Run 1 | Run 2 |
|---|---|---|
| AP4 checks: PASS / WARN / FAIL | 20 / 3 / 0 | 20 / 3 / 0 |
| Rows | 3,288 | 3,288 |
| MD5 of every row | `b92a43cb…` | `b92a43cb…` |

## Results

| Check | Expected | Actual |
|---|---|---|
| Rows 2020 / 2024 (1,642 regular + `UNKNOWN` + `EXCLUDED`) | | 1,644 / 1,644 |
| Every row equals the row rebuilt from the Gold facts (`rows_match_gold`) | 0 differ | 0 |
| Repeated or NULL keys | 0 | 0 |
| Rows outside 2020 / SY 2020-21 and 2024 / SY 2024-25 | 0 | 0 |
| Schools placed in two cities in one school year | 0 | 0 |
| School-age population and enrollment per year, AP4 = Gold | equal | equal |
| Gap, shares and 2020-to-2024 change follow their own row | 0 errors | 0 |
| Regular cities with 2024 population but no 2024 row | 0 | 0 |
| Schools left out for an incomplete offered level | | 0 |
| Learners in schools on `UNKNOWN` / `EXCLUDED` (WARN) | | 23,270 |
| School-age population on `EXCLUDED`, the 2020 SGA clusters (WARN) | | 64,929 |
| Regular rows without population (WARN): the 8 SGA municipalities in 2020, which did not exist in the census | | 8 |
| Regular cities with a negative gap (both periods) | | 761 |
| Regular cities not comparable 2020 to 2024 | | 16 |

By period and member type:

| Period | Member | Rows | Population 5–17 | Enrollment | Gap |
|---|---|---:|---:|---:|---:|
| 2020 / SY 2020-21 | regular | 1,642 | 28,615,370 | 26,193,844 | 2,461,476 |
| | `EXCLUDED` | 1 | 64,929 | 638 | 64,291 |
| | `UNKNOWN` | 1 | — | 12,430 | — |
| 2024 / SY 2024-25 | regular | 1,642 | 27,569,038 | 26,365,125 | 1,203,913 |
| | `EXCLUDED` | 1 | — | 8,172 | — |
| | `UNKNOWN` | 1 | — | 2,030 | — |

2024 in total: 27,569,038 − (26,365,125 + 8,172 + 2,030) = 1,193,711, the metric specification's figure. The specification's national row has no geography; the regular rows' 1,203,913 is larger by the 10,202 learners whose school has no city.

## Not checked

- A run with all six enrollment years and the school map gate passing (2021-22 and 2022-23 archives not on this laptop).
- Databricks `dev`: not run; it follows the next batch run once #196 merges.
- Upstream `run_id` checks: AP4 reads Gold, whose rows carry no `run_id`; lineage runs through the Gold gates.
