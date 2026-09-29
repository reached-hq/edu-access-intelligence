# Profiles psa_psgc (PSA PSGC 2Q 2026 publication datafile). Each check prints under
# the finding ID used in docs/source_inventory/psa_psgc/profile.md.
#
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_psgc.py
#
# The workbook loading repeats dictionary_psgc.py on purpose for now (D-007).

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

FILE = "PSGC-2Q-2026-Publication-Datafile.xlsx"
SHA256 = "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d"

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def column_number(cell_ref):
    n = 0
    for ch in re.match(r"[A-Z]+", cell_ref).group():
        n = n * 26 + ord(ch) - 64
    return n


def read_sheet(path, sheet_name):
    """Return a list of {column number: text} rows. Blank cells are omitted."""
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
            rows.append(cells)
        return rows


path = ORIGINAL / FILE
if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{FILE}: SHA-256 does not match the inventory card. Stop and re-inventory.")

rows = read_sheet(path, "PSGC")
header, body = rows[0], rows[1:]
COLS = ["id", "name", "corr", "level", "old_names", "city_class", "income", "urban_rural", "pop", "col_j", "status"]
assert max(header) == len(COLS)

workdir = tempfile.TemporaryDirectory()
csv_path = Path(workdir.name) / "psgc.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(COLS)
    for r in body:
        writer.writerow([r.get(i, "") for i in range(1, len(COLS) + 1)])

con = duckdb.connect()
con.execute(f"""CREATE TABLE p AS SELECT * FROM read_csv('{csv_path}', all_varchar = true, header = true,
                names = [{", ".join(repr(c) for c in COLS)}], strict_mode = true)""")


def q(sql):
    return con.execute(sql).fetchall()


def one(sql):
    return q(sql)[0][0]


def show(finding, text):
    print(f"[{finding}] {text}")


show("run", f"{FILE}: {len(body):,} data rows; header cells with line breaks: {sum('\n' in v for v in header.values())}")

# %% O-1 10-digit code is a clean primary key
show("O-1", "blank {}, not 10 digits {}, non-numeric {}, duplicates {}, fully duplicated rows {}".format(
    one("SELECT count(*) FROM p WHERE id IS NULL"),
    one("SELECT count(*) FROM p WHERE id IS NOT NULL AND length(id) <> 10"),
    one("SELECT count(*) FROM p WHERE id IS NOT NULL AND NOT regexp_full_match(id, '[0-9]+')"),
    one("SELECT count(*) - count(DISTINCT id) FROM p"),
    one("SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM p)) FROM p"),
))
show("O-1", "leading-zero ids (start with 0): {:,}. Region IX: {}".format(
    one("SELECT count(*) FROM p WHERE id LIKE '0%'"), q("SELECT id, name FROM p WHERE id = '0900000000'")))

# %% O-2 Geographic Level: values, blanks, legend mismatch
show("O-2", "levels: " + ", ".join(f"{v} {n:,}" for v, n in q("SELECT coalesce(level, '(blank)'), count(*) FROM p GROUP BY 1 ORDER BY 2 DESC, 1")))
show("O-2", "blank-level rows: " + "; ".join(str(r) for r in q("SELECT id, name, corr, pop FROM p WHERE level IS NULL ORDER BY id")))
LEGEND = ["Reg", "Prov", "Mun", "Bgy", "Dist", "SubMun"]
present = [v for (v,) in q("SELECT DISTINCT level FROM p WHERE level IS NOT NULL ORDER BY 1")]
show("O-2", f"Notes E legend lists {LEGEND}. Legend levels with 0 rows: {[l for l in LEGEND if l not in present]}; "
     f"data levels missing from the legend: {[v for v in present if v not in LEGEND]}")

# %% O-3 Correspondence code
show("O-3", "blank {:,}; distinct {:,}; not 9 digits {}".format(
    one("SELECT count(*) FROM p WHERE corr IS NULL"),
    one("SELECT count(DISTINCT corr) FROM p"),
    one("SELECT count(*) FROM p WHERE corr IS NOT NULL AND (length(corr) <> 9 OR NOT regexp_full_match(corr, '[0-9]+'))"),
))
show("O-3", "blank by level: " + ", ".join(f"{v} {n}" for v, n in q("SELECT coalesce(level, '(blank)'), count(*) FROM p WHERE corr IS NULL GROUP BY 1 ORDER BY 2 DESC, 1")))
show("O-3", "blank-code examples: " + "; ".join(f"{i} {n} ({l})" for i, n, l in q("SELECT id, name, coalesce(level, '(blank)') FROM p WHERE corr IS NULL AND level IN ('Prov', 'Reg', 'Mun') ORDER BY id LIMIT 6")))

# %% O-4 Population: non-numbers and reconciliation with National Summary
show("O-4", "not a whole number: " + str(q("SELECT id, name, pop FROM p WHERE try_cast(pop AS BIGINT) IS NULL")))
show("O-4", "zero population: {} rows by level: {}".format(
    one("SELECT count(*) FROM p WHERE try_cast(pop AS BIGINT) = 0"),
    q("SELECT coalesce(level, '(blank)'), count(*) FROM p WHERE try_cast(pop AS BIGINT) = 0 GROUP BY 1 ORDER BY 2 DESC, 1")))
summary = read_sheet(path, "National Summary")
national = next(r for r in summary if "PHILIPPINES" in r.values())
nat_values = [v for _, v in sorted(national.items())]
nat_prov, nat_city, nat_mun, nat_bgy, nat_pop = (int(v) for v in nat_values[nat_values.index("PHILIPPINES") + 1:][:5])
region_sum = one("SELECT sum(try_cast(pop AS BIGINT)) FROM p WHERE level = 'Reg'")
show("O-4", f"sum of 18 region populations {region_sum:,}; National Summary {nat_pop:,}; difference {nat_pop - region_sum:,} (Notes D.2: 1,708 abroad)")

# %% O-5 Unit counts against the National Summary sheet
counts = dict(q("SELECT level, count(*) FROM p WHERE level IS NOT NULL GROUP BY 1"))
for label, key, expected in [("provinces", "Prov", nat_prov), ("cities", "City", nat_city), ("municipalities", "Mun", nat_mun), ("barangays", "Bgy", nat_bgy)]:
    show("O-5", f"{label}: PSGC sheet {counts.get(key, 0):,}; National Summary {expected:,}; {'match' if counts.get(key, 0) == expected else 'DIFFER'}")

# %% O-6 Unlabelled column J
show("O-6", f"column J filled in {one('SELECT count(*) FROM p WHERE col_j IS NOT NULL')} rows; by level: "
     + ", ".join(f"{v} {n}" for v, n in q("SELECT coalesce(level, '(blank)'), count(*) FROM p WHERE col_j IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1")))

# %% O-7 Income class values
show("O-7", "income by level (values other than 1st-5th): " + str(q("SELECT level, income, count(*) FROM p WHERE income IS NOT NULL AND NOT regexp_full_match(income, '[1-5](st|nd|rd|th)') GROUP BY 1, 2 ORDER BY 1, 2")))
show("O-7", "starred rows: " + "; ".join(f"{i} {n} {c}" for i, n, c in q("SELECT id, name, income FROM p WHERE income LIKE '%*' ORDER BY id")))
show("O-7", "'-' rows: " + "; ".join(f"{i} {n}" for i, n in q("SELECT id, name FROM p WHERE income = '-' ORDER BY id")))
show("O-7", "income filled outside Prov/City/Mun: {}; city class filled outside City: {}; urban/rural filled outside Bgy: {}".format(
    one("SELECT count(*) FROM p WHERE income IS NOT NULL AND coalesce(level, '') NOT IN ('Prov', 'City', 'Mun')"),
    one("SELECT count(*) FROM p WHERE city_class IS NOT NULL AND coalesce(level, '') <> 'City'"),
    one("SELECT count(*) FROM p WHERE urban_rural IS NOT NULL AND coalesce(level, '') <> 'Bgy'")))

# %% O-8 Urban / Rural, and the suspected link to missing correspondence codes (S-1)
show("O-8", "urban/rural: " + ", ".join(f"{v} {n:,}" for v, n in q("SELECT urban_rural, count(*) FROM p WHERE urban_rural IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1")))
show("O-8", "NCR barangays (id starts 13) not urban: {}".format(one("SELECT count(*) FROM p WHERE level = 'Bgy' AND id LIKE '13%' AND urban_rural <> 'U'")))
dash = one("SELECT count(*) FROM p WHERE urban_rural = '-'")
both = one("SELECT count(*) FROM p WHERE urban_rural = '-' AND corr IS NULL")
no_code_other = one("SELECT count(*) FROM p WHERE level = 'Bgy' AND corr IS NULL AND urban_rural <> '-'")
show("S-1", f"barangays with '-' urban/rural: {dash}; of those with no correspondence code: {both}; barangays with no code and not '-': {no_code_other}")
show("S-1", "'-' urban/rural barangays by city/municipality: " + str(q("SELECT substr(id, 1, 7) AS parent, count(*) FROM p WHERE urban_rural = '-' GROUP BY 1 ORDER BY 1")))

# %% O-9 Names: not unique, trailing spaces, Status link
show("O-9", "distinct names {:,} of {:,} rows; barangay names shared by more than one barangay: {:,}".format(
    one("SELECT count(DISTINCT name) FROM p"), one("SELECT count(*) FROM p"),
    one("SELECT count(*) FROM (SELECT name FROM p WHERE level = 'Bgy' GROUP BY name HAVING count(*) > 1)")))
show("O-9", "names with trailing space: {:,}; of those with a Status value: {:,}; Status rows without trailing space: {:,}".format(
    one("SELECT count(*) FROM p WHERE name <> rtrim(name)"),
    one("SELECT count(*) FROM p WHERE name <> rtrim(name) AND status IS NOT NULL"),
    one("SELECT count(*) FROM p WHERE name = rtrim(name) AND status IS NOT NULL")))
show("O-9", "names with leading space: {}; with double space inside: {}".format(
    one("SELECT count(*) FROM p WHERE name <> ltrim(name)"), one("SELECT count(*) FROM p WHERE name LIKE '%  %'")))
show("O-9", "status: " + ", ".join(f"{v} on {l} {n:,}" for v, l, n in q("SELECT status, coalesce(level, '(blank)'), count(*) FROM p WHERE status IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2")))

# %% O-10 Hierarchy: every unit has its parent in the file
show("O-10", "barangays whose city/municipality code (first 7 digits + 000) is missing: {}".format(
    one("SELECT count(*) FROM p b WHERE b.level = 'Bgy' AND NOT EXISTS (SELECT 1 FROM p x WHERE x.id = substr(b.id, 1, 7) || '000')")))
show("O-10", "provinces/cities/municipalities whose region code is missing: {}".format(
    one("SELECT count(*) FROM p b WHERE b.level IN ('Prov', 'City', 'Mun') AND NOT EXISTS (SELECT 1 FROM p x WHERE x.id = substr(b.id, 1, 2) || '00000000')")))
show("O-10", "municipalities (not NCR) whose province code (first 5 digits + 00000) is missing: {}; examples: {}".format(
    one("SELECT count(*) FROM p b WHERE b.level = 'Mun' AND b.id NOT LIKE '13%' AND NOT EXISTS (SELECT 1 FROM p x WHERE x.id = substr(b.id, 1, 5) || '00000')"),
    q("SELECT id, name FROM p b WHERE b.level = 'Mun' AND b.id NOT LIKE '13%' AND NOT EXISTS (SELECT 1 FROM p x WHERE x.id = substr(b.id, 1, 5) || '00000') ORDER BY id LIMIT 4")))

# %% O-11 Old names
show("O-11", "old names filled {:,}; distinct {:,}; by level: {}".format(
    one("SELECT count(*) FROM p WHERE old_names IS NOT NULL"), one("SELECT count(DISTINCT old_names) FROM p"),
    q("SELECT coalesce(level, '(blank)'), count(*) FROM p WHERE old_names IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1")))

workdir.cleanup()
