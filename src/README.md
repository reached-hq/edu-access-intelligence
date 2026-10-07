# Python source

Reusable application code lives under `src/`.

| Folder | Purpose |
|---|---|
| `ingestion/` | Validate approved deliveries, track batches, and load source-preserving Bronze rows |
| `silver/` | Generate each source's Silver build and gate SQL, and its data dictionary, from its reviewed mapping |
| `profiling/` | Helpers shared by programs under `analysis/` |
| `job/` | Run the Databricks job's tasks from `databricks.yml` locally, in order, on DuckDB |

Source-specific research stays in `analysis/`; relational production
transformations stay in `etl/`.
