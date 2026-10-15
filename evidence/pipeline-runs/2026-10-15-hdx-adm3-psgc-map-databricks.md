# Evidence: the HDX ADM3 to PSGC map builds and passes its gate on Databricks, after the source-lane fan-in, with the same result as locally

Issue #93 · Databricks `dev` · 2026-10-15 · checked by @saraevcldn

## The claim

The two Integration tasks of `edu_access_pipeline` for the map, `03_map_hdx_adm3_psgc` and `90_validate_hdx_adm3_psgc_map`, run by Spark on the SQL warehouse after the source-lane fan-in `90_validate_control` (D-039), build `hdx_adm3_psgc_map` from the published `hdx_adm3_clean` and `psa_psgc_clean`: 1,642 rows, the same count per match method as the local run ([2026-10-15 local record](../reconciliation/2026-10-15-hdx-adm3-psgc-map.md)), 29 PASS, 1 WARN (the 8 Special Geographic Area units, reviewed unmatched) and 0 FAIL. The 12 reviewed overrides apply on Spark as on DuckDB. A second run on the same Silver tables and the same commit gives the same counts and results.

## What was run

The job `[dev sara_celadina] edu_access_pipeline`, deployed with `databricks bundle deploy --target dev --profile reached-hq` from the pushed branch `feat/93-hdx-adm3-psgc-map` at commit `99b03878c628e92ccc953f9fb0b7b19b736f1fdc` (the `code_revision` every Bronze task printed and every map row carries). That commit holds the map code and overrides of `adcbf0c` unchanged, plus the local evidence record. The run was announced to the team first. The job was run twice with `databricks bundle run edu_access_pipeline --target dev --profile reached-hq`. Times are Manila (UTC+8).

| | Run 1 | Run 2 |
|---|---|---|
| Job run (`job_run_id`) | `311552286952841` | `1092224191077542` |
| Whole job | 11:25:39 to 11:37:45, about 12 min, `TERMINATED SUCCESS` | 11:43:49 to 11:52:30, about 9 min, `TERMINATED SUCCESS` |
| Bronze | every load skipped (already loaded; same SHA-256), including `hdx_boundaries__2025-02-13__f682747fbb26` (1,642) and `psa_psgc__2026-Q2__31892bc2bdde` (43,768) | same |
| Silver | all six lanes built and passed their gates | same |
| `90_validate_control`, `03_map_hdx_adm3_psgc`, `90_validate_hdx_adm3_psgc_map` | succeeded | succeeded |

## Results

Gate results per run, from `pipeline_runs` (`pipeline_name = 'integration_build'`) and `data_quality_results` (`layer = 'integration'`):

| `job_run_id` | status | `code_revision` | PASS | WARN | FAIL |
|---|---|---|---:|---:|---:|
| `311552286952841` | succeeded | `99b0387…` | 29 | 1 | 0 |
| `1092224191077542` | succeeded | `99b0387…` | 29 | 1 | 0 |

The published map after run 2, by method, next to the local run:

| match_status | match_method | review_status | Databricks | Local |
|---|---|---|---:|---:|
| matched | `code` | rule | 1,480 | 1,480 |
| matched | `correspondence_code` | rule | 96 | 96 |
| matched | `name_exact` | rule | 29 | 29 |
| matched | `code_region_moved` | rule | 19 | 19 |
| unmatched | | reviewed | 8 | 8 |
| matched | `name_normalized` | rule | 6 | 6 |
| matched | `code_renamed` | reviewed | 4 | 4 |
| | | **Total** | **1,642** | **1,642** |

Content of the published map after run 2, without the run stamp:

| rows | content MD5 | `run_id` |
|---:|---|---|
| 1642 | `896447200a94591b0bc3e78a2479669e` | `1092224191077542` |

The next run on the same Silver tables should give the same MD5.

## Queries

```sql
SELECT r.job_run_id, r.status, r.code_revision,
       COUNT_IF(q.status = 'PASS') AS pass, COUNT_IF(q.status = 'WARN') AS warn, COUNT_IF(q.status = 'FAIL') AS fail
FROM edu_access.`01-control`.pipeline_runs AS r
LEFT JOIN edu_access.`01-control`.data_quality_results AS q
  ON q.run_id = r.run_id AND q.source_id = 'hdx_boundaries' AND q.layer = 'integration'
WHERE r.pipeline_name = 'integration_build' AND r.source_id = 'hdx_boundaries'
GROUP BY r.job_run_id, r.status, r.code_revision, r.started_at_utc
ORDER BY r.started_at_utc;
```

```sql
SELECT match_status, match_method, review_status, COUNT(*) AS features
FROM edu_access.`04-integration`.hdx_adm3_psgc_map
GROUP BY ALL ORDER BY features DESC;
```

```sql
SELECT COUNT(*) AS rows,
       md5(concat_ws('|', sort_array(collect_list(md5(to_json(struct(* EXCEPT (run_id, built_at_utc, code_revision)))))))) AS content_md5,
       MIN(run_id) AS run_id
FROM edu_access.`04-integration`.hdx_adm3_psgc_map;
```

## What this does not show

- The content MD5 was taken once, after run 2, so it shows run 2's content, not a comparison with run 1. Both runs read the same Silver tables at the same commit and gave the same counts and check results.
- The map did not fail on the real data, so a failing gate (a PSGC code taken twice, a bad override) and an override for a P-code missing from the release are shown by the local tests on made-up rows (`tests/test_integration_hdx.py`; full suite 710 passed, 1 skipped), not on Databricks.
- Per-task timings were not recorded.
