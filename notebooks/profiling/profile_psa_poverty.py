# Profiles psa_poverty_stat (PSA city- and municipal-level poverty estimates, 2018, 2021, 2023).
# Each check prints under the finding ID used in docs/source_inventory/psa_poverty_stat/profile.md.
#
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_psa_poverty.py
#
# Check X-1 compares the file with the PSGC 2Q 2026 workbook (source psa_psgc). It runs
# only if that file is in the same folder and its SHA-256 matches; otherwise it is skipped.
# The workbook loading repeats dictionary_psa_poverty.py on purpose for now (D-007).

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

sys.stdout.reconfigure(encoding="utf-8")

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "psa" / "original"

FILE = "2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx"
SHA256 = "303fb0e87bff046acaa21e3ac586f6def6b737b9082eb1f51451a887fd93a026"
DATA_SHEET = "2023_NoHUC_Maguindanao grouped"
FIRST_DATA_ROW = 6
PSGC_FILE = "PSGC-2Q-2026-Publication-Datafile.xlsx"
PSGC_SHA256 = "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d"

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def column_number(cell_ref):
    n = 0
    for ch in re.match(r"[A-Z]+", cell_ref).group():
        n = n * 26 + ord(ch) - 64
    return n


def rich_text(node):
    """Text of a shared or inline string. Skips phonetic guides (rPh), which also hold <t> elements."""
    parts = [t.text or "" for t in node.findall(M + "t")]
    for run in node.findall(M + "r"):
        parts += [t.text or "" for t in run.findall(M + "t")]
    return "".join(parts)


def sql_string(text):
    return "'" + str(text).replace("'", "''") + "'"


def sheet_xml_path(zf, sheet_name):
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))}
    sheet = next(s for s in workbook.find(M + "sheets") if s.get("name") == sheet_name)
    target = rels[sheet.get(R + "id")].lstrip("/")
    return target if target.startswith("xl/") else "xl/" + target


def read_sheet(path, sheet_name):
    """Return a list of (row number, {column number: text}). Blank cells are omitted."""
    with zipfile.ZipFile(path) as zf:
        strings = [rich_text(si) for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(M + "si")]
        rows = []
        for row in ET.fromstring(zf.read(sheet_xml_path(zf, sheet_name))).iter(M + "row"):
            cells = {}
            for c in row.findall(M + "c"):
                v = c.find(M + "v")
                if c.get("t") == "s" and v is not None:
                    text = strings[int(v.text)]
                elif c.get("t") == "inlineStr":
                    inline = c.find(M + "is")
                    text = rich_text(inline) if inline is not None else ""
                else:
                    text = v.text if v is not None else ""
                if text != "":
                    cells[column_number(c.get("r"))] = text
            rows.append((int(row.get("r")), cells))
        return rows


def column_a_cell_types(path, sheet_name):
    """Count the XML cell types in column A (no t attribute means a number)."""
    counts = {}
    with zipfile.ZipFile(path) as zf:
        for row in ET.fromstring(zf.read(sheet_xml_path(zf, sheet_name))).iter(M + "row"):
            if int(row.get("r")) < FIRST_DATA_ROW:
                continue
            for c in row.findall(M + "c"):
                if column_number(c.get("r")) == 1 and c.find(M + "v") is not None:
                    counts[c.get("t") or "number"] = counts.get(c.get("t") or "number", 0) + 1
    return counts


path = ORIGINAL / FILE
if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{FILE}: SHA-256 does not match the inventory card. Stop and re-inventory.")

sheet_rows = dict(read_sheet(path, DATA_SHEET))
notes_row = next(r for r, cells in sorted(sheet_rows.items()) if cells.get(1, "").startswith("Notes:"))
last_row = max(sheet_rows)
body = [(r, sheet_rows[r]) for r in range(FIRST_DATA_ROW, notes_row) if sheet_rows.get(r)]

COLS = ["id", "region_province", "name",
        "pi18", "pi21", "pi23", "cv18", "cv21", "cv23", "se18", "se21", "se23",
        "lo18", "up18", "lo21", "up21", "lo23", "up23"]

workdir = tempfile.TemporaryDirectory()
csv_path = Path(workdir.name) / "sae.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["sheet_row"] + COLS)
    for r, cells in body:
        writer.writerow([r] + [cells.get(i, "") for i in range(1, len(COLS) + 1)])

con = duckdb.connect()
con.execute(f"""CREATE TABLE s_raw AS SELECT * FROM read_csv({sql_string(csv_path)}, all_varchar = true, header = true,
                strict_mode = true)""")
# Unit rows carry an ID. Region banner rows carry only a region name in column B.
# Region and province are filled down from the banner and label rows.
con.execute("""
    CREATE TABLE s AS
    SELECT *, CAST(sheet_row AS INTEGER) AS rn, lpad(id, 6, '0') AS id6,
           last_value(CASE WHEN id IS NULL THEN region_province END IGNORE NULLS) OVER (ORDER BY CAST(sheet_row AS INTEGER)) AS region,
           last_value(region_province IGNORE NULLS) OVER (ORDER BY CAST(sheet_row AS INTEGER)) AS province_label
    FROM s_raw
""")
con.execute("CREATE TABLE u AS SELECT * FROM s WHERE id IS NOT NULL")
NUM = COLS[3:]


def q(sql):
    return con.execute(sql).fetchall()


def one(sql):
    return q(sql)[0][0]


def show(finding, text):
    print(f"[{finding}] {text}")


def fmt(v):
    return f"{v:,.4f}".rstrip("0").rstrip(".")


show("run", f"{FILE}: {len(body):,} rows between header and footnotes; unit rows (with ID) {one('SELECT count(*) FROM u'):,}; region banner rows {one('SELECT count(*) FROM s WHERE id IS NULL'):,}")

# %% O-1 Layout: one sheet, merged header, footnotes, wide by year
with zipfile.ZipFile(path) as zf:
    sheet_names = [s.get("name") for s in ET.fromstring(zf.read("xl/workbook.xml")).find(M + "sheets")]
    sheet_xml = zf.read(sheet_xml_path(zf, DATA_SHEET)).decode("utf-8")
dimension = re.search(r'<dimension ref="([^"]+)"', sheet_xml).group(1)
merged_ranges = re.findall(r'<mergeCell ref="([^"]+)"', sheet_xml)
hidden_rows = len(re.findall(r"<row [^>]*hidden=", sheet_xml))
formulas = len(re.findall(r"<f[ >]", sheet_xml))
show("O-1", f"sheets: {sheet_names}; dimension {dimension}; merged ranges {merged_ranges}; hidden rows {hidden_rows}; formulas {formulas}")
show("O-1", f"title (B1): {sheet_rows[1][2]!r}; data rows {FIRST_DATA_ROW}-{notes_row - 1}; footer rows {notes_row}-{last_row}")
for r in range(notes_row, last_row + 1):
    if sheet_rows.get(r):
        show("O-1", f"row {r}: {sheet_rows[r][1].strip()}")
show("O-1", "column S (in the filter range A4:S1640): cells with values {}".format(sum(1 for _, c in body if 19 in c)))

# %% O-2 PSGC ID: stored as a number, leading zeros lost
show("O-2", f"column A cell types in data rows (no type = number): {column_a_cell_types(path, DATA_SHEET)}")
show("O-2", "id length: " + ", ".join(f"{n} digits {c:,}" for n, c in q("SELECT length(id), count(*) FROM u GROUP BY 1 ORDER BY 1")))
show("O-2", "5-digit ids by first two digits of the padded id: " + ", ".join(f"{p} {c:,}" for p, c in q("SELECT substr(id6, 1, 2), count(*) FROM u WHERE length(id) = 5 GROUP BY 1 ORDER BY 1")))
show("O-2", "blank {}, non-numeric {}, duplicates raw {}, duplicates after padding to 6 digits {}".format(
    one("SELECT count(*) FROM s WHERE id IS NULL AND region_province IS NULL"),
    one("SELECT count(*) FROM u WHERE NOT regexp_full_match(id, '[0-9]+')"),
    one("SELECT count(*) - count(DISTINCT id) FROM u"),
    one("SELECT count(*) - count(DISTINCT id6) FROM u")))

# %% O-3 Region and province labels
show("O-3", "region banner rows: " + "; ".join(f"row {r} {n}" for r, n in q("SELECT rn, region_province FROM s WHERE id IS NULL ORDER BY rn")))
show("O-3", "labels on unit rows: {} (distinct {}); '(Continued)' labels: {}; label repeated on consecutive groups: {}".format(
    one("SELECT count(*) FROM u WHERE region_province IS NOT NULL"), one("SELECT count(DISTINCT region_province) FROM u WHERE region_province IS NOT NULL"),
    one("SELECT count(*) FROM u WHERE region_province = '(Continued)'"),
    q("SELECT region_province, count(*) FROM u WHERE region_province IS NOT NULL GROUP BY 1 HAVING count(*) > 1")))
show("O-3", "'(Continued)' row: " + str(q("SELECT rn, id, name FROM u WHERE region_province = '(Continued)'")))
show("O-3", "province code (first 4 digits of padded id) with more than one label: " + str(q(
    "SELECT substr(id6, 1, 4) AS pc, list(DISTINCT province_label ORDER BY province_label) FROM u GROUP BY 1 HAVING count(DISTINCT province_label) > 1 ORDER BY 1")))
show("O-3", "label with more than one province code: " + str(q(
    "SELECT province_label, list(DISTINCT substr(id6, 1, 4) ORDER BY 1) FROM u GROUP BY 1 HAVING count(DISTINCT substr(id6, 1, 4)) > 1 ORDER BY 1")))
show("O-3", "rows under the label 'Surigao del Norte' with province code 1668: " + str(q(
    "SELECT rn, id, name FROM u WHERE province_label = 'Surigao del Norte' AND substr(id6, 1, 4) = '1668' ORDER BY rn")))
show("O-3", "region label vs first two digits of padded id: " + "; ".join(f"{r} {p}:{c}" for r, p, c in q(
    "SELECT region, substr(id6, 1, 2), count(*) FROM u GROUP BY 1, 2 ORDER BY min(rn), 2")))

# %% O-4 Coverage inside the file
show("O-4", "unit rows by region label: " + ", ".join(f"{r} {c:,}" for r, c in q("SELECT region, count(*) FROM u GROUP BY 1 ORDER BY min(rn)")))
show("O-4", "distinct province codes: {}; NCR (13) rows: {}".format(one("SELECT count(DISTINCT substr(id6, 1, 4)) FROM u"), one("SELECT count(*) FROM u WHERE substr(id6, 1, 2) = '13'")))

# %% O-5 Values: completeness and type
null_rows = q("SELECT rn, id, name FROM u WHERE pi23 IS NULL ORDER BY rn")
show("O-5", f"unit rows with no estimate values: {null_rows}")
show("O-5", "rows with all 15 value columns filled: {}; partially filled: {}; non-numeric values: {}".format(
    one("SELECT count(*) FROM u WHERE " + " AND ".join(f"{c} IS NOT NULL" for c in NUM)),
    one("SELECT count(*) FROM u WHERE (" + " OR ".join(f"{c} IS NOT NULL" for c in NUM) + ") AND NOT (" + " AND ".join(f"{c} IS NOT NULL" for c in NUM) + ")"),
    sum(one(f"SELECT count(*) FROM u WHERE {c} IS NOT NULL AND try_cast({c} AS DOUBLE) IS NULL") for c in NUM)))
show("O-5", "values on region banner rows: {}".format(one("SELECT count(*) FROM s WHERE id IS NULL AND (" + " OR ".join(f"{c} IS NOT NULL" for c in NUM) + ")")))

# %% O-6 Ranges and precision
for c in NUM:
    lo, med, hi = q(f"SELECT min(try_cast({c} AS DOUBLE)), median(try_cast({c} AS DOUBLE)), max(try_cast({c} AS DOUBLE)) FROM u")[0]
    dp2 = one(f"SELECT count(*) FROM u WHERE {c} IS NOT NULL AND abs(try_cast({c} AS DOUBLE) - round(try_cast({c} AS DOUBLE), 2)) < 1e-9")
    dp6 = one(f"SELECT count(*) FROM u WHERE {c} IS NOT NULL AND abs(try_cast({c} AS DOUBLE) - round(try_cast({c} AS DOUBLE), 6)) < 1e-9")
    n = one(f"SELECT count(*) FROM u WHERE {c} IS NOT NULL")
    show("O-6", f"{c}: n {n:,}; min {fmt(lo)}, median {fmt(med)}, max {fmt(hi)}; equal to their 2-decimal rounding {dp2:,}; to 6-decimal rounding {dp6:,}")

# %% O-7 Confidence intervals: order and limits
for y, (pi, lo, up) in {"2018": ("pi18", "lo18", "up18"), "2021": ("pi21", "lo21", "up21"), "2023": ("pi23", "lo23", "up23")}.items():
    show("O-7", f"{y}: estimate outside its interval {one(f'SELECT count(*) FROM u WHERE {pi} IS NOT NULL AND NOT (try_cast({lo} AS DOUBLE) <= try_cast({pi} AS DOUBLE) AND try_cast({pi} AS DOUBLE) <= try_cast({up} AS DOUBLE))')}; "
         f"lower limit <= 0: {q(f'SELECT id, name, {lo} FROM u WHERE try_cast({lo} AS DOUBLE) <= 0 ORDER BY rn')}; "
         f"upper limit > 100: {one(f'SELECT count(*) FROM u WHERE try_cast({up} AS DOUBLE) > 100')}")

# %% O-8 Do CV, standard error, and interval agree? (Footnote 1: SD = incidence x CV / 100)
TOL = 0.05
for y in ("18", "21", "23"):
    bad = one(f"SELECT count(*) FROM u WHERE pi{y} IS NOT NULL AND abs(try_cast(se{y} AS DOUBLE) - try_cast(pi{y} AS DOUBLE) * try_cast(cv{y} AS DOUBLE) / 100) > {TOL}")
    ci_vs_se = one(f"SELECT count(*) FROM u WHERE pi{y} IS NOT NULL AND abs((try_cast(up{y} AS DOUBLE) - try_cast(lo{y} AS DOUBLE)) / 2 / 1.645 - try_cast(se{y} AS DOUBLE)) > {TOL}")
    ci_vs_cv = one(f"SELECT count(*) FROM u WHERE pi{y} IS NOT NULL AND abs((try_cast(up{y} AS DOUBLE) - try_cast(lo{y} AS DOUBLE)) / 2 / 1.645 - try_cast(pi{y} AS DOUBLE) * try_cast(cv{y} AS DOUBLE) / 100) > {TOL}")
    show("O-8", f"20{y}: |SE - incidence x CV / 100| > {TOL}: {bad}; |interval half-width / 1.645 - SE| > {TOL}: {ci_vs_se}; |interval half-width / 1.645 - incidence x CV / 100| > {TOL}: {ci_vs_cv}")
show("O-8", "2021 SE disagreement by region label: " + ", ".join(f"{r} {c}" for r, c in q(
    f"SELECT region, count(*) FROM u WHERE pi21 IS NOT NULL AND abs(try_cast(se21 AS DOUBLE) - try_cast(pi21 AS DOUBLE) * try_cast(cv21 AS DOUBLE) / 100) > {TOL} GROUP BY 1 ORDER BY min(rn)")))
show("O-8", "2021 CALABARZON rows (04): total {}; SE disagrees {}; province codes affected: {}".format(
    one("SELECT count(*) FROM u WHERE substr(id6, 1, 2) = '04'"),
    one(f"SELECT count(*) FROM u WHERE substr(id6, 1, 2) = '04' AND abs(try_cast(se21 AS DOUBLE) - try_cast(pi21 AS DOUBLE) * try_cast(cv21 AS DOUBLE) / 100) > {TOL}"),
    q(f"SELECT substr(id6, 1, 4), count(*) FROM u WHERE substr(id6, 1, 2) = '04' AND abs(try_cast(se21 AS DOUBLE) - try_cast(pi21 AS DOUBLE) * try_cast(cv21 AS DOUBLE) / 100) > {TOL} GROUP BY 1 ORDER BY 1")))

# %% O-9 Reliability: share of estimates with a high coefficient of variation
for y in ("18", "21", "23"):
    n = one(f"SELECT count(*) FROM u WHERE cv{y} IS NOT NULL")
    c20, c30, c50 = (one(f"SELECT count(*) FROM u WHERE try_cast(cv{y} AS DOUBLE) > {t}") for t in (20, 30, 50))
    show("O-9", f"20{y}: CV over 20: {c20:,} ({100 * c20 / n:.1f}%); over 30: {c30:,}; over 50: {c50:,}; of {n:,}")

# %% O-10 Names
show("O-10", "distinct names {:,} of {:,} unit rows; names on more than one row: {:,}; most common: {}".format(
    one("SELECT count(DISTINCT name) FROM u"), one("SELECT count(*) FROM u"),
    one("SELECT count(*) FROM (SELECT name FROM u GROUP BY name HAVING count(*) > 1)"),
    q("SELECT name, count(*) FROM u GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 3")))
show("O-10", "names with a former name in parentheses: {}; leading or trailing space: {}; double space: {}; non-ASCII characters: {}".format(
    one("SELECT count(*) FROM u WHERE name LIKE '%(%'"), one("SELECT count(*) FROM u WHERE name <> trim(name)"),
    one("SELECT count(*) FROM u WHERE name LIKE '%  %'"), one("SELECT count(*) FROM u WHERE regexp_matches(name, '[^\\x00-\\x7F]')")))
show("O-10", "footnote 2 names: {}".format(q("SELECT id, name FROM u WHERE name LIKE '%Bumbaran%' OR name LIKE '%Amai Manabilang%'")))

# %% X-1 Cross-check with PSGC 2Q 2026 (source psa_psgc), if that file is present and verified
psgc_path = ORIGINAL / PSGC_FILE
if not psgc_path.is_file():
    show("X-1", f"skipped: {PSGC_FILE} not found in {ORIGINAL}")
elif hashlib.sha256(psgc_path.read_bytes()).hexdigest() != PSGC_SHA256:
    show("X-1", f"skipped: {PSGC_FILE} does not match the checksum on the psa_psgc source card")
else:
    psgc_csv = Path(workdir.name) / "psgc.csv"
    with psgc_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pid", "pname", "corr", "level", "city_class"])
        for r, cells in read_sheet(psgc_path, "PSGC")[1:]:
            writer.writerow([cells.get(i, "") for i in (1, 2, 3, 4, 6)])
    con.execute(f"CREATE TABLE g AS SELECT * FROM read_csv({sql_string(psgc_csv)}, all_varchar = true, header = true, strict_mode = true)")
    con.execute("CREATE TABLE m AS SELECT u.*, g.pid, g.pname, g.level, g.city_class FROM u LEFT JOIN g ON g.corr = u.id6 || '000'")
    show("X-1", "unit rows {:,}; matched to a PSGC Correspondence Code (id padded to 6 digits + '000'): {:,}; matched to more than one: {}; not matched: {}".format(
        one("SELECT count(*) FROM u"), one("SELECT count(*) FROM m WHERE pid IS NOT NULL"),
        one("SELECT count(*) FROM (SELECT id FROM m GROUP BY id HAVING count(*) > 1)"), one("SELECT count(*) FROM m WHERE pid IS NULL")))
    show("X-1", "matched PSGC level: " + ", ".join(f"{l} {c:,}" for l, c in q("SELECT level, count(*) FROM m GROUP BY 1 ORDER BY 2 DESC")))
    show("X-1", "same match if the id is NOT padded (id + '000'): {:,}".format(one("SELECT count(*) FROM u JOIN g ON g.corr = u.id || '000'")))
    show("X-1", "PSGC provinces, cities, municipalities, sub-municipalities not in this file: " + ", ".join(
        f"{l}/{cc or '-'} {n}" for l, cc, n in q("""SELECT g.level, g.city_class, count(*) FROM g
            WHERE g.level IN ('Mun', 'City', 'SubMun') AND NOT EXISTS (SELECT 1 FROM u WHERE u.id6 || '000' = g.corr)
            GROUP BY 1, 2 ORDER BY 1, 2""")))
    show("X-1", "not in this file, Mun (no correspondence code, or code not in file): " + str(q(
        """SELECT pid, pname, coalesce(corr, '(no code)') FROM g WHERE level = 'Mun'
           AND NOT EXISTS (SELECT 1 FROM u WHERE u.id6 || '000' = g.corr) ORDER BY pid""")))
    show("X-1", "not in this file, City not HUC: " + str(q(
        "SELECT pid, trim(pname), city_class FROM g WHERE level = 'City' AND city_class <> 'HUC' AND NOT EXISTS (SELECT 1 FROM u WHERE u.id6 || '000' = g.corr) ORDER BY pid")))
    show("X-1", "unit rows with a name different from PSGC after upper-casing and trimming: {}".format(
        one("SELECT count(*) FROM m WHERE upper(trim(name)) <> upper(trim(pname))")))
    show("X-1", "name differences, first 12: " + str(q("SELECT id, name, trim(pname) FROM m WHERE upper(trim(name)) <> upper(trim(pname)) ORDER BY rn LIMIT 12")))
    show("X-1", "Surigao rows with province code 1668 under the label 'Surigao del Norte': PSGC province names for those codes: " + str(q(
        """SELECT p.pname, count(*) FROM m JOIN g p ON p.pid = substr(m.pid, 1, 5) || '00000'
           WHERE m.province_label = 'Surigao del Norte' AND substr(m.id6, 1, 4) = '1668' GROUP BY 1""")))
    show("X-1", "PSGC name for the Bumbaran / Amai Manabilang row: " + str(q("SELECT m.id, m.name, trim(m.pname) FROM m WHERE m.id = '153637'")))
    show("X-2", "units with a 2023 estimate by PSGC level: {}; press release: 14 sub-municipalities, 114 cities, 1,483 municipalities".format(
        q("SELECT level, count(*) FROM m WHERE try_cast(pi23 AS DOUBLE) IS NOT NULL GROUP BY 1 ORDER BY 2")))

# %% X-2 Cross-check with the PSA press release 2026-43, released 6 February 2026
# "881 Cities and Municipalities Recorded Poverty Incidence of 20 Percent or Lower in 2023".
# Expected values are copied from its Table 1, Figure 1, text, and Table 2.
CLASS_LIMITS = [(-1, 20), (20, 40), (40, 60), (60, 80), (80, 1000)]  # Levels 1 to 5 (percent)
PRESS_CLASSES_2023 = [881, 603, 119, 8, 0]
PRESS_LEVEL_1_2018 = 783
PRESS_OVER_60 = {"21": 22, "23": 8}
PRESS_CV_20_SHARE = {"18": 89.4, "21": 94.7, "23": 90.3}


def class_counts(y):
    return [one(f"SELECT count(*) FROM u WHERE try_cast(pi{y} AS DOUBLE) > {lo} AND try_cast(pi{y} AS DOUBLE) <= {hi}") for lo, hi in CLASS_LIMITS]


def verdict(ok):
    return "match" if ok else "DIFFERENT"


classes = {y: class_counts(y) for y in ("18", "21", "23")}
show("X-2", f"units with a 2023 estimate {one('SELECT count(*) FROM u WHERE pi23 IS NOT NULL'):,}; press release 1,611")
show("X-2", f"2023 classes (Levels 1 to 5) {classes['23']}; press release Table 1 {PRESS_CLASSES_2023}: {verdict(classes['23'] == PRESS_CLASSES_2023)}")
show("X-2", f"Level 1 in 2018 {classes['18'][0]}; press release {PRESS_LEVEL_1_2018}: {verdict(classes['18'][0] == PRESS_LEVEL_1_2018)}. Classes 2018 {classes['18']}, 2021 {classes['21']}")
for y, expected in PRESS_OVER_60.items():
    n = one(f"SELECT count(*) FROM u WHERE try_cast(pi{y} AS DOUBLE) > 60")
    show("X-2", f"20{y}: units above 60 percent {n}; press release {expected}: {verdict(n == expected)}")
show("X-2", "2023 units above 60 percent by province code: " + str(q(
    "SELECT substr(id6, 1, 4), count(*) FROM u WHERE try_cast(pi23 AS DOUBLE) > 60 GROUP BY 1 ORDER BY 1")) + "; press release: Zamboanga del Norte 3, Tawi-Tawi 2, Maguindanao del Sur 2, Abra 1")
name, pid, top = q("SELECT name, id6, try_cast(pi23 AS DOUBLE) FROM u ORDER BY try_cast(pi23 AS DOUBLE) DESC LIMIT 1")[0]
show("X-2", f"highest 2023 poverty incidence: {name} ({pid}) {top:.1f}; press release: Siayan, Zamboanga del Norte, 67.8")
for y, expected in PRESS_CV_20_SHARE.items():
    share = 100 * one(f"SELECT count(*) FROM u WHERE try_cast(cv{y} AS DOUBLE) <= 20") / one(f"SELECT count(*) FROM u WHERE cv{y} IS NOT NULL")
    show("X-2", f"20{y}: share with CV of 20 or less {share:.2f}%; press release {expected}: {verdict(abs(share - expected) <= 0.1)} within 0.1")

workdir.cleanup()
