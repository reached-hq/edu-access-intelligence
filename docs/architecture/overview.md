# Architecture

> Skeleton. Sections are filled in as each phase produces evidence.

## Overview

<!-- TODO(Phase 5): one paragraph on what the system does and for whom. -->

## Pipeline stages

The stage numbers follow one rule: a stage number matches its `etl/` folder and its Unity Catalog schema. Schema names start with a digit and contain a hyphen, so SQL must quote them with backticks: ``SELECT * FROM edu_access.`02-bronze`.some_table``. Schemas are created when their stage starts.

| Stage | Layer | Responsibility | Code | Schema |
|---|---|---|---|---|
| 00 | Source | Raw files exactly as received | `src/ingestion/` | `` edu_access.`00-source` `` (volume `raw`, no tables) |
| 01 | Control | Pipeline runs, ingestion batches, DQ results | `etl/01_control/` | `` edu_access.`01-control` `` |
| 02 | Bronze | Source landed unchanged, plus origin fields | `etl/02_bronze/` | `` edu_access.`02-bronze` `` |
| 03 | Silver | Typed, standardized, deduplicated, same grain; quarantine | `etl/03_silver/`, `src/silver/` | `` edu_access.`03-silver` `` (created by the first Silver build) |
| 04 | Integration | Matching across sources (e.g. to PSGC) | `etl/04_integration/` | `` edu_access.`04-integration` `` (not created yet) |
| 05 | Gold | Facts and dimensions for the approved question | `etl/05_gold/` | `` edu_access.`05-gold` `` (not created yet) |
| 06 | Analytics | One dataset per business question | `etl/06_analytics/` | `` edu_access.`06-analytics` `` (not created yet) |

## File naming and layout

- Every folder in the layout exists from the start. Until its phase begins, it holds only a short `README.md` saying what will go there.
- SQL files in each `etl/` folder are named `NN_<verb>_<object>.sql` and run in number order.
- Each layer's checks are in `90_validate_<object>.sql`.
- `config/` holds non-secret settings, including the source registry.

## Data flow

<!-- TODO(Phase 5): diagram from sources to dashboards. -->

Built so far, Source to Bronze ([ingestion](../operations/ingestion.md)):

```
official download ─▶ 00-source volume ─▶ checksum + approved contract ─▶ validate ─▶ MERGE ─▶ 02-bronze
                                                     │                                          │
                                                     └──────────── 01-control ◀─────────────────┘
                                      runs, batches, attempts, data-quality results, current_batches
```

Built and tested locally, Bronze to Silver ([Silver](../operations/silver.md)); not yet run on Databricks:

```
Bronze gate passed ─▶ 01_create_<table>: current_batches only ─▶ 03-silver <source>_clean + <source>_quarantine
                                                                   │
                      90_validate_<table> ◀────────────────────────┘
                         │  data-quality results; pipeline_runs 'succeeded' or 'failed'
                         ▼
                      01-control
```

## Sources

See the [source inventory](../data/source-inventory/).

## Workspace

| Item | Value |
|---|---|
| Platform | Databricks Free Edition, one workspace shared by the team |
| Host | `https://dbc-76bcfddb-1669.cloud.databricks.com` |
| CLI profile | `reached-hq` (see [terminal setup, Part 12](../getting-started/terminal-setup.md#part-12-logging-in-to-databricks)) |
| Catalog | `edu_access`: managed, Default Storage, bound to this workspace only (isolated) |
| Owner of the catalog, schemas, and volume | The `reached-hq` group (all five teammates), so no single account is a bottleneck |
| SQL warehouse | Serverless Starter Warehouse, 2X-Small, auto-stop 10 minutes |
| Free Edition limits | Not yet recorded (#1) |

## Storage

Raw files go to the managed volume `` edu_access.`00-source`.raw ``, one folder per publisher, keeping original filenames. A raw file is never overwritten: any later download goes into a dated subfolder (D-016, provisional):

```
/Volumes/edu_access/00-source/raw/
└── deped/
    ├── Enrollment-in-SY-2023-2024.zip      first downloads, uploaded 2026-09-30
    ├── Enrollment-in-SY-2024-2025.zip
    ├── Enrollment-in-SY-2025-2026.zip
    ├── SHA256SUMS.txt                      covers every file in this folder
    ├── ...                                 other DepEd sources
    └── 2027-08-15/                         a later download (example date)
        ├── Enrollment-in-SY-2026-2027.zip
        └── SHA256SUMS.txt
```

Ingestion identifies files by SHA-256, not by path (D-014).

This is provisional (D-009): if the mentor approves the course R2 bucket, an R2-backed volume is added next to it. Local copies for profiling live outside the repository in `raw-data/` ([terminal setup, Part 8](../getting-started/terminal-setup.md#part-8-raw-data-and-raw_data_dir)).

## Data quality

<!-- TODO(Phase 9): checks per layer for Silver onward. -->

Every check writes one row to `` edu_access.`01-control`.data_quality_results `` (#42 columns, plus `batch_id`, `source_id`, `code_revision`); results hold counts and rules, never row values.

| Status | Meaning | Action |
|---|---|---|
| PASS | As expected | None |
| WARN | Worth knowing, not wrong in Bronze (e.g. a publisher's duplicate school) | Recorded; rows are loaded as received; Silver decides |
| FAIL | The batch cannot be trusted | The batch is not marked succeeded, so downstream does not read it; the run exits nonzero |

Bronze checks are listed in [ingestion, Validation](../operations/ingestion.md#validation).

Silver adds its own gate per source (`etl/03_silver/90_validate_<table>.sql`, `layer = 'silver'`): reconciliation with Bronze per school year (rows and learners), unique non-NULL keys, counts non-negative and integer-typed, NULLs kept as NULL, every label in the reviewed mapping, complete lineage, and the quarantine rate; it also records how many rows each cleaning rule changed or flagged. For Silver, WARN means rows were quarantined (at most 1% of a school year) and the build stands; FAIL means the Silver tables cannot be trusted: the task fails, the run is not marked succeeded, and Gold must not read them. Details: [Silver, The gate](../operations/silver.md#the-gate).

## Orchestration

<!-- TODO(Phase 6): task order for the full pipeline. -->

`databricks.yml` defines one job, `edu_access_pipeline` (D-020). Each source has a lane:

| Task | Type | Runs on | Runs when |
|---|---|---|---|
| `01_create_pipeline_runs` through `05_create_current_batches` | SQL | SQL warehouse | At job start, once, in order |
| `NN_create_<table>_raw` | SQL | SQL warehouse | Control setup succeeded; all source DDL tasks fan out in parallel |
| `bronze_<source_id>`: check each delivery against its contract, load, reconcile (`src/ingestion/cli.py ingest --no-gate --no-setup`) | Python | serverless job compute | That source's raw table exists |
| `90_validate_<table>_raw`: the Bronze gate (`etl/02_bronze/90_validate_<table>_raw.sql`) | SQL | SQL warehouse | The load succeeded |
| Silver clean and validation files from `etl/`, one task each | SQL | SQL warehouse | The preceding task in the same source lane succeeded |
| Mapping, dimension, fact, and analytics files from `etl/`, one task each | SQL | SQL warehouse | All required outputs from the preceding stage succeeded |

Python is used only where SQL cannot do the work: the deliveries are zips with a declared encoding. Every SQL file is its own task, so a failed check shows as its own failed task. After the shared control bootstrap, source lanes start in parallel and do not depend on each other. Within each lane, tasks run in order and stop if their own upstream task fails. `90_validate_control` is the source-lane fan-in. Mapping tasks then fan out in parallel and converge on Integration; dimensions fan out after Integration; facts fan out after both dimension gates; and all analytics outputs fan out after both fact gates. SQL tasks receive the job parameters `code_revision` and `run_id` (`{{job.run_id}}`) as `:code_revision` and `:run_id`. The job has no schedule during development, allows only one whole job run at a time, and is safe to rerun. `python -m src.job.local_run` checks the same DAG in a deterministic topological order on DuckDB ([src/job](../../src/job/README.md)).

## Environments and deployment

<!-- TODO(Phase 6): prod target, CD workflow, secrets handling. -->

- `dev` is the only bundle target so far (`mode: development`); `prod` is not defined yet. `dev` and `prod` are deploy targets, not branches (D-005).
- The job runs the commit it was deployed from (`git_source.git_commit: ${bundle.git.commit}`), and records the same value as `code_revision` on every row it writes. New code needs a deploy from a clean, pushed `main`.
- Only `accepted` sources may load into `prod`; `profiled` sources load into `local` and `dev` only.
