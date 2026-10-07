# %% OSM Philippines data dictionary
#
# Generates docs/data/source-inventory/osm_philippines/data_dictionary.md for the three
# OSM layers the project uses: gis_osm_pois_free, gis_osm_pois_a_free and
# gis_osm_roads_free.
#
# The ZIP is the retained raw source and is read in place: the script verifies the
# ZIP checksum, then reads the layers directly from philippines.gpkg inside it.
# Nothing is extracted to disk. Every count and percentage is computed from the
# data; the extract timestamp and the publisher's documentation link are read from
# the README inside the ZIP, and the CRS from the layers themselves.
#
# Runs locally (D-007). Open it in VS Code to run cell by cell (# %% markers),
# or run the whole file:
#   RAW_DATA_DIR=~/Documents/GitHub/raw-data python analysis/profiling/dictionary_osm.py
#
# RAW_DATA_DIR (environment or the repo's .env) must contain osm/ with
# philippines-260928-free.gpkg.zip.


# %% Setup

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

import geopandas as gpd


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


def env_value(name):
    """Read a variable from the environment, else from the repo's git-ignored .env."""
    if os.environ.get(name):
        return os.environ[name]
    env = REPO / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip()
    return None


def on_databricks():
    return bool(os.environ.get("DATABRICKS_RUNTIME_VERSION")) or Path("/databricks").exists()


def resolve_raw_data_dir():
    """RAW_DATA_DIR from the environment or the repo's .env (D-007).
    On Databricks only, fall back to the team's raw volume (D-009)."""
    value = env_value("RAW_DATA_DIR")
    if value:
        return Path(value).expanduser(), "RAW_DATA_DIR"
    if on_databricks():
        return Path("/Volumes/edu_access/00-source/raw"), "Databricks team volume (D-009)"
    sys.exit(
        "Set RAW_DATA_DIR to the folder that contains osm/.\n"
        f"Looked in the environment and in {REPO / '.env'}."
    )


RAW_DIR, RAW_DIR_FROM = resolve_raw_data_dir()
OSM_DIR = RAW_DIR / "osm"
print(f"Raw data folder: {RAW_DIR} (from {RAW_DIR_FROM})")

ZIP_NAME = "philippines-260928-free.gpkg.zip"
ZIP_FILE = OSM_DIR / ZIP_NAME
SOURCE_LABEL = f"RAW_DATA_DIR/osm/{ZIP_NAME}"

ZIP_SHA256 = "d23657256151176c3d2010bb11226406f91ff2f6f0d67b6b3c93e81da19a0627"

SCRIPT_PATH = "analysis/profiling/dictionary_osm.py"
PROFILE_PATH = "docs/data/source-inventory/osm_philippines/profile.md"
README_PATH = "docs/data/source-inventory/osm_philippines/README.md"

OUTPUT = REPO / "docs" / "data" / "source-inventory" / "osm_philippines" / "data_dictionary.md"

LAYERS = [
    "gis_osm_pois_free",
    "gis_osm_pois_a_free",
    "gis_osm_roads_free",
]

SOURCE_NAME = "OpenStreetMap Philippines, Geofabrik GeoPackage extract"


# %% Verify the raw ZIP and read its README

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if not ZIP_FILE.exists():
    sys.exit(f"Retained OSM ZIP not found: {ZIP_FILE}")

actual_zip_sha256 = sha256(ZIP_FILE)
if actual_zip_sha256 != ZIP_SHA256:
    sys.exit(
        f"{ZIP_NAME}: SHA-256 does not match the inventory card. Stop and re-inventory.\n"
        f"Expected: {ZIP_SHA256}\nActual:   {actual_zip_sha256}"
    )
print(f"{ZIP_NAME}: checksum OK")

with zipfile.ZipFile(ZIP_FILE) as z:
    gpkg_members = [n for n in z.namelist() if n.endswith(".gpkg")]
    if len(gpkg_members) != 1:
        sys.exit(f"Expected exactly one GPKG in the ZIP, found {gpkg_members}")
    GPKG_MEMBER = gpkg_members[0]

    readme_name = next(
        (n for n in z.namelist() if Path(n).name.lower().startswith("readme")),
        None,
    )
    readme_text = z.read(readme_name).decode("utf-8", errors="replace") if readme_name else ""

m = re.search(r"as of (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", readme_text)
if not m:
    sys.exit("Could not read the 'as of' data timestamp from the README inside the ZIP.")
SOURCE_TIMESTAMP = m.group(1)

# Link to Geofabrik's layer documentation, as given in the README inside the download.
doc_links = re.findall(r"https?://\S+?\.pdf", readme_text)
PUBLISHER_DOC = doc_links[0] if doc_links else "linked from the README inside the download"

# GDAL virtual path: GeoPandas reads the layers straight from the ZIP.
OSM_FILE = f"/vsizip/{ZIP_FILE}/{GPKG_MEMBER}"

print(f"Data as of: {SOURCE_TIMESTAMP}")
print(f"Publisher documentation: {PUBLISHER_DOC}")


# %% Helpers

def format_value(value, max_length=80):
    """Format a sample value for a Markdown table cell."""
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("|", "\\|").strip()
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def is_text(series):
    return series.dtype == object or str(series.dtype).startswith("string")


def filled_mask(series, is_geometry):
    """A value counts as filled if it is not NULL and, for text, not blank.
    OSM writes a missing name as '' rather than NULL, so NULL counts alone
    would overstate how complete the text columns are."""
    if is_geometry:
        return series.notna() & ~series.is_empty
    if is_text(series):
        return series.notna() & series.astype("string").str.strip().ne("")
    return series.notna()


def observed_type(series, is_geometry):
    if is_geometry:
        return ", ".join(sorted(series.geom_type.dropna().astype(str).unique())) or "geometry"
    return str(series.dtype)


def crs_label(crs):
    if crs is None:
        return "not set"
    authority = crs.to_authority()
    return ":".join(authority) if authority else crs.to_string()


def unknown_maxspeed(series):
    text = series.astype("string").str.strip().str.lower()
    return text.isna() | text.eq("") | text.isin(["0", "unknown", "none", "null", "nan"])


# %% Profile layers

profiles = {}

for layer in LAYERS:
    gdf = gpd.read_file(OSM_FILE, layer=layer, engine="pyogrio")
    geometry_column = gdf.geometry.name
    rows = []

    for column in gdf.columns:
        series = gdf[column]
        is_geometry = column == geometry_column
        filled = filled_mask(series, is_geometry)
        if column == "maxspeed":
            filled = ~unknown_maxspeed(series)  # 0 = no speed recorded; see profile S-6

        if is_geometry:
            samples = []
            distinct = None
        else:
            values = series[filled].drop_duplicates().head(3)
            samples = [format_value(v) for v in values]
            distinct = int(series[filled].nunique())

        rows.append(
            {
                "column": column,
                "is_geometry": is_geometry,
                "type": observed_type(series, is_geometry),
                "filled": int(filled.sum()),
                "filled_pct": filled.mean() * 100 if len(series) else 0,
                "distinct": distinct,
                "samples": samples,
            }
        )

    profiles[layer] = {
        "gdf": gdf,
        "rows": rows,
        "crs": crs_label(gdf.crs),
        "geometry_type": observed_type(gdf.geometry, True),
    }
    print(f"{layer}: {len(gdf):,} rows, {len(gdf.columns)} columns, CRS {profiles[layer]['crs']}")


# %% Figures used in the text (computed, never typed in)

points = profiles["gis_osm_pois_free"]["gdf"]
areas = profiles["gis_osm_pois_a_free"]["gdf"]
roads = profiles["gis_osm_roads_free"]["gdf"]

point_schools = points[points["fclass"].astype("string").str.lower().eq("school")]
area_schools = areas[areas["fclass"].astype("string").str.lower().eq("school")]
school_overlap = len(set(point_schools["osm_id"]) & set(area_schools["osm_id"]))
school_total = len(set(point_schools["osm_id"]) | set(area_schools["osm_id"]))

road_unique_ids = int(roads["osm_id"].nunique())
maxspeed_known = int((~unknown_maxspeed(roads["maxspeed"])).sum())
maxspeed_pct = maxspeed_known / len(roads) * 100 if len(roads) else 0


def name_blank_pct(gdf):
    filled = filled_mask(gdf["name"], False)
    return (1 - filled.mean()) * 100 if len(gdf) else 0


CRS_LABELS = sorted({p["crs"] for p in profiles.values()})

maxspeed_zero_pct = (
    roads["maxspeed"].astype("string").str.strip().eq("0").mean() * 100
    if len(roads) else 0
)
road_layer_min = int(roads["layer"].min())
road_layer_max = int(roads["layer"].max())


def observed_values(gdf, column):
    return ", ".join(f"`{v}`" for v in sorted(gdf[column].dropna().astype(str).unique()))


def code_matches_fclass(gdf):
    """The publisher says code and fclass carry the same information: one fclass per code and vice versa."""
    return (
        gdf.groupby("code")["fclass"].nunique().max() == 1
        and gdf.groupby("fclass")["code"].nunique().max() == 1
    )


# %% Publisher descriptions (D-011: the publisher's words only)
#
# Quoted from Geofabrik, "OpenStreetMap Data in Layered GIS Format // Free Shapefiles
# and GeoPackages", version 2026-04-02 (PUBLISHER_DOC), CC BY-SA 2.0. Section numbers
# refer to that document. Only the publisher's words go here; our readings go in
# interpretation() below.

PUBLISHER_DOC_TITLE = (
    "Geofabrik, \"OpenStreetMap Data in Layered GIS Format // Free Shapefiles and "
    "GeoPackages\", version 2026-04-02 (CC BY-SA 2.0)"
)

PUBLISHER_DESCRIPTIONS = {
    "osm_id": (
        "OSM ID taken from the ID of this feature (node_id, way_id, or relation_id) in the OSM "
        "database. In case several features in the OSM database are joined into one feature, this "
        "is one of the IDs. This ID is not necessarily unique because one OSM object can result in "
        "several geometry objects. (§2.5)"
    ),
    "code": (
        "4 digit code (between 1000 and 9999) defining the feature class. The first one or two "
        "digits define the layer, the last two or three digits the class inside a layer. (§2.5)"
    ),
    "fclass": (
        "Class name of this feature. This does not add any information that is not already in the "
        "\u201ccode\u201d field but it is better readable. (§2.5)"
    ),
    "name": (
        "Name of this feature, like a street or place name. If the name in OSM contains obviously "
        "wrong data such as \u201cfixme\u201d or \u201cnone\u201d, it will be empty. (§2.5)"
    ),
    "ref": "Reference number of this road ('A 5', 'L 605', ...) (§5.1)",
    "oneway": (
        "Is this a oneway road? \u201cF\u201d means that only driving in direction of the "
        "linestring is allowed. \u201cT\u201d means that only the opposite direction is allowed. "
        "\u201cB\u201d (default value) means that both directions are ok. (§5.1)"
    ),
    "maxspeed": "Max allowed speed in km/h (§5.1)",
    "layer": "Relative layering of roads (-5, ..., 0, ..., 5) (§5.1)",
    "bridge": "Is this road on a bridge? (\u201cT\u201d = true, \u201cF\u201d = false) (§5.1)",
    "tunnel": "Is this road in a tunnel? (\u201cT\u201d = true, \u201cF\u201d = false) (§5.1)",
    "geometry": "All coordinates are unprojected WGS84 (EPSG:4326). (§2.2)",
}


# %% Our interpretation (D-011: label, then evidence)

def interpretation(layer, column):
    poi = layer in {"gis_osm_pois_free", "gis_osm_pois_a_free"}
    gdf = profiles[layer]["gdf"]

    if column == "osm_id":
        if poi:
            return (
                "[observed] Not unique on its own in the POI layers: a feature with two categories "
                "appears once per category. `(osm_id, fclass)` is unique; `osm_id` is unique within "
                "the school subset. See profile O-6."
            )
        return f"[observed] Unique in the road layer ({road_unique_ids:,} distinct in {len(roads):,} rows). See profile O-8."

    if column == "fclass" and poi:
        return (
            f"[observed] Education classes present: `school`, `kindergarten`, `college`, `university`. "
            f"`school` has {len(point_schools if layer == 'gis_osm_pois_free' else area_schools):,} rows "
            "in this layer. `college` and `university` are out of scope (D-003). See profile O-5."
        )

    if column == "fclass":
        return "[observed] Road class; `maxspeed` coverage differs strongly by class. See profile O-9."

    if column == "name":
        return (
            f"[observed] Missing names are stored as '' (blank), not NULL: {name_blank_pct(gdf):.1f}% "
            "of rows in this layer are blank. Not a unique or standardized identifier, so it is not "
            "an exact join key to DepEd. See profile O-4."
        )

    if column == "maxspeed":
        return (
            f"[assumed] `0` means no speed limit is recorded in OSM. The publisher gives no rule for `0`, "
            f"but `0` is not a valid limit and is the value on {maxspeed_zero_pct:.1f}% of roads. "
            f"Under that reading, {maxspeed_pct:.2f}% of roads ({maxspeed_known:,}) have a speed, so travel "
            "time cannot come from `maxspeed` alone. See profile O-9 and S-6."
        )

    if column == "geometry":
        return (
            f"[observed] {profiles[layer]['geometry_type']}; the file declares {profiles[layer]['crs']}, "
            "the same WGS84 datum as the publisher's EPSG:4326 with longitude first. Degrees, not metres: "
            "reproject to a metre-based CRS before measuring distance."
        )

    if column == "code":
        same = code_matches_fclass(gdf)
        return (
            "[observed] Each `code` maps to exactly one `fclass` and back, as the publisher states."
            if same
            else "[observed] `code` and `fclass` do NOT map one-to-one in this layer, contrary to the publisher's description."
        )

    if column == "ref":
        return (
            f"[observed] Filled on {filled_mask(gdf['ref'], False).mean() * 100:.1f}% of roads; "
            "not used by the project."
        )

    if column == "oneway":
        return f"[observed] Values present: {observed_values(gdf, 'oneway')}. Only needed for network routing."

    if column == "layer":
        inside = -5 <= road_layer_min and road_layer_max <= 5
        return (
            f"[observed] Range {road_layer_min} to {road_layer_max}"
            + (", inside the documented -5 to 5." if inside else ", outside the documented -5 to 5.")
            + " Not used by the project."
        )

    if column in {"bridge", "tunnel"}:
        return f"[observed] Values present: {observed_values(gdf, column)}. Not used by the project."

    return ""


# %% Build data dictionary

lines = [
    "# osm_philippines: data dictionary",
    "",
    f"_Generated by `{SCRIPT_PATH}`. Do not edit by hand; change the script and rerun._",
    "",
    "## Source",
    "",
    f"- **Source:** {SOURCE_NAME}",
    "- **Publisher:** OpenStreetMap contributors; extract produced by Geofabrik",
    f"- **Data as of:** {SOURCE_TIMESTAMP} (from the README inside the download)",
    f"- **Raw source:** `{SOURCE_LABEL}`, read in place (`{GPKG_MEMBER}` inside the ZIP)",
    f"- **CRS:** {', '.join(CRS_LABELS)}",
    f"- **Publisher documentation:** {PUBLISHER_DOC_TITLE}, {PUBLISHER_DOC}. "
    "Descriptions (publisher) are quoted from it, with section numbers.",
    f"- **Generated by:** `{SCRIPT_PATH}`",
    f"- **Profile:** [`profile.md`](profile.md) · **Card:** [`README.md`](README.md)",
    "",
    "**Filled** counts values that are not NULL and, for text columns, not blank. "
    "OSM stores a missing name as '' rather than NULL (publisher §2.5), so NULL counts alone would "
    "overstate completeness. For `maxspeed`, `0` also counts as not filled (assumption, see profile S-6).",
    "",
]

for layer, profile in profiles.items():
    gdf = profile["gdf"]
    lines += [
        f"## `{layer}`",
        "",
        f"{len(gdf):,} rows, {len(gdf.columns)} columns, {profile['geometry_type']}, {profile['crs']}. "
        + (
            "One row is one mapped OSM feature per category (a feature with two categories has two rows)."
            if layer != "gis_osm_roads_free"
            else "One row is one mapped road or path."
        ),
        "",
        "| Column | Description (publisher) | Our interpretation | Observed type | Filled | Filled % | Distinct | Samples |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for item in profile["rows"]:
        column = item["column"]
        description = PUBLISHER_DESCRIPTIONS.get((layer, column)) or PUBLISHER_DESCRIPTIONS.get(column, "")
        distinct = "" if item["distinct"] is None else f"{item['distinct']:,}"
        lines.append(
            f"| `{column}` | {description} | {interpretation(layer, column)} | "
            f"`{item['type']}` | {item['filled']:,} | {item['filled_pct']:.1f}% | "
            f"{distinct} | {'; '.join(item['samples'])} |"
        )
    lines.append("")

lines += [
    "## Notes across layers",
    "",
    f"- [observed] Schools appear in both POI layers: {len(point_schools):,} points and "
    f"{len(area_schools):,} areas, with {school_overlap:,} shared `osm_id`, so {school_total:,} "
    "distinct mapped schools. Both layers must be used together.",
    "- [observed] No layer carries PSGC codes, addresses or Philippine school identifiers; "
    "features are assigned to administrative areas by spatial join (D-012).",
    "- [other source] OSM is not the official school inventory; DepEd is.",
    "",
]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Data dictionary written to: {OUTPUT}")
