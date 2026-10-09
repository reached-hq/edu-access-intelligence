# hdx_boundaries (ADM3): Databricks dev load and idempotency, 2026-10-08

**What this shows:** on Databricks `dev`, the `bronze_hdx_boundaries` task (first in `bronze_ingest`, then in `edu_access_pipeline`) loads the approved COD-AB ADM3 file into `` edu_access.`02-bronze`.hdx_adm3_raw `` once, and every later run skips it with nothing inserted. It also confirms what only Databricks can prove for this source (D-017): serverless compute has enough memory for the 555 MB file, and rows staged in chunks of at most 64 MB go through Spark Connect.

Times are Manila time (UTC+8), with UTC in brackets.

## Setup

| | |
|---|---|
| Job | `[dev sara_celadina] bronze_ingest` (job `422293332786735`), deployed with `databricks bundle deploy --target dev --profile reached-hq` |
| Branch | `feat/84-hdx-adm3-bronze` (PR #117) |
| Commit (successful runs) | `67ea4a23d21de54f553fc7cf5cedd154c279956e`, pushed; both `git_source.git_commit` and `code_revision` |
| File | `/Volumes/edu_access/00-source/raw/admin_boundaries/phl_admin3.geojson`, SHA-256 `f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41`, 1,642 features |
| Tasks | `bronze_deped_enrollment` → `bronze_deped_facilities` → `bronze_psa_poverty_stat` → `bronze_psa_psgc` → `bronze_hdx_boundaries`, `run_if: ALL_DONE` |

## Runs

| # | Job run | Started | Commit | Result |
|---|---|---|---|---|
| 0 | `555332578823580` | 22:02:23 (14:02:23 UTC) | `c7bf11d` | `FAILED` before loading anything: `KeyError: 'job_run_id'` in `control.save_run` (see below) |
| 1 | `275546090497316` | 22:22:33 (14:22:33 UTC), ended 22:29:30 | `67ea4a2` | `SUCCESS`. Boundaries: `load`, `initial`, `succeeded`, `inserted=1642 bronze=1642` (task run `83937ddb-5965-4565-80f2-d843d275b249`). Every other source skipped, 0 inserted |
| 2 | `990080691102176` | 22:32:55 (14:32:55 UTC) | `67ea4a2` | `SUCCESS`, started from the Databricks UI. Boundaries: `skip`, 0 inserted |
| 3 | `370044913196063` | 22:41:36 (14:41:36 UTC), ended 22:45:38 | `67ea4a2` | `SUCCESS`. Boundaries: `skip`, `inserted=0 bronze=1642`, "already loaded; same SHA-256" (task run `d04563c5-88f6-40e1-9b46-5c2459f8d47e`). Every other source skipped |

Run 1 took about 7 minutes for the whole job and run 3 about 4; neither waited noticeably for compute (notebooks detached, SQL warehouse stopped).

### Run 0: why it failed, and the fix

The shared `dev` control table `pipeline_runs` had a column, `job_run_id`, added by the dev runs of another branch (`feat/47-gate-sql-tasks`, not yet merged). The store stages every column of the live table, so code that does not know that column failed at the first control write, before discovering or loading any file. Nothing was written.

Fixed by applying, unchanged, the `control.py` change from #81 (`7c0464b`, *Handle added nullable control columns*, by @mafelisilda): a control column the code does not know is staged as NULL. Runs 1 to 3 used it.

## Checks (SQL editor, after run 3)

| Check | Expected | Actual |
|---|---|---|
| Bronze rows | 1642 | 1642 |
| Pipeline duplicates | 0 | 0 |
| Feature positions | 1..1642 | 1..1642 |
| Rows without geometry | 0 | 0 |
| Largest geometry (characters) | 11727901 | 11727901 |
| Reference dates | 2025-02-13 | 2025-02-13 |
| Feature 1 code | PH0102801 | PH0102801 |
| Feature 1 `area_sqkm`, as written | 111.14398463000001 | 111.14398463000001 |
| Rows from another commit | 0 | 0 |
| Rows missing provenance | 0 | 0 |
| Batches succeeded and reconciled | 1 | 1 |
| Load attempts with 1,642 rows | 1 | 1 |
| Skip attempts with 0 rows | 2 (runs 2 and 3) | 2 |
| Checks that are not PASS | 0 | 0 |
| Checks recorded | | 28 |

Every value equals the local runs (`2026-10-08-hdx-boundaries-local-idempotency.md`).

## What it confirms (D-017)

- Serverless compute read the 555 MB GeoJSON from `/Volumes/` and held it in memory (about 1.7 GB peak locally) without failing.
- Rows staged in chunks of at most 64 MB (`max_stage_bytes`) went through Spark Connect; the largest single polygon is 11.7 MB of text.
- The Bronze table was created with the team's DDL and loaded, and the gate passed.
- A rerun inserts nothing: two later runs skipped the file and Bronze still has exactly 1,642 rows with no duplicates.

## Not shown here

A single-table commit under a real mid-load failure (D-017 item 2) was not tested, because nothing failed mid-load.

## In the `edu_access_pipeline` DAG (after #113)

After merging `main` (#113, D-020), the HDX lane was enabled in `edu_access_pipeline`: `06_create_hdx_adm3_raw` → `bronze_hdx_boundaries` (`--no-gate --no-setup`) → `90_validate_hdx_adm3_raw` as its own SQL task. One run on `dev`, job `[dev sara_celadina] edu_access_pipeline` (job `413860742211114`), run `876944030170305`, commit `e352330973d4aa44ec7b8788d9b10a642f23b89f`, 2026-10-09 08:38:23 to 08:41:58 Manila (00:38:23 to 00:41:58 UTC):

- `TERMINATED SUCCESS`; every enabled task succeeded, and the Silver tasks stayed disabled.
- `bronze_hdx_boundaries` (load run `e86490bc-5b19-4b1a-aab5-b8c95d985eaa`): `skip`, 0 inserted, `bronze=1642`, "already loaded; same SHA-256".
- `90_validate_hdx_adm3_raw`: succeeded, so the Bronze gate passed as its own task.
- Every other source skipped (enrollment 3 batches, facilities, PSGC, PSA Poverty Stat), with every gate passing.
- Tests at that commit: `python -m pytest tests -q`: 435 passed, 1 skipped.

Bronze still holds exactly the 1,642 rows loaded on 2026-10-08; this run inserted nothing.