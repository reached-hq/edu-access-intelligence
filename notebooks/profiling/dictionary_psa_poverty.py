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
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "psa" / "original"
REPO = Path(__file__).resolve().parents[2]

FILE = "2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx"
SHA256 = "303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026"
DATA_SHEET = "2023_NoHUC_Maguindanao grouped"
FIRST_DATA_ROW = 6  # rows 1-5 are the title and the merged, multi-level header
WIDTH = 18  # columns A to R

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def column_number(cell_ref):
    n = 0
    for ch in re.match(r"[A-Z]+", cell_ref).group():
        n = n * 26 + ord(ch) - 64
    return n


def read_sheet(path, sheet_name):
    """Return a list of (row number, {column number: text}). Blank cells are omitted."""
    with zipfile.ZipFile(path) as zf:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))}
        strings = [
            "".join(t.text or "" for t in si.iter(M + "t"))
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(M + "si")
        ]
        sheet = next(s for s in workbook.find(M + "sheets") if s.get("name") == sheet_name)
        target = rels[sheet.get(R + "id")].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(zf.read(target)).iter(M + "row"):
            cells = {}
            for c in row.findall(M + "c"):
                v = c.find(M + "v")
                if c.get("t") == "s" and v is not None:
                    text = strings[int(v.text)]
                elif c.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in c.iter(M + "t"))
                else:
                    text = v.text if v is not None else ""
                if text != "":
                    cells[column_number(c.get("r"))] = text
            rows.append((int(row.get("r")), cells))
        return rows


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
name_list = "[" + ", ".join(f"'{n}'" for n in names) + "]"
con.execute(f"""CREATE TABLE sae AS SELECT * FROM read_csv('{csv_path}', all_varchar = true, header = true,
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
NOT_DEFINED = "The workbook does not define this measure or its unit."

DOCS = {
    ID: (NO_TYPE, UNDOCUMENTED, "The header reads 'PSGC' over 'ID'. The workbook does not say which PSGC version or how many digits."),
    PROV: (NO_TYPE, UNDOCUMENTED, "Holds region banner rows (no ID), and a province or district label on the first row of each group. Undocumented."),
    MUNI: (
        NO_TYPE,
        UNDOCUMENTED,
        "Footnote 2: Bumbaran, Lanao del Sur was renamed Amai Manabilang (MMA Act No. 316, s. 2014; plebiscite 7 April 2018). Footnote 3: no estimate was generated for Kalayaan, Palawan, a former exclusive military installation.",
    ),
}
for year in ("2018", "2021", "2023"):
    DOCS[f"Poverty Incidence {year}"] = (NO_TYPE, UNDOCUMENTED, "Header only. " + NOT_DEFINED)
    DOCS[f"Coefficient of Variation {year}"] = (
        NO_TYPE, UNDOCUMENTED,
        "Footnote 1: the standard deviation of an estimate is the poverty incidence times the coefficient of variation, divided by 100. " + NOT_DEFINED,
    )
    DOCS[f"Standard Error {year}"] = (NO_TYPE, UNDOCUMENTED, "Header only. " + NOT_DEFINED)
    for limit in ("Lower Limit", "Upper Limit"):
        DOCS[f"90% Confidence Interval {limit} {year}"] = (NO_TYPE, UNDOCUMENTED, "Header only. Level (90%) is in the header; the method is not stated.")

# %% psa_poverty_stat dictionary
total_rows = q("SELECT count(*) FROM sae")[0][0]
unit_rows = q(f"SELECT count(*) FROM sae WHERE {UNIT}")[0][0]
out_rows = []
for c in names:
    kind, pct, distinct, sample = describe(c)
    unit_filled = q(f'SELECT count(*) FROM sae WHERE {UNIT} AND "{c}" IS NOT NULL AND trim("{c}") <> \'\'')[0][0]
    pub_type, desc, notes = DOCS[c]
    out_rows.append(f"| `{c}` | {pub_type} | {cell(desc)} | {cell(notes)} | {kind} | {pct} | {percent(unit_filled, unit_rows)} | {distinct} | {sample} |")

md = f"""# psa_poverty_stat: data dictionary

Generated by [`notebooks/profiling/dictionary_psa_poverty.py`](../../../notebooks/profiling/dictionary_psa_poverty.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** the workbook has no data dictionary. The only publisher text is the title (`Annex 1. Statistical Table on 2018, 2021 and 2023 City- and Municipal-Level Poverty Estimates`), three footnotes, and a source line, all inside `{FILE}`. Where they say nothing about a column it is marked undocumented. The workbook states no data types.
- **Column names:** the workbook has a merged, multi-level header (rows 2 to 5). Names here join those levels, for example `Poverty Incidence 2018`. Column A has the header `PSGC` over `ID`.
- **Observed columns:** measured from the `{DATA_SHEET}` sheet ({total_rows:,} rows between the header and the footnotes: {unit_rows:,} municipality or city rows and {total_rows - unit_rows:,} region banner rows), read as text. "Filled" is the share of those rows that are not blank.
- **Filled (unit rows):** the same fill rate over only the {unit_rows:,} rows that have an ID. The region banner rows carry only a region name.
- **Kinds:** identifier (unique whole numbers), decimal number (min, median, max), text (the three most common values), all blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Observed kind | Filled | Filled (unit rows) | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(out_rows) + "\n"

out_dir = REPO / "docs" / "source_inventory" / "psa_poverty_stat"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "data_dictionary.md").write_text(md, encoding="utf-8")
print(f"psa_poverty_stat: {len(out_rows)} columns written")

workdir.cleanup()
