# Evidence: dim_school_location reconciles to Silver on the real data, every school gets one boundary status, and a rebuild is identical

Issue #217 · local run (DuckDB) only; nothing has run on Databricks · 2026-10-21 · checked by @catweyine

## The claim

Built from the real Silver and Integration tables, `dim_school_location` has one row per school of `deped_psgc_coordinates_clean`: 47,818, with no duplicate or missing key. Every school is in `dim_school`, and each school's longitude, latitude and `coordinate_flag` equal Silver's. Each school has exactly one `boundary_status`, consistent with its inputs. All 15 gate checks pass, and a second build is identical.

**Not claimed:** anything on Databricks; that an `inside` point is the school's exact place (the test is at city or municipality level); anything about barangays (HDX ADM4 is not in Silver).

## What was run

1. **The whole local job on `main`** at `66f6552` (after #218), on the real files in `RAW_DATA_DIR`: `python -m src.job.local_run --db <scratch>/job.duckdb`. Status `succeeded`, every task succeeded. This gives the published inputs:
   - `deped_psgc_coordinates_clean`: 47,818 rows;
   - `deped_school_psgc_map`, `hdx_adm3_psgc_map`, `hdx_adm3_clean`;
   - `dim_school`: 63,793 rows.
   All come from one job run, `54ef3555-a0d3-40fb-a033-329f5d3c9b2c`.
2. **On a copy of that database**, at commit `1ea1592b90b51294d5c119629fd7b342c9f78143` on `feat/217-dim-school-location` (clean worktree): `etl/05_gold/07_build_dim_school_location.sql`, then `etl/05_gold/90_validate_dim_school_location.sql`, twice (`run_id` `gold-ev-1`, `gold-ev-2`).

macOS 26.4.1, Python 3.12.14, DuckDB 1.4.5 with its spatial extension (loaded by `DuckDBStore` for `st_*` functions, as for HDX Silver).

## Results

| | Run 1 | Run 2 |
|---|---|---|
| Build / gate time (local) | 5.3 s / 0.5 s | 6.2 s / 0.0 s |
| Gate checks | 15 PASS | 15 PASS |
| Rows (= Silver) | 47,818 | 47,818 |
| Content hash, all columns | `3f629076e59b…` | `3f629076e59b…` (identical) |
| Per-run gate summary table left behind | 0 | 0 |

FAIL checks that passed:
- `rows_reconcile` (47,818 = 47,818), `key_unique`, `key_not_null`;
- `school_in_dim_school` (0 missing of 63,793 schools);
- `values_match_source`, `boundary_status_allowed`, `boundary_status_follows_inputs`;
- `upstream_run_deped_psgc_coordinates_clean`, `upstream_run_deped_school_psgc_map`, `upstream_run_hdx_adm3_psgc_map`: all the succeeded run above.

### Boundary test S-1, at city or municipality level

| `boundary_status` | Schools | Why |
|---|---:|---|
| `inside` | 44,968 | the point is inside the HDX boundary of the city the reviewed map assigns |
| `outside` | 1,997 | a boundary exists and the point is not in it |
| `no_usable_point` | 738 | `coordinate_flag` set: 679 missing + 54 outside the Philippines + 5 at (0, 0), exactly Silver's flags |
| `no_boundary` | 97 | all in the 8 Special Geographic Area municipalities, which have no HDX boundary: Pahamuddin 17, Nabalawag 13, Tugunan 13, Old Kaabakan 12, Malidegao 12, Ligawasan 12, Kapalawan 10, Kadayangan 8 |
| `no_matched_city` | 18 | the map's SY 2023-24 city status is `excluded` (9) or `ambiguous` (9) |
| **Total** | **47,818** | |

**Sanity check of `inside` and `outside`.** For each tested school, I measured the distance from the median point of the tested schools of its own city:

| | Schools | Median | Under 10 km | 100 km or more |
|---|---:|---:|---:|---:|
| `inside` | 44,968 | 4.4 km | 39,177 | 0 |
| `outside` | 1,997 | 13.5 km | 761 | 260 |

All 260 points 100 km or more from their city are `outside`, which matches the source profile's 260 far-off points (O-6). The 761 `outside` points within 10 km are near a boundary. That is expected for small municipalities and points placed on the town edge; the city-level test cannot tell those apart from slightly misplaced points.

### Cost

On real volumes the build took about 5 s and the gate about 0.5 s locally. These are DuckDB times, not Databricks measurements:
- The scope is applied before the spatial join: SY 2023-24, city level, matched, and unflagged points only.
- Each boundary is parsed once, not once per school.
- There is one `st_contains` per school and city boundary.
- The result is reduced to one row per school before the final join.
- The gate's summary is written once, to a per-run table, as the other Gold gates do.
- The gate does not redo the geometry.

## Not checked here

- **Databricks `dev`:** Gold runs there later, as for the other Gold tables. The spatial functions are the ones HDX Silver already runs on `dev` (`try_to_geometry`, `st_contains`).
- **Whether `inside` points are at the right building.** Only the city boundary is tested.
- **D-061 (#221) is still proposed.** Until it is accepted, which statuses a map may use is a team decision; the data model's recommendation is `inside` only.
