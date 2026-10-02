# Philippine administrative boundaries

## Source identity

- **Source:** Common Operational Dataset – Administrative Boundaries (COD-AB), Philippines
- **Publisher:** UN OCHA
- **Source URL:** https://data.humdata.org/dataset/cod-ab-phl
- **Administrative levels used:** ADM3 (city/municipality) and ADM4 (barangay)
- **Original format:** GeoJSON
- **Derived format used in Databricks:** GeoParquet
- **Source metadata observed:** `valid_on = 2025-02-13`, `version = v03`

## Why this source matters

Administrative boundaries provide the geographic structure needed to associate education-related data with Philippine cities, municipalities, and barangays.

For this project, the boundaries may be used to:

- spatially assign OSM school locations to administrative areas
- support city/municipality-level education access analysis
- support barangay-level geographic analysis
- provide consistent geographic hierarchy for downstream transformations

The boundary dataset is reference data. It does not contain education capacity, enrollment, population, or education outcomes.

## Coverage

| Administrative level | Records | Geographic unit |
| --- | ---: | --- |
| ADM3 | 1,642 | City/municipality |
| ADM4 | 42,048 | Barangay |

Both layers use WGS 84 / EPSG:4326 and contain Polygon and MultiPolygon geometries.

## Storage

The derived GeoParquet files are stored in the Databricks source volume:

`/Volumes/edu_access/00-source/raw/admin_boundaries/`

Files:

- `phl_admin3.parquet`
- `phl_admin4.parquet`

The original GeoJSON files are retained outside the Git repository. Raw source files are not committed to Git.

## Known data-quality findings

### Geometry

The profiling found:

- no missing geometries
- no empty geometries
- no invalid geometries
- no duplicate ADM3 administrative codes
- no duplicate ADM4 administrative codes

### PSGC compatibility

The ADM3 codes were compared with the current PSA PSGC 2Q 2026 publication datafile.

- Boundary ADM3 records: **1,642**
- PSGC city/municipality records: **1,642**
- Exact code matches: **1,500**
- Code mismatches: **142**
- Exact code match rate: **91.35%**

The source codes are preserved as provided. Records without exact PSGC correspondence are not force-matched by name and require a validated crosswalk before a current PSGC code is assigned.

Further details are documented in `profile.md`.

## Limitations

- The boundary source and the current PSGC publication are not fully code-compatible.
- The boundary dataset should not be treated as the project's authoritative PSGC reference.
- Spatial joins should be performed during the Silver transformation layer rather than modifying the source data.
- Geographic boundaries may not exactly represent the administrative boundaries used by every other project dataset.
- Any analysis involving current PSGC identifiers should use a validated crosswalk.

## Intended use in the project

The source is intended to support geographic integration of education and spatial datasets, particularly the relationship between school locations and administrative areas.

Potential downstream uses include:

- assigning OSM school points to cities/municipalities
- assigning OSM school points to barangays
- aggregating school-related measures by administrative area
- supporting geographic education-access analysis

The source should be combined with DepEd, PSA, OSM, and other project datasets rather than used independently.

## Documentation

- Source profile: `docs/source_inventory/admin_boundaries/profile.md`
- Data dictionary: `docs/source_inventory/admin_boundaries/data_dictionary.md`
- Profiling script: `notebooks/profiling/profile_boundaries.py`
- Data dictionary script: `notebooks/profiling/data_dictionary_admin_boundaries.py`