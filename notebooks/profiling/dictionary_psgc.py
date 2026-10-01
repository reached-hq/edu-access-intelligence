# Generates the source data dictionary for psa_psgc:
#   docs/source_inventory/psa_psgc/data_dictionary.md
#
# Descriptions are copied from the Metadata and Notes sheets inside the PSA
# workbook. Everything else (how filled a column is, distinct values, samples,
# ranges) is measured from the PSGC sheet. Output is deterministic, so rerunning
# on the same file changes nothing.
#
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/dictionary_psgc.py
#
# The workbook is read with the standard library and loaded into DuckDB as text,
# so no extra packages are needed beyond requirements-dev.txt.

# %% Setup
import csv
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import column_letter, read_sheet

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "psa" / "original"

FILE = "PSGC-2Q-2026-Publication-Datafile.xlsx"
SHA256 = "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d"
DATA_SHEET = "PSGC"


def sql_string(text):
    return "'" + str(text).replace("'", "''") + "'"


# %% Verify checksum, load the PSGC sheet as text
path = ORIGINAL / FILE
if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{FILE}: SHA-256 does not match the inventory card. Stop and re-inventory.")

rows = [cells for _, cells in read_sheet(path, DATA_SHEET)]
header, body = rows[0], rows[1:]
width = max(header)
names = [
    re.sub(r"\s+", " ", header.get(i, "")).strip() or f"(no header, column {column_letter(i)})"
    for i in range(1, width + 1)
]

workdir = tempfile.TemporaryDirectory()
csv_path = Path(workdir.name) / "psgc.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(names)
    for r in body:
        writer.writerow([r.get(i, "") for i in range(1, width + 1)])

con = duckdb.connect()
name_list = "[" + ", ".join(sql_string(n) for n in names) + "]"
con.execute(f"""CREATE TABLE psgc AS SELECT * FROM read_csv('{csv_path}', all_varchar = true, header = true,
                names = {name_list}, strict_mode = true)""")
LEVEL = '"Geographic Level"'


# %% Column statistics
def q(sql):
    return con.execute(sql).fetchall()


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def quoted(value):
    return "(blank)" if value is None else f"`{cell(value)}`"


def percent(filled, total):
    if not total:
        return "n/a"
    if filled == total:
        return "100.0%"
    p = 100.0 * filled / total
    return "<0.1%" if 0 < p < 0.1 else f"{min(p, 99.9):.1f}%"


def describe(column, where="TRUE"):
    col = f'"{column}"'
    total, filled, distinct, digits, numeric = q(f"""
        SELECT count(*),
               count(*) FILTER (WHERE {col} IS NOT NULL AND trim({col}) <> ''),
               count(DISTINCT {col}),
               count(*) FILTER (WHERE regexp_full_match({col}, '[0-9]+')),
               count(*) FILTER (WHERE regexp_full_match(trim({col}), '-?[0-9]+'))
        FROM psgc WHERE {where}""")[0]
    pct = percent(filled, total)
    if not filled:
        return "all blank", pct, "0", "no values"
    if distinct == filled and digits == filled:
        kind = "identifier (unique)"
        sample = ", ".join(quoted(v) for (v,) in q(f"SELECT {col} FROM psgc WHERE {where} AND {col} IS NOT NULL ORDER BY {col} LIMIT 3"))
    elif numeric == filled:
        kind = "whole number"
        lo, med, hi, zeros = q(f"""SELECT min(try_cast({col} AS BIGINT)), median(try_cast({col} AS BIGINT)),
                                          max(try_cast({col} AS BIGINT)), count(*) FILTER (WHERE try_cast({col} AS BIGINT) = 0)
                                   FROM psgc WHERE {where}""")[0]
        sample = f"min {lo:,}, median {med:,.0f}, max {hi:,}; zeros: {zeros:,}"
    elif distinct <= 20:
        kind = "category"
        sample = ", ".join(f"{quoted(v)} {n:,}" for v, n in q(f"SELECT {col}, count(*) FROM psgc WHERE {where} AND {col} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1"))
    else:
        kind = "text"
        sample = "most common: " + ", ".join(f"{quoted(v)} {n:,}" for v, n in q(f"SELECT {col}, count(*) FROM psgc WHERE {where} AND {col} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 3"))
        if numeric and filled - numeric <= 0.01 * filled:
            lo, med, hi = q(f"""SELECT min(try_cast({col} AS BIGINT)), median(try_cast({col} AS BIGINT)), max(try_cast({col} AS BIGINT))
                                FROM psgc WHERE {where}""")[0]
            odd = q(f"""SELECT {col}, count(*) FROM psgc WHERE {where} AND {col} IS NOT NULL AND trim({col}) <> ''
                        AND NOT regexp_full_match(trim({col}), '-?[0-9]+') GROUP BY 1 ORDER BY 2 DESC, 1""")
            sample = (f"{numeric:,} of {filled:,} values are whole numbers (min {lo:,}, median {med:,.0f}, max {hi:,}); "
                      "not a number: " + ", ".join(f"{quoted(v)} {n:,}" for v, n in odd))
    return kind, pct, f"{distinct:,}", sample


# %% What the workbook's own documentation says, per column (Metadata, Notes, and Coding Structure sheets)
UNDOCUMENTED = "**Not in the publisher's documentation (undocumented)**"
NO_TYPE = "Not stated"

DOCS = {
    "10-digit PSGC": (
        NO_TYPE,
        "`Coding Structure` sheet (an image): the 10-digit code is region (2 digits) + province or HUC (3 digits) + municipality or city (2 digits) + barangay (3 digits). "
        "PSGC Revision 1 widened the province code from 2 to 3 digits; the earlier 9-digit code was region (2) + province (2) + municipality or city (2) + barangay (3).",
        "The Metadata abstract says the PSGC codes four hierarchical levels: region, province, city or municipality, barangay.",
    ),
    "Name": (NO_TYPE, UNDOCUMENTED, ""),
    "Correspondence Code": (NO_TYPE, UNDOCUMENTED, ""),
    "Geographic Level": (
        NO_TYPE,
        "Legend (Notes E): Reg - Region; Prov - Province; Mun - Municipality; Bgy - Barangay; Dist - District; SubMun - Sub-municipality or Municipal District.",
        "",
    ),
    "Old names": (NO_TYPE, UNDOCUMENTED, ""),
    "City Class": (NO_TYPE, UNDOCUMENTED, ""),
    "Income Classification (DOF DO No. 074.2024)": (
        NO_TYPE,
        "Income class of provinces, cities, and municipalities under DOF Department Order No. 074.2024 (first general income reclassification, RA 11964). Source: Local Treasury Operations Division, BLGF (Notes B).",
        "An asterisk marks an LGU downgraded in the reclassification that keeps its current class (RA 11964 s.10). Income ranges per class are listed in Notes B.",
    ),
    "Urban / Rural (based on 2020 CPH)": (
        NO_TYPE,
        "Urban or rural classification of barangays, based on the 2020 Census of Population and Housing (Notes C).",
        "All NCR barangays are urban (PSA Board Res. 2017-098). Urban if population is 5,000 or more, or one establishment has 100+ employees, or 5+ establishments have 10+ employees and 5+ facilities exist (PSA Board Res. 2017-100).",
    ),
    "2024 Population": (
        NO_TYPE,
        "Population count from the 2024 Census of Population (Notes D).",
        "Counts do not add up to the national total. The census includes 1,708 Filipinos in embassies, consulates, and missions abroad. Footnotes 1/, 2/, 3/ are explained in Notes D.",
    ),
    "(no header, column J)": (NO_TYPE, UNDOCUMENTED, "Notes D explains footnote markers 1/, 2/, 3/, which appear in this column."),
    "Status": (NO_TYPE, UNDOCUMENTED, ""),
}

# The team's reading of a column (D-011). Every entry starts with a label and gives its evidence.
# Finding IDs (O-n, S-n) refer to docs/source_inventory/psa_psgc/profile.md.
INTERPRETATION = {
    "10-digit PSGC": (
        "**[observed]** The code is hierarchical, as the `Coding Structure` sheet shows: its first 2 digits identify the region, the first 5 the province, and the first 7 the city or municipality. "
        "0 barangays lack their city or municipality by that prefix, and 0 provinces, cities, or municipalities lack their region (O-10)."
    ),
    "Name": (
        "**[observed]** The place name at the row's level. Not a key: 4,041 barangay names occur more than once, and 2,855 names end in a space (O-9)."
    ),
    "Correspondence Code": (
        "**[observed]** 9 digits, unique where filled, blank on 50 rows (O-3). For units with a new code since `Q4_2023`, it holds the `Q4_2023` correspondence code of the same unit "
        "(1,853 of 1,865; X-1, README Version section), e.g. Negros Occidental `1804500000` carries `064500000`, its earlier code under Region VI. "
        "**[assumed]** It is the older 9-digit PSGC code kept for continuity (S-2). The `Coding Structure` sheet documents that older structure (region 2 + province 2 + municipality or city 2 + barangay 3), "
        "and the values fit it: for 41,898 of 41,909 barangays, the first 6 digits equal those of their city or municipality (S-2)."
    ),
    "Geographic Level": (
        "**[observed]** The data has six values plus 2 blank rows: `Bgy`, `Mun`, `City`, `Prov`, `Reg`, `SubMun`. `City` (149 rows) is not in the legend, and the legend's `Dist` has no rows (O-2). "
        "Read the level list from the data, not the legend."
    ),
    "Income Classification (DOF DO No. 074.2024)": (
        "**[observed]** The value `-` appears on the 8 municipalities of the Special Geographic Area, which the publisher's notes do not explain (O-7). "
        "**[assumed]** It means no class was assigned because these municipalities are not in a province (S-3)."
    ),
    "Urban / Rural (based on 2020 CPH)": (
        "**[observed]** The value `-` appears on 38 barangays, and they are exactly the 38 barangays with no `Correspondence Code` (O-8). "
        "**[assumed]** They are new or split barangays created after the 2020 census, so they have no classification (S-1)."
    ),
    "2024 Population": (
        "**[observed]** Not every value is a whole number: City of Isabela is `#N/A`, and 12 barangays have a population of 0 (O-4)."
    ),
    "Old names": (
        "**[observed]** The former name of the unit, filled on 1,699 rows, 1,618 of them barangays (O-11). After a split, every new barangay lists the same old name "
        "(Barangay 176 in Caloocan became 176-A to 176-F), so an old name can point to more than one unit (README, Version section)."
    ),
    "City Class": (
        "**[other source]** CC, HUC, and ICC are component city, highly urbanized city, and independent component city under the Local Government Code (RA 7160, Sec. 451). "
        "**[observed]** Filled on the 149 City rows only, and blank elsewhere (O-7)."
    ),
    "(no header, column J)": (
        "**[observed]** Footnote text and markers, not data: 19 rows (provinces 16, regions 2, barangays 1), e.g. \"(excluding CITY OF BAGUIO)\" (O-6). "
        "Provincial populations exclude the cities named here."
    ),
    "Status": (
        "**[observed]** `Capital` on 82 rows (45 cities, 37 municipalities), the same count as the 82 provinces, and `Pob.` on 2,773 barangays (O-12). "
        "**[assumed]** `Capital` marks a provincial capital and `Pob.` marks the poblacion of its city or municipality (S-5)."
    ),
}

# Columns that apply to some geographic levels only: (level label, SQL filter).
SUBGROUP = {
    "City Class": ("City", f"{LEVEL} = 'City'"),
    "Income Classification (DOF DO No. 074.2024)": ("Prov, City, Mun", f"{LEVEL} IN ('Prov', 'City', 'Mun')"),
    "Urban / Rural (based on 2020 CPH)": ("Bgy", f"{LEVEL} = 'Bgy'"),
}

# %% psa_psgc dictionary
total_rows = q("SELECT count(*) FROM psgc")[0][0]
out_rows = []
for c in names:
    kind, pct, distinct, sample = describe(c)
    if c in SUBGROUP:
        label, where = SUBGROUP[c]
        sub_total = q(f"SELECT count(*) FROM psgc WHERE {where}")[0][0]
        sub_filled = q(f'SELECT count(*) FROM psgc WHERE {where} AND "{c}" IS NOT NULL AND trim("{c}") <> \'\'')[0][0]
        subgroup = f"{percent(sub_filled, sub_total)} of {sub_total:,} {label} rows"
    else:
        subgroup = "n/a"
    pub_type, desc, notes = DOCS.get(c, (NO_TYPE, UNDOCUMENTED, ""))
    out_rows.append(f"| `{c}` | {pub_type} | {cell(desc)} | {cell(notes)} | {cell(INTERPRETATION.get(c, ''))} | {kind} | {pct} | {subgroup} | {distinct} | {sample} |")

md = f"""# psa_psgc: data dictionary

Generated by [`notebooks/profiling/dictionary_psgc.py`](../../../notebooks/profiling/dictionary_psgc.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** copied from the `Metadata` and `Notes` sheets inside `{FILE}`. The workbook states no data types.
- **Our interpretation:** what the team reads a column to mean when the publisher's description is missing or incomplete (D-011). Every entry starts with a label: **[other source]** (documented elsewhere, cited), **[observed]** (shown by the data, with the numbers), or **[assumed]** (a reasonable reading, not yet proven). Blank when the publisher's description is enough.
- **Observed columns:** measured from the `{DATA_SHEET}` sheet of that file ({total_rows:,} data rows), read as text. "Filled" is the share of rows that are not blank.
- **Filled (applicable level):** some columns apply to certain geographic levels only. This column repeats the fill rate for the rows where the column is expected.
- **Kinds:** identifier (unique whole numbers), whole number (every value is a whole number; min, median, max, zeros), category (up to 20 values, all listed), text (the three most common values; any value that is not a whole number makes a numeric-looking column text, and the exceptions are listed), all blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Filled (applicable level) | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(out_rows) + "\n"

(REPO / "docs/source_inventory/psa_psgc/data_dictionary.md").write_text(md, encoding="utf-8")
print(f"psa_psgc: {len(out_rows)} columns written")

workdir.cleanup()
