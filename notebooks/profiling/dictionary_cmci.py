"""
Generate the CMCI data dictionary.

Input:
    /Volumes/edu_access/00-source/raw/cmci/

Output:
    docs/source_inventory/cmci/data_dictionary.md

The dictionary documents:
- Capacity of School Services
- Education
- CMCI LGU reference list
"""

from pathlib import Path

import duckdb


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

DATA_DIR = Path("/Volumes/edu_access/00-source/raw/cmci")

REPO = Path.cwd()

OUTPUT = (
    REPO
    / "docs"
    / "source_inventory"
    / "cmci"
    / "data_dictionary.md"
)


FILES = {
    "css": DATA_DIR / "cmci_capacity_of_school_services_2023_2024.csv",
    "education": DATA_DIR / "cmci_education_2023_2024.csv",
    "lgu": DATA_DIR / "cmci_lgu_list.csv",
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def q(path: Path) -> str:
    """Safely quote a file path for DuckDB."""
    return "'" + str(path).replace("'", "''") + "'"


def describe_table(con, path: Path):
    """Return column metadata from the CSV."""
    return con.execute(
        f"""
        DESCRIBE
        SELECT *
        FROM read_csv_auto({q(path)})
        """
    ).fetchall()


def profile_columns(con, path: Path):
    """Calculate basic profiling statistics for each column."""

    columns = describe_table(con, path)

    results = []

    for column in columns:
        name = column[0]
        dtype = column[1]

        row_count, non_null_count, distinct_count = con.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                COUNT("{name}") AS non_null_count,
                COUNT(DISTINCT "{name}") AS distinct_count
            FROM read_csv_auto({q(path)})
            """
        ).fetchone()

        completeness = (
            non_null_count / row_count * 100
            if row_count
            else 0
        )

        results.append(
            {
                "column": name,
                "type": dtype,
                "rows": row_count,
                "non_null": non_null_count,
                "distinct": distinct_count,
                "completeness": completeness,
            }
        )

    return results


def profiling_rows(profile):
    """Convert profiling results into Markdown table rows."""

    rows = []

    for col in profile:
        rows.append(
            f"| `{col['column']}` | `{col['type']}` | "
            f"{col['completeness']:.2f}% | {col['distinct']} |\n"
        )

    return "".join(rows)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

con = duckdb.connect()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)


# Check that all required files exist
for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"CMCI input file not found for {name}: {path}"
        )


# Profile each source file
css_profile = profile_columns(con, FILES["css"])
edu_profile = profile_columns(con, FILES["education"])
lgu_profile = profile_columns(con, FILES["lgu"])


# ---------------------------------------------------------
# Build Markdown
# ---------------------------------------------------------

content = f"""# CMCI Data Dictionary

**Source:** Cities and Municipalities Competitiveness Index (CMCI)

**Publisher:** Department of Trade and Industry (DTI)

**Reference years:** 2023–2024

This data dictionary describes the CMCI indicator files extracted from the public CMCI Data Portal.


## 1. Capacity of School Services

**Source file:** `cmci_capacity_of_school_services_2023_2024.csv`

**Grain:** One CMCI Capacity of School Services indicator record per LGU-year.

**Coverage:** 1,634 LGUs for 2023 and 2024.

| Column | Description |
|---|---|
| `lgu` | Name of the city or municipality as provided by the CMCI portal. |
| `year` | CMCI reference year. |
| `capacity_of_school_services` | CMCI Capacity of School Services indicator value. The underlying calculation or formula was not independently verified. |
| `status` | Extraction/data-quality status. Observed values are `valid` and `cmci_server_error`. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
{profiling_rows(css_profile)}

## 2. Education

**Source file:** `cmci_education_2023_2024.csv`

**Grain:** One CMCI Education indicator record per LGU-year.

**Coverage:** 1,634 LGUs for 2023 and 2024.

| Column | Description |
|---|---|
| `lgu` | Name of the city or municipality as provided by the CMCI portal. |
| `year` | CMCI reference year. |
| `education` | CMCI Education indicator value. The underlying calculation or formula was not independently verified. |
| `status` | Extraction/data-quality status. Observed values are `valid`, `cmci_server_error`, and `cmci_missing`. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
{profiling_rows(edu_profile)}

## 3. CMCI LGU Reference List

**Source file:** `cmci_lgu_list.csv`

**Purpose:** Reference list of LGUs available in the CMCI portal. This file is used to validate LGU coverage and support later geographic standardization.

| Column | Description |
|---|---|
| `lgu` | LGU name as provided by the CMCI portal. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
{profiling_rows(lgu_profile)}

## 4. Data Handling Notes

- The analytical grain is **LGU-year-indicator**.
- `lgu` contains CMCI portal names and should be mapped to official PSGC codes before joining with other datasets.
- `capacity_of_school_services` and `education` are kept as separate indicators.
- Missing values are not converted to zero.
- `cmci_server_error` identifies records where the CMCI portal returned a server-side error during extraction.
- `cmci_missing` identifies records where the portal response did not provide a usable indicator value.
- CMCI indicator values should not be interpreted as direct counts of schools, classrooms, teachers, learners, or other education resources.
- The calculation methodology of the CMCI indicators was not independently verified from the extraction output.
"""


# ---------------------------------------------------------
# Write output
# ---------------------------------------------------------

OUTPUT.write_text(content, encoding="utf-8")

con.close()

print(f"Data dictionary written to: {OUTPUT}")