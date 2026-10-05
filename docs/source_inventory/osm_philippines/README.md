# osm_philippines: OpenStreetMap Philippines (Geofabrik GeoPackage extract)

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | OpenStreetMap Philippines, Geofabrik GeoPackage extract |
| Publisher / agency | OpenStreetMap contributors; extract produced by Geofabrik |
| Source system (as stated by the publisher) | OpenStreetMap database, extracted by Geofabrik for the Philippines |
| Source URL or acquisition method | `philippines-260928-free.gpkg.zip` downloaded from [Geofabrik Philippines download page](https://download.geofabrik.de/asia/philippines.html) on 2026-09-28. The README inside the download identifies the distribution as `philippines-latest-free.gpkg.zip` and states the data is as of 2026-09-28T20:23:05Z. The ZIP was unzipped, and `philippines.gpkg` was used for profiling and ingestion. |
| Licensing or access restrictions | Open Database License (ODbL): free to use with attribution (© OpenStreetMap contributors). Share-alike applies to derived databases that are published. |
| Owner (team member) | @saraevcldn |
| Date acquired | 2026-09-28 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---:|---|---|---|
| `philippines-260928-free.gpkg.zip` | ZIP archive | Binary | 1,455,605,668 | n/a | `d23657256151176c3d2010bb11226406f91ff2f6f0d67b6b3c93e81da19a0627` | Databricks volume `/Volumes/edu_access/00-source/raw/osm/` |
| `philippines.gpkg` | GeoPackage (SQLite database) | UTF-8 text, binary file | 3,325,747,200 | Per layer; see [profile.md](profile.md) | `2676115fe9658fbf3677db307cfc0a677671ff5d3c71a76ed707fd6ff3b4e646` | Temporary extraction from retained ZIP; not separately retained |

The original ZIP is the retained raw source. `philippines.gpkg` was extracted from the ZIP for profiling and ingestion and is not separately retained as a raw source.

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Geofabrik Philippines download page | [Geofabrik Philippines download page](https://download.geofabrik.de/asia/philippines.html) | n/a | Extract description and download information |
| Geofabrik layer documentation | Linked from the README inside the downloaded extract | n/a | Layer and attribute definitions, including `maxspeed = 0` meaning unknown |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines |
| Geographic level | Point, line and area features |
| Time coverage | One snapshot, data as of 2026-09-28T20:23:05Z |
| Time basis | Time of the OpenStreetMap data in the extract; OSM is edited continuously |
| Update frequency | Geofabrik publishes updated extracts regularly; this project uses one snapshot |
| Population covered | Features mapped by OpenStreetMap contributors; not an official inventory |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per mapped OSM feature. Education features may be represented as points or areas depending on how they were mapped; roads contain one row per road feature. |
| Candidate primary key | `osm_id` within the relevant feature layer; school point and school area subsets have no observed `osm_id` overlap |
| Candidate join keys | No shared identifier with DepEd or PSA. Links to project geography are made primarily through spatial joins; OSM education `name` may be used as a candidate attribute for matching to DepEd but is not an exact join key. |
| PSGC available? | No; OSM features do not carry the project's PSGC codes |
| Personally identifiable or sensitive fields | None found in the columns used |
| Provenance fields in the source | No edit timestamp or contributor fields in the layers used |

Layers used:

- `gis_osm_pois_free` — point POIs, including school features classified as `school`
- `gis_osm_pois_a_free` — area POIs, including school, kindergarten, college and university features
- `gis_osm_roads_free` — road features used for accessibility/context analysis

Education scope for profiling includes `school`, `kindergarten`, `college`, and `university`. The combined school count includes only `fclass = 'school'` from both the point and area POI layers.

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Layer | Expected (Geofabrik) | Actual | Notes |
|---|---|---|---|
| `gis_osm_pois_free` | `osm_id`, `code`, `fclass`, `name`, point geometry | matches | Contains point POIs, including school features classified as `school` |
| `gis_osm_pois_a_free` | `osm_id`, `code`, `fclass`, `name`, area geometry | matches | Contains area POIs, including school, kindergarten, college and university features |
| `gis_osm_roads_free` | `osm_id`, `code`, `fclass`, `name`, `ref`, `oneway`, `maxspeed`, `layer`, `bridge`, `tunnel`, line geometry | matches | Used for road/accessibility context; `maxspeed = 0` means unknown |

## Known quality problems

See [profile.md](profile.md) for evidence and counts.

- **Observed:** schools are represented in both the point and area POI layers. The `school` subset contains 3,572 point features and 47,068 area features.
- **Observed:** the point and area school subsets have no overlapping `osm_id` values. The combined count is therefore **50,640 distinct mapped OSM school features (OSM IDs)** across the two layers.
- **Observed:** OSM POI layers also contain education features classified as `kindergarten`, `college`, and `university`. These are profiled separately and are not included in the 50,640 school count.
- **Observed:** OSM education features do not contain PSGC codes and must be assigned to project geography through spatial matching to administrative boundaries.
- **Observed:** OSM education `name` is not a guaranteed unique or standardized identifier and should not be used as an exact join key to DepEd.
- **Observed:** `maxspeed` is missing or recorded as `0` on most road features. Coverage is higher on major roads than on smaller roads.
- **Observed:** OSM represents mapped features rather than an official education inventory. Differences from DepEd may reflect unmapped features, differences in feature representation, classification, or source definitions.

## Limitations for analysis

- OSM school features are not the official school inventory. The combined count of 50,640 mapped school features should not be interpreted as the actual number of schools in the Philippines.
- School features may be represented as either points or areas. Both layers must be considered when counting or matching OSM schools.
- OSM coverage and classification may differ from DepEd records. Linking OSM to DepEd requires downstream name and geographic/spatial validation.
- `name` can support candidate matching but should not be treated as a deterministic school identifier.
- `maxspeed` alone cannot support travel-time estimates because it is missing or unknown for most road features. OSM roads are more appropriate for distance, proximity, and accessibility/context indicators unless additional speed assumptions are introduced.
- OSM education features can support spatial enrichment and validation but should not replace DepEd as the authoritative source for school inventory, enrollment, personnel, facilities, and other official education attributes.
- OSM changes continuously, so counts can differ between snapshots.
- Outputs using OSM data must include attribution under the ODbL.