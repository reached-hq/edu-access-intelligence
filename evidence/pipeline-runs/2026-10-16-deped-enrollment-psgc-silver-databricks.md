# Evidence: the DepEd school-to-PSGC crosswalk builds and passes its Silver gate on Databricks `dev`, in two clean job runs

Issue #163 · Databricks `dev` (D-017) · 2026-10-16, Manila time (UTC+8) · run by @maeveylain

## The claim

On Databricks `dev`, the job `edu_access_pipeline`, deployed from `feat/163-silver-deped-enrollment-psgc`, runs the crosswalk lane end to end in two separate job runs: Bronze load (skipped, already loaded), Bronze gate, Silver build `07_clean_deped_enrollment_psgc`, and Silver gate `90_validate_deped_enrollment_psgc_clean`. Both gates passed, so both runs published the tables. The source-lane fan-in `90_validate_control` passed in both runs, with the new lane included.

**Not claimed:** anything about the published table's contents on `dev`. The SQL checks of the tables (row counts, gate results, sample rows) were not run on `dev`; see "Not checked here". The contents are evidenced locally on the same Bronze batch ([local reconciliation](../reconciliation/2026-10-16-deped-enrollment-psgc-bronze-to-silver.md)).

## What was run

- Job `[dev maeve_lumague] edu_access_pipeline` (job ID `921726647955407`), deployed with `databricks bundle deploy --target dev` from a clean checkout of the branch at `2bcd6852b9d3c9d699190c56e993a6e6355b4661`. Every ingestion task of run 3 reports `code_revision=2bcd6852b9d3c9d699190c56e993a6e6355b4661`.
- No new raw file: the EMISD workbook was already in `/Volumes/edu_access/00-source/raw/deped/` from #152.
- Started three times with `databricks bundle run edu_access_pipeline --target dev`. Task states and times below come from `databricks jobs get-run`.

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Job run | `1094635918316055` | `302526353474448` | `737211160986857` |
| Start → end (UTC) | 13:25:24 → 13:36:48 | 13:37:54 → 13:48:44 | 13:52:45 → 14:00:28 |
| Job result | **SUCCESS**: 45 tasks succeeded, 26 disabled | FAILED (see below) | **SUCCESS**: 45 tasks succeeded, 26 disabled |
| `07_create_deped_enrollment_psgc_raw` | SUCCESS | SUCCESS | SUCCESS |
| `bronze_deped_enrollment_psgc` | SUCCESS | SUCCESS | SUCCESS: `skip`, "already loaded; same SHA-256", 0 inserted, Bronze 60,285 |
| `90_validate_deped_enrollment_psgc_raw` | SUCCESS | SUCCESS | SUCCESS |
| `07_clean_deped_enrollment_psgc` (Silver build) | SUCCESS, 13:34:38 → 13:35:23 | SUCCESS, 13:46:36 → 13:47:17 | SUCCESS, 13:58:53 → 13:59:12 |
| `90_validate_deped_enrollment_psgc_clean` (Silver gate) | SUCCESS, 13:35:23 → 13:36:23 | SUCCESS, 13:47:17 → 13:48:26 | SUCCESS, 13:59:12 → 13:59:44 |
| `90_validate_control` (fan-in) | SUCCESS | FAILED | SUCCESS |

The Silver gate stops with `raise_error` on any FAIL check before it publishes, so a gate task that succeeds means its build passed every FAIL check (D-025).

In run 3, every other source's load also skipped its already-loaded files (enrollment three school years, facilities, personnel, PSGC, poverty, HDX), and every other Silver gate succeeded.

### Run 2: a collision with another `dev` job, not this lane

Run 2 failed in two other lanes:

- `01_clean_deped_enrollment` failed with `DELTA_METADATA_CHANGED` on `deped_enrollment_clean_candidate`. The conflicting commit came from another user's `dev` job (job `651937364323543`, task run `801385116721503`, 13:40:34 → 13:41:36), which rebuilt the same table while this run's build (13:40:26 → 13:41:12) was writing it. Every `dev` job writes the same `edu_access` tables.
- `90_validate_deped_personnel_clean` failed with "1 FAIL result(s)" (13:41:35 → 13:45:26), in the same window. Which check failed was not queried; the same collision is the likely cause.
- The fan-in then failed because those two lanes did not succeed. In the same run, the crosswalk lane's four tasks all succeeded.

Run 3 was started after the other job had finished, and succeeded throughout. Runs 1 and 3 are the two clean runs.

## Not checked here

- **The published tables on `dev`:** row counts (expected 60,273 clean, 2 quarantined, from the local evidence), the gate's 28 results per run, the two quarantined rows, sample rows, and whether runs 1 and 3 published identical content. These need SQL warehouse queries, which were not run. Locally, two builds on the same batch gave identical content (SHA-256 `dbf4fa1e…`).
- Table ownership by `reached-hq` on the new Silver tables.
- The failed check in run 2's personnel gate.
