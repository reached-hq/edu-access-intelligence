# %% OSM Philippines profiling
#
# Profiles the retained OpenStreetMap Philippines GeoPackage extract.
#
# Generates:
# docs/source_inventory/osm_philippines/profile.md
#
# The script verifies the retained ZIP checksum, temporarily extracts the
# GeoPackage, profiles the relevant OSM layers, and regenerates profile.md.
#
# Findings:
# O-1  Required layers
# O-2  Layer structure
# O-3  School features across point and area layers
# O-4  School name completeness
# O-5  Education classifications
# O-6  School OSM ID uniqueness
# O-7  Geographic identifier / attribute availability
# O-8  Road OSM ID uniqueness
# O-9  Road maxspeed availability
# O-10 Expected columns
# O-11 Geometry and geographic validation


# %% Setup

import hashlib
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import geopandas as gpd
import pyogrio


def find_repo():
    """Repo root: from this file's location, or by searching upward from the
    working folder when run cell by cell."""
    try:
        return Path(__file__).resolve().parents[2]
    except NameError:
        here = Path.cwd().resolve()

        for folder in [here, *here.parents]:
            if (
                (folder / "config" / "sources.json").exists()
                or (folder / ".git").exists()
            ):
                return folder

        sys.exit(
            "Open the repo folder in VS Code (or cd into it) before "
            "running cell by cell."
        )


REPO = find_repo()

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "osm_philippines"
    / "profile.md"
)

PROFILED_BY = "@saraevcldn"
PROFILE_DATE = date.today().isoformat()

ZIP_FILE = Path(
    "/Volumes/edu_access/00-source/raw/osm/philippines-260928-free.gpkg.zip"
)

ZIP_SHA256 = (
    "d23657256151176c3d2010bb11226406f91ff2f6f0d67b6b3c93e81da19a0627"
)

SOURCE_TIMESTAMP = "2026-09-28T20:23:05Z"

REQUIRED_LAYERS = [
    "gis_osm_pois_free",
    "gis_osm_pois_a_free",
    "gis_osm_roads_free",
]

EXPECTED_COLUMNS = {
    "gis_osm_pois_free": [
        "osm_id",
        "code",
        "fclass",
        "name",
        "geometry",
    ],
    "gis_osm_pois_a_free": [
        "osm_id",
        "code",
        "fclass",
        "name",
        "geometry",
    ],
    "gis_osm_roads_free": [
        "osm_id",
        "code",
        "fclass",
        "name",
        "ref",
        "oneway",
        "maxspeed",
        "layer",
        "bridge",
        "tunnel",
        "geometry",
    ],
}


# %% Helpers

findings = []
suspected = []


def show(finding, text):
    print(f"[OSM {finding}] {text}")

    findings.append(
        {
            "id": finding,
            "finding": text,
        }
    )


def show_suspected(finding, text, test):
    print(f"[OSM {finding}] {text}")

    suspected.append(
        {
            "id": finding,
            "suspicion": text,
            "test": test,
        }
    )


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def read_layer(layer):
    return gpd.read_file(
        OSM_FILE,
        layer=layer,
        engine="pyogrio",
    )


def format_pct(value):
    return f"{value:.2f}%"


# %% Verify retained raw source

if not ZIP_FILE.exists():
    raise FileNotFoundError(
        f"Retained OSM ZIP not found: {ZIP_FILE}"
    )


actual_zip_sha256 = sha256(ZIP_FILE)

if actual_zip_sha256 != ZIP_SHA256:
    raise RuntimeError(
        "OSM ZIP checksum mismatch.\n"
        f"Expected: {ZIP_SHA256}\n"
        f"Actual:   {actual_zip_sha256}"
    )


ZIP_SIZE = ZIP_FILE.stat().st_size

print(f"OSM ZIP checksum OK: {actual_zip_sha256}")
print(f"OSM ZIP size: {ZIP_SIZE:,} bytes")


# %% Extract GPKG temporarily

temp_dir = Path(
    tempfile.mkdtemp(prefix="osm_")
)

with zipfile.ZipFile(ZIP_FILE, "r") as z:
    z.extractall(temp_dir)


gpkg_files = list(
    temp_dir.rglob("*.gpkg")
)

if len(gpkg_files) != 1:
    raise RuntimeError(
        f"Expected exactly one GPKG in ZIP, "
        f"found {len(gpkg_files)}: {gpkg_files}"
    )


OSM_FILE = gpkg_files[0]

GPKG_SIZE = OSM_FILE.stat().st_size
GPKG_SHA256 = sha256(OSM_FILE)

print(f"Temporary GPKG: {OSM_FILE}")
print(f"Temporary GPKG size: {GPKG_SIZE:,} bytes")
print(f"Temporary GPKG SHA-256: {GPKG_SHA256}")


# %% O-1 Required layers

layers = pyogrio.list_layers(OSM_FILE)

layer_names = [
    row[0]
    for row in layers
]

missing_layers = [
    layer
    for layer in REQUIRED_LAYERS
    if layer not in layer_names
]

show(
    "O-1",
    f"Required analysis layers present={not missing_layers}; "
    f"missing={missing_layers if missing_layers else 'none'}; "
    f"total layers={len(layer_names)}.",
)


# %% Load analysis layers

points = read_layer(
    "gis_osm_pois_free"
)

areas = read_layer(
    "gis_osm_pois_a_free"
)

roads = read_layer(
    "gis_osm_roads_free"
)

# Helper for readable CRS display
def crs_label(crs):
    if crs is None:
        return "UNAVAILABLE"

    crs_text = crs.to_string()

    if crs_text == "OGC:CRS84":
        return "CRS84 (WGS 84)"

    if crs.to_epsg() == 4326:
        return "EPSG:4326 (WGS 84)"

    return crs_text

# %% O-2 Layer structure

point_geometry_types = sorted(
    points.geometry.geom_type
    .dropna()
    .unique()
    .tolist()
)

area_geometry_types = sorted(
    areas.geometry.geom_type
    .dropna()
    .unique()
    .tolist()
)

road_geometry_types = sorted(
    roads.geometry.geom_type
    .dropna()
    .unique()
    .tolist()
)

show(
    "O-2",
    f"Point POIs: {len(points):,} rows, "
    f"{len(points.columns)} columns, "
    f"geometry={point_geometry_types}, "
    f"CRS={crs_label(points.crs)}. "
    f"Area POIs: {len(areas):,} rows, "
    f"{len(areas.columns)} columns, "
    f"geometry={area_geometry_types}, "
    f"CRS={crs_label(areas.crs)}. "
    f"Roads: {len(roads):,} rows, "
    f"{len(roads.columns)} columns, "
    f"geometry={road_geometry_types}, "
    f"CRS={crs_label(roads.crs)}.",
)


# %% O-3 School features across point and area layers

point_schools = points[
    points["fclass"]
    .astype("string")
    .str.lower()
    .eq("school")
].copy()


area_schools = areas[
    areas["fclass"]
    .astype("string")
    .str.lower()
    .eq("school")
].copy()


point_school_ids = set(
    point_schools["osm_id"].dropna()
)

area_school_ids = set(
    area_schools["osm_id"].dropna()
)

overlap_school_ids = (
    point_school_ids.intersection(
        area_school_ids
    )
)

combined_school_ids = (
    point_school_ids.union(
        area_school_ids
    )
)

show(
    "O-3",
    f"Mapped OSM school features: "
    f"{len(point_schools):,} point features + "
    f"{len(area_schools):,} area features = "
    f"{len(combined_school_ids):,} distinct school OSM IDs; "
    f"point/area osm_id overlap="
    f"{len(overlap_school_ids):,}.",
)


# %% O-4 School name completeness

point_null_names = int(
    point_schools["name"].isna().sum()
)

area_null_names = int(
    area_schools["name"].isna().sum()
)

point_empty_names = int(
    point_schools["name"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("")
    .sum()
)

area_empty_names = int(
    area_schools["name"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("")
    .sum()
)

total_empty_names = (
    point_empty_names
    + area_empty_names
)

show(
    "O-4",
    f"School names are NULL for "
    f"{point_null_names:,} point and "
    f"{area_null_names:,} area school features. "
    f"Blank/empty names occur in "
    f"{point_empty_names:,} point and "
    f"{area_empty_names:,} area features "
    f"({total_empty_names:,} combined).",
)


# %% O-5 Education classifications

education_classes = [
    "school",
    "kindergarten",
    "college",
    "university",
]

classification_rows = []

classification_counts = {}

for education_class in education_classes:

    point_count = int(
        points["fclass"]
        .astype("string")
        .str.lower()
        .eq(education_class)
        .sum()
    )

    area_count = int(
        areas["fclass"]
        .astype("string")
        .str.lower()
        .eq(education_class)
        .sum()
    )

    classification_counts[education_class] = {
        "point": point_count,
        "area": area_count,
    }

    classification_rows.append(
        f"{education_class}: "
        f"{point_count:,} point, "
        f"{area_count:,} area"
    )


show(
    "O-5",
    "Education classifications — "
    + "; ".join(classification_rows)
    + ".",
)


# %% O-6 School OSM ID uniqueness

point_duplicate_ids = int(
    point_schools["osm_id"].duplicated().sum()
)

area_duplicate_ids = int(
    area_schools["osm_id"].duplicated().sum()
)

# Overall POI duplication
point_all_duplicate_ids = int(
    points["osm_id"].duplicated().sum()
)

area_all_duplicate_ids = int(
    areas["osm_id"].duplicated().sum()
)

# Duplicate osm_id + fclass pairs
point_duplicate_pairs = int(
    points.duplicated(
        subset=["osm_id", "fclass"]
    ).sum()
)

area_duplicate_pairs = int(
    areas.duplicated(
        subset=["osm_id", "fclass"]
    ).sum()
)

show(
    "O-6",
    f"School duplicate osm_ids: "
    f"point={point_duplicate_ids:,}, "
    f"area={area_duplicate_ids:,}. "
    f"Across all POIs, duplicate osm_ids: "
    f"point={point_all_duplicate_ids:,}, "
    f"area={area_all_duplicate_ids:,}. "
    f"Duplicate (osm_id, fclass) pairs: "
    f"point={point_duplicate_pairs:,}, "
    f"area={area_duplicate_pairs:,}.",
)


# %% O-7 Geographic and attribute identifiers

psgc_patterns = [
    "psgc",
    "pcode",
    "barangay_code",
    "municipality_code",
    "city_code",
    "province_code",
]

address_patterns = [
    "addr",
    "address",
    "street",
    "postcode",
]

operator_patterns = [
    "operator",
    "owner",
]

education_patterns = [
    "education",
    "school_level",
    "level",
    "isced",
]

point_psgc_columns = [
    col
    for col in points.columns
    if any(
        pattern in col.lower()
        for pattern in psgc_patterns
    )
]

area_psgc_columns = [
    col
    for col in areas.columns
    if any(
        pattern in col.lower()
        for pattern in psgc_patterns
    )
]

point_address_columns = [
    col
    for col in points.columns
    if any(
        pattern in col.lower()
        for pattern in address_patterns
    )
]

area_address_columns = [
    col
    for col in areas.columns
    if any(
        pattern in col.lower()
        for pattern in address_patterns
    )
]

point_operator_columns = [
    col
    for col in points.columns
    if any(
        pattern in col.lower()
        for pattern in operator_patterns
    )
]

area_operator_columns = [
    col
    for col in areas.columns
    if any(
        pattern in col.lower()
        for pattern in operator_patterns
    )
]

point_education_columns = [
    col
    for col in points.columns
    if any(
        pattern in col.lower()
        for pattern in education_patterns
    )
]

area_education_columns = [
    col
    for col in areas.columns
    if any(
        pattern in col.lower()
        for pattern in education_patterns
    )
]

show(
    "O-7",
    f"PSGC-like columns: "
    f"point={point_psgc_columns or 'none'}, "
    f"area={area_psgc_columns or 'none'}; "
    f"address/location columns: "
    f"point={point_address_columns or 'none'}, "
    f"area={area_address_columns or 'none'}; "
    f"operator/owner columns: "
    f"point={point_operator_columns or 'none'}, "
    f"area={area_operator_columns or 'none'}; "
    f"education-level columns: "
    f"point={point_education_columns or 'none'}, "
    f"area={area_education_columns or 'none'}.",
)


# %% O-8 Road OSM ID uniqueness

road_duplicate_ids = int(
    roads["osm_id"].duplicated().sum()
)

road_unique_ids = int(
    roads["osm_id"].nunique(dropna=True)
)

show(
    "O-8",
    f"Roads: {len(roads):,} rows, "
    f"{road_unique_ids:,} unique osm_ids, "
    f"{road_duplicate_ids:,} duplicate osm_ids.",
)


# %% O-9 Road maxspeed availability

maxspeed = (
    roads["maxspeed"]
    .astype("string")
    .str.strip()
)

unknown_maxspeed = (
    maxspeed.isna()
    | maxspeed.eq("")
    | maxspeed.str.lower().isin(
        [
            "0",
            "unknown",
            "none",
            "null",
            "nan",
        ]
    )
)

unknown_count = int(
    unknown_maxspeed.sum()
)

available_count = int(
    (~unknown_maxspeed).sum()
)

availability_rate = (
    available_count / len(roads) * 100
    if len(roads)
    else 0
)

show(
    "O-9",
    f"Road maxspeed: "
    f"{unknown_count:,} missing/unknown, "
    f"{available_count:,} available; "
    f"availability rate="
    f"{availability_rate:.2f}%.",
)


# %% O-9A Road maxspeed by road class

road_speed_rows = []

for road_class, group in (
    roads.groupby(
        roads["fclass"]
        .astype("string")
        .fillna("unknown")
        .str.lower()
    )
):

    total = len(group)

    group_maxspeed = (
        group["maxspeed"]
        .astype("string")
        .str.strip()
    )

    group_unknown = (
        group_maxspeed.isna()
        | group_maxspeed.eq("")
        | group_maxspeed.str.lower().isin(
            [
                "0",
                "unknown",
                "none",
                "null",
                "nan",
            ]
        )
    )

    available = int(
        (~group_unknown).sum()
    )

    rate = (
        available / total * 100
        if total
        else 0
    )

    road_speed_rows.append(
        {
            "fclass": road_class,
            "features": total,
            "maxspeed_available": available,
            "availability_pct": rate,
        }
    )


road_speed_rows = sorted(
    road_speed_rows,
    key=lambda x: x["features"],
    reverse=True,
)


# %% O-10 Expected columns

column_results = []

for layer_name, expected in EXPECTED_COLUMNS.items():

    if layer_name == "gis_osm_pois_free":
        actual = set(points.columns)

    elif layer_name == "gis_osm_pois_a_free":
        actual = set(areas.columns)

    elif layer_name == "gis_osm_roads_free":
        actual = set(roads.columns)

    else:
        actual = set()

    missing = [
        col
        for col in expected
        if col not in actual
    ]

    column_results.append(
        f"{layer_name}: "
        f"missing={missing if missing else 'none'}"
    )

show(
    "O-10",
    "; ".join(column_results) + ".",
)


# %% O-11 Geometry and geographic validation

point_school_geometry_missing = int(
    point_schools.geometry.isna().sum()
)

area_school_geometry_missing = int(
    area_schools.geometry.isna().sum()
)


# Philippines approximate bounding box:
# longitude 116 to 127
# latitude 4 to 22

valid_point_school_geometry = (
    point_schools.geometry.notna()
    & ~point_schools.geometry.is_empty
)

point_school_lon = (
    point_schools.loc[
        valid_point_school_geometry
    ].geometry.x
)

point_school_lat = (
    point_schools.loc[
        valid_point_school_geometry
    ].geometry.y
)

outside_philippines = (
    (point_school_lon < 116)
    | (point_school_lon > 127)
    | (point_school_lat < 4)
    | (point_school_lat > 22)
)

outside_philippines_count = int(
    outside_philippines.sum()
)


# Exact coordinate duplicates among point schools
point_school_coords = (
    point_schools.loc[
        valid_point_school_geometry,
        ["geometry"],
    ]
    .copy()
)

point_school_coords["x"] = (
    point_school_coords.geometry.x
)

point_school_coords["y"] = (
    point_school_coords.geometry.y
)

shared_coordinate_count = int(
    point_school_coords.duplicated(
        subset=["x", "y"]
    ).sum()
)


show(
    "O-11",
    f"Geometry validation: "
    f"school point geometry missing="
    f"{point_school_geometry_missing:,}, "
    f"area school geometry missing="
    f"{area_school_geometry_missing:,}; "
    f"school point features outside the approximate "
    f"Philippines bounding box="
    f"{outside_philippines_count:,}; "
    f"point school features sharing an exact coordinate="
    f"{shared_coordinate_count:,}. "
    f"Geometry types: "
    f"point={point_geometry_types}, "
    f"area={area_geometry_types}, "
    f"roads={road_geometry_types}.",
)


# %% Suspected findings

show_suspected(
    "S-1",
    "OSM education features should not be treated as the "
    "authoritative school inventory.",
    "Compare the 50,640 distinct mapped OSM school IDs "
    "against the authoritative DepEd school inventory "
    "after geographic and name-based matching. "
    "Differences may reflect unmapped features, "
    "classification differences, or different source coverage.",
)


show_suspected(
    "S-2",
    "OSM school names may not be sufficiently standardized "
    "for direct key-based matching to DepEd school names.",
    "Standardize names and evaluate candidate matches using "
    "both names and geographic proximity.",
)


show_suspected(
    "S-3",
    "Point and area OSM school representations may require "
    "deduplication or reconciliation before spatial analysis.",
    f"Compare point and area school geometries and OSM IDs. "
    f"The current extract has {len(point_schools):,} point "
    f"school features and {len(area_schools):,} area school "
    f"features, with {len(overlap_school_ids):,} shared OSM IDs.",
)


show_suspected(
    "S-4",
    "OSM fclass values do not provide enough information to "
    "reliably distinguish public/private status or all "
    "education levels needed for the capstone.",
    "Compare OSM classifications against DepEd school-level "
    "and sector information after geographic matching.",
)


show_suspected(
    "S-5",
    "OSM road maxspeed coverage may be insufficient for "
    "reliable travel-time estimation.",
    f"Only {availability_rate:.2f}% of road features have "
    "a usable maxspeed value. Assess whether roads should "
    "instead be used for proximity/distance enrichment or "
    "whether an independent speed assumption is justified.",
)


# %% Layer inventory for profile

layer_rows = []

for row in layers:

    layer_name = row[0]
    geometry_type = row[1]

    try:
        info = pyogrio.read_info(
            OSM_FILE,
            layer=layer_name,
        )

        feature_count = info.get(
            "features",
            "UNAVAILABLE",
        )

        crs = info.get(
            "crs",
            "UNAVAILABLE",
        )

    except Exception:
        feature_count = "UNAVAILABLE"
        crs = "UNAVAILABLE"

    if isinstance(feature_count, int):
        feature_text = f"{feature_count:,}"
    else:
        feature_text = str(feature_count)

    layer_rows.append(
        f"| `{layer_name}` | "
        f"{geometry_type} | "
        f"{feature_text} | "
        f"{crs} |"
    )


# %% Build detailed profile sections

observed_rows = []

for item in findings:

    observed_rows.append(
        "| "
        + item["id"]
        + " | "
        + item["finding"]
        + " | Profiling output from the retained OSM extract. "
        + " | Source integration finding. "
        + " | See integration notes and suspected findings. |"
    )


suspected_rows = []

for item in suspected:

    suspected_rows.append(
        "| "
        + item["id"]
        + " | "
        + item["suspicion"]
        + " | "
        + item["test"]
        + " | Open |"
    )


education_table_rows = []

for education_class in education_classes:

    counts = classification_counts[
        education_class
    ]

    education_table_rows.append(
        f"| `{education_class}` | "
        f"{counts['point']:,} | "
        f"{counts['area']:,} | "
        f"{counts['point'] + counts['area']:,} |"
    )


road_speed_table_rows = []

for row in road_speed_rows:

    road_speed_table_rows.append(
        f"| `{row['fclass']}` | "
        f"{row['features']:,} | "
        f"{row['maxspeed_available']:,} | "
        f"{row['availability_pct']:.2f}% |"
    )


# %% Generate profile.md

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


summary_text = (
    "The retained OSM source is a GeoFabrik Philippines "
    "extract downloaded on 2026-09-28, with source data "
    "timestamped 2026-09-28T20:23:05Z. "
    "The retained raw source is the ZIP file; "
    "`philippines.gpkg` is extracted temporarily for "
    "profiling and is not retained separately. "
    f"The point and area POI layers contain "
    f"{len(point_schools):,} and "
    f"{len(area_schools):,} school features respectively, "
    f"representing {len(combined_school_ids):,} distinct "
    "mapped school OSM IDs. "
    "There is no point/area school OSM ID overlap in this "
    "extract. "
    "OSM does not provide PSGC-like geographic identifiers "
    "in the profiled POI layers, so assignment to "
    "city/municipality or other administrative geography "
    "requires spatial matching to a boundary source."
)


profile_text = f"""# osm_philippines: profile

_Generated by `notebooks/profiling/profile_osm.py`. Do not edit by hand; change the script and rerun._

## Run details

| Field | Value |
|---|---|
| Date profiled | {PROFILE_DATE} |
| Profiled by | {PROFILED_BY} |
| Tool | Python, GeoPandas {gpd.__version__}, Pyogrio {pyogrio.__version__}, run locally |
| Profiling script | [`notebooks/profiling/profile_osm.py`](../../../notebooks/profiling/profile_osm.py) |
| Raw source | `philippines-260928-free.gpkg.zip` |
| Raw source path | `/Volumes/edu_access/00-source/raw/osm/philippines-260928-free.gpkg.zip` |
| ZIP size | {ZIP_SIZE:,} bytes |
| ZIP SHA-256 | `{actual_zip_sha256}` |
| Source data timestamp | `{SOURCE_TIMESTAMP}` |
| Temporary GPKG | `philippines.gpkg` |
| Temporary GPKG size | {GPKG_SIZE:,} bytes |
| Temporary GPKG SHA-256 | `{GPKG_SHA256}` |
| Extracted file handling | Extracted temporarily for profiling; not retained separately |

## How to rerun

Run:

`notebooks/profiling/profile_osm.py`

The script:

1. Verifies the retained ZIP SHA-256 checksum.
2. Extracts `philippines.gpkg` to a temporary directory.
3. Profiles the required OSM layers.
4. Runs the school, geometry, geographic, and road checks documented below.
5. Regenerates:

`docs/source_inventory/osm_philippines/profile.md`

The raw retained source is the ZIP file. The extracted GeoPackage is temporary and should not be committed or treated as the retained raw source.

## Summary

{summary_text}

## Identity

| Field | Value |
|---|---|
| Source | OpenStreetMap Philippines geographic data |
| Publisher / distribution | OpenStreetMap / Geofabrik |
| Extract | GeoFabrik Philippines free GeoPackage |
| Source timestamp | `{SOURCE_TIMESTAMP}` |
| Retained raw format | ZIP containing `philippines.gpkg` |
| CRS of profiled layers | WGS 84 / CRS84 |
| Geographic identifiers | No PSGC-like identifiers in profiled POI layers |

## Files

| File | Status | Notes |
|---|---|---|
| `philippines-260928-free.gpkg.zip` | Retained | Raw source; checksum verified before profiling |
| `philippines.gpkg` | Temporary | Extracted from ZIP only for profiling; not separately retained |

### Checksums

| File | Size | SHA-256 |
|---|---:|---|
| `philippines-260928-free.gpkg.zip` | {ZIP_SIZE:,} bytes | `{actual_zip_sha256}` |
| `philippines.gpkg` | {GPKG_SIZE:,} bytes | `{GPKG_SHA256}` |

## Coverage

### School feature representation

OSM represents school features in both point and area POI layers.

| Representation | School features |
|---|---:|
| Point | {len(point_schools):,} |
| Area | {len(area_schools):,} |
| Distinct school OSM IDs | {len(combined_school_ids):,} |
| Point/area OSM ID overlap | {len(overlap_school_ids):,} |

The point-only school count would therefore understate the number of mapped OSM school features. The combined count of {len(combined_school_ids):,} distinct OSM school IDs should be used when describing the mapped OSM school feature coverage.

This does not make OSM an authoritative school inventory. DepEd remains the authoritative source for the capstone school inventory, while OSM is considered a geographic enrichment source.

### Education classifications

| OSM `fclass` | Point | Area | Combined |
|---|---:|---:|---:|
{chr(10).join(education_table_rows)}

The education classifications are kept separate because `school`, `kindergarten`, `college`, and `university` should not automatically be combined into a single education-facility count.

## Structure

### Key fields

The profiled POI layers contain OSM identifiers and classification fields such as `osm_id`, `code`, `fclass`, and `name`. The profiled road layer also contains fields including `ref`, `oneway`, `maxspeed`, `layer`, `bridge`, and `tunnel`.

### Geographic matching

No PSGC-like identifiers were found in the profiled POI layers.

Therefore, OSM features cannot be directly joined to Philippine administrative areas using a PSGC key. A spatial join against a standardized administrative-boundary source such as HDX/PSGC is required before producing city/municipality-level indicators.

### School names

NULL school names:

- Point schools: {point_null_names:,}
- Area schools: {area_null_names:,}

Blank/empty school names:

- Point schools: {point_empty_names:,}
- Area schools: {area_empty_names:,}
- Combined: {total_empty_names:,}

The blank-name count should not be interpreted as NULL values because the current extract contains zero NULL school names but {total_empty_names:,} blank/empty name values.

### OSM ID uniqueness

| Check | Result |
|---|---:|
| Point school duplicate `osm_id` | {point_duplicate_ids:,} |
| Area school duplicate `osm_id` | {area_duplicate_ids:,} |
| Point POI duplicate `osm_id` | {point_all_duplicate_ids:,} |
| Area POI duplicate `osm_id` | {area_all_duplicate_ids:,} |
| Point duplicate `(osm_id, fclass)` | {point_duplicate_pairs:,} |
| Area duplicate `(osm_id, fclass)` | {area_duplicate_pairs:,} |
| Road duplicate `osm_id` | {road_duplicate_ids:,} |

### Geometry validation

| Check | Result |
|---|---:|
| Missing point school geometry | {point_school_geometry_missing:,} |
| Missing area school geometry | {area_school_geometry_missing:,} |
| Point schools outside approximate Philippines bounding box | {outside_philippines_count:,} |
| Point schools sharing exact coordinates | {shared_coordinate_count:,} |

The approximate Philippines bounding-box check is a sanity check only; it is not a substitute for a formal country boundary.

## Roads and accessibility

The road layer contains {len(roads):,} features.

Usable `maxspeed` is defined here as a value that is not NULL, blank, `0`, or another explicit unknown marker.

| Metric | Count |
|---|---:|
| Road features | {len(roads):,} |
| Missing/unknown `maxspeed` | {unknown_count:,} |
| Usable `maxspeed` | {available_count:,} |
| Usable `maxspeed` rate | {availability_rate:.2f}% |

Only {availability_rate:.2f}% of road features have a usable `maxspeed` value. This makes the field unsuitable as the sole basis for nationwide travel-time estimation without additional assumptions or data.

### `maxspeed` availability by road class

| Road class | Features | Usable `maxspeed` | Availability |
|---|---:|---:|---:|
{chr(10).join(road_speed_table_rows)}

The road layer is therefore better treated as a potential spatial enrichment source for distance/proximity analysis unless an independent and defensible speed assumption is introduced.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
{chr(10).join(observed_rows)}

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
{chr(10).join(suspected_rows)}

## Layer inventory

| Layer | Geometry | Features | CRS |
|---|---|---:|---|
{chr(10).join(layer_rows)}

## Changes across files or years

This is a single dated GeoFabrik extract rather than a school-year statistical dataset. OSM changes continuously, so future extracts should be compared by:

- download date
- source data timestamp
- file checksum
- layer counts
- relevant feature classifications
- mapped school feature counts
- relevant road attributes

The current retained snapshot should therefore be treated as a dated spatial snapshot rather than a permanently current representation of OSM.

## Capstone integration notes

- Use DepEd as the authoritative school inventory.
- Use both point and area OSM school representations when evaluating mapped OSM coverage.
- Do not describe {len(combined_school_ids):,} OSM IDs as the official number of schools in the Philippines.
- Assign OSM features to city/municipality using spatial matching to a standardized administrative-boundary source.
- Do not use OSM names as direct join keys without standardization and geographic validation.
- Keep `kindergarten`, `college`, and `university` classifications separate from `school` unless the analytical scope explicitly requires them.
- Treat roads as spatial enrichment rather than assuming they provide reliable travel times.
- Because `maxspeed` is available for only {availability_rate:.2f}% of roads, distance/proximity may be more defensible than travel-time estimation for the MVP.

## Questions for the publisher or mentor

- Should both point and area OSM school features be retained for the capstone, or should one representation be preferred after matching against DepEd?
- Should `kindergarten`, `college`, and `university` features be included in the spatial enrichment scope, or should the MVP focus on `school` features only?
- What geographic matching tolerance should be used when assigning OSM features to HDX/PSGC administrative boundaries?
- Given that only {availability_rate:.2f}% of road features have usable `maxspeed`, should roads be used primarily for proximity/distance enrichment rather than travel-time estimation?
"""


# %% Write profile

OUTPUT.write_text(
    profile_text,
    encoding="utf-8",
)

print()
print(f"Generated profile: {OUTPUT}")