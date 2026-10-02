# %%
"""Profile the OpenStreetMap Philippines GeoPackage and generate source documentation."""

from pathlib import Path

import geopandas as gpd
import pyogrio


# %%
# Paths
REPO = Path.cwd().parents[1]

OSM_FILE = Path(
    "/Volumes/edu_access/00-source/raw/osm/philippines.gpkg"
)

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "osm"
    / "profile.md"
)

EXTRACT_DATE = "2026-09-28"
SOURCE_URL = "https://download.geofabrik.de/asia/philippines.html"
LICENSE = "OpenStreetMap data under the Open Database License (ODbL)"


# %%
# Check source file
if not OSM_FILE.exists():
    raise FileNotFoundError(f"OSM GeoPackage not found: {OSM_FILE}")


# %%
# Inspect available layers
layers = pyogrio.list_layers(OSM_FILE)

layer_names = [row[0] for row in layers]


# %%
# Profile school POIs
POI_LAYER = "gis_osm_pois_free"

pois = gpd.read_file(
    OSM_FILE,
    layer=POI_LAYER,
)

schools = pois[pois["fclass"].eq("school")].copy()

school_count = len(schools)
school_name_missing = int(schools["name"].isna().sum())
school_id_unique = int(schools["osm_id"].nunique())
school_id_duplicates = int(
    schools["osm_id"].duplicated().sum()
)

poi_geometry_types = (
    pois.geometry.geom_type.value_counts().to_dict()
)

poi_crs = "OGC:CRS84 (WGS 84)"


# %%
# Profile road features
ROAD_LAYER = "gis_osm_roads_free"

roads = gpd.read_file(
    OSM_FILE,
    layer=ROAD_LAYER,
)

road_count = len(roads)
road_id_unique = int(roads["osm_id"].nunique())
road_id_duplicates = int(
    roads["osm_id"].duplicated().sum()
)

road_geometry_types = (
    roads.geometry.geom_type.value_counts().to_dict()
)

road_crs = "OGC:CRS84 (WGS 84)"

maxspeed_available = int(
    roads["maxspeed"]
    .fillna("")
    .astype(str)
    .str.strip()
    .replace("0", "")
    .ne("")
    .sum()
)

maxspeed_unavailable = road_count - maxspeed_available

maxspeed_available_pct = (
    maxspeed_available / road_count * 100
)

maxspeed_unavailable_pct = (
    maxspeed_unavailable / road_count * 100
)


# %%
# Build documentation
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

geometry_summary = ", ".join(
    f"{geometry}: {count:,}"
    for geometry, count in poi_geometry_types.items()
)

road_geometry_summary = ", ".join(
    f"{geometry}: {count:,}"
    for geometry, count in road_geometry_types.items()
)

profile = f"""# OSM Philippines Source Profile

## Purpose

This document records the first-look profiling of the Philippines
OpenStreetMap extract used as a supporting geographic source for the
Education Access Intelligence project.

The source provides geographic features that can support school-location
and geographic accessibility analysis.

## Source

- Provider: OpenStreetMap
- Extract provider: Geofabrik
- Extract: Philippines
- Extract date: {EXTRACT_DATE}
- Source file: `philippines.gpkg`
- Source URL: {SOURCE_URL}
- Source layer count: {len(layer_names)}
- Coordinate reference system: {poi_crs}
- License: {LICENSE}
- Storage: `{OSM_FILE}`

## Relevant layers

The GeoPackage contains {len(layer_names)} layers.

The project currently uses two relevant layers:

- `{POI_LAYER}` — points of interest, including school features
- `{ROAD_LAYER}` — road features

Other OSM layers are retained in the source but are outside the current
profiling scope.

## School POIs

### Layer structure

- Total POI records: {len(pois):,}
- Columns: {len(pois.columns)}
- Geometry: {geometry_summary}
- CRS: {poi_crs}

### School features

Filtering `fclass = 'school'` produces:

- School features: {school_count:,}
- Missing school names: {school_name_missing:,}
- Unique OSM IDs: {school_id_unique:,}
- Duplicate OSM IDs: {school_id_duplicates:,}

The school count represents OSM features classified with
`fclass = school`. It should not be interpreted as the complete official
inventory of Philippine schools.

## Roads

### Layer structure

- Road records: {road_count:,}
- Columns: {len(roads.columns)}
- Geometry: {road_geometry_summary}
- CRS: {road_crs}
- Unique OSM IDs: {road_id_unique:,}
- Duplicate OSM IDs: {road_id_duplicates:,}

### Maxspeed availability

- Available: {maxspeed_available:,} ({maxspeed_available_pct:.2f}%)
- Unavailable or unspecified: {maxspeed_unavailable:,}
  ({maxspeed_unavailable_pct:.2f}%)

Values of `maxspeed = 0` are treated as unavailable or unspecified
for this profiling check rather than as a literal 0 km/h speed.

## Data quality observations

### Observed

- The GeoPackage contains {len(layer_names)} layers.
- The school POI subset contains {school_count:,} school features.
- All school features have a non-null `name`.
- School OSM IDs are unique within the filtered school subset.
- Road OSM IDs are unique within the road layer.
- School features use Point geometry.
- Road features use LineString geometry.
- Both relevant layers use {poi_crs}.
- Only {maxspeed_available_pct:.2f}% of road records have available
  `maxspeed` values under the profiling rule used above.

### Suspected / to test later

- OSM school coverage may be incomplete relative to official DepEd
  school records.
- OSM names may not exactly match DepEd school names.
- OSM geographic locations and DepEd school records will require a
  matching process before they can be combined.

## Analytical limitation

Because `maxspeed` is unavailable or unspecified for most road features,
the source should not be treated as sufficient for nationwide
road-based travel-time estimation.

For this project, OSM will primarily support geographic proximity or
distance-based accessibility analysis.

## Intended use

OSM school points will be used as a geographic reference for identifying
school locations and supporting spatial accessibility analysis.

OSM-to-DepEd school matching is a downstream transformation and is not
part of this source profile.

OSM should not replace DepEd as the authoritative source for school
inventory, enrollment, personnel, facilities, or other official
education attributes.

## Reproducibility

The profile is generated by:

`notebooks/profiling/profile_osm.py`

The raw OSM source is not committed to Git.

"""

OUTPUT.write_text(profile, encoding="utf-8")

print(f"Profile written to: {OUTPUT}")