# Generates the source data dictionaries for the four CHED sources:
#   docs/source_inventory/ched_enrollment/data_dictionary.md
#   docs/source_inventory/ched_graduates/data_dictionary.md
#   docs/source_inventory/ched_school_count/data_dictionary.md
#   docs/source_inventory/ched_student_faculty_ratio/data_dictionary.md
#
# Each CSV is a hand extraction of one table in CHED's Higher Education Statistical
# Bulletin 2020-2025. Descriptions and notes are copied from that table (its column
# headings and footnotes). Everything else (how filled a column is, distinct values,
# samples, ranges) is measured from the data. Output is deterministic, so rerunning
# on the same files changes nothing.
#
#   RAW_DATA_DIR=~/Documents/GitHub/raw-data python notebooks/profiling/dictionary_ched.py
#
# The file list and loading repeat profile_ched.py on purpose, as the DepEd
# scripts do (D-007).

# %% Setup
import hashlib
import os
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]


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


raw_dir = env_value("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains ched/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "ched" / "original"

FILES = {
    "ched_enrollment": ("Enrollment - CHED.csv", "6aabc9e14b2abee0dd09c7607815abcd9b75edaf972fd93819610071f4f28c3e"),
    "ched_graduates": ("Graduate - CHED.csv", "69493789bda42ae9b72a1964d3970a423581a7e28b8825e22570e7e8d5a8f809"),
    "ched_school_count": ("School Count - CHED.csv", "27aea7e1c552d7c0adb88a521cc73233a643eb337be67b2fa667df673023b2de"),
    "ched_student_faculty_ratio": ("Student Faculty Ratio - CHED.csv", "bc132836fc86fe36bf4dfb702a5c546f9df8dd7ab05c64e68dc42d30965b25b9"),
}
LABELS = {"Region", "Sector", "Program Level"}

con = duckdb.connect()


def q(sql):
    return con.execute(sql).fetchall()


# %% Verify checksums and load every column as text
for table, (name, sha) in FILES.items():
    path = ORIGINAL / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        sys.exit(f"{name}: SHA-256 does not match the inventory card. Stop and re-inventory.")
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{path}', "
                "all_varchar = true, header = true, strict_mode = true)")

# %% What the bulletin says about each table
# Descriptions are the table's column headings (parent › child); notes quote its footnotes.
TABLES = {
    "ched_enrollment": {
        "table": 'Table 6 "Enrollment by Region, Sector, Sex and Academic Year" (printed pp. 18-19)',
        "notes": ['Table 2 (printed p. 14): "Enrollment data covers only the first semester of the inclusive '
                  'years based on the submission of CHED-recognized Higher Education Institutions as consolidated '
                  'by CHED-OPRKM Knowledge Management Division as of September 2025."'],
        "extraction": "All columns of the table were extracted.",
    },
    "ched_graduates": {
        "table": 'Table 27 "Graduate by Region, Program Level, Sex and Academic Year" (printed pp. 56-57)',
        "notes": [],
        "extraction": "All columns of the table were extracted.",
    },
    "ched_school_count": {
        "table": ('"Higher Education Institutions by Region, Sector and Institutional Type: Academic Year 2023-2024" '
                  "(printed p. 12)"),
        "notes": ['"Figures include SUCs Satellite, Extension Campus, and External Study Center"',
                  '"Include Other Government School, CHED Supervised Institution, Special School"',
                  '"Based on the submission of higher education institutions, as compiled by OPRKM-Knowledge '
                  'Management Division"',
                  '"as of October 10, 2024"'],
        "extraction": ('The two "Including Satellite Campus" totals were extracted; the bulletin\'s two '
                       '"Excluding Satellite Campus" totals were not.'),
    },
    "ched_student_faculty_ratio": {
        "table": 'Table 39 "Student-Faculty Ratio by Academic Year" (printed p. 80)',
        "notes": [],
        "extraction": "All columns of the table were extracted.",
    },
}
SCHOOL_COUNT_HEADINGS = {
    "Region": "Region",
    "Public Main": "PUBLIC › SUCs › Main",
    "Public SUCs": "PUBLIC › SUCs › Satellite Campus*",
    "Public LUCs": "PUBLIC › LUCs",
    "Public Other": "PUBLIC › Other Gov't Schools",
    "Public Total": "PUBLIC › TOTAL (Public) › Including Satellite Campus",
    "Private HEIs": "PRIVATE › Private HEIs",
    "Total": "GRAND TOTAL › Including Satellite Campus",
}
RETRIEVAL_RATE = {"2020-2021": ("2020-21", "89.00%"), "2021-2022": ("2021-22", "87.00%"),
                  "2022-2023": ("2022-23", "84.00%"), "2023-2024": ("2023-24*", "93.00%"),
                  "2024-2025": ("2024-25", "97.00%")}


def documentation(table, column):
    """(publisher type, description, notes) for one column, quoted from the bulletin."""
    notes = ""
    if column in LABELS:
        description = column
    elif table == "ched_school_count":
        description = SCHOOL_COUNT_HEADINGS[column]
    elif table == "ched_student_faculty_ratio":
        metric, year = column.split(" ")
        description = f"{year} › {metric}"
        shown, rate = RETRIEVAL_RATE[year]
        notes = f"Retrieval Rate table beside Table 39: {shown} {rate}"
    else:
        year, sex = column.split(" ")
        description = f"Academic Year › {year} › {sex}" if table == "ched_enrollment" else f"{year} › {sex}"
        if table == "ched_enrollment" and year == "2023-2024":
            notes = ('"Eleven (11) students with unspecified sex in Region VII are excluded from this '
                     'disaggregated data for Academic Year 2023–2024."')
        if table == "ched_graduates" and year == "2022-2023":
            notes = ('"One (1) Baccalaureate graduate in Region VII with unspecified sex in A.Y. 2022–2023 '
                     'is excluded from this disaggregated data."')
    return "CHED", description, notes


# %% Measure each column
def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def fmt(v):
    return f"{v:,.1f}".removesuffix(".0") if isinstance(v, float) else f"{v:,}"


def observe(table, column):
    """Return (kind, filled, distinct, samples) for one column, all values read as text."""
    c = f'"{column}"'
    total, filled, distinct = q(f"SELECT count(*), count({c}), count(DISTINCT {c}) FROM {table}")[0]
    share = f"{100 * filled / total:.1f}%"
    if filled == 0:
        return "all blank", share, 0, ""
    as_int = f"try_cast(replace({c}, ',', '') AS BIGINT)"
    numbers, dashes = q(f"SELECT count({as_int}), count(*) FILTER (WHERE trim({c}) = '-') FROM {table}")[0]
    if column not in LABELS and numbers + dashes == filled and numbers > 0:
        lo, med, hi, zeros = q(f"SELECT min(n), median(n), max(n), count(*) FILTER (WHERE n = 0) "
                               f"FROM (SELECT {as_int} AS n FROM {table}) WHERE n IS NOT NULL")[0]
        sample = f"min {fmt(lo)}, median {fmt(med)}, max {fmt(hi)}; zeros: {zeros}"
        if dashes:
            sample += f"; `-`: {dashes}"
        return "whole number", share, distinct, sample
    top = q(f"SELECT {c}, count(*) AS n FROM {table} WHERE {c} IS NOT NULL GROUP BY 1 ORDER BY n DESC, 1")
    if distinct <= 20:
        return "category", share, distinct, ", ".join(f"`{cell(v)}` {n}" for v, n in top)
    return "text", share, distinct, "most common: " + ", ".join(f"`{cell(v)}` {n}" for v, n in top[:3])


# %% Write one dictionary per source
def table_md(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


HEADER = ["Column", "Publisher type", "Description (publisher)", "Publisher notes",
          "Observed kind", "Filled", "Distinct", "Samples or range"]

for table, (name, _) in FILES.items():
    columns = [r[0] for r in q(f"DESCRIBE {table}")]
    rows = [[f"`{c}`", *documentation(table, c), *observe(table, c)] for c in columns]
    info = TABLES[table]
    notes = "".join(f"\n  - {n}" for n in info["notes"]) or " none"
    md = f"""# {table}: data dictionary

Generated by [`notebooks/profiling/dictionary_ched.py`](../../../notebooks/profiling/dictionary_ched.py). Do not edit by hand; rerun the script instead.

- **Description and publisher notes:** copied from {info["table"]} of CHED's Higher Education Statistical Bulletin 2020-2025. The CSV is a hand extraction of that table; each description is the table's column heading (parent › child). {info["extraction"]}
- **Table-wide publisher notes:**{notes}
- **Observed columns:** measured from `{name}`, read as text. "Filled" is the share of rows that are not blank.
- **Kinds:** whole number (min, median, max, zeros; thousands commas removed, `-` counted separately), category (up to 20 values, all listed), text (the three most common values), all blank.

See [profile.md](profile.md) for the findings behind these numbers, and [README.md](README.md) for the source card.

""" + table_md(HEADER, rows)
    (REPO / "docs/source_inventory" / table / "data_dictionary.md").write_text(md, encoding="utf-8")
    print(f"{table}: wrote data_dictionary.md ({len(columns)} columns)")
