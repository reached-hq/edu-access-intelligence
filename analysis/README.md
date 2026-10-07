# Analysis

Reproducible research programs live here. They read checksum-verified source
files from `RAW_DATA_DIR` and write documentation or compact review artifacts;
they are not production pipeline tasks.

| Folder | Purpose |
|---|---|
| `profiling/` | Inspect one source and generate its profile or data dictionary |
| `cross_source/` | Compare sources, test joinability, and generate exception lists |

Reusable code shared by more than one program belongs in `src/profiling/`.
Production ingestion belongs in `src/ingestion/`, and production transformations
belong in `etl/`.
