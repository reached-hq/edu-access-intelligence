# Profiles four sources: ched_enrollment, ched_graduates, ched_school_count and
# ched_student_faculty_ratio.
#
# Reproduces every finding in docs/source_inventory/ched_*/profile.md.
# Each check prints under its source and finding ID (O-n observed, S-n suspected).
#
# Each CSV is a hand extraction of one table in CHED's Higher Education Statistical
# Bulletin 2020-2025 (StatBull2025.pdf). The bulletin's Grand Total rows are copied
# into GRAND_TOTALS below so the extraction can be checked (O-1).
#
# Runs locally with DuckDB; no Databricks compute. Open it in VS Code to run
# cell by cell (# %% markers), or run the whole file:
#   RAW_DATA_DIR=~/Documents/GitHub/raw-data python notebooks/profiling/profile_ched.py
#
# RAW_DATA_DIR (environment or the repo's .env) must contain ched/original/ with
# the files listed in FILES. Raw files are read, never modified.

# %% Setup
import hashlib
import math
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

# What arrived, as recorded in the inventory cards.
FILES = {
    "ched_enrollment": ("Enrollment - CHED.csv", "4977e3a6bc7c1c91d90fc9e0254847a0241d9e20529956a4b1a49ef8c59781f6"),
    "ched_graduates": ("Graduate - CHED.csv", "36017b30bc792021b742b2f63e52bd64c4f216b351a0f96ddc5dd10dbff14ac6"),
    "ched_school_count": ("School Count - CHED.csv", "a6cc097fecc61eacc5d995529eb4fb31d1d3e1dd7114cddee91151254ba9bd58"),
    "ched_student_faculty_ratio": ("Student Faculty Ratio - CHED.csv", "25ea8e9675ef10a018b2dff721802f6039cc6a1461ac8ef2c1924db09130a924"),
}
BULLETIN = ("StatBull2025.pdf", "41e5ed465c713cc23dca7e14c24134d96cd72ae2252ce336c85f8432195f3bf2")
YEARS = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"]
LABELS = {"Region", "Sector", "Program Level"}

# Grand Total rows as printed in the bulletin.
GRAND_TOTALS = {
    "ched_enrollment": {  # Table 6, p. 19
        "2020-2021 Male": 1594704, "2020-2021 Female": 2044117, "2021-2022 Male": 1749426,
        "2021-2022 Female": 2415383, "2022-2023 Male": 2051426, "2022-2023 Female": 2740734,
        "2023-2024 Male": 2274015, "2023-2024 Female": 2866383, "2024-2025 Male": 2438417,
        "2024-2025 Female": 2964304},
    "ched_graduates": {  # Table 27, p. 57
        "2020-2021 Male": 218945, "2020-2021 Female": 272327, "2021-2022 Male": 137438,
        "2021-2022 Female": 157812, "2022-2023 Male": 262694, "2022-2023 Female": 403604,
        "2023-2024 Male": 332046, "2023-2024 Female": 496713, "2024-2025 Male": 350271,
        "2024-2025 Female": 475323},
    "ched_school_count": {  # AY 2023-2024 institutions table, p. 12
        "Public Main": 113, "Public SUCs": 437, "Public LUCs": 143, "Public Other": 13,
        "Public Total": 706, "Private HEIs": 1704, "Total": 2410},
    "ched_student_faculty_ratio": {  # Table 39, p. 80
        "Student 2020-2021": 3638821, "Faculty 2020-2021": 148031, "Student 2021-2022": 4164809,
        "Faculty 2021-2022": 143571, "Student 2022-2023": 4792160, "Faculty 2022-2023": 167296,
        "Student 2023-2024": 5140409, "Faculty 2023-2024": 172605, "Student 2024-2025": 5402721,
        "Faculty 2024-2025": 188261},
}

con = duckdb.connect()


def q(sql):
    return con.execute(sql).fetchall()


def show(source, finding, text):
    print(f"[{source} {finding}] {text}")


def columns(table):
    return [r[0] for r in q(f"DESCRIBE {table}")]


def count_columns(table):
    return [c for c in columns(table) if c not in LABELS and not c.startswith("Ratio ")]


def as_int(column):
    # Counts are whole numbers, some with thousands commas; blank and "-" stay NULL.
    return f"try_cast(replace(\"{column}\", ',', '') AS BIGINT)"


def region(value):
    return value.replace("\n", " ")


# %% Verify checksums and load every column as text
# A changed file must stop the run, not silently produce new numbers
# under the old checksum.
raw_bytes = {}
for name, sha in [BULLETIN, *FILES.values()]:
    data = (ORIGINAL / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        sys.exit(f"{name}: SHA-256 does not match the inventory card. Stop and re-inventory.")
    raw_bytes[name] = data
for table, (name, _) in FILES.items():
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{ORIGINAL / name}', "
                "all_varchar = true, header = true, strict_mode = true)")
    print(f"{table}: {q(f'SELECT count(*) FROM {table}')[0][0]} rows, {len(columns(table))} columns, checksum OK")
print(f"{BULLETIN[0]}: checksum OK")

# %% Checks for every source
for table, (name, _) in FILES.items():
    print(f"\n=== {table} ===")

    # O-1: the hand extraction adds up to the bulletin's Grand Total row.
    expected = GRAND_TOTALS[table]
    sums = {c: q(f"SELECT coalesce(sum({as_int(c)}), 0) FROM {table}")[0][0] for c in expected}
    wrong = {c: (sums[c], expected[c]) for c in expected if sums[c] != expected[c]}
    show(table, "O-1", f"columns matching the bulletin Grand Total: {len(expected) - len(wrong)} of {len(expected)}; mismatches={wrong or 'none'}")

    # O-2: grain.
    keys = [c for c in columns(table) if c in LABELS]
    key = ", ".join(f'"{c}"' for c in keys)
    rows, distinct = q(f"SELECT count(*), count(DISTINCT ({key})) FROM {table}")[0]
    show(table, "O-2", f"rows={rows} key=({', '.join(keys)}) duplicate_keys={rows - distinct}")

    # O-3: region labels.
    labels = [r[0] for r in q(f'SELECT DISTINCT "Region" FROM {table} ORDER BY 1')]
    show(table, "O-3", f"regions={len(labels)} with_line_break={[region(v) for v in labels if chr(10) in v]} last={region(labels[-1])}")

    # O-4: blank cells, by region.
    counts = count_columns(table)
    blanks = q(f"""SELECT "Region", count(*) FROM (SELECT "Region", unnest([{', '.join(f'"{c}"' for c in counts)}]) AS v FROM {table})
                   WHERE v IS NULL GROUP BY 1 ORDER BY 1""")
    show(table, "O-4", f"blank count cells={sum(n for _, n in blanks)} by region={[(region(r), n) for r, n in blanks]}")

    # O-5: how numbers are written.
    cells = f"(SELECT unnest([{', '.join(f'\"{c}\"' for c in counts)}]) AS v FROM {table}) WHERE v IS NOT NULL"
    commas, dashes, invalid = q(f"""SELECT count(*) FILTER (WHERE v LIKE '%,%'), count(*) FILTER (WHERE trim(v) = '-'),
                                          count(*) FILTER (WHERE trim(v) <> '-' AND NOT regexp_full_match(v, '[0-9]{{1,3}}(,[0-9]{{3}})*|[0-9]+'))
                                   FROM {cells}""")[0]
    show(table, "O-5", f"filled count cells with thousands commas={commas} dash cells={dashes} other non-numbers={invalid}")

    # O-6: which years each region has data for (wide files only).
    if table != "ched_school_count":
        for label in ["19 - Bangsamoro", "18 - Negros"]:
            present = [y for y in YEARS
                       if q(f"""SELECT count(*) FROM {table} WHERE "Region" LIKE '{label}%'
                                AND ({' OR '.join(f'"{c}" IS NOT NULL' for c in counts if y in c)})""")[0][0]]
            show(table, "O-6", f"{label}: years with any value={present}")

# %% Region labels across the four files
label_sets = {t: {r[0] for r in q(f'SELECT DISTINCT "Region" FROM {t}')} for t in FILES}
every = set.union(*label_sets.values())
for t, labels in label_sets.items():
    show(t, "O-3", f"labels missing compared with the other CHED files: {sorted(region(v) for v in every - labels) or 'none'}")

# %% ched_graduates
dash_cells = [(region(r), p, c) for c in count_columns("ched_graduates")
              for r, p in q(f"""SELECT "Region", "Program Level" FROM ched_graduates WHERE trim("{c}") = '-'""")]
show("ched_graduates", "O-5", f"dash cells: {dash_cells}")

# %% ched_school_count
parts = " + ".join(f"coalesce({as_int(c)}, 0)" for c in ["Public Main", "Public SUCs", "Public LUCs", "Public Other"])
r = q(f"""SELECT count(*), count(*) FILTER (WHERE {parts} = {as_int('Public Total')}),
                 count(*) FILTER (WHERE {as_int('Public Total')} + {as_int('Private HEIs')} = {as_int('Total')})
          FROM ched_school_count""")[0]
show("ched_school_count", "O-6", f"rows={r[0]}; Main + SUCs + LUCs + Other (blank as 0) = Public Total: {r[1]}; Public Total + Private HEIs = Total: {r[2]}")

# %% ched_student_faculty_ratio
checked = ceiling = rounded = 0
header = columns("ched_student_faculty_ratio")
for row in q("SELECT * FROM ched_student_faculty_ratio"):
    for year in YEARS:
        student, faculty, ratio = (row[header.index(f"{m} {year}")] for m in ["Student", "Faculty", "Ratio"])
        if ratio is None:
            continue
        s, f, n = int(student.replace(",", "")), int(faculty.replace(",", "")), int(ratio.split(":")[1])
        checked += 1
        ceiling += n == math.ceil(s / f)
        rounded += n == round(s / f)
show("ched_student_faculty_ratio", "O-7", f"filled ratios={checked}; equal to 1:ceil(Student/Faculty)={ceiling}; equal to 1:round(Student/Faculty)={rounded}")
