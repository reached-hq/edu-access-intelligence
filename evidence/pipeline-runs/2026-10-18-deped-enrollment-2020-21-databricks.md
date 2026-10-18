# Evidence: DepEd enrollment SY 2020-21 loads on Databricks `dev` as a backfill, Silver passes every check, and a second run inserts nothing

Issue #170 (part of #43) · Databricks `dev` (D-017) · 2026-10-18, Manila time (UTC+8) · run by @hyenalouise

## The claim

On Databricks `dev`, the job `edu_access_pipeline` loads the SY 2020-21 enrollment delivery into the existing `deped_enrollment_raw` table as a `backfill`, leaving the three years already loaded untouched. Silver rebuilds all four years and passes all 153 gate checks, with the same counts as the [local run](../reconciliation/2026-10-16-deped-enrollment-2020-21-bronze-to-silver.md). Running the job again skips all four deliveries and inserts nothing.

## What was run

1. **File move.** After #171 and #172 merged, the three files in `raw/_holding/deped/2026-10-16/` (`Enrollment-in-SY-2020-2021.zip`, `SHA256SUMS.txt`, `RETRIEVED.txt`) were copied to `/Volumes/edu_access/00-source/raw/deped/2026-10-16/` with `databricks fs cp`. The copied zip was downloaded back and hashed: `65c400aa31ba63730b8f9a7b4d60ade91c6a29cdb34a3c6bf255e5fc9e91a241`, equal to the contract and to the folder's `SHA256SUMS.txt`; `RETRIEVED.txt` also matched its listed hash. The holding folder was then removed, so `raw/_holding/deped/` is empty.
2. **Deploy.** `databricks bundle validate` and `databricks bundle deploy --target dev` from a clean checkout of `main` at `df63d635c3cb73873d4ad70d195f9724ab83624a`. `databricks bundle summary` showed both `git_source.git_commit` and the `code_revision` parameter equal to that commit. No other job run was active.
3. **Runs.** `databricks bundle run edu_access_pipeline --target dev`, twice.

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `146052617753176` | `250134607484273` |
| Job start → end (UTC) | 2026-10-18 03:43:23 → 04:02:12 | 2026-10-18 04:03:11 → 04:11:42 |
| Job result | `SUCCESS`: 43 enabled tasks succeeded, 26 disabled | `SUCCESS`: 43 enabled tasks succeeded, 26 disabled |
| `bronze_deped_enrollment` (UTC) | `SUCCESS`, 03:51:50 → 03:54:49 | `SUCCESS`, 04:03:59 → 04:05:31 |
| `90_validate_deped_enrollment_raw` (UTC) | `SUCCESS`, 03:54:50 → 03:55:16 | `SUCCESS`, 04:05:31 → 04:05:54 |
| `01_clean_deped_enrollment` (UTC) | `SUCCESS`, 03:55:16 → 03:56:15 | `SUCCESS`, 04:05:54 → 04:06:52 |
| `90_validate_deped_enrollment_clean` (UTC) | `SUCCESS`, 03:56:15 → 03:58:53 | `SUCCESS`, 04:06:53 → 04:09:08 |
| Ingestion `run_id` | `1c504726-f1d2-4b4c-a5bf-6fa41507c4a3` | `97c1baca-29c6-43e6-bda1-67cae03a040c` |

The job-run and task rows come from `databricks jobs get-run`. The queries below ran on the job's SQL warehouse through the Statement Execution API after run 2.

## Results

### Bronze

The loader's output for `bronze_deped_enrollment`:

| Batch | Run 1 | Run 2 |
|---|---|---|
| `deped_enrollment__2020-21__65c400aa31ba` | `load`, `backfill`, inserted 60,957 | `skip`, inserted 0 |
| `deped_enrollment__2023-24__a10f4d0f9082` | `skip`, inserted 0 | `skip`, inserted 0 |
| `deped_enrollment__2024-25__fd5dd74a62b8` | `skip`, inserted 0 | `skip`, inserted 0 |
| `deped_enrollment__2025-26__ab4d7e24b3a4` | `skip`, inserted 0 | `skip`, inserted 0 |

```sql
SELECT school_year, delivery_version, COUNT(*) AS rows
FROM edu_access.`02-bronze`.deped_enrollment_raw GROUP BY ALL ORDER BY 1, 2;
```

| `school_year` | `delivery_version` | rows |
|---|---:|---:|
| 2020-21 | 1 | 60,957 |
| 2023-24 | 1 | 60,167 |
| 2024-25 | 1 | 60,129 |
| 2025-26 | 1 | 60,204 |

The SY 2020-21 batch's attempts, in run order: `load` / `succeeded` / 60,957 rows (run 1), then `skip` / `skipped` / 0 (run 2). The three later years' counts equal the [2026-10-06 record](2026-10-06-deped-enrollment-idempotency.md), so the backfill inserted only SY 2020-21.

### Checks

```sql
SELECT r.job_run_id, d.layer, d.status, COUNT(*)
FROM edu_access.`01-control`.data_quality_results AS d
JOIN edu_access.`01-control`.pipeline_runs AS r ON r.run_id = d.run_id AND r.source_id = d.source_id
WHERE d.source_id = 'deped_enrollment' AND r.job_run_id IN ('146052617753176', '250134607484273')
GROUP BY ALL ORDER BY 1, 2, 3;
```

| Layer | Run 1 (PASS / WARN / FAIL) | Run 2 (PASS / WARN / FAIL) |
|---|---|---|
| Bronze (batch checks for the one load, `approved_deliveries_present`, and the gate's 3) | 15 / 0 / 0 | 4 / 0 / 0 (skips write no batch checks) |
| Silver gate | 153 / 0 / 0 | 153 / 0 / 0 |
| Control | 2 / 0 / 0 | 2 / 0 / 0 |

Both runs' `bronze_ingest` and `silver_build` rows in `pipeline_runs` are `succeeded`.

### Silver

The verification query in [Silver, Running on Databricks](../../docs/operations/silver.md#running-on-databricks), with `<commit that ran>` set to `df63d635c3cb73873d4ad70d195f9724ab83624a`, returned `OK` on all 22 rows:

| Check | Expected | Actual |
|---|---|---|
| clean rows SY 2020-21 / 2023-24 / 2024-25 / 2025-26 | 60957 / 60167 / 60129 / 60204 | same |
| quarantined rows | 0 | 0 |
| repeated keys | 0 | 0 |
| learners SY 2020-21 / 2023-24 / 2024-25 / 2025-26 | 26227022 / 27081292 / 26400182 / 25935863 | same |
| blank SHS counts kept NULL, SY 2025-26 | 47352 | 47352 |
| absent v2 column NULL in v1 rows | 181253 | 181253 |
| standard labels, school_management, SY 2025-26 | 9 | 9 |
| Local Government kept, SY 2020-21 | 154 | 154 |
| mangled `Ã‘` left | 0 | 0 |
| overseas flagged | 137 | 137 |
| no counts published, SY 2025-26 | 46 | 46 |
| checks in the last run / not PASS | 153 / 0 | 153 / 0 |
| rows from the last run | 241457 | 241457 |
| rows from another commit | 0 | 0 |
| last silver run | succeeded | succeeded |
| silver runs succeeded at this commit | 2 | 2 |
| published rows from a succeeded run | 241457 | 241457 |
| candidate rows not published | 0 | 0 |

SY 2020-21 `school_management` in Silver: DepEd 47,252; Non-Sectarian 9,496; Sectarian 3,758; SUC 210; Local Government 154; LUC 37; PSO 33; DOST 13; International School 2; Other GA 2. This is the same breakdown as the local run.

## What this does not prove

- Byte-level equality with the local Silver content. The local record compares MD5 hashes; this record compares counts, learners, labels, and flags, as the earlier Databricks records do.
- Quarantine on real data: no real row is quarantined.
- That `Local Government` schools were managed differently from `DepEd` schools (see the local record).

## How to reproduce

From a clean checkout of `df63d63`, deploy with `databricks bundle deploy --target dev`, run `databricks bundle run edu_access_pipeline --target dev` (a third run should skip all four deliveries), and run the queries above in a notebook or through the SQL warehouse.
