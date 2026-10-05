# osm_philippines: data dictionary

## Purpose

This data dictionary documents the observed schema and project interpretation of the OpenStreetMap Philippines Geofabrik extract used for geographic enrichment.

The dictionary distinguishes publisher/source meaning from project interpretation and observed values.

## Source metadata

- **Source:** OpenStreetMap Philippines — Geofabrik extract
- **Publisher:** OpenStreetMap contributors; extract by Geofabrik
- **Extract date:** 2026-09-28
- **Source file:** `/Volumes/edu_access/00-source/raw/osm/philippines-260928-free.gpkg.zip`
- **CRS:** OGC:CRS84 (WGS 84)
- **Profile script:** `notebooks/profiling/profile_osm_data_dictionary.py`
- **Profile:** `docs/source_inventory/osm_philippines/profile.md`
- **README:** `docs/source_inventory/osm_philippines/README.md`

## Interpretation labels

| Label | Meaning |
|---|---|
| `[other source]` | Meaning retained from the source or source schema. |
| `[observed]` | Interpretation supported by values observed during profiling. |
| `[assumed]` | Project assumption that should be validated before analytical use. |

## `gis_osm_pois_free`

- **Rows:** 173,183
- **Columns:** 5
- **Geometry:** Point
- **CRS:** OGC:CRS84 (WGS 84)

One row represents one mapped OSM feature in this layer.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples |
|---|---|---|---|---|---|---:|---:|---|
| `osm_id` | attribute | OSM feature identifier assigned to the OpenStreetMap feature. | Identifier comes from the OpenStreetMap-derived extract. | [observed] OSM feature identifier. It should not be assumed to be globally unique across separate OSM layers. | `object` | 173,183 | 172,735 | 21717820; 21717872; 24078959 |
| `code` | attribute | Numeric classification code included in the Geofabrik OSM-derived extract. | Source classification field; exact values depend on the Geofabrik extract schema. | [other source] Retained as a source classification field. The project does not assign additional meaning beyond the source schema. | `int32` | 173,183 | 140 | 2907; 2722; 2542 |
| `fclass` | attribute | Feature class used to categorize the mapped OSM feature. | Feature class values depend on the OSM-derived layer. | [observed] Used to classify mapped POI features. Observed values include education-related classes such as `school`, `kindergarten`, `college`, and `university`. | `object` | 173,183 | 140 | camera_surveillance; museum; bicycle_shop |
| `name` | attribute | Name associated with the mapped OSM feature, where available. | Names may be incomplete, inconsistent, or formatted differently from authoritative Philippine records. | [observed] Descriptive name of the mapped POI. Useful for matching and validation, but not treated as a reliable unique school identifier. | `object` | 173,183 | 97,289 | ; Ayala Museum; Christine Sports Cycle Marketing |
| `geometry` | geometry | Spatial geometry representing the mapped OSM feature. | Geometry is stored using the layer's spatial representation. | [observed] Spatial feature used for geographic enrichment and proximity analysis. OSM uses CRS84 (WGS 84) in this extract. | `Point` | 173,183 | 172,694 | POINT (121.0212036 14.5760764); POINT (121.0232447 14.5535834); POINT (121.0594506 14.6009796) |

## `gis_osm_pois_a_free`

- **Rows:** 148,468
- **Columns:** 5
- **Geometry:** MultiPolygon
- **CRS:** OGC:CRS84 (WGS 84)

One row represents one mapped OSM feature in this layer.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples |
|---|---|---|---|---|---|---:|---:|---|
| `osm_id` | attribute | OSM feature identifier assigned to the OpenStreetMap feature. | Identifier comes from the OpenStreetMap-derived extract. | [observed] OSM feature identifier. It should not be assumed to be globally unique across separate OSM layers. | `object` | 148,468 | 147,862 | 3495210; 4271669; 4271685 |
| `code` | attribute | Numeric classification code included in the Geofabrik OSM-derived extract. | Source classification field; exact values depend on the Geofabrik extract schema. | [other source] Retained as a source classification field. The project does not assign additional meaning beyond the source schema. | `int32` | 148,468 | 129 | 2258; 2204; 2721 |
| `fclass` | attribute | Feature class used to categorize the mapped OSM feature. | Feature class values depend on the OSM-derived layer. | [observed] Used to classify mapped POI features. Observed values include education-related classes such as `school`, `kindergarten`, `college`, and `university`. | `object` | 148,468 | 129 | track; park; attraction |
| `name` | attribute | Name associated with the mapped OSM feature, where available. | Names may be incomplete, inconsistent, or formatted differently from authoritative Philippine records. | [observed] Descriptive name of the mapped POI. Useful for matching and validation, but not treated as a reliable unique school identifier. | `object` | 148,468 | 77,954 | Teachers Camp Athletic Oval; Town square; Butanding / Whale Shark Interaction |
| `geometry` | geometry | Spatial geometry representing the mapped OSM feature. | Geometry is stored using the layer's spatial representation. | [observed] Spatial feature used for geographic enrichment and proximity analysis. OSM uses CRS84 (WGS 84) in this extract. | `MultiPolygon` | 148,468 | 147,801 | MULTIPOLYGON (((120.6076864 16.411819, 120.6077762 16.4117619, 120.6078178 16...; MULTIPOLYGON (((123.5961487 12.9060616, 123.596322 12.9057936, 123.5965218 12...; MULTIPOLYGON (((123.5414156 12.9422894, 123.5429309 12.9365597, 123.5443515 1... |

## `gis_osm_roads_free`

- **Rows:** 1,612,315
- **Columns:** 11
- **Geometry:** LineString
- **CRS:** OGC:CRS84 (WGS 84)

One row represents one mapped OSM feature in this layer.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples |
|---|---|---|---|---|---|---:|---:|---|
| `osm_id` | attribute | OSM feature identifier assigned to the OpenStreetMap feature. | Identifier comes from the OpenStreetMap-derived extract. | [observed] OSM feature identifier. It should not be assumed to be globally unique across separate OSM layers. | `object` | 1,612,315 | 1,612,315 | 267; 2508359; 2667097 |
| `code` | attribute | Numeric classification code included in the Geofabrik OSM-derived extract. | Source classification field; exact values depend on the Geofabrik extract schema. | [other source] Retained as a source classification field. The project does not assign additional meaning beyond the source schema. | `int32` | 1,612,315 | 28 | 5115; 5153; 5113 |
| `fclass` | attribute | Feature class used to categorize the mapped OSM feature. | Feature class values depend on the OSM-derived layer. | [observed] Used to classify mapped road features. Observed values include `tertiary`, `footway`, and `primary`. | `object` | 1,612,315 | 28 | tertiary; footway; primary |
| `name` | attribute | Name associated with the mapped OSM feature, where available. | Names may be incomplete, inconsistent, or formatted differently from authoritative Philippine records. | [observed] Descriptive name of the mapped road feature. It is not treated as a unique road identifier. | `object` | 1,612,315 | 52,641 | Maharlika Street; Sagada Mission Compound; Taft Avenue |
| `ref` | attribute | Reference identifier or reference value associated with the mapped feature, where available. | No additional publisher note recorded. | [other source] Retained as a road reference attribute where provided. | `object` | 1,612,315 | 549 | ; 170; E3 |
| `oneway` | attribute | Indicates whether the road feature is designated as one-way. | No additional publisher note recorded. | [other source] Retained as a road-network attribute. It may be useful for future network analysis. | `object` | 1,612,315 | 3 | B; F; T |
| `maxspeed` | attribute | Maximum speed value associated with the road feature, where available. | A value of 0 is treated as unavailable/unknown for the project's road-speed profiling. | [observed] Only 5.18% of road records have a usable maxspeed value under the profiling rule. This is therefore not sufficient as the sole basis for nationwide travel-time estimation. | `int32` | 1,612,315 | 28 | 25; 0; 60 |
| `layer` | attribute | Layer value associated with the mapped road feature. | No additional publisher note recorded. | [other source] Retained as a road-layer attribute and not used as a standalone accessibility measure. | `int32` | 1,612,315 | 9 | 0; -1; 1 |
| `bridge` | attribute | Indicates whether the road feature is associated with a bridge. | No additional publisher note recorded. | [other source] Retained as a road infrastructure attribute. | `object` | 1,612,315 | 2 | F; T |
| `tunnel` | attribute | Indicates whether the road feature is associated with a tunnel. | No additional publisher note recorded. | [other source] Retained as a road infrastructure attribute. | `object` | 1,612,315 | 2 | F; T |
| `geometry` | geometry | Spatial geometry representing the mapped OSM feature. | Geometry is stored using the layer's spatial representation. | [observed] Spatial feature used for geographic enrichment and proximity analysis. OSM uses CRS84 (WGS 84) in this extract. | `LineString` | 1,612,315 | 1,612,307 | LINESTRING (121.0519904 14.6503159, 121.0521254 14.6503023, 121.0535739 14.65...; LINESTRING (120.9019854 17.0809031, 120.9019741 17.0811501, 120.9019697 17.08...; LINESTRING (120.9967123 14.5562681, 120.9966989 14.5563258, 120.9966061 14.55... |

## Project interpretation

### Education features

- `[observed]` `fclass` values include `school`, `kindergarten`, `college`, and `university`.
- `[observed]` The point and area POI layers should be considered together when assessing mapped education features.
- `[observed]` The profiled extract contains 3,572 point school features and 47,068 area school features.
- `[observed]` There are no shared `osm_id` values between the point and area school subsets in this extract.
- `[other source]` OSM is not treated as the authoritative Philippine school inventory.
- `[assumed]` School features may be used for geographic enrichment and validation after matching against authoritative DepEd records.

### Geographic matching

- `[observed]` The OSM layers do not provide PSGC-style city/municipality identifiers.
- `[observed]` The layers do not provide standardized Philippine school identifiers.
- `[observed]` City/municipality assignment is not directly available in the OSM attributes and therefore requires spatial matching to a standardized administrative boundary source.

### Roads

- `[observed]` `gis_osm_roads_free` contains 1,612,315 road features.
- `[observed]` All 1,612,315 road features have unique `osm_id` values within the road layer.
- `[observed]` Only 83,477 road records have a usable `maxspeed` value under the profiling rule.
- `[observed]` This corresponds to 5.18% usable coverage.
- `[assumed]` OSM roads are more appropriate for proximity or distance-based enrichment than nationwide travel-time estimation unless independent speed assumptions or data are introduced.

## Reproducibility

This dictionary is generated from the actual source schema and profiled values.

`notebooks/profiling/profile_osm_data_dictionary.py`

The raw OSM download is retained separately from the repository. The extracted GeoPackage is used temporarily for profiling and ingestion.
