# 02 Bronze

Each source landed unchanged, every column as text, plus provenance columns saying where each row came from.

| File | What it does |
|---|---|
| `01_create_deped_enrollment_raw.sql` | `deped_enrollment_raw`: all school years and delivery versions in one table. Generated from `config/ingestion/deped_enrollment.json` (`python -m src.ingestion.cli ddl --source deped_enrollment`); a test fails if it differs |
| `90_validate_deped_enrollment_raw.sql` | Bronze gate, run after every load: no pipeline duplicates, every row has a known batch, every succeeded batch reconciles to its file. Writes to `data_quality_results` and fails on any FAIL. Reads `:run_id` and `:code_revision` |

Loading is Python (`src/ingestion/`), because the files arrive as zips with a declared encoding. The rules:

- Values are kept exactly as received, as text. A blank stays `''`; a column that a year's file does not have is `NULL`. No trimming, relabeling, typing, or deduplication: that is Silver.
- A row is identified by `(source_sha256, source_row_number)`, and loaded with an insert-only MERGE, so loading a file again adds nothing (D-015). Rows the publisher repeated are all kept and flagged as WARN.
- Downstream reads only rows whose batch is in `` `01-control`.current_batches ``.

Files follow `NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File naming and layout](../../docs/architecture.md#file-naming-and-layout)).
