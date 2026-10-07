# Builds docs/data/source-inventory/dti_cmci/data_dictionary.md for the three CMCI files:
#   css = Capacity of School Services, edu = Education, lgu = LGU reference list.
#
# Follows the dictionary template and D-011: the publisher's words and our own
# interpretation are kept in separate columns, and every interpretation starts
# with a label: [other source], [observed], or [assumed]. Every number is
# computed here, so rerunning the script regenerates the dictionary.
#
# Source files and expected columns are defined below.
#
# Files are read as text (all_varchar), never type-guessed. The "Observed kind"
# column is worked out from the text values.
#
# Runs locally with DuckDB. Open it in VS Code to run cell by cell (# %% markers),
# or run the whole file:
#   RAW_DATA_DIR=~/Documents/GitHub/raw-data python analysis/profiling/dictionary_cmci.py
#
# RAW_DATA_DIR (environment or the repo's .env) must contain dti/original/ with
# the files listed in FILES. In Databricks, with RAW_DATA_DIR unset, the files are read
# from /Volumes/edu_access/00-source/raw/cmci/. Raw files are read, never modified.

# %% Setup
import hashlib
import os
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    sys.exit(
        "DuckDB is not installed. In Databricks run `%pip install duckdb` "
        "in its own cell first; locally `pip install duckdb`."
    )


def find_repo():
    """Repo root: from this file's location, or by searching upward from the working
    folder when run cell by cell (VS Code interactive window, notebook), where
    __file__ does not exist."""
    try:
        return Path(__file__).resolve().parents[2]
    except NameError:
        here = Path.cwd().resolve()
        for folder in [here, *here.parents]:
            if (folder / "config" / "sources.json").exists() or (folder / ".git").exists():
                return folder
        sys.exit("Open the repo folder (or cd into it) before running cell by cell.")


REPO = find_repo()
OUTPUT = REPO / "docs" / "data" / "source-inventory" / "dti_cmci" / "data_dictionary.md"


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


# Locally: RAW_DATA_DIR/dti/original/.
# In Databricks, use the source volume when RAW_DATA_DIR is not set.
DATABRICKS_VOLUME = Path("/Volumes/edu_access/00-source/raw/cmci")
raw_dir = env_value("RAW_DATA_DIR")

if raw_dir:
    ORIGINAL = Path(raw_dir).expanduser() / "dti" / "original"
elif DATABRICKS_VOLUME.exists():
    ORIGINAL = DATABRICKS_VOLUME
else:
    sys.exit(
        "Set RAW_DATA_DIR to the folder that contains dti/original/ "
        "(or run in Databricks with the source volume)."
    )

print(f"Reading raw files from {ORIGINAL}")


# What arrived, as recorded in docs/data/source-inventory/dti_cmci/README.md.
FILES = {
    "css": (
        "cmci_capacity_of_school_services_2023_2024.csv",
        "a9258fede279e1194e53a0ffeefd596df33505e82558e928f3adaee9791214e4",
    ),
    "edu": (
        "cmci_education_2023_2024.csv",
        "6267b77a1043dbcd63f37957ec7c01cc4eb9fcba1bf88ed9c6247c6a8e7de102",
    ),
    "lgu": (
        "cmci_lgu_list.csv",
        "187931b652b0912a5fa176b9743f107d6bb8c020004b132e42b753a1afabbebb",
    ),
}

EXPECTED_COLUMNS = {
    "css": ["lgu", "year", "capacity_of_school_services", "status"],
    "edu": ["lgu", "year", "education", "status"],
    "lgu": ["lgu"],
}

# The score column of each indicator file, and the label the CMCI portal shows for it.
SCORE = {
    "css": ("capacity_of_school_services", "Capacity of School Services"),
    "edu": ("education", "Education"),
}

con = duckdb.connect()


def q(sql):
    return con.execute(sql).fetchall()


def columns(table):
    return [r[0] for r in q(f"DESCRIBE {table}")]


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def md_table(headers, rows):
    out = [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
    ]
    out += [
        "| " + " | ".join(cell(v) for v in row) + " |"
        for row in rows
    ]
    return "\n".join(out)


def fmt(x):
    return "" if x is None else f"{x:.4f}".rstrip("0").rstrip(".")


# %% Verify checksums and expected columns, then load every column as text
# A changed file must stop the run, not silently produce a new dictionary
# under the old checksum.
for key, (name, sha) in FILES.items():
    path = ORIGINAL / name

    if not path.exists():
        sys.exit(f"Missing file: {path}")

    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        sys.exit(
            f"{name}: SHA-256 does not match the inventory card. "
            "Stop and re-inventory."
        )


for key, (name, _) in FILES.items():
    con.execute(
        f"CREATE TABLE {key} AS "
        f"SELECT * FROM read_csv('{ORIGINAL / name}', "
        "all_varchar = true, header = true, strict_mode = true)"
    )

    observed = columns(key)

    if observed != EXPECTED_COLUMNS[key]:
        sys.exit(
            f"{name}: columns changed. "
            f"Expected {EXPECTED_COLUMNS[key]}, found {observed}."
        )

    print(
        f"{key}: {q(f'SELECT count(*) FROM {key}')[0][0]} rows, "
        f"columns {observed}, checksum OK"
    )


# %% Measure each column
# Identifier-like columns are never read as numbers.
NON_NUMERIC_COLUMNS = {"lgu", "year", "status"}


def measure(table, col):
    """Fill rate, distinct count, observed kind and samples, from the text values."""
    ident = '"' + col + '"'
    value = f"nullif(trim({ident}), '')"

    total = q(f"SELECT count(*) FROM {table}")[0][0]

    nonblank, distinct = q(
        f"SELECT count({value}), count(DISTINCT {value}) FROM {table}"
    )[0]

    info = {
        "filled": f"{100 * nonblank / total:.1f}%",
        "distinct": distinct,
        "blank": total - nonblank,
        "min": None,
        "max": None,
        "zeros": None,
    }

    if nonblank == 0:
        info.update(kind="all blank", samples="")
        return info

    number = "-?[0-9]+(\\.[0-9]+)?"
    whole = "-?[0-9]+"

    not_number = q(
        f"SELECT count(*) FROM {table} "
        f"WHERE {value} IS NOT NULL "
        f"AND NOT regexp_full_match(trim({ident}), '{number}')"
    )[0][0]

    not_whole = q(
        f"SELECT count(*) FROM {table} "
        f"WHERE {value} IS NOT NULL "
        f"AND NOT regexp_full_match(trim({ident}), '{whole}')"
    )[0][0]

    if col not in NON_NUMERIC_COLUMNS and not_number == 0:
        num = f"try_cast({value} AS DOUBLE)"

        lo, med, hi, zeros = q(
            f"SELECT min({num}), median({num}), max({num}), "
            f"count(*) FILTER (WHERE {num} = 0) "
            f"FROM {table}"
        )[0]

        info.update(
            kind="whole number" if not_whole == 0 else "decimal number",
            min=lo,
            max=hi,
            zeros=zeros,
            samples=(
                f"min {fmt(lo)}, median {fmt(med)}, "
                f"max {fmt(hi)}; zeros: {zeros}"
            ),
        )

        return info

    top = q(
        f"SELECT trim({ident}), count(*) AS n "
        f"FROM {table} "
        f"WHERE {value} IS NOT NULL "
        f"GROUP BY 1 "
        f"ORDER BY n DESC, 1"
    )

    if distinct <= 20:
        info.update(
            kind="category",
            samples=", ".join(
                f"`{cell(v)}` {n}"
                for v, n in top
            ),
        )
    else:
        info.update(
            kind="text",
            samples="most common: " + ", ".join(
                f"`{cell(v)}` {n}"
                for v, n in top[:3]
            ),
        )

    return info


meas = {
    t: {
        c: measure(t, c)
        for c in EXPECTED_COLUMNS[t]
    }
    for t in FILES
}


# %% Evidence used in the interpretations
n_list = q(
    "SELECT count(DISTINCT trim(lgu)) FROM lgu"
)[0][0]

n_suffixed = q(
    "SELECT count(DISTINCT trim(lgu)) "
    "FROM lgu "
    "WHERE lgu LIKE '%(%'"
)[0][0]


grain = {}
status_counts = {}
status_check = {}

for t, (col, _) in SCORE.items():
    rows, distinct = q(
        f"SELECT count(*), count(DISTINCT (trim(lgu), year)) FROM {t}"
    )[0]

    grain[t] = (rows, rows - distinct)

    status_counts[t] = q(
        f"SELECT status, count(*) "
        f"FROM {t} "
        f"GROUP BY 1 "
        f"ORDER BY 1"
    )

    score = (
        f"try_cast(nullif(trim(\"{col}\"), '') AS DOUBLE)"
    )

    bad_valid = q(
        f"SELECT count(*) "
        f"FROM {t} "
        f"WHERE status = 'valid' "
        f"AND {score} IS NULL"
    )[0][0]

    bad_other = q(
        f"SELECT count(*) "
        f"FROM {t} "
        f"WHERE status <> 'valid' "
        f"AND nullif(trim(\"{col}\"), '') IS NOT NULL"
    )[0][0]

    status_check[t] = (bad_valid, bad_other)


list_not_in = {
    t: q(
        f"SELECT trim(lgu) FROM lgu "
        f"EXCEPT "
        f"SELECT trim(lgu) FROM {t}"
    )
    for t in SCORE
}

in_not_list = {
    t: q(
        f"SELECT trim(lgu) FROM {t} "
        f"EXCEPT "
        f"SELECT trim(lgu) FROM lgu"
    )
    for t in SCORE
}


# Status rules exactly as coded in the extraction scripts
# (src/ingestion/dti_cmci/, status-rules comment block). Keep the two in step.
INGESTION_SCRIPTS = "src/ingestion/dti_cmci/"
STATUS_RULES = {
    "valid": "HTTP 200, the indicator row was found, and its score is a number",
    "cmci_missing": (
        "HTTP 200, the indicator row was found, and the portal showed `-` as the score; "
        "the only source-side gap"
    ),
    "cmci_server_error": (
        "the request failed, returned a non-200 status, or returned a page without the "
        "indicator row (for example the portal's \"Please choose a Province and/or a Local "
        "Government Unit\" message); an extraction failure, not missing data (S-1)"
    ),
    "unexpected_value": (
        "the indicator row was found but its score is neither `-` nor a number; "
        "review by hand"
    ),
}


# %% Interpretations (D-011: every entry starts with a label)
def interp_lgu_indicator(t):
    d = meas[t]["lgu"]["distinct"]

    return (
        f"**[observed]** {d:,} distinct LGU names as shown by the portal; "
        "there is no PSGC code column (profile O-7). "
        f"{n_suffixed:,} of the {n_list:,} names in the reference list "
        "carry a parenthetical suffix such as `Alaminos (LA)`. "
        "**[assumed]** The parenthetical suffixes appear to be province "
        "abbreviations used by CMCI to distinguish LGUs with the same base "
        "name; this has not been verified against an official CMCI "
        "abbreviation list."
    )


def interp_year(t):
    return (
        "**[observed]** Values are 2023 and 2024. "
        "Each indicator file contains the same number of records for each "
        "year (profile O-2). "
        "**[assumed]** These represent CMCI reference years; whether they "
        "correspond to calendar years, rating years, or another reporting "
        "period is not stated (S-3)."
    )


def interp_score(t):
    info = meas[t][SCORE[t][0]]

    return (
        f"**[observed]** A numeric value is present when `status` is "
        f"`valid`; the score field is blank for the remaining {info['blank']:,} records. "
        f"{info['zeros']:,} scores are exactly 0, and the observed maximum "
        f"is {fmt(info['max'])} (profile O-5, O-6). "
        "**[assumed]** The meaning of an exact 0 is not established; "
        "one possibility is that it represents no data submitted (S-2). "
        "**[assumed]** The scale and calculation method are not stated in "
        "the extracted data; the score should be treated as contextual "
        "information, not as a direct count of schools, classrooms, "
        "teachers, or learners (S-4)."
    )


def interp_status(t):
    bad_valid, bad_other = status_check[t]

    counts = ", ".join(
        f"`{s}` {n:,}"
        for s, n in status_counts[t]
    )

    rules = "; ".join(
        f"`{s}`: {STATUS_RULES.get(s, 'not documented')}"
        for s, _ in status_counts[t]
    )

    return (
        f"**[observed]** Values and counts: {counts}. "
        f"{bad_valid} `valid` rows have no numeric score and "
        f"{bad_other} other rows still carry a score (profile O-4). "
        f"**[other source]** Rules as coded in the extraction scripts "
        f"(`{INGESTION_SCRIPTS}`, status-rules block): {rules}. "
        "**[assumed]** The delivered CSVs follow these rules; the non-valid "
        "LGU-years can be re-checked on the portal (S-1)."
    )


def interp_lgu_list(_):
    t_names = ", ".join(
        f"{INDICATOR_LABELS[t]} {len(list_not_in[t])}"
        for t in SCORE
    )

    t_back = ", ".join(
        f"{INDICATOR_LABELS[t]} {len(in_not_list[t])}"
        for t in SCORE
    )

    return (
        f"**[observed]** {meas['lgu']['lgu']['distinct']:,} distinct names. "
        f"Names in the reference list but not in a file: {t_names}. "
        f"Names in a file but not in the reference list: {t_back} "
        "(profile O-9). "
        "**[assumed]** The list represents the LGUs available for "
        "selection in the CMCI portal and is therefore used as the "
        "project's reference for portal coverage."
    )


INDICATOR_LABELS = {
    "css": "CSS",
    "edu": "Education",
}


# %% Build the dictionary
HEADERS = [
    "Column",
    "Publisher type",
    "Description (publisher)",
    "Publisher notes",
    "Our interpretation",
    "Observed kind",
    "Filled",
    "Distinct",
    "Samples or range",
]


def rows_for(t):
    out = []

    for col in EXPECTED_COLUMNS[t]:
        m = meas[t][col]

        if t == "lgu":
            ptype, pdesc, interp = (
                "Not stated",
                "Not stated",
                interp_lgu_list(t),
            )

        elif col == "lgu":
            ptype, pdesc, interp = (
                "Not stated",
                "Not stated",
                interp_lgu_indicator(t),
            )

        elif col == "year":
            ptype, pdesc, interp = (
                "Not stated",
                "Not stated",
                interp_year(t),
            )

        elif col == "status":
            ptype, pdesc, interp = (
                "Not published",
                "None. Not a CMCI field; created by our extraction",
                interp_status(t),
            )

        else:
            ptype, pdesc, interp = (
                "Not stated",
                SCORE[t][1],
                interp_score(t),
            )

        out.append(
            (
                f"`{col}`",
                ptype,
                pdesc,
                "",
                interp,
                m["kind"],
                m["filled"],
                f"{m['distinct']:,}",
                m["samples"],
            )
        )

    return out


def section(t, title):
    name = FILES[t][0]

    head = (
        f"## {title}\n\n"
        f"Source file: `{name}`."
    )

    if t in SCORE:
        rows, dupes = grain[t]
        head += (
            f" {rows:,} rows; one record per LGU and year; "
            f"{dupes} duplicate (`lgu`, `year`) keys."
        )
    else:
        head += (
            " The LGUs offered by the CMCI portal, used as the "
            "reference for coverage."
        )

    return f"{head}\n\n{md_table(HEADERS, rows_for(t))}\n"


dictionary = f"""# dti_cmci: data dictionary

Generated by [`analysis/profiling/dictionary_cmci.py`](../../../../analysis/profiling/dictionary_cmci.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** only what the CMCI portal itself shows goes here, which is the indicator names used as row labels. No definitions, data types, or formulas were read from the portal (see [README.md](README.md)), so everything else says "Not stated". `status` is not a CMCI field: our extraction created it.
- **Table-wide publisher notes:** none. No publisher documentation has been read.
- **Our interpretation:** what the team reads a column to mean when the publisher's description is missing or incomplete (D-011). Every entry starts with a label: **[other source]** (documented elsewhere, cited), **[observed]** (shown by the data, with the numbers), or **[assumed]** (a reasonable reading, not yet proven). Blank when the publisher's description is enough.
- **Observed columns:** measured from the three CSV files, read as text (`all_varchar`). "Filled" is the share of rows that are not blank.
- **Kinds:** whole number or decimal number (min, median, max, zeros; `lgu`, `year`, and `status` are never read as numbers), category (up to 20 values, all listed), text (the three most common values), all blank.

See [profile.md](profile.md) for the findings behind these numbers, and [README.md](README.md) for the source card.

{section("css", "Capacity of School Services")}
{section("edu", "Education")}
{section("lgu", "LGU reference list")}

## Our interpretation

This column keeps the team's reading of a column separate from the publisher's words, so a reader always knows who said what (D-011). Every entry starts with one label and gives its evidence:

| Label | Use when | Evidence to give |
|---|---|---|
| **[other source]** | Another authoritative document explains it (a law, a department order, the publisher's website) | The document and section |
| **[observed]** | The data shows it clearly | The numbers, or the finding ID in `profile.md`, e.g. "0 duplicate keys (O-1)" |
| **[assumed]** | It is a reasonable reading of the header or the values, but not proven | What it rests on, and the suspected finding that tests it, e.g. "an exact 0 may mean no data submitted (S-2)" |
"""


# %% Write dictionary
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(dictionary, encoding="utf-8")
print(f"Data dictionary written to {OUTPUT}")