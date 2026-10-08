# hdx_boundaries (ADM3): local load and idempotency, 2026-10-08

**What this shows:** the approved COD-AB ADM3 file loads into Bronze through the pipeline, every check passes, and a second run inserts nothing. Local DuckDB only; the Databricks confirmation run is separate.

## Setup

| | |
|---|---|
| Machine | Windows, Python 3.12, local DuckDB (`--db ..\hdx-local.duckdb`, a fresh database) |
| Branch | `feat/84-hdx-adm3-bronze`, at `5cac676` plus the uncommitted GeoJSON changes, committed right after the run without further edits as `605dc29` and `093e1a4` (hence `-dirty` in `code_revision`) |
| File | `admin_boundaries/phl_admin3.geojson`, 555,585,099 bytes, SHA-256 `f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41`, downloaded from the team volume and checked with `Get-FileHash` before the run |
| Tests | `python -m pytest tests -q`: 307 passed, 1 skipped (`tests/test_ingestion_boundaries.py`: 11 passed) |

## Commands

```bash
python -m src.ingestion.cli ingest --source hdx_boundaries --db ../hdx-local.duckdb   # run 1
python -m src.ingestion.cli ingest --source hdx_boundaries --db ../hdx-local.duckdb   # run 2
```

## Runs

Times are UTC; Manila is UTC+8 (run 1 started 15:31 Manila).

| Run | `run_id` | Started (UTC) | Duration | Result |
|---|---|---|---|---|
| 1 | `515e73fe-8594-41fb-8be6-6d23856140dd` | 2026-10-08 07:31:57 | 21.8 s | `succeeded`: 1 batch `load`, `initial`, 1,642 rows inserted |
| 2 | `09dd12f0-6e24-4a1a-b8a8-a05ed45d9288` | 2026-10-08 07:32:37 | 0.6 s | `succeeded`: 1 batch `skip`, 0 rows inserted, `bronze=1642` ("already loaded; same SHA-256") |

Both runs recorded `code_revision` `5cac6762eef0a4b897e07c32f7688fe8a1d0a3ff-dirty`. Batch: `hdx_boundaries__2025-02-13__f682747fbb26`.

## Results (queried after run 2)

| Check | Expected | Actual |
|---|---|---|
| Bronze rows, distinct row numbers, first, last | 1642, 1642, 1, 1642 | 1642, 1642, 1, 1642 |
| Attempts | load / succeeded / 1642, then skip / skipped / 0 | the same |
| Check results, both runs | no FAIL | 24 PASS, 0 WARN, 0 FAIL |
| `valid_on` values | only `2025-02-13` | `2025-02-13` × 1642 |
| Rows without geometry | 0 | 0 |
| Geometry length (characters) | | smallest 607, largest 11,727,901 |
| Feature 1 | Adams, Ilocos Norte, `PH0102801` | `PH0102801`, Adams, Ilocos Norte |
| Feature 1 values kept as written | the file's digits | `area_sqkm` `111.14398463000001`, `center_lat` `18.44225072`, `center_lon` `120.91417544`; geometry text starts `{"type":"Polygon","coordinates":[[[120.969145182000148,18.51` |
| Feature 1 provenance | filled | `phl_admin3.geojson`, `f682747fbb26…`, `2025-02-13`, v1, schema `v1`, `hdx_boundaries__2025-02-13__f682747fbb26` |

## What it means

- The contract's 31 properties and their order match the real file: no `unknown_schema_drift`.
- Every feature carries the approved reference date, has a geometry, and has an `adm3_pcode` matching `^PH[0-9]{7}$`, unique in the file.
- Values and geometry are stored as the file's characters: numbers keep the publisher's digits, and no geometry was parsed or rounded.
- The largest polygon is 11.7 MB of text, which is why rows are merged in chunks of at most 64 MB, and close to DuckDB's default 16 MB row limit, which is raised for staging.
- Rerunning is safe: the second run recognised the file by its SHA-256 and inserted nothing, in under a second.

## Not shown here

The Databricks run (D-017): whether serverless has enough memory for the 1.7 GB peak, and whether 64 MB chunks go through Spark Connect. That evidence will be added after the confirmation run.