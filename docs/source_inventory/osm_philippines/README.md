# osm_philippines: OpenStreetMap Philippines (Geofabrik GeoPackage extract)

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | OpenStreetMap Philippines, Geofabrik GeoPackage extract |
| Publisher / agency | OpenStreetMap contributors; extract produced by Geofabrik |
| Source system (as stated by the publisher) | OpenStreetMap database, extracted by Geofabrik for the Philippines |
| Source URL or acquisition method | `philippines-260928-free.gpkg.zip` downloaded from the [Geofabrik Philippines download page](https://download.geofabrik.de/asia/philippines.html) on 2026-09-28. The README inside the download identifies the distribution as `philippines-latest-free.gpkg.zip` and states the data is as of 2026-09-28T20:23:05Z. The "latest" file is replaced daily, so this exact snapshot is identified by the size and SHA-256 below. The ZIP is kept as downloaded and read in place; `philippines.gpkg` inside it is not extracted. |
| Licensing or access restrictions | Open Database License (ODbL): free to use with attribution (© OpenStreetMap contributors). Share-alike applies to derived databases that are published. |
| Owner (team member) | @saraevcldn |
| Date acquired | 2026-09-28 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---:|---|---|---|
| `philippines-260928-free.gpkg.zip` | ZIP archive | Binary | 1,455,605,668 | n/a | `d23657256151176c3d2010bb11226406f91ff2f6f0d67b6b3c93e81da19a0627` | `RAW_DATA_DIR/osm/` (team copy: Databricks volume `/Volumes/edu_access/00-source/raw/osm/`) |
| `philippines.gpkg` (inside the ZIP) | GeoPackage (SQLite database) | UTF-8 strings (publisher §2.3) | 3,325,747,200 | Per layer; see [profile.md](profile.md) | `2676115fe9658fbf3677db307cfc0a677671ff5d3c71a76ed707fd6ff3b4e646` | Inside the ZIP; read in place, not extracted or stored separately |

The ZIP is the retained raw source. Both profiling scripts verify its SHA-256 before reading it and stop on a mismatch; `profile_osm.py` also verifies the checksum of `philippines.gpkg` inside it.

### Rerunning the profile

- **Locally (default, D-007):** set `RAW_DATA_DIR` in the environment or the repo's `.env` to the folder that contains `osm/philippines-260928-free.gpkg.zip`, then run `python notebooks/profiling/profile_osm.py` and `python notebooks/profiling/dictionary_osm.py`.
- **On Databricks (alternative):** open both scripts from the team Git folder and run all cells. `RAW_DATA_DIR` is optional there; the scripts fall back to the team raw volume `/Volumes/edu_access/00-source/raw` (D-009). If `geopandas` or `pyogrio` is missing, run `%pip install geopandas==1.2.0 pyogrio==0.13.0` first. Databricks compute is shared, so prefer a local run (D-008).

The current `profile.md` and `data_dictionary.md` were generated on Databricks.

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Geofabrik Philippines download page | [download.geofabrik.de/asia/philippines.html](https://download.geofabrik.de/asia/philippines.html) | n/a (web page) | Extract description and download information |
| Geofabrik, "OpenStreetMap Data in Layered GIS Format // Free Shapefiles and GeoPackages", version 2026-04-02 (CC BY-SA 2.0); linked from the README inside the download | [osm-data-in-gis-formats-free.pdf](https://download.geofabrik.de/osm-data-in-gis-formats-free.pdf); copy kept at `RAW_DATA_DIR/osm/` (1,268,346 bytes) | `ea7995f1d70dc30903a7e0302b4e76c83ed58255e0fb5bb245fcd42392d6414f` | §2.2 map datum; §2.3 encoding; §2.5 common attributes (`osm_id` not necessarily unique; unusable names written as empty); §2.8 points and areas; §4.2 POI education classes (2081–2084); §5.1 road attributes and classes; §7.4 fields missing from the free files |

The layer documentation does not define a meaning for `maxspeed = 0` (§5.1 says only "Max allowed speed in km/h"). Reading `0` as "no speed recorded" is the team's assumption, tested in profile S-6.

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
| Apparent grain | POI layers: one row per mapped feature per category (a feature with two categories has two rows). Roads: one row per road or path. Features drawn as areas in OSM are in the `_a` layer, points in the layer without it (publisher §2.8), so schools appear in both POI layers. |
| Candidate primary key | POI layers: `(osm_id, fclass)`; `osm_id` alone repeats (448 extra rows in points, 606 extra rows / 605 IDs in areas). School subsets: `osm_id`, unique in each layer with no overlap between them. Roads: `osm_id`. |
| Candidate join keys | No shared identifier with DepEd or PSA. Links to project geography are made through spatial joins to the administrative boundaries, which carry PSGC codes (D-012). OSM `name` may support candidate matching to DepEd but is not an exact join key. |
| PSGC available? | No; OSM features do not carry the project's PSGC codes |
| Personally identifiable or sensitive fields | None found in the columns used |
| Provenance fields in the source | None in the layers used; the free files omit the per-feature `lastchange` timestamp (publisher §7.4) |

Layers used:

- `gis_osm_pois_free`: point POIs, including school features classified as `school`
- `gis_osm_pois_a_free`: area POIs, including `school`, `kindergarten`, `college` and `university` features
- `gis_osm_roads_free`: roads and paths, used for distance and accessibility context

Education scope: `school` is the basic-education class used by the project, counted from both POI layers. `college` and `university` are higher education, which is out of scope (D-003); they are profiled for context only and do not move to ingestion. Whether `kindergarten` is counted with `school` is an open question for the mentor (see profile).

Column-by-column publisher descriptions, our interpretations, fill rates and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Layer | Expected (Geofabrik §2.5, §5.1) | Actual | Notes |
|---|---|---|---|
| `gis_osm_pois_free` | `osm_id`, `code`, `fclass`, `name`, point geometry | matches | Point POIs, including `school` |
| `gis_osm_pois_a_free` | `osm_id`, `code`, `fclass`, `name`, area geometry | matches | Area POIs, including `school`, `kindergarten`, `college` and `university` |
| `gis_osm_roads_free` | `osm_id`, `code`, `fclass`, `name`, `ref`, `oneway`, `maxspeed`, `layer`, `bridge`, `tunnel`, line geometry | matches | `maxspeed = 0` treated as unknown (assumption, profile S-6) |

The publisher states coordinates are WGS84 (EPSG:4326, §2.2); the GeoPackage declares OGC:CRS84, the same datum with longitude first.

## Known quality problems

See [profile.md](profile.md) for evidence and counts.

- **Observed:** schools are in both POI layers: 3,572 points and 47,068 areas, with no shared `osm_id`, so **50,640 distinct mapped OSM schools**. Counting points alone would miss 92.9% of them.
- **Observed:** 770 school features (124 points, 646 areas) have a blank name (`''`), not NULL, so NULL counts alone show 0 missing names.
- **Observed:** `osm_id` is not unique in the POI layers, as the publisher warns (§2.5). Every repeat (448 in points, 605 in areas) is the same place with the same geometry under a second category; there are 0 exact duplicate rows. `(osm_id, fclass)` is unique.
- **Observed:** POI layers also contain `kindergarten`, `college` and `university`; these are counted separately and not included in the 50,640.
- **Observed:** OSM features carry no PSGC codes and must be assigned to project geography by spatial join.
- **Observed:** OSM `name` is not a unique or standardized identifier and is not an exact join key to DepEd.
- **Observed:** only 5.18% of roads have a `maxspeed` other than NULL, blank or `0`; coverage is much higher on major roads (for example 98.5% of motorways, 46.8% of secondary roads, 3.0% of residential roads).
- **Suspected:** `maxspeed = 0` means no speed recorded in OSM (S-6).
- **Observed:** OSM represents mapped features, not an official education inventory. Differences from DepEd may reflect unmapped features, different representation, classification, or source definitions.

## Limitations for analysis

- OSM school features are not the official school inventory. The 50,640 mapped school features should not be read as the number of schools in the Philippines; DepEd remains authoritative.
- Schools may be points or areas; both layers must be used when counting or matching OSM schools.
- Linking OSM to DepEd requires name and spatial validation downstream.
- Coordinates are in degrees; reproject to a metre-based CRS before measuring distance.
- Travel time cannot come from `maxspeed` alone. Use distance by default; if travel time is needed, assign a typical speed per road class (`fclass`) and document it as an assumption.
- OSM changes continuously, so counts differ between snapshots.
- Outputs using OSM data must include attribution under the ODbL.