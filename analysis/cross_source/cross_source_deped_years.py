# Cross-year checks for deped_enrollment, SY 2023-24 to 2025-26 (part of #8).
#
# Reproduces every finding in:
#   docs/data/cross-source/deped-year-comparison.md
# and regenerates:
#   docs/data/cross-source/generated/deped_year_changes.md
# Each check prints under its finding ID (Y-n).
#
# Reuses the PSGC 2Q 2026 matching rules of cross_source_deped.py by running it first
# (its output is hidden here; it also rewrites generated/deped_psgc_unmatched.md, unchanged).
#
# Runs locally; no Databricks compute:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_deped_years.py
#
# RAW_DATA_DIR needs the files of cross_source_deped.py plus the SY 2024-25 and 2025-26
# enrollment zips in deped/original/. Raw files are read, never modified.

# %% Setup
import collections
import contextlib
import csv
import hashlib
import io
import re
import runpy
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")
RAW = deped["RAW"]
repair, match, match_province, match_locality, barangay_candidates = (
    deped[name] for name in ("repair", "match", "match_province", "match_locality", "barangay_candidates")
)


def show(finding, text):
    print(f"[{finding}] {text}")


# Checksums and encodings come from the deped_enrollment card (Files; O-6).
FILES = {
    "2023-24": ("Enrollment-in-SY-2023-2024.zip", "a10f4d0f9082919c13b3a091774c8231c99c95b1b1872310714107013b77dbbb", "utf-8"),
    "2024-25": ("Enrollment-in-SY-2024-2025.zip", "fd5dd74a62b828608c62335b7c324ddf05be58e3f05465fee68854795f5b1a92", "utf-8"),
    "2025-26": ("Enrollment-in-SY-2025-2026.zip", "ab4d7e24b3a46a99db2c76dee5279a976e4c3a76062e79f7217e70dc6dd1b450", "cp1252"),
}
YEARS = list(FILES)
PAIRS = list(zip(YEARS, YEARS[1:]))

data = {}
for year, (zip_name, sha, encoding) in FILES.items():
    zip_path = RAW / "deped" / "original" / zip_name
    if hashlib.sha256(zip_path.read_bytes()).hexdigest() != sha:
        sys.exit(f"{zip_name}: SHA-256 does not match the deped_enrollment card. Stop and re-inventory.")
    with zipfile.ZipFile(zip_path) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".csv"))
        text = zf.read(member).decode(encoding)
    data[year] = {r["school_id"]: r for r in csv.DictReader(io.StringIO(text))}

DESCRIPTIVE = [
    "school_id", "school_name", "region", "division", "province", "school_district", "legislative_district",
    "municipality", "barangay", "street_address", "sector", "school_management", "annex_status",
    "offers_es", "offers_jhs", "offers_shs", "Modified Curricular Offering Classification",
]
CATEGORIES = ["region", "legislative_district", "sector", "school_management", "annex_status", "offers_es", "offers_jhs", "offers_shs"]
PLACES = ["region", "division", "province", "municipality", "barangay"]


def norm(text):
    """Compare place names as the PSGC match does: repaired, capitals, spaces collapsed, no '(Capital)'."""
    text = re.sub(r"\s+", " ", repair(text or "").upper()).strip()
    return re.sub(r"\s*\(CAPITAL\)$", "", text)


# %% Y-1: rows and columns
for year in YEARS:
    first = next(iter(data[year].values()))
    show("Y-1", f"SY {year}: {len(data[year]):,} schools, {len(first)} columns, checksum OK")
for a, b in PAIRS:
    cols_a, cols_b = list(next(iter(data[a].values()))), list(next(iter(data[b].values())))
    show("Y-1", f"{a} -> {b}: columns added {[c for c in cols_b if c not in cols_a]}; removed {[c for c in cols_a if c not in cols_b]}")

# %% Y-2: category labels, compared on the same schools
# For each category, cross-tabulate a school's value in one year against the next. A pair
# that holds for (nearly) every school is a relabel; the rest are schools that changed.
label_pairs = {}
for a, b in PAIRS:
    kept = data[a].keys() & data[b].keys()
    for column in CATEGORIES:
        pairs = collections.Counter((data[a][i][column], data[b][i][column]) for i in kept)
        label_pairs[(a, b, column)] = pairs
        values_a = {v for v, _ in pairs}
        values_b = {v for _, v in pairs}
        renamed = sorted(values_b - values_a)
        show("Y-2", f"{a} -> {b} {column}: labels only in {a} {sorted(values_a - values_b)}; only in {b} {renamed}; "
             f"value pairs on kept schools {dict(pairs.most_common())}")

# %% Y-3: blank count cells
for year in YEARS:
    rows = list(data[year].values())
    counts = [c for c in rows[0] if c not in DESCRIPTIVE]
    blank_cells = collections.Counter(c for r in rows for c in counts if r[c] == "")
    shs = [c for c in counts if c.startswith(("g11_", "g12_"))]
    below = [c for c in counts if c not in shs]
    shs_blank = sum(1 for r in rows if all(r[c] == "" for c in shs))
    below_blank = sum(1 for r in rows if all(r[c] == "" for c in below))
    shs_blank_offering = sum(1 for r in rows if r["offers_shs"] in ("True", "Yes") and all(r[c] == "" for c in shs))
    shs_learners_not_offering = sum(1 for r in rows if r["offers_shs"] in ("False", "No") and any(r[c] not in ("", "0") for c in shs))
    all_blank = sum(1 for r in rows if all(r[c] == "" for c in counts))
    show("Y-3", f"SY {year}: count columns {len(counts)}; columns with any blank {len(blank_cells)}; "
         f"schools with every SHS column blank {shs_blank:,} (of them offering SHS {shs_blank_offering}); "
         f"SHS learners counted but not offering SHS {shs_learners_not_offering}; every Kinder to Grade 10 column blank {below_blank:,}; "
         f"every count blank {all_blank}")

# %% Y-4: school IDs that leave, join, or skip a year
id_rows = []
for a, b in PAIRS:
    kept, dropped, new = data[a].keys() & data[b].keys(), data[a].keys() - data[b].keys(), data[b].keys() - data[a].keys()
    show("Y-4", f"{a} -> {b}: kept {len(kept):,}; dropped {len(dropped):,} by sector {dict(collections.Counter(data[a][i]['sector'] for i in dropped).most_common())}; "
         f"new {len(new):,} by sector {dict(collections.Counter(data[b][i]['sector'] for i in new).most_common())}")
    id_rows += [(f"{a} to {b}", "dropped", data[a][i]) for i in sorted(dropped)]
    id_rows += [(f"{a} to {b}", "new", data[b][i]) for i in sorted(new)]
gap = (data["2023-24"].keys() & data["2025-26"].keys()) - data["2024-25"].keys()
all_three = data["2023-24"].keys() & data["2024-25"].keys() & data["2025-26"].keys()
show("Y-4", f"in all three years {len(all_three):,}; in SY 2023-24 and 2025-26 but not 2024-25: {len(gap)} {sorted(gap)}")

# %% Y-5: place names that change for the same school
place_rows = []
for a, b in PAIRS:
    kept = sorted(data[a].keys() & data[b].keys())
    for column in PLACES:
        raw = [i for i in kept if data[a][i][column] != data[b][i][column]]
        real = [i for i in raw if norm(data[a][i][column]) != norm(data[b][i][column])]
        show("Y-5", f"{a} -> {b} {column}: differs as published {len(raw):,}; after normalizing spacing, case, encoding, and '(Capital)' {len(real):,}"
             + (f"; changes {dict(collections.Counter((data[a][i][column], data[b][i][column], norm(data[b][i]['province'])) for i in real).most_common(8))}" if column in ("region", "province") else ""))
        if column in ("province", "municipality", "barangay"):
            place_rows += [(f"{a} to {b}", column, i, data[a][i], data[b][i]) for i in real]
    moved = [i for i in kept if norm(data[a][i]["municipality"]) != norm(data[b][i]["municipality"])
             or norm(data[a][i]["province"]) != norm(data[b][i]["province"])]
    show("Y-5", f"{a} -> {b}: schools whose province or city/municipality changes {len(moved):,}")

# %% Y-6: PSGC 2Q 2026 match for each year, with the SY 2023-24 rules
matched_code = {}
unmatched_names = {}
for year in YEARS:
    schools = [
        (i, r["region"], repair(r["province"]), repair(r["municipality"]), repair(r["barangay"]) or None)
        for i, r in data[year].items() if r["sector"] != "PSO"
    ]
    prov_result = {p: match_province(p) for p in {s[2] for s in schools}}
    loc_result, bgy_result = {}, {}
    for _, _, prov, mun, bgy in schools:
        if (prov, mun) not in loc_result:
            loc_result[(prov, mun)] = match_locality(mun, prov_result[prov][1])
        locality = loc_result[(prov, mun)][1]
        if (prov, mun, bgy) not in bgy_result:
            if bgy is None:
                bgy_result[(prov, mun, bgy)] = ("no barangay given", None)
            elif locality is None:
                bgy_result[(prov, mun, bgy)] = ("locality unmatched", None)
            else:
                bgy_result[(prov, mun, bgy)] = match(bgy, barangay_candidates(locality), truncatable=True)
    outcome = collections.Counter()
    for i, _, prov, mun, bgy in schools:
        tier, unit = bgy_result[(prov, mun, bgy)]
        matched_code[(year, i)] = unit.id if unit else None
        outcome["matched" if unit else ("ambiguous barangay" if tier == "ambiguous" else tier if tier != "unmatched" else "barangay unmatched")] += 1
    # Keys are normalized so that a spacing or case change alone is not a new unmatched name.
    unmatched_names[year] = {
        "province": {norm(p) for p, (t, pre) in prov_result.items() if not pre},
        "city or municipality": {tuple(map(norm, k)) for k, (t, u) in loc_result.items() if u is None},
        "barangay": {tuple(map(norm, k)) for k, (t, u) in bgy_result.items() if u is None and t != "locality unmatched"},
    }
    show("Y-6", f"SY {year}: schools {len(schools):,} (overseas excluded); matched to barangay {outcome['matched']:,} "
         f"({100 * outcome['matched'] / len(schools):.1f}%); not matched {dict((k, v) for k, v in outcome.most_common() if k != 'matched')}; "
         f"unmatched or ambiguous names: provinces {len(unmatched_names[year]['province'])} {sorted(unmatched_names[year]['province'])}, "
         f"cities and municipalities {len(unmatched_names[year]['city or municipality'])}, barangays {len(unmatched_names[year]['barangay'])}")

name_rows = []
for year in YEARS[1:]:
    for level in ("province", "city or municipality", "barangay"):
        new = unmatched_names[year][level] - unmatched_names["2023-24"][level]
        show("Y-6", f"SY {year} {level} names unmatched that were not unmatched in SY 2023-24: {len(new)}")
        name_rows += [(year, level, n) for n in sorted(new, key=lambda k: tuple(x or "" for x in (k if isinstance(k, tuple) else (k,))))]

for a, b in PAIRS:
    kept = [i for i in data[a].keys() & data[b].keys() if (a, i) in matched_code]
    same = sum(1 for i in kept if matched_code[(a, i)] and matched_code[(a, i)] == matched_code[(b, i)])
    differ = sum(1 for i in kept if matched_code[(a, i)] and matched_code[(b, i)] and matched_code[(a, i)] != matched_code[(b, i)])
    only_a = sum(1 for i in kept if matched_code[(a, i)] and not matched_code[(b, i)])
    only_b = sum(1 for i in kept if not matched_code[(a, i)] and matched_code[(b, i)])
    show("Y-6", f"{a} -> {b} kept schools {len(kept):,}: same barangay code {same:,}; different code {differ:,}; "
         f"matched in {a} only {only_a:,}; matched in {b} only {only_b:,}")

# %% Write the lists
def cell(value):
    return str(value or "").replace("|", "\\|")


lines = [
    "# DepEd enrollment: changes between SY 2023-24, 2024-25, and 2025-26",
    "",
    "Generated by [`cross_source_deped_years.py`](../../../analysis/cross_source/cross_source_deped_years.py). Do not edit by hand; change the script and rerun. "
    "Findings and how to read these lists: [deped-year-comparison.md](../deped-year-comparison.md). Part of #8.",
    "",
    "## School IDs dropped or new (Y-4)",
    "",
    f"{len(id_rows):,} rows. A dropped ID is not proof that a school closed.",
    "",
    "| Years | Change | School ID | School name | Sector | Region | Province | City or municipality |",
    "|---|---|---|---|---|---|---|---|",
]
lines += [f"| {y} | {c} | {r['school_id']} | {cell(r['school_name'])} | {cell(r['sector'])} | {cell(r['region'])} | {cell(r['province'])} | {cell(r['municipality'])} |" for y, c, r in id_rows]
lines += [
    "",
    "## Place names that change for the same school (Y-5)",
    "",
    f"{len(place_rows):,} rows: province, city or municipality, or barangay names that still differ after spacing, case, encoding, and '(Capital)' are normalized.",
    "",
    "| Years | Field | School ID | Province | City or municipality | Before | After |",
    "|---|---|---|---|---|---|---|",
]
lines += [f"| {y} | {f} | {i} | {cell(rb['province'])} | {cell(rb['municipality'])} | {cell(ra[f])} | {cell(rb[f])} |" for y, f, i, ra, rb in place_rows]
lines += [
    "",
    "## Names not matched to PSGC 2Q 2026 that were matched, or absent, in SY 2023-24 (Y-6)",
    "",
    f"{len(name_rows):,} rows.",
    "",
    "| School year | Level | Province | City or municipality | Barangay |",
    "|---|---|---|---|---|",
]
for year, level, key in name_rows:
    key = key if isinstance(key, tuple) else (key,)
    lines.append(f"| {year} | {level} | " + " | ".join(cell(k) for k in (list(key) + ["", ""])[:3]) + " |")
(REPO / "docs" / "data" / "cross-source" / "generated" / "deped_year_changes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
show("run", f"wrote docs/data/cross-source/generated/deped_year_changes.md: {len(id_rows):,} ID rows, {len(place_rows):,} place rows, {len(name_rows):,} name rows")
