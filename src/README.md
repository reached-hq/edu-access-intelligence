# Python source

Reusable application code lives under `src/`.

| Folder | Purpose |
|---|---|
| `ingestion/` | Validate approved deliveries, track batches, and load source-preserving Bronze rows |
| `profiling/` | Helpers shared by programs under `analysis/` |

Source-specific research stays in `analysis/`; relational production
transformations stay in `etl/`.
