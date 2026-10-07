# %%
"""
Administrative boundaries source profiling

Profiles the retained Philippine administrative boundary GeoJSON extracts.

Generates:
    docs/data/source-inventory/hdx_boundaries/profile.md

The script verifies the SHA-256 of every input file against the value
recorded on the inventory cards, then loads the ADM3 and ADM4 GeoJSON files
and profiles their structure, identifiers, geometry, hierarchy, source
metadata, and compatibility with the current PSGC publication.

Runs locally (D-007). Open it in VS Code to run cell by cell (# %% markers),
or run the whole file:
    RAW_DATA_DIR=~/Documents/GitHub/raw-data python analysis/profiling/profile_boundaries.py

RAW_DATA_DIR (environment or the repo's .env) must contain:
    admin_boundaries/phl_admin3.geojson
    admin_boundaries/phl_admin4.geojson
    psa/original/PSGC-2Q-2026-Publication-Datafile.xlsx  (the file on the PSGC card)

Alternative: run on Databricks. Open this file from the team Git folder and
run all cells. RAW_DATA_DIR is optional there: if it is not set, the script
falls back to the team raw volume /Volumes/edu_access/00-source/raw (D-009).
Databricks compute is shared Free Edition capacity, so prefer a local run (D-008).

Findings:
    O-1  Extracted file structure
    O-2  Schema
    O-3  Row counts and geographic coverage
    O-4  Administrative code uniqueness
    O-5  Missing administrative identifiers
    O-6  Geometry types
    O-7  Coordinate reference system
    O-8  Geometry validity
    O-9  Administrative hierarchy
    O-10 Source metadata
    O-11 ADM3 code compatibility with PSGC

Suspected findings:
    S-1  Boundary codes may require a validated PSGC crosswalk
    S-2  Boundary source version may differ from current PSGC
    S-3  Spatial joins should be performed using geometry rather than names
"""


# %% Setup

import hashlib
import os
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd


def find_repo():
    """Repo root: from this file's location, or by searching upward from
    the working folder when run cell by cell."""
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
        "Set RAW_DATA_DIR to the folder that contains admin_boundaries/ and psa/.\n"
        f"Looked in the environment and in {REPO / '.env'}."
    )


RAW_DIR, RAW_DIR_FROM = resolve_raw_data_dir()
RUN_ON = "run on Databricks" if on_databricks() else "run locally"
print(f"Raw data folder: {RAW_DIR} (from {RAW_DIR_FROM})")

OUTPUT = (
    REPO
    / "docs"
    / "data"
    / "source-inventory"
    / "hdx_boundaries"
    / "profile.md"
)

PROFILED_BY = "@saraevcldn"
PROFILE_DATE = date.today().isoformat()

DATA_DIR = RAW_DIR / "admin_boundaries"

# The PSGC datafile recorded on the PSGC card (psa/original/). The team volume
# keeps it directly under psa/, so that location is accepted as a fallback.
PSGC_NAME = "PSGC-2Q-2026-Publication-Datafile.xlsx"
PSGC_FILE = next(
    (
        p
        for p in [RAW_DIR / "psa" / "original" / PSGC_NAME, RAW_DIR / "psa" / PSGC_NAME]
        if p.exists()
    ),
    RAW_DIR / "psa" / "original" / PSGC_NAME,
)

FILES = {
    "adm3": DATA_DIR / "phl_admin3.geojson",
    "adm4": DATA_DIR / "phl_admin4.geojson",
}

# Expected SHA-256, as recorded on the inventory cards. A changed file must
# stop the run, not silently produce new numbers under the old checksum (D-007).
PENDING = "PASTE_SHA256_FROM_PSGC_CARD"
EXPECTED_SHA256 = {
    "adm3": "f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41",
    "adm4": "4ebb5e3cf7b3245c659ea5886725e6a77ffc2d4bcbe3963d8f704d5adc5523d2",
    "psgc": "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d",
}

SOURCE_LABEL = "RAW_DATA_DIR/admin_boundaries/"
PSGC_LABEL = f"RAW_DATA_DIR/psa/original/{PSGC_NAME}"


# %% Helpers

findings = []
suspected = []


def show(finding, text):
    print(f"[BOUNDARIES {finding}] {text}")

    findings.append(
        {
            "id": finding,
            "finding": text,
        }
    )


def show_suspected(finding, text, test):
    print(f"[BOUNDARIES {finding}] {text}")

    suspected.append(
        {
            "id": finding,
            "suspicion": text,
            "test": test,
        }
    )


def format_pct(value):
    return f"{value:.2f}%"


def format_values(values):
    if not values:
        return "none"

    return ", ".join(
        f"`{value}`"
        for value in values
    )


def crs_label(crs):
    if crs is None:
        return "UNAVAILABLE"

    crs_text = crs.to_string()

    if crs_text == "OGC:CRS84":
        return "CRS84 (WGS 84)"

    if crs.to_epsg() == 4326:
        return "EPSG:4326 (WGS 84)"

    return crs_text


def sha256_file(path):
    """Return SHA-256 checksum for a file."""
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def file_size_mb(path):
    """Return file size in MB."""
    return path.stat().st_size / (1024 * 1024)


# %% Verify retained source files exist

for name, path in FILES.items():
    if not path.exists():
        sys.exit(f"Retained {name} file not found: {path}")

if not PSGC_FILE.exists():
    sys.exit(f"PSGC file not found: {PSGC_FILE}")

print("Administrative boundary source files found.")

for name, path in FILES.items():
    print(f"- {name}: {path}")

print(f"- PSGC: {PSGC_FILE}")


# %% File integrity: verify every checksum before reading any data

file_metadata = {}
pending = []

for name, path in [*FILES.items(), ("psgc", PSGC_FILE)]:
    size_bytes = path.stat().st_size
    size_mb = file_size_mb(path)
    sha256 = sha256_file(path)
    expected = EXPECTED_SHA256[name]

    if expected == PENDING:
        pending.append((path.name, sha256))
    elif sha256 != expected:
        sys.exit(
            f"{path.name}: SHA-256 does not match the inventory card. "
            "Stop and re-inventory.\n"
            f"Expected: {expected}\nActual:   {sha256}"
        )

    file_metadata[name] = {
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "sha256": sha256,
    }

    print(f"{name.upper()}: {path.name}, {size_bytes:,} bytes ({size_mb:.2f} MB), SHA-256 OK")

if pending:
    lines = "\n".join(f"  {name}: {actual}" for name, actual in pending)
    sys.exit(
        f"No expected SHA-256 recorded yet for {len(pending)} file(s). Computed:\n{lines}\n"
        "Copy the value from the PSGC inventory card into EXPECTED_SHA256 "
        "(it must match the card), then run again."
    )


# %% Load retained source files

adm3 = gpd.read_file(FILES["adm3"])
adm4 = gpd.read_file(FILES["adm4"])

print("Administrative boundary files loaded.")


# %% O-1 Extracted file structure

file_rows = []

for key, path in FILES.items():
    gdf = adm3 if key == "adm3" else adm4

    file_rows.append(
        (
            key.upper(),
            path.name,
            f"{path.stat().st_size:,} bytes",
            f"{len(gdf):,}",
        )
    )

show(
    "O-1",
    "Administrative boundary files: "
    + "; ".join(
        f"{layer}={rows} rows"
        for layer, _, _, rows in file_rows
    )
    + ".",
)


# %% O-2 Schema

adm3_columns = list(adm3.columns)
adm4_columns = list(adm4.columns)

adm3_schema = [
    f"{column} ({adm3[column].dtype})"
    for column in adm3.columns
]

adm4_schema = [
    f"{column} ({adm4[column].dtype})"
    for column in adm4.columns
]

show(
    "O-2",
    f"ADM3 columns={adm3_columns}; "
    f"ADM4 columns={adm4_columns}.",
)


# %% O-3 Row counts and geographic coverage

adm3_row_count = len(adm3)
adm4_row_count = len(adm4)

adm3_code_count = adm3["adm3_pcode"].nunique()
adm4_code_count = adm4["adm4_pcode"].nunique()

show(
    "O-3",
    f"ADM3: {adm3_row_count:,} rows and "
    f"{adm3_code_count:,} unique administrative codes; "
    f"ADM4: {adm4_row_count:,} rows and "
    f"{adm4_code_count:,} unique administrative codes.",
)


# %% O-4 Administrative code uniqueness

adm3_duplicate_codes = int(
    adm3["adm3_pcode"].duplicated().sum()
)

adm4_duplicate_codes = int(
    adm4["adm4_pcode"].duplicated().sum()
)

show(
    "O-4",
    f"Duplicate administrative codes: "
    f"ADM3={adm3_duplicate_codes:,}, "
    f"ADM4={adm4_duplicate_codes:,}.",
)


# %% O-5 Missing administrative identifiers

adm3_missing_code = int(
    adm3["adm3_pcode"].isna().sum()
)

adm4_missing_code = int(
    adm4["adm4_pcode"].isna().sum()
)

adm3_missing_name = int(
    adm3["adm3_name"].isna().sum()
)

adm4_missing_name = int(
    adm4["adm4_name"].isna().sum()
)

show(
    "O-5",
    f"Missing identifiers: "
    f"ADM3 pcode={adm3_missing_code:,}, "
    f"name={adm3_missing_name:,}; "
    f"ADM4 pcode={adm4_missing_code:,}, "
    f"name={adm4_missing_name:,}.",
)


# %% O-6 Geometry types

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

show(
    "O-6",
    f"ADM3 geometry types="
    f"{adm3_geometry_counts.to_dict()}; "
    f"ADM4 geometry types="
    f"{adm4_geometry_counts.to_dict()}.",
)


# %% O-7 Coordinate reference system

adm3_crs_name = crs_label(adm3.crs)
adm4_crs_name = crs_label(adm4.crs)

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

show(
    "O-7",
    f"ADM3 CRS={adm3_crs_name} "
    f"(EPSG={adm3_epsg}); "
    f"ADM4 CRS={adm4_crs_name} "
    f"(EPSG={adm4_epsg}).",
)


# %% O-8 Geometry validity

adm3_empty_geometry = int(
    adm3.geometry.is_empty.sum()
)

adm4_empty_geometry = int(
    adm4.geometry.is_empty.sum()
)

adm3_invalid_geometry = int(
    (~adm3.geometry.is_valid).sum()
)

adm4_invalid_geometry = int(
    (~adm4.geometry.is_valid).sum()
)

adm3_missing_geometry = int(
    adm3.geometry.isna().sum()
)

adm4_missing_geometry = int(
    adm4.geometry.isna().sum()
)

show(
    "O-8",
    f"Geometry validation: "
    f"ADM3 missing={adm3_missing_geometry:,}, "
    f"empty={adm3_empty_geometry:,}, "
    f"invalid={adm3_invalid_geometry:,}; "
    f"ADM4 missing={adm4_missing_geometry:,}, "
    f"empty={adm4_empty_geometry:,}, "
    f"invalid={adm4_invalid_geometry:,}.",
)


# %% O-9 Administrative hierarchy

adm4_missing_parent_adm3 = int(
    adm4["adm3_pcode"].isna().sum()
)

adm4_parent_adm3_count = (
    adm4["adm3_pcode"].nunique()
)

adm3_province_count = (
    adm3["adm2_pcode"].nunique()
)

adm3_region_count = (
    adm3["adm1_pcode"].nunique()
)

show(
    "O-9",
    f"ADM3 represents {adm3_province_count:,} provinces "
    f"across {adm3_region_count:,} regions; "
    f"ADM4 has {adm4_parent_adm3_count:,} distinct parent "
    f"ADM3 codes and {adm4_missing_parent_adm3:,} missing "
    f"parent ADM3 codes.",
)


# %% O-10 Source metadata

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

show(
    "O-10",
    f"ADM3 valid_on={adm3_valid_on or 'none'}, "
    f"version={adm3_versions or 'none'}; "
    f"ADM4 valid_on={adm4_valid_on or 'none'}, "
    f"version={adm4_versions or 'none'}.",
)


# %% O-11 ADM3 code compatibility with PSGC

psgc = pd.read_excel(
    PSGC_FILE,
    sheet_name="PSGC",
)

psgc_city_mun = psgc[
    psgc["Geographic Level"].isin(
        ["City", "Mun"]
    )
].copy()

adm3_psgc_codes = (
    adm3["adm3_pcode"]
    .astype("string")
    .str.replace(r"^PH", "", regex=True)
    .str.zfill(7)
    .add("000")
)

psgc_codes = (
    psgc_city_mun["10-digit PSGC"]
    .astype("string")
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(10)
)

psgc_code_set = set(
    psgc_codes.dropna()
)

adm3_exact_psgc_matches = int(
    adm3_psgc_codes.isin(psgc_code_set).sum()
)

adm3_psgc_mismatches = (
    adm3_row_count
    - adm3_exact_psgc_matches
)

adm3_psgc_match_rate = (
    adm3_exact_psgc_matches
    / adm3_row_count
    * 100
    if adm3_row_count
    else 0
)

show(
    "O-11",
    f"ADM3 converted-code comparison with current PSGC: "
    f"{adm3_exact_psgc_matches:,}/{adm3_row_count:,} "
    f"records matched "
    f"({adm3_psgc_match_rate:.2f}%); "
    f"{adm3_psgc_mismatches:,} did not match.",
)


# %% Suspected findings

show_suspected(
    "S-1",
    "ADM3 boundary codes may require a validated PSGC "
    "crosswalk before being treated as official PSGC identifiers.",
    "Compare the boundary-derived codes against the current "
    "PSGC publication and manually review mismatches. "
    "Do not assign PSGC codes by name alone.",
)


show_suspected(
    "S-2",
    "The administrative boundary version may not represent "
    "the same geographic edition as the current PSGC file.",
    "Compare the boundary source version and valid_on metadata "
    "with the PSGC publication date and review any changed, "
    "created, merged, or renamed LGUs.",
)


show_suspected(
    "S-3",
    "Administrative names should not be used as the primary "
    "join key when a geographic or validated code-based join "
    "is available.",
    "Use PSGC codes or validated crosswalks for tabular joins "
    "and spatial joins for assigning geographic features to "
    "administrative areas.",
)


# %% Build profile sections

observed_rows = []

for item in findings:
    observed_rows.append(
        "| "
        + item["id"]
        + " | "
        + item["finding"]
        + " | Profiling output from the retained "
          "administrative boundary extracts. "
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


# %% Generate profile.md

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


summary_text = (
    "The retained administrative boundary source contains "
    f"{adm3_row_count:,} ADM3 city/municipality records and "
    f"{adm4_row_count:,} ADM4 barangay records. "
    f"The ADM3 layer contains {adm3_code_count:,} unique "
    "administrative codes, while the ADM4 layer contains "
    f"{adm4_code_count:,}. "
    f"The ADM3 converted-code comparison matched "
    f"{adm3_exact_psgc_matches:,} of {adm3_row_count:,} "
    f"records ({adm3_psgc_match_rate:.2f}%) against the "
    "current PSGC city/municipality list. "
    "Administrative boundaries are treated as geographic "
    "reference data and are not themselves an education "
    "dataset."
)


profile_text = f"""# hdx_boundaries: profile

_Generated by `analysis/profiling/profile_boundaries.py`. Do not edit by hand; change the script and rerun._

## Run details

| Field | Value |
|---|---|
| Date profiled | {PROFILE_DATE} |
| Profiled by | {PROFILED_BY} |
| Tool | Python, GeoPandas {gpd.__version__}, Pandas {pd.__version__}, {RUN_ON} |
| Profiling script | [`analysis/profiling/profile_boundaries.py`](../../../analysis/profiling/profile_boundaries.py) |
| ADM3 source | `phl_admin3.geojson` |
| ADM4 source | `phl_admin4.geojson` |
| Raw source path | `{SOURCE_LABEL}` |
| PSGC reference | `{PSGC_LABEL}` |

## How to rerun

Set `RAW_DATA_DIR` (environment or the repo's `.env`) to the folder that contains `admin_boundaries/` and `psa/original/`, then run:

`python analysis/profiling/profile_boundaries.py`

The script:

1. Verifies that the ADM3, ADM4 and PSGC files exist.
2. Verifies each file's SHA-256 against the inventory cards and stops on a mismatch.
3. Loads the GeoJSON boundary layers.
4. Profiles identifiers, geometry, CRS, hierarchy, and source metadata.
5. Compares ADM3 codes with the current PSGC city/municipality list.
6. Regenerates `docs/data/source-inventory/hdx_boundaries/profile.md`.

## Summary

{summary_text}

## Identity

| Field | Value |
|---|---|
| Source | Philippine administrative boundary data |
| Geographic levels | ADM3 city/municipality; ADM4 barangay |
| Retained format | GeoJSON |
| Primary ADM3 identifier | `adm3_pcode` |
| Primary ADM4 identifier | `adm4_pcode` |
| Geometry | Polygon / MultiPolygon |
| PSGC reference | PSA 2Q 2026 PSGC publication |

## Files

| File | Status | Size | SHA-256 | Notes |
|---|---|---:|---|---|
| `phl_admin3.geojson` | Retained | {file_metadata["adm3"]["size_mb"]:.2f} MB | `{file_metadata["adm3"]["sha256"]}` | City/municipality administrative boundaries |
| `phl_admin4.geojson` | Retained | {file_metadata["adm4"]["size_mb"]:.2f} MB | `{file_metadata["adm4"]["sha256"]}` | Barangay administrative boundaries |

Exact file sizes:

- `phl_admin3.geojson`: {file_metadata["adm3"]["size_bytes"]:,} bytes
- `phl_admin4.geojson`: {file_metadata["adm4"]["size_bytes"]:,} bytes

## Coverage

### ADM3 — city/municipality

| Metric | Result |
|---|---:|
| Rows | {adm3_row_count:,} |
| Unique `adm3_pcode` | {adm3_code_count:,} |
| Duplicate `adm3_pcode` | {adm3_duplicate_codes:,} |
| Missing `adm3_pcode` | {adm3_missing_code:,} |
| Missing `adm3_name` | {adm3_missing_name:,} |

### ADM4 — barangay

| Metric | Result |
|---|---:|
| Rows | {adm4_row_count:,} |
| Unique `adm4_pcode` | {adm4_code_count:,} |
| Duplicate `adm4_pcode` | {adm4_duplicate_codes:,} |
| Missing `adm4_pcode` | {adm4_missing_code:,} |
| Missing `adm4_name` | {adm4_missing_name:,} |

## Structure

### ADM3 schema

| Column | Data type |
|---|---|
{chr(10).join(f"| `{column}` | `{adm3[column].dtype}` |" for column in adm3.columns)}

### ADM4 schema

| Column | Data type |
|---|---|
{chr(10).join(f"| `{column}` | `{adm4[column].dtype}` |" for column in adm4.columns)}

### Geometry

| Layer | Geometry types | CRS |
|---|---|---|
| ADM3 | {", ".join(adm3_geometry_counts.index)} | {adm3_crs_name} |
| ADM4 | {", ".join(adm4_geometry_counts.index)} | {adm4_crs_name} |

### Geometry validation

| Check | ADM3 | ADM4 |
|---|---:|---:|
| Missing geometry | {adm3_missing_geometry:,} | {adm4_missing_geometry:,} |
| Empty geometry | {adm3_empty_geometry:,} | {adm4_empty_geometry:,} |
| Invalid geometry | {adm3_invalid_geometry:,} | {adm4_invalid_geometry:,} |

## Administrative hierarchy

| Metric | Result |
|---|---:|
| ADM3 provinces represented | {adm3_province_count:,} |
| ADM3 regions represented | {adm3_region_count:,} |
| ADM4 parent ADM3 codes | {adm4_parent_adm3_count:,} |
| ADM4 missing parent ADM3 code | {adm4_missing_parent_adm3:,} |

The ADM4 layer contains a parent `adm3_pcode`, allowing barangays to be related to their corresponding city or municipality.

## Source metadata

### ADM3

| Field | Values |
|---|---|
| `valid_on` | {format_values(adm3_valid_on)} |
| `version` | {format_values(adm3_versions)} |

### ADM4

| Field | Values |
|---|---|
| `valid_on` | {format_values(adm4_valid_on)} |
| `version` | {format_values(adm4_versions)} |

## PSGC compatibility

The ADM3 `adm3_pcode` values were structurally converted to a 10-digit representation for comparison with the PSA 2Q 2026 PSGC city/municipality records.

| Metric | Result |
|---|---:|
| ADM3 records checked | {adm3_row_count:,} |
| PSGC city/municipality records | {len(psgc_city_mun):,} |
| Converted-code matches | {adm3_exact_psgc_matches:,} |
| Converted-code mismatches | {adm3_psgc_mismatches:,} |
| Match rate | {adm3_psgc_match_rate:.2f}% |

This is a compatibility check only. The converted boundary code should not automatically be treated as an official PSGC assignment. Records without an exact correspondence require a validated crosswalk before being joined to PSGC-based datasets.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
{chr(10).join(observed_rows)}

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
{chr(10).join(suspected_rows)}

## Capstone integration notes

- Use administrative boundaries as the geographic reference layer.
- Use `adm3_pcode` / validated PSGC crosswalks rather than LGU names as the primary tabular join mechanism.
- Use ADM3 boundaries for the project's city/municipality-level analysis.
- Use ADM4 boundaries only where barangay-level analysis is required and the underlying data supports it.
- Use spatial joins to assign OSM features to administrative areas.
- Do not treat administrative boundaries as an education-capacity dataset.
- Preserve the source version/date because administrative boundaries can change over time.

## Questions for the publisher or mentor

- Is this boundary source the preferred administrative-boundary source for the capstone?
- Should ADM3 be the standard geographic grain for the MVP?
- Should ADM4 be retained for possible future barangay-level analysis?
- Should the project maintain a formal PSGC crosswalk between the boundary source and the PSA PSGC publication?
"""


# %% Write profile

OUTPUT.write_text(
    profile_text,
    encoding="utf-8",
)

print()
print(f"Generated profile: {OUTPUT}")
