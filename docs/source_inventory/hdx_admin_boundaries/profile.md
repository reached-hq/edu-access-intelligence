# Philippine administrative boundaries source profile

## Purpose

This profile documents the structure and observed data-quality
characteristics of the Philippine administrative boundary data used
by the Education Access Intelligence project.

The profiling covers:

1. City/municipality boundaries (`ADM3`)
2. Barangay boundaries (`ADM4`)

The boundary data is intended to provide geographic context for
school locations and support spatial joins during later transformations.

## Source data location

The optimized GeoParquet files are stored in the Databricks source volume:

`/Volumes/edu_access/00-source/raw/admin_boundaries/`

The original source was published as GeoJSON. The GeoParquet files are
derived local representations created to reduce storage size while
preserving the spatial geometry.

## O-1. Extracted file structure

| Layer | File | Path | File size (MB) | Rows |
| --- | --- | --- | --- | --- |
| ADM3 | phl_admin3.parquet | /Volumes/edu_access/00-source/raw/admin_boundaries/phl_admin3.parquet | 173.89 | 1642 |
| ADM4 | phl_admin4.parquet | /Volumes/edu_access/00-source/raw/admin_boundaries/phl_admin4.parquet | 206.73 | 42048 |

## O-2. Schema

### ADM3 — city/municipality

| Column | Data type |
| --- | --- |
| adm3_name | object |
| adm3_name1 | object |
| adm3_name2 | object |
| adm3_name3 | object |
| adm3_pcode | object |
| adm2_name | object |
| adm2_name1 | object |
| adm2_name2 | object |
| adm2_name3 | object |
| adm2_pcode | object |
| adm1_name | object |
| adm1_name1 | object |
| adm1_name2 | object |
| adm1_name3 | object |
| adm1_pcode | object |
| adm0_name | object |
| adm0_name1 | object |
| adm0_name2 | object |
| adm0_name3 | object |
| adm0_pcode | object |
| valid_on | datetime64[ms] |
| valid_to | object |
| area_sqkm | float64 |
| version | object |
| lang | object |
| lang1 | object |
| lang2 | object |
| lang3 | object |
| adm3_ref_name | object |
| center_lat | float64 |
| center_lon | float64 |
| geometry | geometry |

Observed columns:

`adm3_name, adm3_name1, adm3_name2, adm3_name3, adm3_pcode, adm2_name, adm2_name1, adm2_name2, adm2_name3, adm2_pcode, adm1_name, adm1_name1, adm1_name2, adm1_name3, adm1_pcode, adm0_name, adm0_name1, adm0_name2, adm0_name3, adm0_pcode, valid_on, valid_to, area_sqkm, version, lang, lang1, lang2, lang3, adm3_ref_name, center_lat, center_lon, geometry`

### ADM4 — barangay

| Column | Data type |
| --- | --- |
| adm4_name | object |
| adm4_name1 | object |
| adm4_name2 | object |
| adm4_name3 | object |
| adm4_pcode | object |
| adm3_name | object |
| adm3_name1 | object |
| adm3_name2 | object |
| adm3_name3 | object |
| adm3_pcode | object |
| adm2_name | object |
| adm2_name1 | object |
| adm2_name2 | object |
| adm2_name3 | object |
| adm2_pcode | object |
| adm1_name | object |
| adm1_name1 | object |
| adm1_name2 | object |
| adm1_name3 | object |
| adm1_pcode | object |
| adm0_name | object |
| adm0_name1 | object |
| adm0_name2 | object |
| adm0_name3 | object |
| adm0_pcode | object |
| valid_on | datetime64[ms] |
| valid_to | object |
| area_sqkm | float64 |
| version | object |
| lang | object |
| lang1 | object |
| lang2 | object |
| lang3 | object |
| adm4_ref_name | object |
| center_lat | float64 |
| center_lon | float64 |
| geometry | geometry |

Observed columns:

`adm4_name, adm4_name1, adm4_name2, adm4_name3, adm4_pcode, adm3_name, adm3_name1, adm3_name2, adm3_name3, adm3_pcode, adm2_name, adm2_name1, adm2_name2, adm2_name3, adm2_pcode, adm1_name, adm1_name1, adm1_name2, adm1_name3, adm1_pcode, adm0_name, adm0_name1, adm0_name2, adm0_name3, adm0_pcode, valid_on, valid_to, area_sqkm, version, lang, lang1, lang2, lang3, adm4_ref_name, center_lat, center_lon, geometry`

## O-3. Row counts and geographic coverage

### ADM3

- Row count: **1,642**
- Unique administrative codes: **1,642**

### ADM4

- Row count: **42,048**
- Unique administrative codes: **42,048**

The ADM3 layer represents city/municipality boundaries.
The ADM4 layer represents barangay boundaries.

## O-4. Administrative code uniqueness

### ADM3

- Duplicate `adm3_pcode` records: **0**

### ADM4

- Duplicate `adm4_pcode` records: **0**

Each observed administrative code is unique within its respective layer.

## O-5. Missing administrative identifiers

### ADM3

- Missing `adm3_pcode`: **0**
- Missing `adm3_name`: **0**

### ADM4

- Missing `adm4_pcode`: **0**
- Missing `adm4_name`: **0**

## O-6. Geometry types

### ADM3

| Geometry type | Records |
| --- | --- |
| MultiPolygon | 369 |
| Polygon | 1273 |

### ADM4

| Geometry type | Records |
| --- | --- |
| MultiPolygon | 1117 |
| Polygon | 40931 |

The boundary layers contain Polygon and MultiPolygon geometries.

## O-7. Coordinate reference system

### ADM3

- CRS: **WGS 84**
- EPSG: **4326**

### ADM4

- CRS: **WGS 84**
- EPSG: **4326**

Both layers use WGS 84 / EPSG:4326.

## O-8. Geometry validity

### ADM3

- Missing geometries: **0**
- Empty geometries: **0**
- Invalid geometries: **0**

### ADM4

- Missing geometries: **0**
- Empty geometries: **0**
- Invalid geometries: **0**

## O-9. Administrative hierarchy

### ADM3

- Distinct provinces represented by `adm2_pcode`: **88**
- Distinct regions represented by `adm1_pcode`: **17**

### ADM4

- Distinct parent city/municipality codes: **1,642**
- Missing parent `adm3_pcode`: **0**

The ADM4 layer contains the parent city/municipality code needed
to relate barangays to their corresponding ADM3 area.

## O-10. Source metadata

### ADM3

- `valid_on` values: **2025-02-13**
- `version` values: **v03**

### ADM4

- `valid_on` values: **2025-02-13**
- `version` values: **v03**

## O-11. PSGC compatibility

The ADM3 administrative codes were compared with the current
Philippine Standard Geographic Code (PSGC) 2Q 2026 publication
datafile.

The boundary source uses `adm3_pcode` values such as `PH0102802`,
while the PSGC uses 10-digit codes such as `0102802000`. The
boundary codes were structurally converted to the equivalent
10-digit format for this compatibility check.

- Boundary ADM3 records checked: **1,642**
- PSGC city/municipality records: **1,642**
- Exact code matches: **1,500**
- Code mismatches: **142**
- Exact code match rate: **91.35%**

This check measures exact structural correspondence between the
two code systems. Records without an exact code match are not
force-matched by name and require separate crosswalk validation
before a PSGC code is assigned.

## Analytical limitations

### Administrative boundaries are geographic reference data

The dataset provides administrative boundaries and identifiers.
It does not provide:

- school counts
- enrollment
- teachers
- classrooms
- population
- education outcomes

It should therefore be combined with DepEd, PSA, OSM, and other
project datasets rather than treated as an education dataset.

### Spatial join is a later transformation

The boundary files are preserved as source/reference data.

Matching OSM school points to barangay or city/municipality polygons
should be performed during the Silver transformation layer.

### PSGC compatibility

An exact structural comparison was performed against the PSGC 2Q 2026
publication datafile. Exact code correspondence was found for
1,500 of 1,642 ADM3 records.

Records without exact code correspondence were not force-matched by
name. A validated crosswalk is required before assigning a current
PSGC code to those records.

### Source representation

The original source was acquired as GeoJSON. The Parquet files used
in Databricks are derived GeoParquet representations created for
more efficient storage and analytical processing.

## Reproducibility

Profiling script:

`notebooks/profiling/profile_boundaries.py`

Raw/optimized source location:

`/Volumes/edu_access/00-source/raw/admin_boundaries/`

Output:

`docs/source_inventory/admin_boundaries/profile.md`
