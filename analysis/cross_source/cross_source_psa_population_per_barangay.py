# Cross-source checks for psa_population_per_barangay against PSGC 2Q 2026 (part of #8).
#
# Prints the findings labelled BP-n in:
#   docs/data/cross-source/coverage.md
# and regenerates:
#   docs/data/cross-source/generated/psa_population_psgc_unmatched.md
#
# Reuses two scripts by running them first (their output is hidden here):
#   - cross_source_deped.py for the PSGC 2Q 2026 matching rules (it also rewrites
#     deped_psgc_unmatched.md, unchanged);
#   - profile_psa_population_per_barangay.py for the checksum check and the workbook parser
#     (it also rewrites its data_dictionary.md, unchanged).
#
# Runs locally; no Databricks compute:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_psa_population_per_barangay.py
#
# RAW_DATA_DIR needs the files of both scripts above. Raw files are read, never modified.

# %% Setup
import collections
import contextlib
import html
import io
import re
import runpy
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")
    population = runpy.run_path(str(HERE / "profile_psa_population_per_barangay.py"), run_name="__main__")
match, match_province, match_locality, barangay_candidates = (
    deped[name] for name in ("match", "match_province", "match_locality", "barangay_candidates")
)
units = {u.id: u for u in deped["units"]}
localities = deped["localities"]
barangays = population["all_barangays"]
sheet_totals = {(t["file"], t["sheet"]): t for t in population["sheet_totals"]}
SOURCE_DIR = population["SOURCE_DIR"]


def show(finding, text):
    print(f"[{finding}] {text}")


def psgc_population(row):
    try:
        return int(float(str(row.get(9)).replace(",", "")))
    except ValueError:
        return None


psgc_pop = {r.get(1, ""): psgc_population(r) for r in deped["psgc_rows"][1:]}

# %% Footnote markers
# The workbooks set footnote markers in superscript runs ("Barangay 176-A" + superscript "1"),
# and a few as Unicode superscript digits. Text extraction keeps them as plain digits
# (profile S-1). Here they are dropped exactly, from the workbooks' own formatting.
SUPERSCRIPT_DIGITS = "¹²³⁰⁴⁵⁶⁷⁸⁹"
without_superscript = {}
for workbook in sorted({b["file"] for b in barangays}):
    xml = zipfile.ZipFile(SOURCE_DIR / workbook).read("xl/sharedStrings.xml").decode("utf-8")
    for item in re.findall(r"<si>(.*?)</si>", xml, re.S):
        runs = re.findall(r"<r>(.*?)</r>", item, re.S)
        text = lambda keep: "".join(html.unescape(t) for r in runs if keep(r) for t in re.findall(r"<t[^>]*>(.*?)</t>", r, re.S))
        full, kept = text(lambda r: True), text(lambda r: 'vertAlign val="superscript"' not in r)
        if runs and full != kept:
            without_superscript[re.sub(r"\s+", " ", full).strip()] = re.sub(r"\s+", " ", kept).strip()


def clean(name):
    name = re.sub(r"\s+", " ", name).strip()
    name = without_superscript.get(name, name)
    name = re.sub(f"\\s*[{SUPERSCRIPT_DIGITS}]+", "", name)
    return re.sub(r"\s*\*+$", "", name).strip()


show("BP-1", f"strings with superscript footnote markers in the workbooks: {len(without_superscript)}; examples "
     f"{list(without_superscript.items())[:4]}")

# %% Match: sheet to province or city, parent to city or municipality, then barangay
# Same rules as the DepEd match (cross_source_deped.py). Added here: the Special Geographic
# Area sheet maps to its PSGC municipalities (codes 19999), and an asterisk at the end of a
# PSGC barangay name (for example "Fuentes*") is ignored, as one more counted tier.
sheet_unit = {}
for key, total in sheet_totals.items():
    name = clean(total["name"])
    if name.upper() in ("SGA", "SPECIAL GEOGRAPHIC AREA"):
        sheet_unit[key] = ("province", ["19999"])
        continue
    tier, prefixes = match_province(name)
    if prefixes:
        sheet_unit[key] = ("province", prefixes)
    else:
        tier, unit = match(name, localities)
        sheet_unit[key] = ("locality", unit) if unit else ("unmatched", None)


def locality_of(row):
    kind, value = sheet_unit[(row["file"], row["sheet"])]
    parent = clean(row["parent_area"])
    if kind == "province":
        return match_locality(parent, value)
    if kind == "locality":
        if parent.upper() == clean(sheet_totals[(row["file"], row["sheet"])]["name"]).upper():
            return "sheet", value
        return match(parent, [u for u in localities if u.id.startswith(value.id[:5])])
    return "sheet unmatched", None


results = []
locality_cache = {}
for row in barangays:
    key = (row["file"], row["sheet"], row["parent_area"])
    if key not in locality_cache:
        locality_cache[key] = locality_of(row)
    locality = locality_cache[key][1]
    if locality is None:
        results.append((row, "city or municipality unmatched", None))
        continue
    candidates = barangay_candidates(locality)
    tier, unit = match(clean(row["name"]), candidates)
    if unit is None and tier == "unmatched":
        hits = [u for u in candidates if re.sub(r"\*+$", "", u.name).strip().upper() == clean(row["name"]).upper()]
        tier, unit = ("asterisk ignored", hits[0]) if len(hits) == 1 else (tier, None)
    results.append((row, tier, unit))

by_tier = collections.Counter(t for _, t, u in results if u)
left = [(r, t) for r, t, u in results if u is None]
codes = collections.Counter(u.id for _, _, u in results if u)
show("BP-2", f"workbook barangays {len(barangays):,}; matched to a PSGC barangay by name {sum(by_tier.values()):,} "
     f"({100 * sum(by_tier.values()) / len(barangays):.2f}%) by tier {dict(by_tier.most_common())}; "
     f"PSGC codes matched more than once {sum(1 for c in codes.values() if c > 1)}; not matched {len(left)} "
     f"{dict(collections.Counter(t for _, t in left))}")

# %% Population of each name match against PSGC 2024 Population
named = [(r, u) for r, _, u in results if u]
differ = [(u.id, u.name, units[u.id[:7] + "000"].name, psgc_pop[u.id], r["population"]) for r, u in named if psgc_pop[u.id] != r["population"]]
show("BP-3", f"name matches with the same population in PSGC 2Q 2026: {len(named) - len(differ):,} of {len(named):,}; "
     f"different (code, name, city or municipality, PSGC, workbook): {differ}")

# %% Pair what is left by population inside the same province or HUC
# A pair is accepted only when exactly one leftover PSGC barangay under the same province or
# HUC code has the same population. It is evidence of the same place under another name, not
# a name match, and is listed separately.
matched_codes = set(codes)
psgc_left = [u for u in deped["units"] if u.level == "Bgy" and u.id not in matched_codes]


def area_prefixes(row):
    kind, value = sheet_unit[(row["file"], row["sheet"])]
    return value if kind == "province" else [value.id[:5]] if kind == "locality" else []


pairs, unpaired = [], []
for row, tier in left:
    same = [u for u in psgc_left if any(u.id.startswith(p) for p in area_prefixes(row)) and psgc_pop[u.id] == row["population"]]
    (pairs.append((row, same[0])) if len(same) == 1 else unpaired.append(row))
paired_codes = {u.id for _, u in pairs}
psgc_unpaired = [u for u in psgc_left if u.id not in paired_codes]
show("BP-4", f"left after the name match: workbook {len(left)}, PSGC {len(psgc_left)}; paired by equal population {len(pairs)}; "
     f"still unpaired: workbook {[(r['sheet'], clean(r['parent_area']), r['name'], r['population']) for r in unpaired]}; "
     f"PSGC {[(u.id, u.name, psgc_pop[u.id]) for u in psgc_unpaired]}")

# %% Explain the one-barangay difference
for row in unpaired:
    for code, name, parent, psgc_value, workbook_value in differ:
        if psgc_value == workbook_value + row["population"]:
            show("BP-5", f"workbook barangay {row['name']} ({clean(row['parent_area'])}, {row['population']:,}) plus workbook {name} "
                 f"({workbook_value:,}) equals PSGC {name} ({code}, {psgc_value:,}): one PSGC barangay covers two workbook barangays")

# %% Write the list
def cell(value):
    return str(value).replace("|", "\\|")


lines = [
    "# PSA 2024 barangay population: names not matched exactly to PSGC 2Q 2026",
    "",
    "Generated by [`cross_source_psa_population_per_barangay.py`](../../../analysis/cross_source/cross_source_psa_population_per_barangay.py). "
    "Do not edit by hand; change the script and rerun. Every other workbook barangay matches a PSGC barangay by its exact name. Part of #8.",
    "",
    "| Province or HUC sheet | City or municipality | Workbook barangay | Population | How it was matched | PSGC code | PSGC name |",
    "|---|---|---|---:|---|---|---|",
]
for row, tier, unit in results:
    if unit and tier != "exact":
        lines.append(f"| {cell(row['sheet'])} | {cell(clean(row['parent_area']))} | {cell(row['name'])} | {row['population']:,} | name, {tier} | {unit.id} | {cell(unit.name)} |")
for row, unit in pairs:
    lines.append(f"| {cell(row['sheet'])} | {cell(clean(row['parent_area']))} | {cell(row['name'])} | {row['population']:,} | equal population, same province or HUC | {unit.id} | {cell(unit.name)} |")
for row in unpaired:
    lines.append(f"| {cell(row['sheet'])} | {cell(clean(row['parent_area']))} | {cell(row['name'])} | {row['population']:,} | not matched | | |")
(REPO / "docs" / "data" / "cross-source" / "generated" / "psa_population_psgc_unmatched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
show("run", f"wrote docs/data/cross-source/generated/psa_population_psgc_unmatched.md: {len(lines) - 6} rows")
