# %%
"""
Administrative boundaries source profiling

Purpose:
- Profile Philippine administrative boundary data:
    1. City/municipality boundaries (ADM3)
    2. Barangay boundaries (ADM4)

Source files:
    /Volumes/edu_access/00-source/raw/admin_boundaries/

Output:
    docs/source_inventory/admin_boundaries/profile.md
"""

# %%
from pathlib import Path

import geopandas as gpd
import pandas as pd


# %%
# Paths

DATA_DIR = Path(
    "/Volumes/edu_access/00-source/raw/admin_boundaries"
)

REPO = Path.cwd()

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "admin_boundaries"
    / "profile.md"
)

PSGC_FILE = Path(
    "/Volumes/edu_access/00-source/raw/psa/PSGC-2Q-2026-Publication-Datafile.xlsx"
)


# %%
# Input files

FILES = {
    "adm3": DATA_DIR / "phl_admin3.parquet",
    "adm4": DATA_DIR / "phl_admin4.parquet",
}


# %%
# Helper functions

def format_table(headers, data):
    """Create a simple Markdown table."""
    lines = []

    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in data:
        lines.append(
            "| "
            + " | ".join(
                "" if value is None else str(value)
                for value in row
            )
            + " |"
        )

    return "\n".join(lines)


def file_size_mb(path):
    """Return file size in MB."""
    return path.stat().st_size / (1024 * 1024)


# %%
# Check input files

for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {name} file:\n{path}"
        )

if not PSGC_FILE.exists():
    raise FileNotFoundError(
        f"Missing PSGC file:\n{PSGC_FILE}"
    )

print("Administrative boundary files found.")

for name, path in FILES.items():
    print(f"- {name}: {path}")

print(f"- PSGC: {PSGC_FILE}")


# %%
# Load source files

adm3 = gpd.read_parquet(FILES["adm3"])
adm4 = gpd.read_parquet(FILES["adm4"])

print("Administrative boundary files loaded.")


# %%
# O-1. Extracted file structure

file_rows = []

for key, path in FILES.items():
    gdf = adm3 if key == "adm3" else adm4

    file_rows.append(
        (
            key.upper(),
            path.name,
            str(path),
            f"{file_size_mb(path):.2f}",
            len(gdf),
        )
    )

file_table = format_table(
    [
        "Layer",
        "File",
        "Path",
        "File size (MB)",
        "Rows",
    ],
    file_rows,
)


# %%
# O-2. Schema

adm3_columns = list(adm3.columns)
adm4_columns = list(adm4.columns)

adm3_schema = [
    (column, str(adm3[column].dtype))
    for column in adm3.columns
]

adm4_schema = [
    (column, str(adm4[column].dtype))
    for column in adm4.columns
]

adm3_schema_table = format_table(
    ["Column", "Data type"],
    adm3_schema,
)

adm4_schema_table = format_table(
    ["Column", "Data type"],
    adm4_schema,
)


# %%
# O-3. Row counts and geographic coverage

adm3_row_count = len(adm3)
adm4_row_count = len(adm4)

adm3_code_count = adm3["adm3_pcode"].nunique()
adm4_code_count = adm4["adm4_pcode"].nunique()


# %%
# O-4. Administrative code uniqueness

adm3_duplicate_codes = (
    adm3["adm3_pcode"]
    .duplicated()
    .sum()
)

adm4_duplicate_codes = (
    adm4["adm4_pcode"]
    .duplicated()
    .sum()
)


# %%
# O-5. Missing administrative identifiers

adm3_missing_code = (
    adm3["adm3_pcode"]
    .isna()
    .sum()
)

adm4_missing_code = (
    adm4["adm4_pcode"]
    .isna()
    .sum()
)

adm3_missing_name = (
    adm3["adm3_name"]
    .isna()
    .sum()
)

adm4_missing_name = (
    adm4["adm4_name"]
    .isna()
    .sum()
)


# %%
# O-6. Geometry types

adm3_geometry_counts = (
    adm3.geometry
    .geom_type
    .value_counts()
    .sort_index()
)

adm4_geometry_counts = (
    adm4.geometry
    .geom_type
    .value_counts()
    .sort_index()
)

adm3_geometry_table = format_table(
    ["Geometry type", "Records"],
    [
        (geometry_type, count)
        for geometry_type, count
        in adm3_geometry_counts.items()
    ],
)

adm4_geometry_table = format_table(
    ["Geometry type", "Records"],
    [
        (geometry_type, count)
        for geometry_type, count
        in adm4_geometry_counts.items()
    ],
)


# %%
# O-7. Coordinate reference system

adm3_crs_name = (
    adm3.crs.name
    if adm3.crs
    else None
)

adm4_crs_name = (
    adm4.crs.name
    if adm4.crs
    else None
)

adm3_epsg = (
    adm3.crs.to_epsg()
    if adm3.crs
    else None
)

adm4_epsg = (
    adm4.crs.to_epsg()
    if adm4.crs
    else None
)


# %%
# O-8. Geometry validity

adm3_empty_geometry = (
    adm3.geometry.is_empty
    .sum()
)

adm4_empty_geometry = (
    adm4.geometry.is_empty
    .sum()
)

adm3_invalid_geometry = (
    (~adm3.geometry.is_valid)
    .sum()
)

adm4_invalid_geometry = (
    (~adm4.geometry.is_valid)
    .sum()
)

adm3_missing_geometry = (
    adm3.geometry.isna()
    .sum()
)

adm4_missing_geometry = (
    adm4.geometry.isna()
    .sum()
)


# %%
# O-9. Administrative hierarchy

adm4_missing_parent_adm3 = (
    adm4["adm3_pcode"]
    .isna()
    .sum()
)

adm4_parent_adm3_count = (
    adm4["adm3_pcode"]
    .nunique()
)

adm3_province_count = (
    adm3["adm2_pcode"]
    .nunique()
)

adm3_region_count = (
    adm3["adm1_pcode"]
    .nunique()
)


# %%
# O-10. Source metadata

adm3_valid_on = (
    adm3["valid_on"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

adm4_valid_on = (
    adm4["valid_on"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

adm3_versions = (
    adm3["version"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

adm4_versions = (
    adm4["version"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


# %%
# O-11. PSGC compatibility

# Load the current PSGC publication datafile.
psgc = pd.read_excel(
    PSGC_FILE,
    sheet_name="PSGC",
)

# Keep only city and municipality records because
# ADM3 represents cities and municipalities.
psgc_city_mun = psgc[
    psgc["Geographic Level"].isin(["City", "Mun"])
].copy()

# The boundary source uses codes such as:
# PH0102802
#
# The PSGC uses 10-digit codes such as:
# 0102802000
#
# Convert the boundary code into the corresponding
# 10-digit structure for the exact-code comparison.

adm3_psgc_codes = (
    adm3["adm3_pcode"]
    .astype(str)
    .str.replace(r"^PH", "", regex=True)
    .str.zfill(7)
    .add("000")
)

# Read PSGC codes as strings so leading zeros are preserved.
psgc_codes = (
    psgc_city_mun["10-digit PSGC"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(10)
)

psgc_code_set = set(psgc_codes)

# Count boundary records whose converted code
# exists exactly in the current PSGC city/municipality list.
adm3_exact_psgc_matches = (
    adm3_psgc_codes.isin(psgc_code_set)
    .sum()
)

adm3_psgc_mismatches = (
    adm3_row_count
    - adm3_exact_psgc_matches
)

adm3_psgc_match_rate = (
    adm3_exact_psgc_matches / adm3_row_count
    if adm3_row_count
    else 0
)


# %%
# Build profile Markdown

profile_md = f"""# Philippine administrative boundaries source profile

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

{file_table}

## O-2. Schema

### ADM3 — city/municipality

{adm3_schema_table}

Observed columns:

`{", ".join(adm3_columns)}`

### ADM4 — barangay

{adm4_schema_table}

Observed columns:

`{", ".join(adm4_columns)}`

## O-3. Row counts and geographic coverage

### ADM3

- Row count: **{adm3_row_count:,}**
- Unique administrative codes: **{adm3_code_count:,}**

### ADM4

- Row count: **{adm4_row_count:,}**
- Unique administrative codes: **{adm4_code_count:,}**

The ADM3 layer represents city/municipality boundaries.
The ADM4 layer represents barangay boundaries.

## O-4. Administrative code uniqueness

### ADM3

- Duplicate `adm3_pcode` records: **{adm3_duplicate_codes:,}**

### ADM4

- Duplicate `adm4_pcode` records: **{adm4_duplicate_codes:,}**

Each observed administrative code is unique within its respective layer.

## O-5. Missing administrative identifiers

### ADM3

- Missing `adm3_pcode`: **{adm3_missing_code:,}**
- Missing `adm3_name`: **{adm3_missing_name:,}**

### ADM4

- Missing `adm4_pcode`: **{adm4_missing_code:,}**
- Missing `adm4_name`: **{adm4_missing_name:,}**

## O-6. Geometry types

### ADM3

{adm3_geometry_table}

### ADM4

{adm4_geometry_table}

The boundary layers contain Polygon and MultiPolygon geometries.

## O-7. Coordinate reference system

### ADM3

- CRS: **{adm3_crs_name}**
- EPSG: **{adm3_epsg}**

### ADM4

- CRS: **{adm4_crs_name}**
- EPSG: **{adm4_epsg}**

Both layers use WGS 84 / EPSG:4326.

## O-8. Geometry validity

### ADM3

- Missing geometries: **{adm3_missing_geometry:,}**
- Empty geometries: **{adm3_empty_geometry:,}**
- Invalid geometries: **{adm3_invalid_geometry:,}**

### ADM4

- Missing geometries: **{adm4_missing_geometry:,}**
- Empty geometries: **{adm4_empty_geometry:,}**
- Invalid geometries: **{adm4_invalid_geometry:,}**

## O-9. Administrative hierarchy

### ADM3

- Distinct provinces represented by `adm2_pcode`: **{adm3_province_count:,}**
- Distinct regions represented by `adm1_pcode`: **{adm3_region_count:,}**

### ADM4

- Distinct parent city/municipality codes: **{adm4_parent_adm3_count:,}**
- Missing parent `adm3_pcode`: **{adm4_missing_parent_adm3:,}**

The ADM4 layer contains the parent city/municipality code needed
to relate barangays to their corresponding ADM3 area.

## O-10. Source metadata

### ADM3

- `valid_on` values: **{", ".join(adm3_valid_on)}**
- `version` values: **{", ".join(adm3_versions)}**

### ADM4

- `valid_on` values: **{", ".join(adm4_valid_on)}**
- `version` values: **{", ".join(adm4_versions)}**

## O-11. PSGC compatibility

The ADM3 administrative codes were compared with the current
Philippine Standard Geographic Code (PSGC) 2Q 2026 publication
datafile.

The boundary source uses `adm3_pcode` values such as `PH0102802`,
while the PSGC uses 10-digit codes such as `0102802000`. The
boundary codes were structurally converted to the equivalent
10-digit format for this compatibility check.

- Boundary ADM3 records checked: **{adm3_row_count:,}**
- PSGC city/municipality records: **{len(psgc_city_mun):,}**
- Exact code matches: **{adm3_exact_psgc_matches:,}**
- Code mismatches: **{adm3_psgc_mismatches:,}**
- Exact code match rate: **{adm3_psgc_match_rate:.2%}**

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
{adm3_exact_psgc_matches:,} of {adm3_row_count:,} ADM3 records.

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
"""


# %%
# Write profile

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    profile_md,
    encoding="utf-8",
)

print(f"Profile written to: {OUTPUT}")


# %%
# Summary

print()
print("Administrative boundary profiling complete.")
print()

print(f"ADM3 rows:               {adm3_row_count:,}")
print(f"ADM3 unique codes:       {adm3_code_count:,}")
print(f"ADM3 duplicate codes:    {adm3_duplicate_codes:,}")
print(f"ADM3 invalid geometries: {adm3_invalid_geometry:,}")

print()

print(f"ADM4 rows:               {adm4_row_count:,}")
print(f"ADM4 unique codes:       {adm4_code_count:,}")
print(f"ADM4 duplicate codes:    {adm4_duplicate_codes:,}")
print(f"ADM4 invalid geometries: {adm4_invalid_geometry:,}")

print()

print(f"PSGC City/Mun records:   {len(psgc_city_mun):,}")
print(f"PSGC exact matches:      {adm3_exact_psgc_matches:,}")
print(f"PSGC code mismatches:    {adm3_psgc_mismatches:,}")
print(f"PSGC exact match rate:   {adm3_psgc_match_rate:.2%}")

print()

print(f"Output: {OUTPUT}")