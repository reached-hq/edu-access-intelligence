# %%
"""
CMCI source profiling

Purpose:
- Profile the two CMCI indicators used by the project:
    1. Capacity of School Services
    2. Education

Source files:
    /Volumes/edu_access/00-source/raw/cmci/

Output:
    docs/source_inventory/cmci/profile.md
"""

# %%
from pathlib import Path

import duckdb


# %%
# Paths

# CMCI raw files are stored in the Databricks Volume.
DATA_DIR = Path("/Volumes/edu_access/00-source/raw/cmci")

# Repository root:
# notebooks/profiling/profile_cmci.py
#                    ^          ^
#                  parent      repo
REPO = Path.cwd()

OUTPUT = REPO / "docs" / "source_inventory" / "cmci" / "profile.md"


# %%
# Input files

FILES = {
    "css": DATA_DIR / "cmci_capacity_of_school_services_2023_2024.csv",
    "edu": DATA_DIR / "cmci_education_2023_2024.csv",
    "lgu": DATA_DIR / "cmci_lgu_list.csv",
}

EXPECTED_COLUMNS = {
    "css": [
        "lgu",
        "year",
        "capacity_of_school_services",
        "status",
    ],
    "edu": [
        "lgu",
        "year",
        "education",
        "status",
    ],
}

EXPECTED_YEARS = ["2023", "2024"]

# CMCI portal contained 1,634 LGUs.
EXPECTED_LGUS = 1634
EXPECTED_ROWS = EXPECTED_LGUS * len(EXPECTED_YEARS)


# %%
# Helper functions

def sql_escape(value: str) -> str:
    """Escape a Python string for a DuckDB SQL literal."""
    return value.replace("'", "''")


def load_csv(con, path: Path, table_name: str):
    """
    Load a CSV into DuckDB as text.

    Values are initially loaded as VARCHAR so that profiling can
    inspect the raw extracted values before numeric validation.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing CMCI file: {path}")

    escaped_path = sql_escape(str(path))

    con.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW {table_name} AS
        SELECT *
        FROM read_csv(
            '{escaped_path}',
            header = true,
            all_varchar = true,
            strict_mode = true
        )
        """
    )


def scalar(con, query: str):
    """Return the first value from the first row."""
    return con.execute(query).fetchone()[0]


def rows(con, query: str):
    """Return all rows from a query."""
    return con.execute(query).fetchall()


def get_columns(con, table_name: str):
    """Return column names for a DuckDB table/view."""
    return [
        row[0]
        for row in con.execute(
            f"DESCRIBE {table_name}"
        ).fetchall()
    ]


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


# %%
# Check input files

for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {name} file:\n{path}"
        )

print("CMCI input files found.")

for name, path in FILES.items():
    print(f"- {name}: {path}")


# %%
# Start DuckDB

con = duckdb.connect(database=":memory:")


# %%
# Load source files

load_csv(
    con,
    FILES["css"],
    "css",
)

load_csv(
    con,
    FILES["edu"],
    "edu",
)

load_csv(
    con,
    FILES["lgu"],
    "lgu",
)

print("CMCI files loaded into DuckDB.")


# %%
# O-1. Extracted file structure

file_rows = []

for key, path in FILES.items():
    file_rows.append(
        (
            key,
            path.name,
            str(path),
            path.stat().st_size,
        )
    )


# %%
# O-2. Schema

css_columns = get_columns(con, "css")
edu_columns = get_columns(con, "edu")
lgu_columns = get_columns(con, "lgu")


# %%
# O-3. Row count and LGU coverage

css_row_count = scalar(
    con,
    "SELECT COUNT(*) FROM css",
)

edu_row_count = scalar(
    con,
    "SELECT COUNT(*) FROM edu",
)

css_lgu_count = scalar(
    con,
    """
    SELECT COUNT(DISTINCT TRIM(lgu))
    FROM css
    WHERE TRIM(lgu) <> ''
    """,
)

edu_lgu_count = scalar(
    con,
    """
    SELECT COUNT(DISTINCT TRIM(lgu))
    FROM edu
    WHERE TRIM(lgu) <> ''
    """,
)

lgu_list_count = scalar(
    con,
    """
    SELECT COUNT(DISTINCT TRIM(lgu))
    FROM lgu
    WHERE TRIM(lgu) <> ''
    """,
)


# %%
# O-4. Records by year

css_by_year = rows(
    con,
    """
    SELECT
        year,
        COUNT(*) AS records,
        COUNT(DISTINCT lgu) AS distinct_lgus
    FROM css
    GROUP BY year
    ORDER BY year
    """,
)

edu_by_year = rows(
    con,
    """
    SELECT
        year,
        COUNT(*) AS records,
        COUNT(DISTINCT lgu) AS distinct_lgus
    FROM edu
    GROUP BY year
    ORDER BY year
    """,
)


# %%
# O-5. Duplicate LGU-year records

css_duplicate_groups = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM (
        SELECT
            TRIM(lgu) AS lgu,
            year
        FROM css
        GROUP BY TRIM(lgu), year
        HAVING COUNT(*) > 1
    )
    """,
)

edu_duplicate_groups = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM (
        SELECT
            TRIM(lgu) AS lgu,
            year
        FROM edu
        GROUP BY TRIM(lgu), year
        HAVING COUNT(*) > 1
    )
    """,
)


# %%
# O-6. Status distribution

css_status = rows(
    con,
    """
    SELECT
        status,
        COUNT(*) AS records
    FROM css
    GROUP BY status
    ORDER BY status
    """,
)

edu_status = rows(
    con,
    """
    SELECT
        status,
        COUNT(*) AS records
    FROM edu
    GROUP BY status
    ORDER BY status
    """,
)


# %%
# O-7. Score completeness

css_missing_scores = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM css
    WHERE
        capacity_of_school_services IS NULL
        OR TRIM(capacity_of_school_services) = ''
    """,
)

edu_missing_scores = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM edu
    WHERE
        education IS NULL
        OR TRIM(education) = ''
    """,
)


# %%
# O-8. Numeric validation

css_invalid_numeric = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM css
    WHERE status = 'valid'
      AND TRY_CAST(
            NULLIF(TRIM(capacity_of_school_services), '')
            AS DOUBLE
          ) IS NULL
    """,
)

edu_invalid_numeric = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM edu
    WHERE status = 'valid'
      AND TRY_CAST(
            NULLIF(TRIM(education), '')
            AS DOUBLE
          ) IS NULL
    """,
)


# %%
# O-9. Descriptive ranges

css_range = con.execute(
    """
    SELECT
        MIN(
            TRY_CAST(
                NULLIF(TRIM(capacity_of_school_services), '')
                AS DOUBLE
            )
        ),
        MAX(
            TRY_CAST(
                NULLIF(TRIM(capacity_of_school_services), '')
                AS DOUBLE
            )
        ),
        AVG(
            TRY_CAST(
                NULLIF(TRIM(capacity_of_school_services), '')
                AS DOUBLE
            )
        )
    FROM css
    WHERE status = 'valid'
    """
).fetchone()

edu_range = con.execute(
    """
    SELECT
        MIN(
            TRY_CAST(
                NULLIF(TRIM(education), '')
                AS DOUBLE
            )
        ),
        MAX(
            TRY_CAST(
                NULLIF(TRIM(education), '')
                AS DOUBLE
            )
        ),
        AVG(
            TRY_CAST(
                NULLIF(TRIM(education), '')
                AS DOUBLE
            )
        )
    FROM edu
    WHERE status = 'valid'
    """
).fetchone()


# %%
# O-10. Status/value consistency

css_status_value_issues = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM css
    WHERE
        (
            status = 'valid'
            AND (
                capacity_of_school_services IS NULL
                OR TRIM(capacity_of_school_services) = ''
                OR TRY_CAST(
                    TRIM(capacity_of_school_services)
                    AS DOUBLE
                ) IS NULL
            )
        )
        OR
        (
            status <> 'valid'
            AND capacity_of_school_services IS NOT NULL
            AND TRIM(capacity_of_school_services) <> ''
        )
    """,
)

edu_status_value_issues = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM edu
    WHERE
        (
            status = 'valid'
            AND (
                education IS NULL
                OR TRIM(education) = ''
                OR TRY_CAST(
                    TRIM(education)
                    AS DOUBLE
                ) IS NULL
            )
        )
        OR
        (
            status <> 'valid'
            AND education IS NOT NULL
            AND TRIM(education) <> ''
        )
    """,
)


# %%
# O-11. Non-valid records

css_nonvalid = rows(
    con,
    """
    SELECT
        lgu,
        year,
        capacity_of_school_services,
        status
    FROM css
    WHERE status <> 'valid'
    ORDER BY lgu, year
    """,
)

edu_nonvalid = rows(
    con,
    """
    SELECT
        lgu,
        year,
        education,
        status
    FROM edu
    WHERE status <> 'valid'
    ORDER BY lgu, year
    """,
)


# %%
# O-12. Cross-indicator coverage

css_keys = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM (
        SELECT DISTINCT
            TRIM(lgu) AS lgu,
            year
        FROM css
    )
    """,
)

edu_keys = scalar(
    con,
    """
    SELECT COUNT(*)
    FROM (
        SELECT DISTINCT
            TRIM(lgu) AS lgu,
            year
        FROM edu
    )
    """,
)


# %%
# S-1. LGU-year differences between indicators

css_only = rows(
    con,
    """
    SELECT
        TRIM(lgu) AS lgu,
        year
    FROM css

    EXCEPT

    SELECT
        TRIM(lgu) AS lgu,
        year
    FROM edu

    ORDER BY lgu, year
    """,
)

edu_only = rows(
    con,
    """
    SELECT
        TRIM(lgu) AS lgu,
        year
    FROM edu

    EXCEPT

    SELECT
        TRIM(lgu) AS lgu,
        year
    FROM css

    ORDER BY lgu, year
    """,
)


# %%
# S-2. Expected LGU-year coverage

css_missing_expected = EXPECTED_ROWS - css_keys
edu_missing_expected = EXPECTED_ROWS - edu_keys


# %%
# S-3. Compare indicator LGUs against the CMCI LGU list

css_lgu_only = rows(
    con,
    """
    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM css

    EXCEPT

    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM lgu

    ORDER BY lgu
    """,
)

edu_lgu_only = rows(
    con,
    """
    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM edu

    EXCEPT

    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM lgu

    ORDER BY lgu
    """,
)

lgu_list_only = rows(
    con,
    """
    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM lgu

    EXCEPT

    SELECT DISTINCT
        TRIM(lgu) AS lgu
    FROM css

    ORDER BY lgu
    """,
)


# %%
# Format Markdown tables

file_table = format_table(
    [
        "Source",
        "File",
        "Path",
        "File size (bytes)",
    ],
    file_rows,
)

css_schema_table = format_table(
    ["Column", "Expected"],
    [
        (column, "yes")
        for column in EXPECTED_COLUMNS["css"]
    ],
)

edu_schema_table = format_table(
    ["Column", "Expected"],
    [
        (column, "yes")
        for column in EXPECTED_COLUMNS["edu"]
    ],
)

css_year_table = format_table(
    [
        "Year",
        "Records",
        "Distinct LGUs",
    ],
    css_by_year,
)

edu_year_table = format_table(
    [
        "Year",
        "Records",
        "Distinct LGUs",
    ],
    edu_by_year,
)

css_status_table = format_table(
    ["Status", "Records"],
    css_status,
)

edu_status_table = format_table(
    ["Status", "Records"],
    edu_status,
)

css_nonvalid_table = format_table(
    [
        "LGU",
        "Year",
        "Score",
        "Status",
    ],
    css_nonvalid,
)

edu_nonvalid_table = format_table(
    [
        "LGU",
        "Year",
        "Score",
        "Status",
    ],
    edu_nonvalid,
)

css_only_table = format_table(
    ["LGU", "Year"],
    css_only,
)

edu_only_table = format_table(
    ["LGU", "Year"],
    edu_only,
)

css_lgu_only_table = format_table(
    ["LGU"],
    css_lgu_only,
)

edu_lgu_only_table = format_table(
    ["LGU"],
    edu_lgu_only,
)

lgu_list_only_table = format_table(
    ["LGU"],
    lgu_list_only,
)


# %%
# Descriptive range values

css_min, css_max, css_avg = css_range
edu_min, edu_max, edu_avg = edu_range

css_range_text = (
    f"min={css_min}, max={css_max}, mean={css_avg}"
)

edu_range_text = (
    f"min={edu_min}, max={edu_max}, mean={edu_avg}"
)


# %%
# Build profile Markdown

profile_md = f"""# CMCI source profile

## Purpose

This profile documents the structure and observed data-quality characteristics
of the CMCI indicator extracts used by the Education Access Intelligence project.

The profiling covers:

1. Capacity of School Services (`css`)
2. Education (`edu`)

The CMCI LGU list is also used as a reference for LGU coverage validation.

## Source data location

The raw CMCI files are stored in the Databricks source volume:

`/Volumes/edu_access/00-source/raw/cmci/`

## O-1. Extracted file structure

{file_table}

## O-2. Expected schema

### Capacity of School Services

{css_schema_table}

Observed columns:

`{", ".join(css_columns)}`

### Education

{edu_schema_table}

Observed columns:

`{", ".join(edu_columns)}`

### LGU reference list

Observed columns:

`{", ".join(lgu_columns)}`

## O-3. Row count and LGU coverage

### Capacity of School Services

- Row count: **{css_row_count:,}**
- Distinct LGUs: **{css_lgu_count:,}**
- Expected LGUs: **{EXPECTED_LGUS:,}**

### Education

- Row count: **{edu_row_count:,}**
- Distinct LGUs: **{edu_lgu_count:,}**
- Expected LGUs: **{EXPECTED_LGUS:,}**

### CMCI LGU reference list

- Distinct LGUs: **{lgu_list_count:,}**

Expected LGU-year combinations:

**{EXPECTED_LGUS:,} LGUs × 2 years = {EXPECTED_ROWS:,} records**

## O-4. Records by year

### Capacity of School Services

{css_year_table}

### Education

{edu_year_table}

## O-5. Duplicate LGU-year records

The expected grain is one indicator value per LGU per year.

### Capacity of School Services

- Duplicate LGU-year groups: **{css_duplicate_groups}**

### Education

- Duplicate LGU-year groups: **{edu_duplicate_groups}**

## O-6. Status distribution

### Capacity of School Services

{css_status_table}

### Education

{edu_status_table}

The `status` field distinguishes valid extracted values from
server errors and explicit missing values.

## O-7. Score completeness

### Capacity of School Services

- Missing or blank scores: **{css_missing_scores:,}**

### Education

- Missing or blank scores: **{edu_missing_scores:,}**

Missing values are not converted to zero because a missing response does not
establish that the underlying indicator value is zero.

## O-8. Numeric validation

### Capacity of School Services

- Invalid numeric values among records marked `valid`:
  **{css_invalid_numeric:,}**

### Education

- Invalid numeric values among records marked `valid`:
  **{edu_invalid_numeric:,}**

The files were initially loaded as text and numeric conversion was performed
separately during validation.

## O-9. Descriptive score ranges

### Capacity of School Services

{css_range_text}

### Education

{edu_range_text}

These are descriptive statistics of the extracted CMCI scores. They should not
be interpreted as direct counts of schools, classrooms, teachers, learners,
or population.

## O-10. Status/value consistency

### Capacity of School Services

- Status/value consistency issues: **{css_status_value_issues}**

### Education

- Status/value consistency issues: **{edu_status_value_issues}**

## O-11. Non-valid records

### Capacity of School Services

{css_nonvalid_table}

### Education

{edu_nonvalid_table}

Non-valid records are retained rather than replaced with zero.

## O-12. Cross-indicator coverage

Distinct LGU-year keys:

- Capacity of School Services: **{css_keys:,}**
- Education: **{edu_keys:,}**

## S-1. LGU-year differences between indicators

### Present in CSS but not Education

Count: **{len(css_only)}**

{css_only_table}

### Present in Education but not CSS

Count: **{len(edu_only)}**

{edu_only_table}

## S-2. Expected LGU-year coverage

Expected LGU-year combinations:

**{EXPECTED_ROWS:,}**

### Capacity of School Services

- Missing expected combinations: **{css_missing_expected}**

### Education

- Missing expected combinations: **{edu_missing_expected}**

## S-3. Comparison with CMCI LGU reference list

### CSS LGUs not found in the reference list

Count: **{len(css_lgu_only)}**

{css_lgu_only_table}

### Education LGUs not found in the reference list

Count: **{len(edu_lgu_only)}**

{edu_lgu_only_table}

### LGUs in the reference list but not in CSS

Count: **{len(lgu_list_only)}**

{lgu_list_only_table}

## Analytical limitations

### CMCI is an indicator dataset

The CMCI values are indicator/index measures and are not direct counts of:

- schools
- classrooms
- teachers
- learners
- population

CMCI should therefore be used as contextual information alongside the
education supply and population datasets.

### LGU name standardization

The CMCI extracts use LGU names as provided by the portal.

LGU names should be mapped to official PSGC codes before joining with PSA,
DepEd, CHED, or other geographic datasets.

### Missing/server-error records

CMCI server errors and explicit missing values are retained as non-valid
records. They should not be interpreted as zero.

### Indicator separation

`Capacity of School Services` and `Education` are kept as separate indicators.
No combined CMCI education score is created because no verified CMCI formula
for combining the two indicators was established.

## Reproducibility

Profiling script:

`notebooks/profiling/profile_cmci.py`

Raw source location:

`/Volumes/edu_access/00-source/raw/cmci/`

Output:

`docs/source_inventory/cmci/profile.md`
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
print("CMCI profiling complete.")
print()

print(f"CSS rows:        {css_row_count:,}")
print(f"CSS LGUs:        {css_lgu_count:,}")
print(f"CSS duplicates:  {css_duplicate_groups:,}")
print(f"CSS non-valid:   {len(css_nonvalid):,}")

print()

print(f"EDU rows:        {edu_row_count:,}")
print(f"EDU LGUs:        {edu_lgu_count:,}")
print(f"EDU duplicates:  {edu_duplicate_groups:,}")
print(f"EDU non-valid:   {len(edu_nonvalid):,}")

print()

print(f"CMCI LGU list:   {lgu_list_count:,}")
print(f"Output:          {OUTPUT}")