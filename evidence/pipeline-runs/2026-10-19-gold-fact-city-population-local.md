# Evidence: fact_city_population builds and passes its gate locally on real data

Issue #46 · local DuckDB · 2026-10-19, Manila time (UTC+8) · run by @Catweyine

## The claim

`13_build_fact_city_population.sql` and `90_validate_fact_city_population.sql`, run on the real published `psa_psgc_clean` (PSGC 2Q 2026) and the regular cities and municipalities, build 1,642 rows for 2024, every one `available`. They total 112,727,776, the same as Silver's cities and municipalities and as its 18 regions (profile O-4). The gate records 19 PASS, 0 WARN, 0 FAIL and publishes. A second run gives the same table. **Observed**, local only: not yet run on Databricks.

## What was run

- A copy of the local database `local_state/poverty_check.duckdb` (not committed), which holds the published `psa_psgc_clean` of Silver run `0eed74ff-d307-46ea-a35c-c2653c95830a` (`silver_build` succeeded in `pipeline_runs`).
- **Stand-in for `dim_city_municipality`:** #193, which builds it, is not merged. Its regular members are the master quarter's `City` and `Mun` rows (149 + 1,493 = 1,642), so the stand-in held exactly those rows plus `UNKNOWN` and `EXCLUDED`, the only columns this build reads (`city_mun_psgc_code`, `member_type`). This run proves the population rules, not #193's dimension.
- The build and gate SQL of this branch, through `DuckDBStore.run_file` with the job's parameters, as the job's two SQL tasks run them. Run twice.

## Results

| Check | Expected | Run 1 | Run 2 |
|---|---:|---:|---:|
| `rows_reconcile` | 1,642 | 1,642 | 1,642 |
| `total_equals_psgc` | 112,727,776 | 112,727,776 | 112,727,776 |
| `total_equals_regions` | 112,727,776 | 112,727,776 | 112,727,776 |
| `members_without_population` | 0 | 0 | 0 |
| `members_with_zero_population` | count | 0 | 0 |
| `population_equals_psgc`, `keys_in_dimension`, `regular_members_present`, `key_unique` | 0 | 0 | 0 |
| PASS / WARN / FAIL | | 19 / 0 / 0 | 19 / 0 / 0 |
| MD5 of the published table, ordered by key | | `7a422d47bbc6458fae8abd4933d96ef8` | `7a422d47bbc6458fae8abd4933d96ef8` |

Spot checks: City of Isabela `0990101000` 151,297; City of Manila `1380600000` 1,902,590 (its 14 districts are not added again); Kapalawan `1999901000` (Special Geographic Area) 29,191. The only `#N/A` population in PSGC is on the blank-level container `0990100000` "City of Isabela (Not a Province)", which is not a member, so no city or municipality is `missing`. The metric specification's note that "Isabela City has no 2024 population in PSGC" refers to that container row; the city row has one (observed).

## What this does not show

- A Databricks `dev` run. The tasks are enabled, but they wait for `90_validate_dim_city_municipality` (#193).
- #193's real `dim_city_municipality`. The stand-in has its regular members by its rule, not its build.
- The `missing` path on real data: no member has it today. `tests/test_gold_fact_city_population.py` covers it on made-up rows, as well as a published 0, a negative value, a NULL with an unknown reason, a member not in PSGC, and a Silver run that did not succeed.
