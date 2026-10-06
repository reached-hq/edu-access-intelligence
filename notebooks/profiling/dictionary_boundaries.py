# %%
"""
Administrative boundaries data dictionary

Purpose:
- Document the fields present in the ADM3 and ADM4 boundary datasets.
- Generate a reusable Markdown data dictionary.
- Keep publisher documentation separate from the team's interpretation.

Input:
    RAW_DATA_DIR/admin_boundaries/

Output:
    docs/source_inventory/hdx_boundaries/data_dictionary.md
"""

# %%
from datetime import date
from pathlib import Path
import hashlib
import os


import geopandas as gpd
import pandas as pd


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
# Resolve raw data directory


def env_value(name):
    """Read a variable from the environment, else from the repo .env."""
    if os.environ.get(name):
        return os.environ[name]

    env = REPO / ".env"

    for line in (
        env.read_text(encoding="utf-8").splitlines()
        if env.exists()
        else []
    ):
        key, _, value = line.partition("=")

        if key.strip() == name and value.strip():
            return value.strip()

    return None


def on_databricks():
    return (
        bool(os.environ.get("DATABRICKS_RUNTIME_VERSION"))
        or Path("/databricks").exists()
    )


def resolve_raw_data_dir():
    """Resolve RAW_DATA_DIR using the project convention."""

    value = env_value("RAW_DATA_DIR")

    if value:
        return Path(value).expanduser(), "RAW_DATA_DIR"

    if on_databricks():
        return (
            Path("/Volumes/edu_access/00-source/raw"),
            "Databricks team volume (D-009)",
        )

    raise SystemExit(
        "Set RAW_DATA_DIR to the folder that contains admin_boundaries/.\n"
        f"Looked in the environment and in {REPO / '.env'}."
    )


RAW_DIR, RAW_DIR_FROM = resolve_raw_data_dir()

DATA_DIR = RAW_DIR / "admin_boundaries"

print(f"Raw data folder: {DATA_DIR} (from {RAW_DIR_FROM})")


# %%
# Paths

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "hdx_boundaries"
    / "data_dictionary.md"
)

FILES = {
    "ADM3": DATA_DIR / "phl_admin3.geojson",
    "ADM4": DATA_DIR / "phl_admin4.geojson",
}


# %%
# Source metadata

SOURCE_NAME = (
    "Common Operational Dataset – Administrative Boundaries "
    "(COD-AB), Philippines"
)

PUBLISHER = "UN OCHA"

SOURCE_URL = "https://data.humdata.org/dataset/cod-ab-phl"

PROFILE_PATH = (
    "docs/source_inventory/hdx_boundaries/profile.md"
)

README_PATH = (
    "docs/source_inventory/hdx_boundaries/README.md"
)

SCRIPT_PATH = (
    "notebooks/profiling/dictionary_boundaries.py"
)

PROFILE_DATE = date.today().isoformat()


# %%
# Expected source files and SHA-256

EXPECTED_SHA256 = {
    "ADM3": (
        "f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41"
    ),
    "ADM4": (
        "4ebb5e3cf7b3245c659ea5886725e6a77ffc2d4bcbe3963d8f704d5adc5523d2"
    ),
}


# %%
# Publisher documentation

# No retained publisher document currently provides column-level
# descriptions for these GeoJSON fields. Therefore publisher descriptions
# are not inferred here. Team interpretation is kept separately below.

UNDOCUMENTED = (
    "Not in the publisher's documentation (undocumented)"
)


def documentation(column):
    """Return publisher type, description, and publisher notes."""

    return (
        "Not stated in retained publisher documentation",
        UNDOCUMENTED,
        "",
    )


# %%
# SHA-256 helper

def sha256_file(path):
    """Return SHA-256 checksum for a file."""

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


# %%
# Check source files before reading anything

for level, path in FILES.items():

    if not path.exists():
        raise FileNotFoundError(
            f"Missing {level} file:\n{path}"
        )

    actual_sha256 = sha256_file(path)
    expected_sha256 = EXPECTED_SHA256[level]

    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"{level} SHA-256 mismatch.\n"
            f"Expected: {expected_sha256}\n"
            f"Actual:   {actual_sha256}\n"
            f"File:     {path}"
        )

    print(
        f"{level}: SHA-256 verified "
        f"({actual_sha256})"
    )


# %%
# Load datasets

adm3 = gpd.read_file(
    FILES["ADM3"]
)

adm4 = gpd.read_file(
    FILES["ADM4"]
)

print("Administrative boundary files loaded.")


# %%
# Team interpretation

def interpretation(column, gdf, level):
    """Return team interpretation with evidence where supported."""

    filled = int(gdf[column].notna().sum())
    distinct = int(gdf[column].dropna().nunique())

    # Administrative codes
    if column == "adm3_pcode":
        return (
            f"[observed] {distinct:,} distinct values across "
            f"{len(gdf):,} ADM3 records; the field is used as the "
            f"source ADM3 administrative code in the profile (O-4)."
        )

    if column == "adm4_pcode":
        return (
            f"[observed] {distinct:,} distinct values across "
            f"{len(gdf):,} ADM4 records; the field is used as the "
            f"source ADM4 administrative code in the profile (O-4)."
        )

    # Parent administrative codes
    if column == "adm2_pcode":
        return (
            f"[observed] Filled in {filled:,}/{len(gdf):,} records "
            f"and used in the observed administrative hierarchy "
            f"as the parent ADM2 code (O-9)."
        )

    if column == "adm1_pcode":
        return (
            f"[observed] Filled in {filled:,}/{len(gdf):,} records "
            f"and used in the observed administrative hierarchy "
            f"as the parent ADM1 code (O-9)."
        )

    if column == "adm0_pcode":
        return (
            f"[observed] Filled in {filled:,}/{len(gdf):,} records "
            f"and represents the country-level code field present "
            f"in the source hierarchy."
        )

    # Names
    if column in {
        "adm3_name",
        "adm4_name",
        "adm2_name",
        "adm1_name",
        "adm0_name",
    }:
        return (
            f"[observed] Filled in {filled:,}/{len(gdf):,} records."
        )

    # Geometry
    if column == "geometry":
        geometry_counts = (
            gdf.geometry.geom_type
            .value_counts()
            .sort_index()
            .to_dict()
        )

        geometry_summary = ", ".join(
            f"{kind}={count:,}"
            for kind, count in geometry_counts.items()
        )

        return (
            f"[observed] Geometry types: {geometry_summary}. "
            f"Geometry validation found no missing, empty, or invalid "
            f"geometries in the profile (O-6, O-8)."
        )

    # Source metadata
    if column == "valid_on":
        return (
            "[observed] The retained boundary files report "
            "`2025-02-13` as the `valid_on` value (O-10)."
        )

    if column == "valid_to":
        return (
            f"[observed] Field is present and filled in "
            f"{filled:,}/{len(gdf):,} records; exact publisher "
            f"semantics for the field are not documented."
        )

    if column == "version":
        return (
            "[observed] The retained boundary files report "
            "`v03` as the source version (O-10)."
        )

    # Numeric geographic fields
    if column in {
        "area_sqkm",
        "center_lat",
        "center_lon",
    }:
        numeric = pd.to_numeric(
            gdf[column],
            errors="coerce",
        ).dropna()

        if not numeric.empty:
            return (
                f"[observed] Numeric values are present in "
                f"{len(numeric):,}/{len(gdf):,} records; "
                f"min={numeric.min():g}, "
                f"median={numeric.median():g}, "
                f"max={numeric.max():g}."
            )

    return ""


# %%
# Observation helpers

def escape_markdown(value):
    """Keep generated Markdown table cells valid."""

    if value is None:
        return ""

    value = str(value)

    return (
        value
        .replace("|", "\\|")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def observe(series, column):
    """
    Summarize an observed column.

    Returns:
        kind, filled, distinct, samples_or_range
    """

    total = len(series)

    if total == 0:
        return (
            "all blank",
            "0.00%",
            0,
            "",
        )

    nonblank = series.dropna()
    filled_count = len(nonblank)

    filled_rate = (
        filled_count / total * 100
    )

    filled = f"{filled_rate:.2f}%"

    distinct = int(
        nonblank.nunique()
    )

    # Geometry
    if column == "geometry":
        geometry_types = (
            nonblank.geom_type
            .value_counts()
            .sort_index()
        )

        samples = "; ".join(
            f"{kind}: {count:,}"
            for kind, count in geometry_types.items()
        )

        return (
            "geometry",
            filled,
            distinct,
            samples,
        )

    if nonblank.empty:
        return (
            "all blank",
            filled,
            distinct,
            "",
        )

    # Date fields
    if column in {"valid_on", "valid_to"}:
        dates = pd.to_datetime(
            nonblank,
            errors="coerce",
        ).dropna()

        if not dates.empty:
            return (
                "date",
                filled,
                distinct,
                f"{dates.min().date()} to "
                f"{dates.max().date()}",
            )

    # Numeric fields
    numeric = pd.to_numeric(
        nonblank,
        errors="coerce",
    )

    if numeric.notna().sum() == len(nonblank):

        numeric = numeric.dropna()

        if not numeric.empty:
            zero_count = int(
                (numeric == 0).sum()
            )

            return (
                "numeric",
                filled,
                distinct,
                (
                    f"min={numeric.min():g}; "
                    f"median={numeric.median():g}; "
                    f"max={numeric.max():g}; "
                    f"zeros={zero_count:,}"
                ),
            )

    # Small categorical fields
    value_counts = (
        nonblank
        .astype(str)
        .value_counts()
        .sort_index()
    )

    if distinct <= 20:
        samples = "; ".join(
            f"{value} ({count:,})"
            for value, count in value_counts.items()
        )

        return (
            "category",
            filled,
            distinct,
            samples,
        )

    # Text fields
    top_values = (
        nonblank
        .astype(str)
        .value_counts()
        .head(3)
    )

    samples = "; ".join(
        f"{value} ({count:,})"
        for value, count in top_values.items()
    )

    return (
        "text",
        filled,
        distinct,
        samples,
    )


# %%
# Build dictionary rows

def build_dictionary(gdf, level):
    """Build approved data-dictionary rows from the observed schema."""

    rows = []

    for column in gdf.columns:

        publisher_type, description, publisher_notes = (
            documentation(column)
        )

        our_interpretation = interpretation(
            column,
            gdf,
            level,
        )

        kind, filled, distinct, samples = observe(
            gdf[column],
            column,
        )

        rows.append(
            (
                column,
                publisher_type,
                description,
                publisher_notes,
                our_interpretation,
                kind,
                filled,
                distinct,
                samples,
            )
        )

    return rows


# %%
# Build dictionaries

adm3_dictionary = build_dictionary(
    adm3,
    "ADM3",
)

adm4_dictionary = build_dictionary(
    adm4,
    "ADM4",
)


# %%
# Generate Markdown

lines = []

lines.append(
    "# hdx_boundaries: data dictionary"
)
lines.append("")

lines.append(
    f"Generated by `{SCRIPT_PATH}`. "
    "Do not edit by hand; rerun the script instead."
)
lines.append("")

lines.append(
    "- **Description, publisher type, and publisher notes:** "
    "No retained publisher document currently provides "
    "column-level descriptions for these GeoJSON fields. "
    "The publisher description column therefore uses the "
    "required undocumented label rather than team inference."
)
lines.append(
    "- **Our interpretation:** team interpretation is kept "
    "separate from publisher documentation. Every non-blank "
    "interpretation uses an evidence label such as "
    "**[observed]**."
)
lines.append(
    "- **Observed columns:** measured from the retained ADM3 "
    "and ADM4 GeoJSON files. Filled is the share of rows that "
    "are not blank."
)
lines.append(
    "- **Kinds:** numeric, date, category, text, geometry, "
    "or all blank. Geometry fields are summarized by geometry type."
)
lines.append("")

lines.append(
    "This source contains two retained GeoJSON layers: "
    "ADM3 city/municipality boundaries and ADM4 barangay "
    "boundaries. The dictionary is separated by layer."
)
lines.append("")

lines.append(
    f"See [profile.md]({PROFILE_PATH}) for findings and "
    f"[README.md]({README_PATH}) for the source card."
)
lines.append("")


# %%
# Source details

lines.append("## Source")
lines.append("")

lines.append(
    f"- **Source name:** {SOURCE_NAME}"
)
lines.append(
    f"- **Publisher:** {PUBLISHER}"
)
lines.append(
    f"- **Source URL:** {SOURCE_URL}"
)
lines.append(
    "- **Retained format:** GeoJSON"
)
lines.append(
    "- **Coordinate reference system:** EPSG:4326 / WGS 84"
)
lines.append("")


# %%
# File verification details

lines.append("## Retained files")
lines.append("")

lines.append(
    "| File | Rows | Size (bytes) | SHA-256 |"
)
lines.append(
    "|---|---:|---:|---|"
)

for level, path in FILES.items():

    size_bytes = path.stat().st_size
    sha256 = sha256_file(path)

    gdf = (
        adm3
        if level == "ADM3"
        else adm4
    )

    lines.append(
        f"| `{path.name}` | "
        f"{len(gdf):,} | "
        f"{size_bytes:,} | "
        f"`{sha256}` |"
    )

lines.append("")


# %%
# ADM3 section

lines.append(
    "## ADM3 — City/Municipality"
)
lines.append("")

lines.append(
    f"Source file: `{FILES['ADM3'].name}`"
)
lines.append("")

lines.append(
    f"Rows observed: **{len(adm3):,}**"
)
lines.append("")

lines.append(
    "| Column | Publisher type | Description (publisher) | "
    "Publisher notes | Our interpretation | Observed kind | "
    "Filled | Distinct | Samples or range |"
)

lines.append(
    "|---|---|---|---|---|---|---:|---:|---|"
)

for row in adm3_dictionary:

    (
        column,
        publisher_type,
        description,
        publisher_notes,
        our_interpretation,
        kind,
        filled,
        distinct,
        samples,
    ) = row

    lines.append(
        "| "
        + " | ".join(
            [
                f"`{escape_markdown(column)}`",
                escape_markdown(publisher_type),
                escape_markdown(description),
                escape_markdown(publisher_notes),
                escape_markdown(our_interpretation),
                escape_markdown(kind),
                escape_markdown(filled),
                escape_markdown(f"{distinct:,}"),
                escape_markdown(samples),
            ]
        )
        + " |"
    )

lines.append("")


# %%
# ADM4 section

lines.append(
    "## ADM4 — Barangay"
)
lines.append("")

lines.append(
    f"Source file: `{FILES['ADM4'].name}`"
)
lines.append("")

lines.append(
    f"Rows observed: **{len(adm4):,}**"
)
lines.append("")

lines.append(
    "| Column | Publisher type | Description (publisher) | "
    "Publisher notes | Our interpretation | Observed kind | "
    "Filled | Distinct | Samples or range |"
)

lines.append(
    "|---|---|---|---|---|---|---:|---:|---|"
)

for row in adm4_dictionary:

    (
        column,
        publisher_type,
        description,
        publisher_notes,
        our_interpretation,
        kind,
        filled,
        distinct,
        samples,
    ) = row

    lines.append(
        "| "
        + " | ".join(
            [
                f"`{escape_markdown(column)}`",
                escape_markdown(publisher_type),
                escape_markdown(description),
                escape_markdown(publisher_notes),
                escape_markdown(our_interpretation),
                escape_markdown(kind),
                escape_markdown(filled),
                escape_markdown(f"{distinct:,}"),
                escape_markdown(samples),
            ]
        )
        + " |"
    )

lines.append("")


# %%
# Our interpretation guide

lines.append(
    "## Our interpretation"
)
lines.append("")

lines.append(
    "This column keeps the team's reading of a column separate "
    "from the publisher's words, so a reader always knows who "
    "said what."
)
lines.append("")

lines.append(
    "| Label | Use when | Evidence to give |"
)
lines.append(
    "|---|---|---|"
)
lines.append(
    "| **[other source]** | Another authoritative document "
    "explains it | Document and section |"
)
lines.append(
    "| **[observed]** | The data shows it clearly | Numbers "
    "or finding ID in `profile.md` |"
)
lines.append(
    "| **[assumed]** | Reasonable reading but not proven | "
    "What the assumption rests on |"
)
lines.append("")

lines.append(
    "For this source, undocumented field meanings are not "
    "presented as publisher descriptions. Interpretations are "
    "only added where they can be supported by observed data "
    "or existing profile findings."
)
lines.append("")


# %%
# Reproducibility

lines.append(
    "## Reproducibility"
)
lines.append("")

lines.append(
    f"- **Generated by:** `{SCRIPT_PATH}`"
)
lines.append(
    f"- **Generated on:** **{PROFILE_DATE}**"
)
lines.append(
    "- **Source directory:** `RAW_DATA_DIR/admin_boundaries/`"
)
lines.append(
    "- **ADM3 SHA-256 verified before reading:** "
    f"`{EXPECTED_SHA256['ADM3']}`"
)
lines.append(
    "- **ADM4 SHA-256 verified before reading:** "
    f"`{EXPECTED_SHA256['ADM4']}`"
)
lines.append("")

lines.append(
    "The script verifies each retained source file's SHA-256 "
    "before reading the GeoJSON files. Rerunning the script "
    "against the same files regenerates the dictionary from "
    "the observed source schema and values."
)
lines.append("")


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