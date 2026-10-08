# Evidence: PSGC 2Q 2026 loads into Bronze on Databricks once, and a second run inserts nothing

Issue #82 · PR #111 · Databricks `dev` · 2026-10-08, Manila time (UTC+8; UTC in brackets) · run by @maeveylain

## The claim

On Databricks `dev`, the job `bronze_ingest` loads the official `PSGC-2Q-2026-Publication-Datafile.xlsx` from the team volume into `` edu_access.`02-bronze`.psa_psgc_raw `` with every data row of sheet `PSGC`, every value as stored, and complete provenance, with the same counts as the local runs and the source card. Running the job again skips the workbook and inserts nothing. The DepEd tasks in the same job skip their files and leave their tables unchanged.

## What was run

The job `[dev maeve_lumague] bronze_ingest` (job ID `529600752168614`), deployed from a clean checkout of branch `feat/82-psgc-bronze` at commit `cb274bf96001aa3159ef3d5d0514cd6204e727a1`. Both `git_source.git_commit` and the `code_revision` job parameter were that commit, read back from the deployed job. Tasks in order: `bronze_deped_enrollment`, `bronze_deped_facilities` (`run_if: ALL_DONE`), `bronze_psa_psgc` (`run_if: ALL_DONE`). The run was announced to the team beforehand.

```bash
databricks bundle validate --target dev --profile reached-hq
```

```bash
databricks bundle deploy --target dev --profile reached-hq
```

```bash
databricks bundle run bronze_ingest --target dev --profile reached-hq
```

The last command was run twice. The landing folder `/Volumes/edu_access/00-source/raw/psa/` held the same workbook both times (uploaded 2026-09-30; the job hashed it itself and it matched the approved SHA-256 `31892bc2…ca5d`).

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `468579404509795` | `96808622487518` |
| Whole job | 13:01:48 to 13:05:09 (05:01:48 to 05:05:09 UTC), 3 min 21 s, `SUCCESS` | 13:09:10 to 13:11:40 (05:09:10 to 05:11:40 UTC), 2 min 30 s, `SUCCESS` |
| DepEd tasks | `SUCCESS`, every file skipped | `SUCCESS`, every file skipped |
| PSGC pipeline `run_id` | `bad4df9a-d5ee-46c6-ab51-35a38670073d` | `cbed0f09-8df4-431a-85ef-81f32cdce170` |
| PSGC task output | `psa_psgc__2026-Q2__31892bc2bdde load initial succeeded inserted= 43768 bronze= 43768` | `… skip initial skipped inserted= 0 bronze= 43768`, "already loaded; same SHA-256" |

### The failed attempt before these runs

The first deployment, at commit `2da9a99`, ran as job run `780199342841699` (12:50 to 12:55, 04:50 to 04:55 UTC) and **failed** in all three tasks, each retried once by the job: `KeyError: 'logical_dataset'` while writing to `01-control.ingestion_batches`. The shared control tables on `dev` had already gained `logical_dataset`, `estimate_years_covered` and `source_sheet` from the #109 branch's run on 2026-10-07 (@catweyine), which code on `main` did not yet set. Nothing was loaded: it left an empty `psa_psgc_raw` table and unfinished `running` rows in `pipeline_runs` (two for `psa_psgc`, kept as the honest record). Commit `cb274bf` fixed it (`control.py` writes NULL to control-table columns a row does not name; tests in `tests/test_ingestion_psgc.py` reproduce the Databricks table shape) and was redeployed before the two runs above.

## Results

Queried read-only through the SQL warehouse after both runs, on 2026-10-08.

### 1. Bronze against the source card and the local runs

| Check | Expected (card, local) | Databricks |
|---|---|---|
| Rows for `2026-Q2` v1 | 43,768 | 43,768 |
| Excel row span; distinct codes | 2 to 43,769; 43,768 | 2 to 43,769; 43,768 |
| `Bgy` / `Mun` / `City` / `Prov` / `Reg` / `SubMun` / blank level | 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 | 42,010 / 1,493 / 149 / 82 / 18 / 14 / 2 |
| Blank correspondence code / `#N/A` / population `0` / `-` urban-rural | 50 / 1 / 12 / 38 | 50 / 1 / 12 / 38 |
| Names ending in a space / codes starting with `0` / codes not exactly 10 digits | 2,855 / 29,620 / 0 | 2,855 / 29,620 / 0 |
| Names containing `Tañong` | 2 | 2 (Unicode kept) |
| Pipeline duplicates (`COUNT(*) - COUNT(DISTINCT source_sha256, source_row_number)`) | 0 | 0 |
| Rows missing any of the 16 provenance columns | 0 | 0 |
| Distinct `code_revision` in Bronze | 1 | 1 (`cb274bf…`) |

One row traced: Excel row 2 of sheet `PSGC` in `PSGC-2Q-2026-Publication-Datafile.xlsx` is code `1300000000`, `2026-Q2`, published `2026-06-30`, batch `psa_psgc__2026-Q2__31892bc2bdde`, commit `cb274bf…`.

### 2. Control tables

- `ingestion_batches`: one PSGC batch, `2026-Q2` v1, `initial`, `succeeded`, 1 attempt, expected = source = Bronze = 43,768, no error, `code_revision` `cb274bf…`. Its `logical_dataset`, `estimate_years_covered` and `source_sheet` are NULL, as D-018 defines them for sources that are not estimate-year workbooks.
- `ingestion_batch_attempts`: `load succeeded 43768` (run 1), then `skip skipped 0` (run 2).
- `pipeline_runs` for `psa_psgc`: the two unfinished rows from the failed attempt (`2da9a99`), then two `succeeded` runs in `dev` (1 loaded, then 1 skipped) at `cb274bf`.
- `current_batches`: `2026-Q2`, version 1, `psa_psgc__2026-Q2__31892bc2bdde`.

### 3. Checks

Loading run: 30 PASS, 11 WARN, 0 FAIL; the 11 WARNs are the same checks at the same profiled counts as the [local runs](2026-10-07-psa-psgc-local-idempotency.md#4-checks). No FAIL was recorded for `psa_psgc` in any succeeded run, and the Bronze gate (which raises on any FAIL) let both runs succeed.

### 4. What only Databricks could show (D-017)

- Delta column mapping is on for `psa_psgc_raw` (`delta.columnMapping.mode = name`).
- The workbook is read from a `/Volumes/` path on serverless compute, and the xlsx reader (standard library only) needs no extra package there.
- Unity Catalog permissions: the job created and wrote the table, which belongs to `reached-hq`.
- Not tested: a single-table commit under a real failure during the MERGE (nothing failed mid-load).

### 5. Nothing else changed

DepEd Bronze still has 180,500 enrollment rows and 60,167 facilities rows; both DepEd tasks skipped every file in both runs.

## Limitations

- One quarter only. Re-issue, new-quarter and backfill behavior is proven locally with made-up workbooks, not on Databricks.
- This record covers commit `cb274bf`. #109 merged into `main` later the same day, and this branch was then merged with `main`, which changed the shared code these runs exercised (`formats.py`, `contract.py`, `control.py`). The `control.py` change made at `cb274bf` was dropped in that merge, because `main` now creates and fills those columns itself. Runs at the merged commit are recorded separately.

## How to reproduce

From a clean checkout of `cb274bf` (or later on this branch), with the `reached-hq` profile signed in, notebooks detached and the run announced: the three commands above, the last one twice. Then the validation queries in [docs/operations/ingestion.md](../../docs/operations/ingestion.md#validation-queries-psgc).

## Repeated at the merged commit (after #109)

After this branch was merged with `main` (including #109), the job was redeployed and run twice at merge commit `bfa3c14b4a70d39a88ee377ad81de59b4c4d2b19`, the code that will merge. The deployed job's `git_commit` and `code_revision` were both `bfa3c14…`, and it had four tasks: `bronze_deped_enrollment`, `bronze_deped_facilities`, `bronze_psa_poverty_stat` (from #109), `bronze_psa_psgc`, each after the previous one with `run_if: ALL_DONE`. The run was announced, as before.

| | Run 1 | Run 2 |
|---|---|---|
| Job run | `164635696195` | `801279430383461` |
| Whole job | 14:33:46 to 14:38:42 (06:33:46 to 06:38:42 UTC), 4 min 56 s, `SUCCESS` | 14:45:06 to 14:48:45 (06:45:06 to 06:48:45 UTC), 3 min 39 s, `SUCCESS` |
| DepEd enrollment | skip ×3, 0 inserted (Bronze 60,167 / 60,129 / 60,204) | same |
| DepEd facilities | skip, 0 inserted (Bronze 60,167) | same |
| PSA Poverty Stat | skip, 0 inserted (Bronze 1,641) | same |
| PSGC pipeline `run_id` | `f3d52399-e84c-4897-8369-c2082c48b669` | `bca49ab2-ce71-47cc-8acb-50da7dfa1860` |
| PSGC | `skip`, 0 inserted, Bronze 43,768, "already loaded; same SHA-256" | same |

Every task succeeded on its first attempt, so every Bronze gate (which raises on any FAIL) passed. Counts are from each task's own output; the SQL warehouse was stopped and was not started for this check. Nothing was inserted, so the table-level results above (rows, levels, duplicates, provenance) are unchanged.

**What this does and does not show.** At `bfa3c14`, on Databricks, the merged code recognises the batch loaded at `cb274bf` by its checksum and adds nothing, alongside the three other sources. It does **not** re-read and re-load the workbook on Databricks: the full load path at the merged commit is shown only by the local runs ([local evidence](2026-10-07-psa-psgc-local-idempotency.md#repeated-at-the-merged-commit-after-109)). A skip does not rewrite the batch row, so on `dev` the PSGC row in `ingestion_batches` still has `source_sheet` NULL (written at `cb274bf`), where the merged code writes `PSGC`; a `--rerun` of the batch, or the next delivery, would fill it.
