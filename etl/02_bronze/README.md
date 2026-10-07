# 02 Bronze

Each source landed unchanged, every column as text, plus provenance columns saying where each row came from.

| File | What it does |
|---|---|
| `01_create_<table>.sql` | One table per logical source, including all delivery years. Generated from `config/ingestion/<source_id>.json` once that source has an ingestion contract (`python -m src.ingestion.cli ddl --source <source_id>`); a test fails if it differs |
| `90_validate_<table>.sql` | Bronze gate, run after every load: no pipeline duplicates, every row has a known batch, every succeeded batch reconciles to its file. Writes to `data_quality_results` and fails on any FAIL. Reads `:run_id` and `:code_revision`. Generated the same way (`cli gate`) |

Implemented sources: `deped_enrollment`, `deped_facilities`. Final names for
these and the four known sources still awaiting ingestion contracts are in the
[ETL table registry](../../docs/standards/tables.md).

Loading is Python (`src/ingestion/`), because the files arrive as zips with a declared encoding. The rules:

- Values are kept exactly as received, as text. A blank stays `''`; a column that a year's file does not have is `NULL`. No trimming, relabeling, typing, or deduplication: that is Silver.
- A row is identified by `(source_sha256, source_row_number)`, and loaded with an insert-only MERGE, so loading a file again adds nothing (D-015). Rows the publisher repeated are all kept and flagged as WARN.
- Downstream reads only rows whose batch is in `` `01-control`.current_batches ``.

Files follow `NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see [File naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
