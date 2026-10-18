# Evidence: downstream tasks start from the gates they read, and the fan-in is an audit

PR #166 · D-051 · Databricks `dev` · 2026-10-18 · checked by @hyenalouise

## The claim

With D-051, each Integration, Gold, and Analytics task depends on the gates of the tasks it reads, not on `90_validate_control`. On Databricks:

1. The only live Integration map, `04_map_deped_annex_mother`, starts as soon as the enrollment Silver gate passes, without waiting for the other lanes.
2. `90_validate_control` and `90_validate_freshness` both start once every Silver gate has finished, side by side, and freshness also waits for the EMISD Bronze gate.
3. The fan-in still writes one `silver_lane_succeeded` result per Silver lane switched on, and every result carries the commit that ran.

## What was run

The job `[dev ina_magno] edu_access_pipeline` (job `651937364323543`), deployed with `databricks bundle deploy --target dev --profile reached-hq` from a clean checkout of the pushed commit `8d3f6e88c272b4d55f1e0f04159b527065830be1` (`bundle validate` OK; 94 tasks). The job's `code_revision` parameter equals that commit. No other job run was active in the workspace when it started (`databricks jobs list-runs --active-only`). It was run once with `databricks bundle run edu_access_pipeline --target dev --profile reached-hq`. Times are Manila (UTC+8).

| | Job run `268106548429452` |
|---|---|
| Whole job | 09:28:08 to 09:36:09 (01:28:08 to 01:36:09 UTC), 8 min 1 s, `SUCCESS` |
| Tasks | 43 `SUCCESS`, 51 disabled |
| Every file | Already loaded, so each load skipped and inserted nothing |

## Results

### Run graph: the annex map hangs off the enrollment gate, and nothing waits for the fan-in

**Screenshot to add:** the **Graph** tab of run `268106548429452`, zoomed so `90_validate_deped_enrollment_clean` → `04_map_deped_annex_mother` → `90_validate_deped_annex_mother_map` and `90_validate_control` (no arrow out of it) are both visible.

### 1. The annex map does not wait for other lanes

| Task | Start | End |
|---|---|---|
| `90_validate_deped_enrollment_clean` | 09:32:42 | 09:33:42 |
| `04_map_deped_annex_mother` | **09:33:43** | 09:33:48 |
| `90_validate_deped_annex_mother_map` | 09:33:48 | 09:34:00 |
| `90_validate_deped_personnel_clean` | 09:32:58 | 09:34:07 |
| `90_validate_psa_psgc_clean` | 09:32:35 | 09:33:48 |
| `06_clean_hdx_adm3` | 09:35:03 | 09:35:27 |
| `90_validate_hdx_adm3_clean` | 09:35:27 | 09:36:03 |

The annex map started one second after the enrollment Silver gate passed. The personnel and PSGC gates were still running, and HDX had not started cleaning. Under D-039 it would have waited for `90_validate_control` at 09:36:04, about two and a half minutes later.

### Run timeline: the annex map finishes while personnel, PSGC, and HDX are still running

**Screenshot to add:** the **Timeline** tab of run `268106548429452`, covering 09:32 to 09:36, with the annex map and its gate in view beside the personnel, PSGC, and HDX tasks.


### 2. The fan-in and freshness run side by side, after every lane

| Task | `run_if` | Start | End | Result |
|---|---|---|---|---|
| `90_validate_deped_enrollment_psgc_raw` (EMISD Bronze) | `ALL_SUCCESS` | 09:34:53 | 09:35:03 | `SUCCESS` |
| `90_validate_hdx_adm3_clean` (last Silver gate) | `ALL_SUCCESS` | 09:35:27 | 09:36:03 | `SUCCESS` |
| `90_validate_control` | `ALL_DONE` | 09:36:04 | 09:36:09 | `SUCCESS` |
| `90_validate_freshness` | `ALL_DONE` | 09:36:04 | 09:36:09 | `SUCCESS` |

Both started in the same second, after the last Silver gate. Freshness started after the EMISD Bronze gate, so it checked EMISD's latest batch only after that load had finished.

### Timeline: the fan-in and freshness start in the same second

**Screenshot to add:** the **Timeline** tab, 09:35 to 09:37, showing `90_validate_hdx_adm3_clean` ending and `90_validate_control` and `90_validate_freshness` starting together.


### 3. Control results for this run

On the SQL warehouse after the run (`run_id = '268106548429452'`):

| Check | Expected | Actual | Result |
|---|---|---|---|
| `silver_lane_succeeded` results | 6, one per Silver lane switched on | 6 | OK |
| … that are PASS | 6 | 6 (`deped_enrollment`, `deped_facilities`, `deped_personnel`, `hdx_boundaries`, `psa_poverty_stat`, `psa_psgc`) | OK |
| `source_fresh` results | 7, one per loaded source | 7, all PASS | OK |
| `code_revision` on every control result | `8d3f6e8…` | `8d3f6e8…` | OK |
| `pipeline_runs` for this job run | 7 `bronze_ingest`, 6 `silver_build`, all succeeded | the same | OK |
| FAIL results in this run, any layer | 0 | 0 | OK |

### Control results: 6 lane PASS and 7 freshness PASS, all at `8d3f6e8`

**Screenshot to add:** the result of query 1 below in the SQL editor, all 13 rows visible.

The run wrote 424 results: 21 Bronze, 382 Silver, 8 Integration, and 13 control, of which 414 PASS and 10 WARN. The WARNs are expected and unchanged by this PR: 2,331 annexes without a mother school (D-044), and nine PSA poverty flags (coefficient of variation over 20%, a non-positive lower limit, and SE/CV inconsistencies) for 2018, 2021, and 2023.

## Earlier runs of this branch

- Run `548256684216044` at `6386c34` (2026-10-16) showed the annex map starting one second after the enrollment gate. It was cancelled during `06_clean_hdx_adm3`, so the fan-in and freshness did not run.
- Run `1106317898727605` at `12fe065` (2026-10-16) started nine seconds after another dev run. Both recreated `edu_access.03-silver.deped_personnel_gate_summary_candidate` at once, so the personnel gate failed on `INSUFFICIENT_PERMISSIONS` while the other run briefly owned the table, and the fan-in correctly failed the run. This was a collision between runs, not a code fault. Dev jobs share the `edu_access` catalog, so only one should run at a time.

## How to reproduce

Run these on the SQL warehouse after the job run has finished, never while a run is going (D-017). For another run, replace the run id.

1. The fan-in and freshness results, expected 6 `silver_lane_succeeded` and 7 `source_fresh`, all PASS, all with `code_revision` `8d3f6e8…`:

   ```sql
   SELECT check_name, source_id, status, actual, code_revision
   FROM edu_access.`01-control`.data_quality_results
   WHERE run_id = '268106548429452' AND layer = 'control'
   ORDER BY check_name, source_id;
   ```

2. Every result in the run by layer and status, expected 21 Bronze, 382 Silver, 8 Integration, 13 control; 414 PASS, 10 WARN, no FAIL:

   ```sql
   SELECT layer, status, COUNT(*) AS results
   FROM edu_access.`01-control`.data_quality_results
   WHERE run_id = '268106548429452'
   GROUP BY layer, status
   ORDER BY layer, status;
   ```

3. The WARN rows, expected the annex count (2,331) and nine PSA poverty flags:

   ```sql
   SELECT layer, source_id, check_name, actual
   FROM edu_access.`01-control`.data_quality_results
   WHERE run_id = '268106548429452' AND status = 'WARN'
   ORDER BY layer, source_id, check_name;
   ```

4. The loads and Silver builds in the run, expected 7 `bronze_ingest` and 6 `silver_build`, all succeeded:

   ```sql
   SELECT pipeline_name, source_id, status
   FROM edu_access.`01-control`.pipeline_runs
   WHERE job_run_id = '268106548429452'
   ORDER BY pipeline_name, source_id;
   ```

5. The annex map's gate, expected 7 PASS and `annexes_without_mother_school` WARN with 2,331:

   ```sql
   SELECT check_name, status, actual
   FROM edu_access.`01-control`.data_quality_results
   WHERE run_id = '268106548429452' AND layer = 'integration'
   ORDER BY check_name;
   ```

6. Task start and end times, which the tables above come from:

   ```bash
   databricks jobs get-run 268106548429452 --profile reached-hq -o json
   ```
