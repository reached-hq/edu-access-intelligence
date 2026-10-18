# Evidence: the DepEd school-to-PSGC crosswalk builds, reconciles, and passes its Silver gate on Databricks `dev`, with the same result in every run

Issue #163 · Databricks `dev` (D-017) · 2026-10-16, Manila time (UTC+8) · run by @maeveylain

These runs are of commit `2bcd685`, before the review changes of 2026-10-18 (row-level reconciliation, published coordinate text, the empty-batch FAIL, and the guarded Sulu recode). The gate then had 28 checks; the runs of the reviewed code are recorded separately.

## The claim

On Databricks `dev`, the job `edu_access_pipeline`, deployed from `feat/163-silver-deped-enrollment-psgc`, runs the crosswalk lane end to end in two separate job runs: Bronze load (skipped, already loaded), Bronze gate, Silver build `07_clean_deped_enrollment_psgc`, and Silver gate `90_validate_deped_enrollment_psgc_clean`. Both gates passed, so both runs published the tables. The source-lane fan-in `90_validate_control` passed in both runs, with the new lane included. The published tables reconcile to Bronze (60,275 = 60,273 + 2), and every run of the lane recorded the same 27 PASS and 1 WARN, with each profiled count equal to the rules file.

**Not claimed:** row-by-row identity of the published content between runs on `dev`. It is shown by equal counts on every rule, and locally by identical content hashes ([local reconciliation](../reconciliation/2026-10-16-deped-enrollment-psgc-bronze-to-silver.md)).

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
- `90_validate_deped_personnel_clean` failed with "1 FAIL result(s)" (13:41:35 → 13:45:26). **Observed:** the failure, and that it ran in the same window as the other job. **Suspected:** the concurrent shared-table rebuild caused it. The specific failed check was not queried, so the cause is unverified.
- The fan-in then failed because those two lanes did not succeed. In the same run, the crosswalk lane's four tasks all succeeded.

Run 3 was started after the other job had finished, and succeeded throughout. Runs 1 and 3 are the two clean runs.

## The published tables (SQL, after run 3)

Queried in a notebook on 2026-10-17 at 00:11–00:12 Manila (2026-10-16 16:11–16:12 UTC), after checking no other job was running (screenshots kept by @maeveylain).

**Reconciliation**

```sql
SELECT
  (SELECT COUNT(*) FROM edu_access.`02-bronze`.deped_enrollment_psgc_raw WHERE source_row_kind = 'unit') AS bronze_unit_rows,
  (SELECT COUNT(*) FROM edu_access.`03-silver`.deped_enrollment_psgc_clean) AS clean_rows,
  (SELECT COUNT(*) FROM edu_access.`03-silver`.deped_enrollment_psgc_quarantine) AS quarantine_rows;
```

| `bronze_unit_rows` | `clean_rows` | `quarantine_rows` |
|---|---|---|
| 60,275 | 60,273 | 2 |

The same as the local run on the same batch.

**Gate results per run**

```sql
SELECT run_id, status, COUNT(*) AS checks
FROM edu_access.`01-control`.data_quality_results
WHERE source_id = 'deped_enrollment_psgc' AND layer = 'silver'
GROUP BY run_id, status
ORDER BY run_id, status;
```

| `run_id` (the job run) | PASS | WARN | FAIL |
|---|---|---|---|
| `1094635918316055` (run 1) | 27 | 1 | 0 |
| `302526353474448` (run 2) | 27 | 1 | 0 |
| `737211160986857` (run 3) | 27 | 1 | 0 |

The WARN is `quarantine_rate` (2 rows; FAIL only above 1%). The 27 PASS include all 15 `profiled_*` records, which PASS only when the count equals the rules file (for example 467 Sulu recodes, 36,010 padded codes, 13,899 missing coordinates), so every run produced the same counts on every rule.

## Not checked here

- Row-by-row identity of the published content between the runs on `dev` (no content hash was taken there). Locally, two builds on the same batch gave identical content (SHA-256 `dbf4fa1e…`).
- The individual quarantined rows and sample rows on `dev` (expected `1406363` and `404520`, as locally).
- Table ownership by `reached-hq` on the new Silver tables.
- The failed check in run 2's personnel gate.
