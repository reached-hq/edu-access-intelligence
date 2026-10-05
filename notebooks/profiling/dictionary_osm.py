# %%
"""
Generate a reproducible data dictionary for the OSM Philippines source layers.
"""

from pathlib import Path

import geopandas as gpd


# %%
# Find repository root

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
        raise SystemExit(
            "Open the repo folder in VS Code (or cd into it) before "
            "running cell by cell."
        )


REPO = find_repo()


# %%
# Paths

OSM_FILE = Path(
    "/Volumes/edu_access/00-source/raw/osm/philippines-260928-free.gpkg.zip"
)

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "osm_philippines"
    / "data_dictionary.md"
)

LAYERS = [
    "gis_osm_pois_free",
    "gis_osm_pois_a_free",
    "gis_osm_roads_free",
]


# %%
# Source metadata

SOURCE_NAME = "OpenStreetMap Philippines — Geofabrik extract"
EXTRACT_DATE = "2026-09-28"
CRS_LABEL = "OGC:CRS84 (WGS 84)"

PROFILE_SCRIPT = (
    "notebooks/profiling/profile_osm_data_dictionary.py"
)

README_PATH = "docs/source_inventory/osm_philippines/README.md"
PROFILE_PATH = "docs/source_inventory/osm_philippines/profile.md"


# %%
# Check source

if not OSM_FILE.exists():
    raise FileNotFoundError(
        f"OSM GeoPackage not found: {OSM_FILE}"
    )


# %%
def format_value(value, max_length=80):
    """Format a sample value for Markdown."""
    if value is None:
        return ""

    text = str(value).replace("\n", " ").strip()

    if len(text) > max_length:
        return text[: max_length - 3] + "..."

    return text


def observed_kind(series, geometry_column=False):
    """Return a simple observed data kind."""
    if geometry_column:
        geometry_types = (
            series.geom_type
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

        return ", ".join(geometry_types) or "geometry"

    if series.dropna().empty:
        return "empty"

    return str(series.dtype)


def profile_layer(layer_name):
    """Read and profile one OSM layer."""
    gdf = gpd.read_file(
        OSM_FILE,
        layer=layer_name,
    )

    geometry_column = gdf.geometry.name

    rows = []

    for column in gdf.columns:
        series = gdf[column]

        is_geometry = column == geometry_column

        non_null = series.dropna()

        sample_values = [
            format_value(value)
            for value in non_null.drop_duplicates().head(3)
        ]

        rows.append(
            {
                "column": column,
                "dtype": observed_kind(
                    series,
                    geometry_column=is_geometry,
                ),
                "null_count": int(series.isna().sum()),
                "filled_count": int(series.notna().sum()),
                "distinct_count": int(
                    series.nunique(dropna=True)
                ),
                "sample": sample_values,
                "is_geometry": is_geometry,
            }
        )

    return gdf, rows


# %%
# Publisher descriptions

PUBLISHER_DESCRIPTIONS = {
    "osm_id": (
        "OSM feature identifier assigned to the OpenStreetMap feature."
    ),
    "code": (
        "Numeric classification code included in the Geofabrik "
        "OSM-derived extract."
    ),
    "fclass": (
        "Feature class used to categorize the mapped OSM feature."
    ),
    "name": (
        "Name associated with the mapped OSM feature, where available."
    ),
    "ref": (
        "Reference identifier or reference value associated with "
        "the mapped feature, where available."
    ),
    "oneway": (
        "Indicates whether the road feature is designated as one-way."
    ),
    "maxspeed": (
        "Maximum speed value associated with the road feature, "
        "where available."
    ),
    "layer": (
        "Layer value associated with the mapped road feature."
    ),
    "bridge": (
        "Indicates whether the road feature is associated with a bridge."
    ),
    "tunnel": (
        "Indicates whether the road feature is associated with a tunnel."
    ),
    "geometry": (
        "Spatial geometry representing the mapped OSM feature."
    ),
}


# %%
# Publisher notes

PUBLISHER_NOTES = {
    "osm_id": (
        "Identifier comes from the OpenStreetMap-derived extract."
    ),
    "code": (
        "Source classification field; exact values depend on the "
        "Geofabrik extract schema."
    ),
    "fclass": (
        "Feature class values depend on the OSM-derived layer."
    ),
    "name": (
        "Names may be incomplete, inconsistent, or formatted "
        "differently from authoritative Philippine records."
    ),
    "geometry": (
        "Geometry is stored using the layer's spatial representation."
    ),
    "maxspeed": (
        "A value of 0 is treated as unavailable/unknown for the "
        "project's road-speed profiling."
    ),
}


# %%
# Project interpretations by layer

def get_interpretation(layer, column):
    """Return the project interpretation for a layer/column combination."""

    # Common fields

    if column == "osm_id":
        return (
            "[observed] OSM feature identifier. It should not be "
            "assumed to be globally unique across separate OSM layers."
        )

    if column == "code":
        return (
            "[other source] Retained as a source classification field. "
            "The project does not assign additional meaning beyond "
            "the source schema."
        )

    if column == "geometry":
        return (
            "[observed] Spatial feature used for geographic enrichment "
            "and proximity analysis. OSM uses CRS84 (WGS 84) in this "
            "extract."
        )

    # POI-specific fields

    if layer in {
        "gis_osm_pois_free",
        "gis_osm_pois_a_free",
    }:

        if column == "fclass":
            return (
                "[observed] Used to classify mapped POI features. "
                "Observed values include education-related classes "
                "such as `school`, `kindergarten`, `college`, and "
                "`university`."
            )

        if column == "name":
            return (
                "[observed] Descriptive name of the mapped POI. "
                "Useful for matching and validation, but not treated "
                "as a reliable unique school identifier."
            )

        if column == "ref":
            return (
                "[other source] Retained as a reference attribute "
                "where provided. It is not treated as a standardized "
                "Philippine school identifier."
            )

        if column == "type":
            return (
                "[other source] Retained as provided by the source; "
                "no additional project classification is imposed."
            )

    # Road-specific fields

    if layer == "gis_osm_roads_free":

        if column == "fclass":
            return (
                "[observed] Used to classify mapped road features. "
                "Observed values include `tertiary`, `footway`, "
                "and `primary`."
            )

        if column == "name":
            return (
                "[observed] Descriptive name of the mapped road feature. "
                "It is not treated as a unique road identifier."
            )

        if column == "ref":
            return (
                "[other source] Retained as a road reference attribute "
                "where provided."
            )

        if column == "oneway":
            return (
                "[other source] Retained as a road-network attribute. "
                "It may be useful for future network analysis."
            )

        if column == "maxspeed":
            return (
                "[observed] Only 5.18% of road records have a usable "
                "maxspeed value under the profiling rule. This is "
                "therefore not sufficient as the sole basis for "
                "nationwide travel-time estimation."
            )

        if column == "layer":
            return (
                "[other source] Retained as a road-layer attribute "
                "and not used as a standalone accessibility measure."
            )

        if column == "bridge":
            return (
                "[other source] Retained as a road infrastructure "
                "attribute."
            )

        if column == "tunnel":
            return (
                "[other source] Retained as a road infrastructure "
                "attribute."
            )

    return (
        "[other source] Retained as provided by the source; "
        "no additional project interpretation assigned."
    )


# %%
# Profile layers

profiles = {}

for layer in LAYERS:
    gdf, rows = profile_layer(layer)

    profiles[layer] = {
        "gdf": gdf,
        "rows": rows,
        "row_count": len(gdf),
        "column_count": len(gdf.columns),
        "geometry_type": ", ".join(
            sorted(
                gdf.geometry.geom_type
                .dropna()
                .astype(str)
                .unique()
            )
        ),
        "crs": str(gdf.crs),
    }


# %%
# Build data dictionary

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "# osm_philippines: data dictionary",
    "",
    "## Purpose",
    "",
    "This data dictionary documents the observed schema and "
    "project interpretation of the OpenStreetMap Philippines "
    "Geofabrik extract used for geographic enrichment.",
    "",
    "The dictionary distinguishes publisher/source meaning from "
    "project interpretation and observed values.",
    "",
    "## Source metadata",
    "",
    f"- **Source:** {SOURCE_NAME}",
    "- **Publisher:** OpenStreetMap contributors; extract by Geofabrik",
    f"- **Extract date:** {EXTRACT_DATE}",
    f"- **Source file:** `{OSM_FILE}`",
    f"- **CRS:** {CRS_LABEL}",
    f"- **Profile script:** `{PROFILE_SCRIPT}`",
    f"- **Profile:** `{PROFILE_PATH}`",
    f"- **README:** `{README_PATH}`",
    "",
    "## Interpretation labels",
    "",
    "| Label | Meaning |",
    "|---|---|",
    "| `[other source]` | Meaning retained from the source or source schema. |",
    "| `[observed]` | Interpretation supported by values observed during profiling. |",
    "| `[assumed]` | Project assumption that should be validated before analytical use. |",
    "",
]


# %%
# Add layer sections

for layer, profile in profiles.items():

    lines.extend(
        [
            f"## `{layer}`",
            "",
            f"- **Rows:** {profile['row_count']:,}",
            f"- **Columns:** {profile['column_count']}",
            f"- **Geometry:** {profile['geometry_type']}",
            f"- **CRS:** {CRS_LABEL}",
            "",
            "One row represents one mapped OSM feature in this layer.",
            "",
            "| Column | Publisher type | Description (publisher) | "
            "Publisher notes | Our interpretation | Observed kind | "
            "Filled | Distinct | Samples |",
            "|---|---|---|---|---|---|---:|---:|---|",
        ]
    )

    for item in profile["rows"]:

        column = item["column"]

        publisher_type = (
            "geometry"
            if item["is_geometry"]
            else "attribute"
        )

        description = PUBLISHER_DESCRIPTIONS.get(
            column,
            "Publisher/source field retained from the OSM-derived extract.",
        )

        notes = PUBLISHER_NOTES.get(
            column,
            "No additional publisher note recorded.",
        )

        interpretation = get_interpretation(
            layer,
            column,
        )

        samples = item["sample"]

        if samples:
            sample_text = "; ".join(samples)
        else:
            sample_text = ""

        sample_text = sample_text.replace("|", "\\|")

        lines.append(
            f"| `{column}` | "
            f"{publisher_type} | "
            f"{description} | "
            f"{notes} | "
            f"{interpretation} | "
            f"`{item['dtype']}` | "
            f"{item['filled_count']:,} | "
            f"{item['distinct_count']:,} | "
            f"{sample_text} |"
        )

    lines.append("")


# %%
# Project interpretation

lines.extend(
    [
        "## Project interpretation",
        "",
        "### Education features",
        "",
        "- `[observed]` `fclass` values include `school`, "
        "`kindergarten`, `college`, and `university`.",
        "- `[observed]` The point and area POI layers should be "
        "considered together when assessing mapped education features.",
        "- `[observed]` The profiled extract contains 3,572 point "
        "school features and 47,068 area school features.",
        "- `[observed]` There are no shared `osm_id` values between "
        "the point and area school subsets in this extract.",
        "- `[other source]` OSM is not treated as the authoritative "
        "Philippine school inventory.",
        "- `[assumed]` School features may be used for geographic "
        "enrichment and validation after matching against authoritative "
        "DepEd records.",
        "",
        "### Geographic matching",
        "",
        "- `[observed]` The OSM layers do not provide PSGC-style "
        "city/municipality identifiers.",
        "- `[observed]` The layers do not provide standardized "
        "Philippine school identifiers.",
        "- `[observed]` City/municipality assignment is not directly "
        "available in the OSM attributes and therefore requires "
        "spatial matching to a standardized administrative boundary "
        "source.",
        "",
        "### Roads",
        "",
        "- `[observed]` `gis_osm_roads_free` contains 1,612,315 "
        "road features.",
        "- `[observed]` All 1,612,315 road features have unique "
        "`osm_id` values within the road layer.",
        "- `[observed]` Only 83,477 road records have a usable "
        "`maxspeed` value under the profiling rule.",
        "- `[observed]` This corresponds to 5.18% usable coverage.",
        "- `[assumed]` OSM roads are more appropriate for proximity "
        "or distance-based enrichment than nationwide travel-time "
        "estimation unless independent speed assumptions or data "
        "are introduced.",
        "",
        "## Reproducibility",
        "",
        "This dictionary is generated from the actual source schema "
        "and profiled values.",
        "",
        f"`{PROFILE_SCRIPT}`",
        "",
        "The raw OSM download is retained separately from the "
        "repository. The extracted GeoPackage is used temporarily "
        "for profiling and ingestion.",
        "",
    ]
)


# %%
# Write output

OUTPUT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(f"Data dictionary written to: {OUTPUT}")