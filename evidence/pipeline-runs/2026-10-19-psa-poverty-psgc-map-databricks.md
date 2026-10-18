# Evidence: the PSA poverty to PSGC map builds and passes its gate on Databricks, with the same result as locally

Issue #92 · Databricks `dev` · 2026-10-19, Manila time (UTC+8) · run by @Catweyine

## The claim

The two Integration tasks of `edu_access_pipeline` for the map, `02_map_psa_poverty_psgc` and `90_validate_psa_poverty_psgc_map`, run by Spark on the SQL warehouse right after the poverty and PSGC Silver gates (D-051), build `psa_poverty_psgc_map` from the published `psa_poverty_stat_clean` and `psa_psgc_clean`: 4,836 rows, every one matched by `Correspondence Code`, 44 PASS, 4 WARN and 0 FAIL. Every count equals the local run ([2026-10-19 local record](../reconciliation/2026-10-19-psa-poverty-psgc-map.md)).

## What was run

The job `[dev catherine_balane] edu_access_pipeline` (job `268191948913843`), deployed with `databricks bundle deploy --target dev --profile reached-hq` from the pushed branch `feature/psa-poverty-psgc-map` at commit `e36725be0e3410cd2bc6a71ca19e76ac70be0957` (the `code_revision` on the run record and every map row), then run with `databricks bundle run edu_access_pipeline --target dev --profile reached-hq`.

| | Run 1 |
|---|---|
| Job run (`job_run_id`) | `77367722346520` |
| Whole job | 02:30:01 to 02:58:53, about 29 min (tasks waited for the workspace limit of 5 active runs), `TERMINATED SUCCESS` |
| `bronze_psa_psgc`, `bronze_psa_poverty_stat` | succeeded (02:44 to 02:48) |
| Poverty and PSGC Silver builds and gates | succeeded |
| `02_map_psa_poverty_psgc` | succeeded, 02:53:13 to 02:53:46 |
| `90_validate_psa_poverty_psgc_map` | succeeded, 02:53:46 to 02:56:33 |
| `06_build_dim_city_poverty`, `90_validate_dim_city_poverty` | disabled (Gold not built: D-048) |

## Results

From `pipeline_runs` (`pipeline_name = 'integration_build'`, `source_id = 'psa_poverty_stat'`) and `data_quality_results` (`layer = 'integration'`):

| `job_run_id` | status | `code_revision` | PASS | WARN | FAIL |
|---|---|---|---:|---:|---:|
| `77367722346520` | succeeded | `e36725b…` | 44 | 4 | 0 |

| Check | Databricks | Local |
|---|---:|---:|
| `rows_reconcile` | 4,836 | 4,836 |
| `psgc_code_taken_once` (matched codes) | 4,836 | 4,836 |
| `psgc_name_matches_unit` | 0 | 0 |
| `estimates_unchanged` | 0 | 0 |
| `match_rate_percent` | 100.00 | 100.0 |
| `names_differ` (WARN) | 183 | 183 |
| `psgc_units_not_in_source_2018` / `_2021` / `_2023` (WARN) | 44 / 44 / 44 | 44 / 44 / 44 |
| `not_in_source_huc_2023` | 33 | 33 |
| `not_in_source_without_correspondence_code_2023` | 8 | 8 |
| `not_in_source_other_2023` | 3 | 3 |
| `not_in_source_with_sub_municipality_rows_2023` | 1 | 1 |
| `sub_municipality_rows_2023` | 14 | 14 |
| `no_estimate_rows_2023` | 1 | 1 |

The published map, the same in each estimate year (2018, 2021, 2023):

| match_status | geographic_level | estimate_status | names_agree | Rows per year |
|---|---|---|---|---:|
| matched | `city_mun` | estimated | true | 1,537 |
| matched | `city_mun` | estimated | false | 60 |
| matched | `city_mun` | no_estimate | true | 1 |
| matched | `sub_mun` | estimated | true | 13 |
| matched | `sub_mun` | estimated | false | 1 |
| | | | **Total** | **1,612** |

Content of the published map after run 1, from the last query below:

| rows | content MD5 |
|---:|---|
| 4836 | `bde441c0eaad9bb0b1d4e94e9caefaee` |

A rerun on the same Silver tables should give the same MD5.

## Queries

```sql
SELECT run_id, status, COUNT(*) AS checks
FROM edu_access.`01-control`.data_quality_results
WHERE source_id = 'psa_poverty_stat' AND layer = 'integration'
GROUP BY ALL ORDER BY run_id, status;

SELECT run_id, status, code_revision, failure_stage
FROM edu_access.`01-control`.pipeline_runs
WHERE pipeline_name = 'integration_build' AND source_id = 'psa_poverty_stat'
ORDER BY started_at_utc;

SELECT estimate_year, match_status, geographic_level, estimate_status, names_agree, COUNT(*) AS n
FROM edu_access.`04-integration`.psa_poverty_psgc_map
GROUP BY ALL ORDER BY ALL;

SELECT COUNT(*) AS n,
       md5(concat_ws('|', sort_array(collect_list(concat_ws(',', source_row_ref, coalesce(psgc_code, ''), match_status,
           coalesce(CAST(poverty_incidence AS STRING), '')))))) AS content_md5
FROM edu_access.`04-integration`.psa_poverty_psgc_map;
```

## Not checked

- A second Databricks run (rerun on the same input). The local job was run twice with identical content ([local record](../reconciliation/2026-10-19-psa-poverty-psgc-map.md)).
- A failing candidate on Databricks: the gate's publish-only-on-pass path is covered by the local tests (`tests/test_integration_poverty.py`), not by a deliberately broken Databricks run.
