# Architecture

> Skeleton. Sections are filled in as each phase produces evidence.

## Overview

<!-- TODO(Phase 5): one paragraph on what the system does and for whom. -->

## Pipeline stages

The stage numbers follow the NYC Mobility convention: a stage number matches its `etl/` folder and its Unity Catalog schema. Schema names start with a digit and contain a hyphen, so SQL must quote them with backticks: ``SELECT * FROM edu_access.`02-bronze`.some_table``. Schemas are created when their stage starts.

| Stage | Layer | Responsibility | Code | Schema |
|---|---|---|---|---|
| 00 | Source | Raw files exactly as received | `src/ingestion/` | `` edu_access.`00-source` `` (volume `raw`, no tables) |
| 01 | Control | Pipeline runs, ingestion batches, DQ results | `etl/01_control/` | `` edu_access.`01-control` `` |
| 02 | Bronze | Source landed unchanged, plus origin fields | `etl/02_bronze/` | `` edu_access.`02-bronze` `` |
| 03 | Silver | Typed, standardized, deduplicated, same grain; quarantine | `etl/03_silver/` | `` edu_access.`03-silver` `` (not created yet) |
| 04 | Integration | Matching across sources (e.g. to PSGC) | `etl/04_integration/` | `` edu_access.`04-integration` `` (not created yet) |
| 05 | Gold | Facts and dimensions for the approved question | `etl/05_gold/` | `` edu_access.`05-gold` `` (not created yet) |
| 06 | Analytics | One dataset per business question | `etl/06_analytics/` | `` edu_access.`06-analytics` `` (not created yet) |

## Data flow

<!-- TODO(Phase 5): diagram from sources to dashboards. -->

## Sources

See [source_inventory/](source_inventory/).

## Workspace

| Item | Value |
|---|---|
| Platform | Databricks Free Edition, one workspace shared by the team |
| Host | `https://dbc-76bcfddb-1669.cloud.databricks.com` |
| CLI profile | `reached-hq` (see [terminal_setup.md, Part 12](terminal_setup.md#part-12-logging-in-to-databricks)) |
| Catalog | `edu_access`: managed, Default Storage, bound to this workspace only (isolated) |
| Owner of the catalog, schemas, and volume | The `reached-hq` group (all six teammates), so no single account is a bottleneck |
| SQL warehouse | Serverless Starter Warehouse, 2X-Small, auto-stop 10 minutes |
| Free Edition limits | Not yet recorded (#1) |

## Storage

Raw files go to the managed volume `` edu_access.`00-source`.raw ``, one folder per publisher, keeping original filenames:

```
/Volumes/edu_access/00-source/raw/
└── deped/
    └── Enrollment-in-SY-2023-2024.zip
```

This is provisional (D-009): if the mentor approves the course R2 bucket, an R2-backed volume is added next to it. Local copies for profiling live outside the repository in `raw-data/` ([terminal_setup.md, Part 8](terminal_setup.md#part-8-raw-data-and-raw_data_dir)).

## Data quality

<!-- TODO(Phase 9): checks per layer, the data_quality_results table, PASS/WARN/FAIL actions. -->

## Orchestration

<!-- TODO(Phase 6): Databricks job task order (databricks.yml). -->

## Environments and deployment

<!-- TODO(Phase 6): dev/prod bundle targets, CD workflow, secrets handling. -->
