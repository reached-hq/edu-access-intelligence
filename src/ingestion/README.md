# Ingestion

Code that checks a raw delivery and turns it into rows for Bronze. Raw files in `00-source` are read, never modified, and never extracted to disk.

| Module | What it does |
|---|---|
| `contract.py` | Loads and validates `config/ingestion/<source_id>.json`: schema versions, approved deliveries, school year from the file names |
| `archive.py` | SHA-256 of a file; opens a zip safely (no `..`, absolute paths, symbolic links, or encrypted members; size limit); finds the data file and documents by name |
| `reader.py` | Decodes with the encoding approved for those exact bytes, strictly; parses the CSV keeping every value as text and blanks as `''`; numbers data rows from 1 |
| `validate.py` | `prepare_delivery`: from an archive on disk to checked rows, or a refusal saying why. Row checks return PASS, WARN, or FAIL |
| `revision.py` | `code_revision`: the commit that produced a row (from the job parameter on Databricks, from git locally, `UNSET` otherwise) |
| `errors.py` | `IngestionError(stage, code, message)` and the command-line exit codes |

How a new delivery is approved: [config/ingestion/README.md](../../config/ingestion/README.md).

Loading into Bronze and the control tables (`etl/01_control/`, `etl/02_bronze/`) are not built yet (#11).
