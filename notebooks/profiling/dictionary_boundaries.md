# %%
"""
Administrative boundaries data dictionary

Purpose:
- Document the fields present in the ADM3 and ADM4 boundary datasets.
- Generate a reusable Markdown data dictionary.

Input:
    /Volumes/edu_access/00-source/raw/admin_boundaries/

Output:
    docs/source_inventory/admin_boundaries/data_dictionary.md
"""

# %%
from pathlib import Path

import geopandas as gpd

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
    / "data_dictionary.md"
)

FILES = {
    "ADM3": DATA_DIR / "phl_admin3.parquet",
    "ADM4": DATA_DIR / "phl_admin4.parquet",
}

# %%
# Field descriptions

DESCRIPTIONS = {
    "adm3_name": "Name of the city or municipality.",
    "adm3_name1": "Source-provided alternate or language-specific name for the city or municipality.",
    "adm3_name2": "Source-provided alternate or language-specific name for the city or municipality.",
    "adm3_name3": "Source-provided alternate or language-specific name for the city or municipality.",
    "adm3_pcode": "Administrative code assigned to the city or municipality in the source.",
    "adm2_name": "Name of the parent province.",
    "adm2_name1": "Source-provided alternate or language-specific name for the parent province.",
    "adm2_name2": "Source-provided alternate or language-specific name for the parent province.",
    "adm2_name3": "Source-provided alternate or language-specific name for the parent province.",
    "adm2_pcode": "Administrative code of the parent province.",
    "adm1_name": "Name of the parent region.",
    "adm1_name1": "Source-provided alternate or language-specific name for the parent region.",
    "adm1_name2": "Source-provided alternate or language-specific name for the parent region.",
    "adm1_name3": "Source-provided alternate or language-specific name for the parent region.",
    "adm1_pcode": "Administrative code of the parent region.",
    "adm0_name": "Name of the country.",
    "adm0_name1": "Source-provided alternate or language-specific country name.",
    "adm0_name2": "Source-provided alternate or language-specific country name.",
    "adm0_name3": "Source-provided alternate or language-specific country name.",
    "adm0_pcode": "Administrative code of the country.",
    "adm4_name": "Name of the barangay.",
    "adm4_name1": "Source-provided alternate or language-specific name for the barangay.",
    "adm4_name2": "Source-provided alternate or language-specific name for the barangay.",
    "adm4_name3": "Source-provided alternate or language-specific name for the barangay.",
    "adm4_pcode": "Administrative code assigned to the barangay in the source.",
    "valid_on": "Date from which the administrative boundary record or version is valid.",
    "valid_to": "End date of validity when provided by the source.",
    "area_sqkm": "Area of the administrative boundary in square kilometers.",
    "version": "Source dataset version.",
    "lang": "Primary language or name-language indicator provided by the source.",
    "lang1": "Source-provided language or name-language indicator.",
    "lang2": "Source-provided language or name-language indicator.",
    "lang3": "Source-provided language or name-language indicator.",
    "adm3_ref_name": "Reference name for the city or municipality.",
    "adm4_ref_name": "Reference name for the barangay.",
    "center_lat": "Latitude of the administrative area's representative center.",
    "center_lon": "Longitude of the administrative area's representative center.",
    "geometry": "Polygon or MultiPolygon geometry representing the administrative boundary.",
}

# %%
# Load datasets

for level, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {level} file:\n{path}"
        )

adm3 = gpd.read_parquet(FILES["ADM3"])
adm4 = gpd.read_parquet(FILES["ADM4"])

print("Administrative boundary files loaded.")

# %%
# Helper function

def build_dictionary(gdf, level):
    """Build data dictionary rows from the observed dataset schema."""

    rows = []

    for column in gdf.columns:
        dtype = str(gdf[column].dtype)

        description = DESCRIPTIONS.get(
            column,
            "Source-provided field; meaning should be confirmed from source metadata.",
        )

        rows.append(
            (
                column,
                dtype,
                description,
            )
        )

    return rows

# %%
# Build dictionaries

adm3_dictionary = build_dictionary(adm3, "ADM3")
adm4_dictionary = build_dictionary(adm4, "ADM4")

# %%
# Generate Markdown

profile_date = "2026-10-02"

lines = []

lines.append("# Philippine administrative boundaries data dictionary")
lines.append("")
lines.append("## Purpose")
lines.append("")
lines.append(
    "This data dictionary documents the fields observed in the "
    "Philippine administrative boundary datasets used by the "
    "Education Access Intelligence project."
)
lines.append("")
lines.append(
    "The dictionary covers:"
)
lines.append("")
lines.append("1. City/municipality boundaries (ADM3)")
lines.append("2. Barangay boundaries (ADM4)")
lines.append("")
lines.append(
    "The field names and data types are generated from the observed "
    "GeoParquet schemas. Field descriptions are based on the source "
    "structure and observed administrative hierarchy."
)
lines.append("")

# %%
# ADM3 section

lines.append("## ADM3 — City/Municipality")
lines.append("")
lines.append(
    f"Source file: `{FILES['ADM3']}`"
)
lines.append("")
lines.append(
    f"Rows profiled: **{len(adm3):,}**"
)
lines.append("")
lines.append(
    "| Column | Data type | Description |"
)
lines.append("| --- | --- | --- |")

for column, dtype, description in adm3_dictionary:
    lines.append(
        f"| `{column}` | `{dtype}` | {description} |"
    )

lines.append("")

# %%
# ADM4 section

lines.append("## ADM4 — Barangay")
lines.append("")
lines.append(
    f"Source file: `{FILES['ADM4']}`"
)
lines.append("")
lines.append(
    f"Rows profiled: **{len(adm4):,}**"
)
lines.append("")
lines.append(
    "| Column | Data type | Description |"
)
lines.append("| --- | --- | --- |")

for column, dtype, description in adm4_dictionary:
    lines.append(
        f"| `{column}` | `{dtype}` | {description} |"
    )

lines.append("")

# %%
# Notes

lines.append("## Notes")
lines.append("")
lines.append(
    "- `adm3_*` fields describe city/municipality-level information."
)
lines.append(
    "- `adm4_*` fields describe barangay-level information."
)
lines.append(
    "- `adm2_*` fields identify the parent province."
)
lines.append(
    "- `adm1_*` fields identify the parent region."
)
lines.append(
    "- `geometry` contains the administrative boundary geometry."
)
lines.append(
    "- Source administrative codes are preserved as provided and "
    "are not modified in the source layer."
)
lines.append(
    "- PSGC compatibility is documented separately in the source profile."
)
lines.append("")

lines.append("## Reproducibility")
lines.append("")
lines.append(
    f"Generated by: `notebooks/profiling/data_dictionary_admin_boundaries.py`"
)
lines.append("")
lines.append(
    f"Generated from source files under: "
    f"`{DATA_DIR}/`"
)
lines.append("")
lines.append(
    f"Generated on: **{profile_date}**"
)

# %%
# Write output

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print("Data dictionary generated.")
print(f"Output: {OUTPUT}")