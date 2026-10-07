# Profiles psa_openstat_education: 13 PSA OpenSTAT education and literacy tables.
#
# Reproduces every finding in:
#   docs/source_inventory/psa_openstat_education/profile.md
# and regenerates:
#   docs/source_inventory/psa_openstat_education/data_dictionary.md
# Each check prints under its finding ID (O-n observed, S-n suspected, X-n cross-check).
#
# Runs locally with DuckDB; no Databricks compute. Run cell by cell (# %% markers) or as a whole:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_psa_openstat.py
#
# RAW_DATA_DIR must contain psa/original/openstat/ (the files in SHA256) and, for X-1,
# deped/original/Enrollment-in-SY-2023-2024.zip. Raw files are read, never modified.

# %% Setup
import collections
import hashlib
import json
import os
import re
import statistics
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
SOURCE_ID = "psa_openstat_education"

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/openstat/.")
RAW = Path(raw_dir).expanduser()
OPENSTAT = RAW / "psa" / "original" / "openstat"

# file stem -> (OpenSTAT table ID, kind of value)
TABLES = {
    "table_10_2a_net_enrolment_kindergarten": ("0031C2BNRP0", "rate"),
    "table_10_2b_net_enrolment_elementary": ("0043E2BNRP1", "rate"),
    "table_10_3a_net_enrolment_jhs": ("0051C2BNRP2", "rate"),
    "table_10_3b_net_enrolment_shs": ("0061C2BRPS3", "rate"),
    "table_10_4_cohort_survival_elementary": ("0073E2BCSR0", "rate"),
    "table_10_5_cohort_survival_jhs": ("0083I2BCSR1", "rate"),
    "table_10_8_nat_grade_6": ("0091C2BNAT0", "score"),
    "table_10_9a_nat_grade_10": ("0101C2BNAT0", "score"),
    "table_10_9b_nat_grade_12": ("0111C2BNAT2", "score"),
    "table_10_10_public_private_schools": ("0151C2BSCH1", "count"),
    "table_10_11_public_school_teachers": ("0131C2BNTP1", "count"),
    "table_10_13_basic_literacy": ("0153E2BLRP0", "rate"),
    "table_10_14_functional_literacy": ("0163E2BFLR0", "rate"),
}
# What arrived, as recorded in the source card and raw-data/psa/SHA256SUMS.txt.
SHA256 = {
    "table_10_10_public_private_schools.csv": "489eb18ed7f9c120fbc51a6151c515e5f599900ad0298b98a2340216f70ef813",
    "table_10_10_public_private_schools_metadata.json": "647c998959c4257d3b48bced85228bd8cacd42b6a804f836d9b2de3ecff7ea59",
    "table_10_11_public_school_teachers.csv": "b9fe82ed7e3dd72535be158c52281eb2f22310f7536fe30e5f653e66040ad826",
    "table_10_11_public_school_teachers_metadata.json": "ba9d85987a391f4410bbf4e9d4bd9b189bf62df12f7f83d5927ac33563f570b6",
    "table_10_13_basic_literacy.csv": "6b5acf52c76eb5a4c57cb2f734bca66f5779678fe87c75b34d1b9120ac36fb2e",
    "table_10_13_basic_literacy_metadata.json": "268d2ee5a8b4b63854d6a0032dc1c90957bebf51a2612e2d45954b285c7879fc",
    "table_10_14_functional_literacy.csv": "a4966f5321616dc916246327f7cabf4ad9846b1945bf3302dd3cc414c442070e",
    "table_10_14_functional_literacy_metadata.json": "20073765715666b5e23a67fb1a00ab0ff83b9d0b11780ce91e089c5043e82d74",
    "table_10_2a_net_enrolment_kindergarten.csv": "b4aad032549a08dfa58338eb67b2cf082c6e98a1d64f5d96617eed059b8dc1c1",
    "table_10_2a_net_enrolment_kindergarten_metadata.json": "d59d323e44cd8112a59bd43a85c9b110d0ea14fc900ff1313f9354be6f1426a3",
    "table_10_2b_net_enrolment_elementary.csv": "a96f004d7eee34af19290ac0304d9aafe0913115ff832e4931e6fc53a7bad7e4",
    "table_10_2b_net_enrolment_elementary_metadata.json": "48194e83ee139b08f8b92e3e20458396bed2c694073c2cc33c9e453a2ade0368",
    "table_10_3a_net_enrolment_jhs.csv": "d69560d001420e0a0b5b25b009c14adf97c53d690d1b0a64f66ab5e190e34806",
    "table_10_3a_net_enrolment_jhs_metadata.json": "ad87c065ecb0e210794eb1b9387967ef67806e22ad315854de5553ac002cf0ce",
    "table_10_3b_net_enrolment_shs.csv": "d3354bab1fb541913b1c727e45896d6a13b68f37b40b6124e44f46d414fc353b",
    "table_10_3b_net_enrolment_shs_metadata.json": "b88a92f6159e3c922ecf99a36e02eceacba6d1940ae90650abb3ffc6d37c1215",
    "table_10_4_cohort_survival_elementary.csv": "ce71f4f566fec1c9006562ae21fc3cf740104441924641be64e48e8319e5f7c2",
    "table_10_4_cohort_survival_elementary_metadata.json": "d6938b8b5cdad404746ff479352a01136080b6dd5126fe5739e0945ba03553c1",
    "table_10_5_cohort_survival_jhs.csv": "2b62d5f9d24432fc9fc43e13483e7281464b34003fa3e40d643b6c8d85c97c8f",
    "table_10_5_cohort_survival_jhs_metadata.json": "d581ef156f4790ffc35ea051a064f343d315a908e62fbb643e54e85bf770943f",
    "table_10_8_nat_grade_6.csv": "a80431364aea2f41dd966943b59c241e2f02384e99c3aba7729ecf7ffa276c90",
    "table_10_8_nat_grade_6_metadata.json": "d25154b407b2d73c0dcc4609221693c24c82e1c39e9dd29e4ff3aa88cf574a19",
    "table_10_9a_nat_grade_10.csv": "c04995653f7b4a759c0b27040ff7c2f354e15c86068d9c96287734a767b22704",
    "table_10_9a_nat_grade_10_metadata.json": "2d876e4f22216d4af2e3927308b869721aeac84f0c2a43eeeecfc88ae78cb673",
    "table_10_9b_nat_grade_12.csv": "c79edda63077eff67f7bafc21d94fc936553fa98e31ab2a092db73eb8e059693",
    "table_10_9b_nat_grade_12_metadata.json": "4c2e862af624f07e78584d99ca3148381a55bc5c1a23852b97722511e0d61727",
}
DEPED_ZIP = ("Enrollment-in-SY-2023-2024.zip", "a10f4d0f9082919c13b3a091774c8231c99c95b1b1872310714107013b77dbbb", "enrollment_2023-24.csv")
MISSING = ("..", "...", "a")

# Every geography label used in the 13 tables, mapped to one region key.
# A label not in this map stops the run, so a new label is noticed.
REGION = {
    "Philippines": "PH", "NCR": "NCR", "CAR": "CAR",
    "Ilocos Region": "I", "I - Ilocos Region": "I",
    "Cagayan Valley": "II", "II - Cagayan Valley": "II",
    "Central Luzon": "III", "III - Central Luzon": "III",
    "CALABARZON": "IV-A", "IV-A - CALABARZON": "IV-A", "IV-A  CALABARZON": "IV-A",
    "MIMAROPA Region": "MIMAROPA",
    "Bicol Region": "V", "V - Bicol Region": "V",
    "Western Visayas": "VI", "VI - Western Visayas": "VI",
    "Central Visayas": "VII", "VII - Central Visayas": "VII",
    "Eastern Visayas": "VIII", "VIII - Eastern Visayas": "VIII",
    "Zamboanga Peninsula": "IX", "IX - Zamboanga Peninsula": "IX",
    "Northern Mindanao": "X", "X - Northern Mindanao": "X",
    "Davao Region": "XI", "XI - Davao Region": "XI",
    "SOCCSKSARGEN": "XII", "XII - SOCCSKSARGEN": "XII",
    "Caraga": "CARAGA", "BARMM": "BARMM",
    "Negros Island Region": "NIR", "Negros Island Region (NIR)": "NIR", "NIR": "NIR",
    "Unknown": "UNKNOWN",
}
DEPED_REGION = {
    "Region I": "I", "Region II": "II", "Region III": "III", "Region IV-A": "IV-A", "Region V": "V",
    "Region VI": "VI", "Region VII": "VII", "Region VIII": "VIII", "Region IX": "IX", "Region X": "X",
    "Region XI": "XI", "Region XII": "XII", "NCR": "NCR", "CAR": "CAR", "CARAGA": "CARAGA",
    "MIMAROPA": "MIMAROPA", "BARMM": "BARMM",
}
YEAR = re.compile(r"^(.*?)\s*(\d{4}(?:-\d{4})?)$")

con = duckdb.connect()


def show(finding, text):
    print(f"[{finding}] {text}")


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


# %% Verify checksums and load into long form
tables = {}
for stem, (table_id, kind) in TABLES.items():
    for suffix in (".csv", "_metadata.json"):
        path = OPENSTAT / f"{stem}{suffix}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != SHA256[path.name]:
            sys.exit(f"{path.name}: SHA-256 {digest} does not match the source card. Stop and re-inventory.")
    meta = json.loads((OPENSTAT / f"{stem}_metadata.json").read_text(encoding="utf-8"))
    rel = con.execute(f"SELECT * FROM read_csv('{OPENSTAT / (stem + '.csv')}', all_varchar = true, header = true, strict_mode = true)")
    header = [d[0] for d in rel.description]
    rows = rel.fetchall()
    n_dims = sum(1 for h in header if not YEAR.match(h))
    cells = []
    for row in rows:
        label = row[0].lstrip(".")
        if label not in REGION:
            sys.exit(f"{stem}: unknown geography label {row[0]!r}; add it to REGION after checking it.")
        for column, value in zip(header[n_dims:], row[n_dims:]):
            group, year = YEAR.match(column).groups()
            cells.append({"geo_raw": row[0], "geo": REGION[label], "dims": tuple(row[1:n_dims]), "group": group, "year": year, "value": value})
    tables[stem] = {"id": table_id, "kind": kind, "meta": meta, "header": header, "rows": rows, "n_dims": n_dims, "cells": cells}
    show("run", f"{stem} ({table_id}): {len(rows)} rows, {len(header)} columns, checksums OK")

# %% O-1 Each CSV matches its metadata
for stem, t in tables.items():
    expected = 1
    for variable in t["meta"]["variables"]:
        expected *= len(variable["values"])
    keys = [row[: t["n_dims"]] for row in t["rows"]]
    show("O-1", f"{stem}: metadata cells {expected}; CSV cells {len(t['cells'])}; match {expected == len(t['cells'])}; "
         f"duplicate row keys {len(keys) - len(set(keys))}; dimensions {[v['code'] for v in t['meta']['variables']]}; "
         f"metadata keys {sorted(t['meta'])}")

# %% O-2 Geography labels
labels = collections.Counter(row[0] for t in tables.values() for row in t["rows"])
show("O-2", f"distinct geography labels across the 13 tables: {len(labels)}; mapped to {len(set(REGION[l.lstrip('.')] for l in labels))} keys")
for stem, t in tables.items():
    raw = list(dict.fromkeys(row[0] for row in t["rows"]))
    no_prefix = [l for l in raw if not l.startswith("..") and l != "Philippines"]
    show("O-2", f"{stem}: {len(raw)} labels; regions {len([l for l in raw if l.startswith('..')])}; "
         f"labels without the '..' prefix other than Philippines {no_prefix}")
variants = collections.defaultdict(set)
for label in labels:
    variants[REGION[label.lstrip(".")]].add(label)
show("O-2", "keys with more than one label: " + "; ".join(f"{k}: {sorted(v)}" for k, v in sorted(variants.items()) if len(v) > 1))

# %% O-8 Negros Island Region rows
has_nir = {stem: any(REGION[row[0].lstrip(".")] == "NIR" for row in t["rows"]) for stem, t in tables.items()}
show("O-8", f"tables with a Negros Island Region row: {[s for s, v in has_nir.items() if v]}; "
     f"without: {[s for s, v in has_nir.items() if not v]}")

# %% O-3 Missing-value markers
for stem, t in tables.items():
    counts = collections.Counter(c["value"] for c in t["cells"] if c["value"] in MISSING)
    if not counts:
        continue
    where = collections.Counter((c["value"], c["geo"], c["dims"], c["group"]) for c in t["cells"] if c["value"] in MISSING)
    years = collections.defaultdict(set)
    for c in t["cells"]:
        if c["value"] in MISSING:
            years[(c["value"], c["dims"])].add(c["year"])
    show("O-3", f"{stem}: {dict(counts)} of {len(t['cells'])} cells; by marker and dimension, years: "
         + "; ".join(f"{m} {d or ''} {sorted(y)}" for (m, d), y in sorted(years.items())))
    show("O-3", f"{stem}: geographies with markers: {sorted({(m, g) for (m, g, _, _) in where})}")

# %% O-4 Values parse and fall in range
for stem, t in tables.items():
    values = [c["value"] for c in t["cells"] if c["value"] not in MISSING]
    numbers = [number(v) for v in values]
    bad = [v for v, n in zip(values, numbers) if n is None]
    good = [n for n in numbers if n is not None]
    extra = ""
    if t["kind"] == "count":
        extra = f"; non-integers {sum(n != int(n) for n in good)}; negatives {sum(n < 0 for n in good)}"
    else:
        extra = f"; below 0 {sum(n < 0 for n in good)}; above 100 {sum(n > 100 for n in good)}"
    show("O-4", f"{stem} ({t['kind']}): numeric cells {len(good)}; unparseable {bad[:5]}; min {min(good):g}; max {max(good):g}{extra}")
over = [(stem, c["geo"], c["group"], c["year"], c["value"]) for stem, t in tables.items() if t["kind"] == "rate"
        for c in t["cells"] if (number(c["value"]) or 0) > 100]
show("O-4", f"rates above 100: {over}")

# %% O-5 Totals reconcile
t = tables["table_10_10_public_private_schools"]
by = {(c["geo"], c["dims"], c["year"]): number(c["value"]) for c in t["cells"]}
type_mismatch = [
    (g, level, y, by[(g, (level, "Total"), y)], by[(g, (level, "Public"), y)] + by[(g, (level, "Private"), y)])
    for (g, (level, kind), y) in by if kind == "Total"
    and by[(g, (level, "Total"), y)] != by[(g, (level, "Public"), y)] + by[(g, (level, "Private"), y)]
]
show("O-5", f"table_10_10: Total = Public + Private fails in {len(type_mismatch)} of {sum(1 for k in by if k[1][1] == 'Total')} cells: {type_mismatch[:5]}")
for stem in ("table_10_10_public_private_schools", "table_10_11_public_school_teachers"):
    t = tables[stem]
    region_sum, national = collections.Counter(), {}
    for c in t["cells"]:
        n = number(c["value"])
        if n is None:
            continue
        if c["geo"] == "PH":
            national[(c["dims"], c["year"])] = n
        else:
            region_sum[(c["dims"], c["year"])] += n
    diff = [(k, national[k], region_sum[k]) for k in national if national[k] != region_sum[k]]
    show("O-5", f"{stem}: regions sum to Philippines in {len(national) - len(diff)} of {len(national)} cells; differences {diff[:6]}")

# %% O-6 Years covered
for stem, t in tables.items():
    years = sorted({c["year"] for c in t["cells"]})
    show("O-6", f"{stem}: {len(years)} years {years[0]} to {years[-1]}: {years}")

# %% O-7 Literacy levels, Philippines and BARMM
for stem in ("table_10_13_basic_literacy", "table_10_14_functional_literacy"):
    t = tables[stem]
    show("O-7", f"{stem}: " + "; ".join(
        f"{geo} {[(c['year'], c['value']) for c in t['cells'] if c['geo'] == geo and c['group'] == 'Both Sexes']}" for geo in ("PH", "BARMM")))

# %% X-1 School counts against DepEd enrollment SY 2023-24
zip_path = RAW / "deped" / "original" / DEPED_ZIP[0]
if hashlib.sha256(zip_path.read_bytes()).hexdigest() != DEPED_ZIP[1]:
    sys.exit(f"{DEPED_ZIP[0]}: SHA-256 does not match the deped_enrollment card.")
workdir = tempfile.TemporaryDirectory()
with zipfile.ZipFile(zip_path) as zf:
    data = zf.read(next(n for n in zf.namelist() if n.endswith("/" + DEPED_ZIP[2])))
copy = Path(workdir.name) / DEPED_ZIP[2]
copy.write_bytes(data)
con.execute(f"CREATE TABLE enr AS SELECT * FROM read_csv('{copy}', all_varchar = true, header = true, strict_mode = true)")
deped = collections.Counter()
for region, sector, es, jhs, shs in con.execute("SELECT region, sector, offers_es, offers_jhs, offers_shs FROM enr WHERE sector <> 'PSO'").fetchall():
    kind = "Private" if sector == "Private" else "Public"  # SUC/LUC schools are public
    for level, offered in (("Elementary", es), ("Junior High School", jhs), ("Senior High School", shs)):
        if offered == "True":
            for geo in (DEPED_REGION[region], "PH"):
                deped[(geo, level, kind)] += 1
t = tables["table_10_10_public_private_schools"]
compared = [(c["geo"], c["dims"][0], c["dims"][1], int(number(c["value"])), deped[(c["geo"], c["dims"][0], c["dims"][1])])
            for c in t["cells"] if c["year"] == "2023-2024" and c["dims"][1] != "Total"]
mismatch = [r for r in compared if r[3] != r[4]]
show("X-1", f"table_10_10 SY 2023-24 vs DepEd enrollment (Public includes SUC/LUC; overseas schools excluded): "
     f"{len(compared) - len(mismatch)} of {len(compared)} region-level-type cells equal; differences (geo, level, type, OpenSTAT, DepEd): {mismatch}")
show("X-1", "Philippines: " + "; ".join(f"{level} {kind} {o:,} vs {d:,}" for g, level, kind, o, d in compared if g == "PH"))

# %% X-2 Teacher years against DepEd personnel
years = sorted({c["year"] for c in tables["table_10_11_public_school_teachers"]["cells"]})
show("X-2", f"table_10_11 latest school year {years[-1]}; DepEd personnel (#40) is SY 2023-24, so the two do not share a year")

# %% O-9 FLEMMS 2024 drop (the definition change is documented in the FLEMMS 2024 Technical Notes, not checked here)
for stem in ("table_10_13_basic_literacy", "table_10_14_functional_literacy"):
    vals = {c["year"]: c["value"] for c in tables[stem]["cells"] if c["geo"] == "PH" and c["group"] == "Both Sexes"}
    show("O-9", f"{stem}: Philippines 2019 {vals['2019']} -> 2024 {vals['2024']}; change {number(vals['2024']) - number(vals['2019']):+.1f} points")

# %% Data dictionary
lines = []
for stem, t in tables.items():
    lines.append(f"\n## {t['meta']['title'].strip()}\n\nFile `{stem}.csv`, OpenSTAT table `{t['id']}`.\n")
    lines.append("| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, column in enumerate(t["header"]):
        raw = [row[i] for row in t["rows"]]
        if i < t["n_dims"]:
            distinct = list(dict.fromkeys(raw))
            interp = ("**[observed]** Geography label; `..` marks a region and no prefix the country, except the `NIR` and `Unknown` rows in NAT Grades 6 and 10. Mapped to one region key per label (O-2)."
                      if i == 0 else "**[observed]** Category from the table's dimension list.")
            lines.append(f"| `{column}` | Not stated | {column} | Dimension in the API metadata | {interp} | category | 100.0% | {len(distinct)} | "
                         + ", ".join(f"`{d}`" for d in distinct[:4]) + (", ..." if len(distinct) > 4 else "") + " |")
            continue
        nums = [number(v) for v in raw if v not in MISSING and number(v) is not None]
        markers = collections.Counter(v for v in raw if v in MISSING)
        kind = {"count": "whole number", "rate": "percent", "score": "score"}[t["kind"]]
        unit_note = ("The title states the unit (In Percent); no source or footnote in the API metadata"
                     if "(In Percent)" in t["meta"]["title"] else "No unit, source, or footnote in the title or API metadata")
        interp = {
            "count": "**[observed]** Count for the categories in the row and the school year in the header.",
            "rate": "**[observed]** Percent for the group and year in the header.",
            "score": "**[assumed]** Mean percentage score for the subject and school year in the header; the unit is not stated, values run from 26 to 55.",
        }[t["kind"]]
        sample = (f"min {min(nums):g}, median {statistics.median(nums):g}, max {max(nums):g}" if nums else "no values")
        if markers:
            sample += "; markers " + ", ".join(f"`{m}` {n}" for m, n in sorted(markers.items()))
        lines.append(f"| `{column}` | Not stated | {column} | {unit_note} | {interp} | {kind} | "
                     f"{100 * len(nums) / len(raw):.1f}% | {len(set(nums))} | {sample} |")
dictionary = f"""# {SOURCE_ID}: data dictionary

Generated by [`notebooks/profiling/profile_psa_openstat.py`](../../../notebooks/profiling/profile_psa_openstat.py). Do not edit by hand; rerun the script instead.

- **Publisher descriptions:** the API metadata gives each table's title and dimension labels only; the exact column header is therefore the only publisher description available.
- **Observed columns:** measured from the checksum-verified CSVs, read as text. `Filled` is the share of rows with a number; `..`, `...`, and `a` are counted as markers, not values.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.
""" + "\n".join(lines) + "\n"
out = REPO / "docs" / "source_inventory" / SOURCE_ID / "data_dictionary.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(dictionary, encoding="utf-8")
print(f"wrote {out.relative_to(REPO)}")
