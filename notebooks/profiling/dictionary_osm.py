# %%
"""Generate a reproducible data dictionary for the OSM source layers."""

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
    / "data_dictionary.md"
)

LAYERS = [
    "gis_osm_pois_free",
    "gis_osm_roads_free",
]


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

        if column == geometry_column:
            rows.append(
                {
                    "column": column,
                    "dtype": "geometry",
                    "null_count": int(series.isna().sum()),
                    "distinct_count": int(series.nunique()),
                    "sample": (
                        gdf.geometry.geom_type
                        .dropna()
                        .astype(str)
                        .drop_duplicates()
                        .tolist()
                    ),
                }
            )
            continue

        non_null = series.dropna()

        sample_values = [
            format_value(value)
            for value in non_null.drop_duplicates().head(3)
        ]

        rows.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "null_count": int(series.isna().sum()),
                "distinct_count": int(series.nunique(dropna=True)),
                "sample": sample_values,
            }
        )

    return gdf, rows


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
    "# OpenStreetMap Philippines — Data Dictionary",
    "",
    "## Source",
    "",
    "- **Source:** OpenStreetMap Philippines — Geofabrik extract",
    "- **Extract date:** 2026-09-28",
    "- **Source file:** `philippines.gpkg`",
    "- **Coordinate reference system:** OGC:CRS84 (WGS 84)",
    "",
    "This data dictionary is generated from the actual source schema "
    "and profiled values.",
    "",
]

for layer, profile in profiles.items():
    lines.extend(
        [
            f"## `{layer}`",
            "",
            f"- **Rows:** {profile['row_count']:,}",
            f"- **Columns:** {profile['column_count']}",
            f"- **Geometry:** {profile['geometry_type']}",
            "- **CRS:** OGC:CRS84 (WGS 84)",
            "",
            "One row represents one feature in this OSM layer.",
            "",
            "| Column | Data type | Nulls | Distinct values | Sample values |",
            "|---|---|---:|---:|---|",
        ]
    )

    for item in profile["rows"]:
        samples = item["sample"]

        if isinstance(samples, list):
            sample_text = "; ".join(samples)
        else:
            sample_text = str(samples)

        sample_text = sample_text.replace("|", "\\|")

        lines.append(
            f"| `{item['column']}` | "
            f"`{item['dtype']}` | "
            f"{item['null_count']:,} | "
            f"{item['distinct_count']:,} | "
            f"{sample_text} |"
        )

    lines.extend(
        [
            "",
        ]
    )


# %%
# Add project interpretation notes
lines.extend(
    [
        "## Project interpretation",
        "",
        "### `gis_osm_pois_free`",
        "",
        "- `fclass = 'school'` is used to identify OSM school features.",
        "- OSM school features are geographic reference points and are "
        "not treated as the official Philippine school inventory.",
        "- OSM school names and locations may require downstream matching "
        "against DepEd records.",
        "",
        "### `gis_osm_roads_free`",
        "",
        "- Road features support geographic proximity or distance-based "
        "accessibility analysis.",
        "- `maxspeed` was profiled for potential travel-time analysis.",
        "- Only 5.18% of road records have available `maxspeed` values "
        "under the profiling rule used for this source.",
        "- Nationwide road-based travel-time analysis is therefore not "
        "supported by this source alone.",
        "",
        "## Reproducibility",
        "",
        "This dictionary is generated by:",
        "",
        "`notebooks/profiling/profile_osm_data_dictionary.py`",
        "",
        "The raw OSM GeoPackage is stored outside Git and is not committed "
        "to the repository.",
        "",
    ]
)

OUTPUT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(f"Data dictionary written to: {OUTPUT}")