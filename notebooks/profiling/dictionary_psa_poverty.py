# Generates the source data dictionary for psa_poverty_stat:
#   docs/source_inventory/psa_poverty_stat/data_dictionary.md
#
# The PSA workbook has one sheet and almost no documentation: a title, three
# footnotes, and a source line. Those are the only descriptions copied here.
# Everything else (how filled a column is, ranges, samples) is measured from
# the sheet. Output is deterministic, so rerunning on the same file changes nothing.
#
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/dictionary_psa_poverty.py
#
# The workbook is read with the standard library and loaded into DuckDB as text,
# so no extra packages are needed beyond requirements-dev.txt.

# %% Setup
import csv
import hashlib
import os
import sys
import tempfile
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "psa" / "original"

FILE = "2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx"
SHA256 = "303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026"
DATA_SHEET = "2023_NoHUC_Maguindanao grouped"
FIRST_DATA_ROW = 6  # rows 1-5 are the title and the merged, multi-level header
WIDTH = 18  # columns A to R


def sql_string(text):
    return "'" + str(text).replace("'", "''") + "'"


# %% Verify checksum, load the sheet as text
path = ORIGINAL / FILE
if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{FILE}: SHA-256 does not match the inventory card. Stop and re-inventory.")

rows = dict(read_sheet(path, DATA_SHEET))
notes_row = next(r for r, cells in sorted(rows.items()) if cells.get(1, "").startswith("Notes:"))
data_rows = [rows.get(r, {}) for r in range(FIRST_DATA_ROW, notes_row)]
data_rows = [(r, c) for r, c in zip(range(FIRST_DATA_ROW, notes_row), data_rows) if c]

# Column names from the merged header: row 2 (group, filled across its merge),
# row 4 (ID, and Lower/Upper Limit), row 5 (year).
group = ""
names = []
for i in range(1, WIDTH + 1):
    top = rows[2].get(i, "")
    if i >= 4:
        group = top or group
        top = group
    sub = rows[4].get(i, "") if i == 1 or i >= 13 else ""
    year = rows[5].get(i, "")
    names.append(" ".join(x for x in (top, sub, year) if x))
ID, PROV, MUNI = names[0], names[1], names[2]

workdir = tempfile.TemporaryDirectory()
csv_path = Path(workdir.name) / "sae.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(names)
    for _, cells in data_rows:
        writer.writerow([cells.get(i, "") for i in range(1, WIDTH + 1)])

con = duckdb.connect()
name_list = "[" + ", ".join(sql_string(n) for n in names) + "]"
con.execute(f"""CREATE TABLE sae AS SELECT * FROM read_csv({sql_string(csv_path)}, all_varchar = true, header = true,
                names = {name_list}, strict_mode = true)""")


# %% Column statistics
def q(sql):
    return con.execute(sql).fetchall()


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def quoted(value):
    return "(blank)" if value is None else f"`{cell(value)}`"


def number(x):
    return f"{x:,.4f}".rstrip("0").rstrip(".")


def percent(filled, total):
    if not total:
        return "n/a"
    if filled == total:
        return "100.0%"
    p = 100.0 * filled / total
    return "<0.1%" if 0 < p < 0.1 else f"{min(p, 99.9):.1f}%"


UNIT = f'"{ID}" IS NOT NULL'


def describe(column):
    col = f'"{column}"'
    total, filled, distinct, digits, numeric = q(f"""
        SELECT count(*),
               count(*) FILTER (WHERE {col} IS NOT NULL AND trim({col}) <> ''),
               count(DISTINCT {col}),
               count(*) FILTER (WHERE regexp_full_match({col}, '[0-9]+')),
               count(try_cast({col} AS DOUBLE))
        FROM sae""")[0]
    pct = percent(filled, total)
    if not filled:
        return "all blank", pct, "0", "no values"
    if distinct == filled and digits == filled:
        kind = "identifier (unique)"
        lengths = ", ".join(f"{n} digits {c:,}" for n, c in q(f"SELECT length({col}), count(*) FROM sae WHERE {col} IS NOT NULL GROUP BY 1 ORDER BY 1"))
        first = ", ".join(quoted(v) for (v,) in q(f"SELECT {col} FROM sae WHERE {col} IS NOT NULL LIMIT 3"))
        sample = f"{lengths}; first: {first}"
    elif numeric == filled:
        kind = "decimal number"
        lo, med, hi = q(f"SELECT min(try_cast({col} AS DOUBLE)), median(try_cast({col} AS DOUBLE)), max(try_cast({col} AS DOUBLE)) FROM sae")[0]
        sample = f"min {number(lo)}, median {number(med)}, max {number(hi)}"
    else:
        kind = "text"
        sample = "most common: " + ", ".join(f"{quoted(v)} {n:,}" for v, n in q(f"SELECT {col}, count(*) FROM sae WHERE {col} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 3"))
    return kind, pct, f"{distinct:,}", sample


# %% What the workbook's own documentation says (title, footnotes, source line)
UNDOCUMENTED = "**Not in the publisher's documentation (undocumented)**"
NO_TYPE = "Not stated"

DOCS = {
    ID: (NO_TYPE, UNDOCUMENTED, "The header reads 'PSGC' over 'ID'. The workbook does not say which PSGC version or how many digits."),
    PROV: (NO_TYPE, UNDOCUMENTED, "Holds region banner rows (no ID), and a province or district label on the first row of each group. Undocumented."),
    MUNI: (
        NO_TYPE,
        UNDOCUMENTED,
        "Footnote 2: Bumbaran, Lanao del Sur was renamed Amai Manabilang (MMA Act No. 316, s. 2014; plebiscite 7 April 2018). Footnote 3: no estimate was generated for Kalayaan, Palawan, a former exclusive military installation.",
    ),
}
# The PSA press release for the same estimates (reference number 2026-43, released 6 February 2026)
# defines two of the measures. Its other mentions of standard errors and intervals define nothing.
PRESS = "PSA press release 2026-43"
PRESS_LISTS = "The press release lists standard errors, coefficients of variation, and confidence intervals with the estimates but does not define them."

for year in ("2018", "2021", "2023"):
    DOCS[f"Poverty Incidence {year}"] = (
        NO_TYPE,
        f"{PRESS}, section B: \"the proportion of the population with an income below the poverty threshold\".",
        "The workbook itself does not define this measure or its unit. The poverty threshold is footnoted in the press release; its value is not yet recorded here.",
    )
    DOCS[f"Coefficient of Variation {year}"] = (
        NO_TYPE,
        f"{PRESS}, section C: the coefficients of variation \"measure the reliability of the generated small area poverty estimates\".",
        "Workbook footnote 1: the standard deviation of an estimate is the poverty incidence times the coefficient of variation, divided by 100. The unit is not stated.",
    )
    DOCS[f"Standard Error {year}"] = (NO_TYPE, UNDOCUMENTED, "Header only. " + PRESS_LISTS)
    for limit in ("Lower Limit", "Upper Limit"):
        DOCS[f"90% Confidence Interval {limit} {year}"] = (
            NO_TYPE, UNDOCUMENTED, "Header only. Level (90%) is in the header; the method is not stated. " + PRESS_LISTS,
        )

# The team's reading of a column (D-011). Every entry starts with a label and gives its evidence.
# Finding IDs (O-n, S-n, X-n) refer to docs/source_inventory/psa_poverty_stat/profile.md.
SE_DIFFERS = {"2018": 6, "2021": 133, "2023": 1}  # SE vs incidence x CV / 100 (O-8)
CI_SE_DIFFERS = {"2018": 3, "2021": 133, "2023": 0}  # interval half-width / 1.645 vs SE (O-8)
CALABARZON_NOTE = {"2018": "", "2021": " The 133 exceptions are all in CALABARZON (S-1).", "2023": ""}


def all_but(n):
    return "in every row" if n == 0 else f"in all but {n} row{'s' if n > 1 else ''}"


LOWEST_LOWER_LIMIT = {"2018": "Adams (0)", "2021": "Port Area (0)", "2023": "Ivana (-0.0241)"}  # O-7

INTERPRETATION = {
    ID: (
        "**[observed]** The six-digit code of a city or municipality: the ID padded to 6 digits plus `000` equals the PSGC 2Q 2026 `Correspondence Code` for all 1,612 unit rows (X-1). "
        "1,073 IDs have only 5 digits because the cells are stored as numbers, which drops the leading zero (O-2)."
    ),
    PROV: (
        "**[observed]** The region name on the 18 banner rows, and a province or district label on the first row of each group (85 unit rows). The labels are not reliable: one is `(Continued)`, "
        "and 7 rows sit under `Surigao del Norte` with Surigao del Sur codes (O-3). Take the province from the ID, not from this column."
    ),
    MUNI: (
        "**[observed]** The name of the city, municipality, or sub-municipality. Not unique (114 names on more than one row); 37 carry a former name in parentheses, "
        "and 61 differ from the PSGC spelling (O-10, X-1). Join on the ID, not the name."
    ),
}
for year in ("2018", "2021", "2023"):
    INTERPRETATION[f"Poverty Incidence {year}"] = (
        "**[observed]** Values are on a percent scale, about 1 to 90 across the three years (O-6). The 2023 values reproduce the press release's class counts and highest value exactly (X-2)."
    )
    INTERPRETATION[f"Coefficient of Variation {year}"] = (
        f"**[observed]** Standard error equals incidence times CV divided by 100 (footnote 1), to within 0.05, {all_but(SE_DIFFERS[year])} (O-8), "
        "so CV is the standard error as a percent of the estimate. Blank only for Kalayaan (O-5)."
    )
    INTERPRETATION[f"Standard Error {year}"] = (
        f"**[observed]** Agrees with incidence times CV divided by 100 (footnote 1), to within 0.05, {all_but(SE_DIFFERS[year])} (O-8)."
        f"{CALABARZON_NOTE[year]} "
        "**[assumed]** It is the standard error of the estimate; footnote 1 calls it the standard deviation of an estimate (S-7)."
    )
    for limit in ("Lower Limit", "Upper Limit"):
        text = (
            f"**[observed]** The estimate is inside its interval in every row, and half the interval width divided by 1.645 matches the standard error {all_but(CI_SE_DIFFERS[year])} (O-7, O-8). "
        )
        if limit == "Lower Limit":
            text += f"The lowest lower limit is {LOWEST_LOWER_LIMIT[year]} (O-7). "
        text += "**[assumed]** A normal-approximation interval: the estimate plus or minus 1.645 standard errors (S-7)."
        INTERPRETATION[f"90% Confidence Interval {limit} {year}"] = text

# %% psa_poverty_stat dictionary
total_rows = q("SELECT count(*) FROM sae")[0][0]
unit_rows = q(f"SELECT count(*) FROM sae WHERE {UNIT}")[0][0]
out_rows = []
for c in names:
    kind, pct, distinct, sample = describe(c)
    unit_filled = q(f'SELECT count(*) FROM sae WHERE {UNIT} AND "{c}" IS NOT NULL AND trim("{c}") <> \'\'')[0][0]
    pub_type, desc, notes = DOCS[c]
    out_rows.append(f"| `{c}` | {pub_type} | {cell(desc)} | {cell(notes)} | {cell(INTERPRETATION.get(c, ''))} | {kind} | {pct} | {percent(unit_filled, unit_rows)} | {distinct} | {sample} |")

md = f"""# psa_poverty_stat: data dictionary

Generated by [`notebooks/profiling/dictionary_psa_poverty.py`](../../../notebooks/profiling/dictionary_psa_poverty.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** the workbook has no data dictionary. The only publisher text is the title (`Annex 1. Statistical Table on 2018, 2021 and 2023 City- and Municipal-Level Poverty Estimates`), three footnotes, and a source line, all inside `{FILE}`. The PSA press release for the same estimates (reference number 2026-43, released 6 February 2026) also defines poverty incidence and the coefficient of variation, and is cited where it does. Where neither says anything about a column it is marked undocumented. The workbook states no data types.
- **Our interpretation:** what the team reads a column to mean when the publisher's description is missing or incomplete (D-011). Every entry starts with a label: **[other source]** (documented elsewhere, cited), **[observed]** (shown by the data, with the numbers), or **[assumed]** (a reasonable reading, not yet proven). Blank when the publisher's description is enough.
- **Column names:** the workbook has a merged, multi-level header (rows 2 to 5). Names here join those levels, for example `Poverty Incidence 2018`. Column A has the header `PSGC` over `ID`.
- **Observed columns:** measured from the `{DATA_SHEET}` sheet ({total_rows:,} rows between the header and the footnotes: {unit_rows:,} municipality or city rows and {total_rows - unit_rows:,} region banner rows), read as text. "Filled" is the share of those rows that are not blank.
- **Filled (unit rows):** the same fill rate over only the {unit_rows:,} rows that have an ID. The region banner rows carry only a region name.
- **Kinds:** identifier (unique whole numbers), decimal number (min, median, max), text (the three most common values), all blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Filled (unit rows) | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(out_rows) + "\n"

out_dir = REPO / "docs" / "source_inventory" / "psa_poverty_stat"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "data_dictionary.md").write_text(md, encoding="utf-8")
print(f"psa_poverty_stat: {len(out_rows)} columns written")

workdir.cleanup()
