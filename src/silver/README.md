# Silver

Code that turns the Bronze rows of a source's current deliveries into its Silver tables, and decides when there is nothing to do. The rules themselves are SQL in `etl/03_silver/`, generated from reviewed configuration. Design: [docs/operations/silver.md](../../docs/operations/silver.md).

| Module | What it does |
|---|---|
| `spec.py` | Loads the Bronze contract and the Silver mapping (`config/mappings/<source_id>.json`) and classifies every publisher column (identifier, free text, category, boolean, count); stops on any column or label it cannot place |
| `sql.py` | Generates the build SQL (`01_create_<table>.sql`) and the gate (`90_validate_<table>.sql`) from the spec |
| `dictionary.py` | Generates the Silver data dictionary (`docs/data/silver/`) from the spec |
| `run.py` | One Silver run: read `current_batches`, skip if nothing changed since the last successful build, otherwise build, check column types, run the gate, and record the build and the run (`layer_builds`, `pipeline_runs`) |
| `cli.py` | `build`, `status`, `sql`, `gate`, `dictionary` from the command line, with exit codes. The Databricks job runs it with `--backend spark` |

It reuses `src/ingestion/` for the store (DuckDB locally, Spark on Databricks), the control-table writes, `code_revision`, and the error type.

```bash
python -m src.silver.cli build --source deped_enrollment
python -m src.silver.cli status --source deped_enrollment
```
