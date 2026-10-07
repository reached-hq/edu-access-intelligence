# 03 Silver

Typed, standardized, and validated data at the source's own grain, with a quarantine for rows that cannot be trusted. Design, rules, counts, and runbook: [docs/operations/silver.md](../../docs/operations/silver.md).

| File | What it does |
|---|---|
| `01_create_<table>.sql` | Rebuilds the source's clean and quarantine tables from the Bronze rows of `` `01-control`.current_batches `` only: a temporary view classifies every row (cleaned values and quarantine reasons), then two `CREATE OR REPLACE TABLE ... AS SELECT`, each handed to `reached-hq`. Needs the one-row temporary table `silver_run` staged by `src/silver/run.py` |
| `90_validate_<table>.sql` | Silver gate, run after every build: reconciliation with Bronze per school year, keys, ranges, NULLs, labels, lineage, quarantine rate, and a record of each rule's affected rows. Writes to `data_quality_results` (`layer = 'silver'`) and fails on any FAIL. Reads `:run_id` and `:code_revision` |

Both files are generated from the Bronze contract (`config/ingestion/<source_id>.json`) and the reviewed Silver mapping (`config/mappings/<source_id>.json`); a test fails if they differ:

```bash
python -m src.silver.cli sql --source deped_enrollment > etl/03_silver/01_create_deped_enrollment_clean.sql
```

```bash
python -m src.silver.cli gate --source deped_enrollment > etl/03_silver/90_validate_deped_enrollment_clean.sql
```

Implemented: `deped_enrollment` → `deped_enrollment_clean`, `deped_enrollment_quarantine` ([data dictionary](../../docs/data/silver/deped-enrollment-clean.md)). Final names for the other sources are in the [ETL table registry](../../docs/standards/tables.md).

The SQL uses only what Databricks and DuckDB share; `src/ingestion/store.py` translates `regexp_like` and `regexp_replace` for DuckDB. Files follow `NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
