# Architecture

> Skeleton. Sections are filled in as each phase produces evidence.

## Overview

<!-- TODO(Phase 5): one paragraph on what the system does and for whom. -->

## Pipeline stages

The stage numbers follow the NYC Mobility convention: a stage number matches its `etl/` folder and its Unity Catalog schema.

| Stage | Layer | Responsibility | Code | Schema |
|---|---|---|---|---|
| 00 | Source | Raw files exactly as received | `src/ingestion/` | TBD (storage pending) |
| 01 | Control | Pipeline runs, ingestion batches, DQ results | `etl/01_control/` | TBD |
| 02 | Bronze | Source landed unchanged, plus origin fields | `etl/02_bronze/` | TBD |
| 03 | Silver | Typed, standardized, deduplicated, same grain; quarantine | `etl/03_silver/` | TBD |
| 04 | Integration | Matching across sources (e.g. to PSGC) | `etl/04_integration/` | TBD |
| 05 | Gold | Facts and dimensions for the approved question | `etl/05_gold/` | TBD |
| 06 | Analytics | One dataset per business question | `etl/06_analytics/` | TBD |

## Data flow

<!-- TODO(Phase 5): diagram from sources to dashboards. -->

## Sources

See [source_inventory/](source_inventory/).

## Storage

<!-- TODO: pending the decision on R2 vs a Unity Catalog volume. -->

## Data quality

<!-- TODO(Phase 9): checks per layer, the data_quality_results table, PASS/WARN/FAIL actions. -->

## Orchestration

<!-- TODO(Phase 6): Databricks job task order (databricks.yml). -->

## Environments and deployment

<!-- TODO(Phase 6): dev/prod bundle targets, CD workflow, secrets handling. -->
