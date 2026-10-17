# Option B check for #137 and #91: compare the PSGC codes in the EMISD workbook
# (deped_enrollment_psgc, #135) with the name match of cross_source_deped.py, school by school,
# for SY 2023-24. Answers: how often do they agree, where do they disagree and why, and how
# many schools are matched when the EMISD code comes first and the name match is the fallback.
#
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_deped_enrollment_psgc.py
#
# RAW_DATA_DIR needs the files of cross_source_deped.py plus, in deped/original/, the EMISD
# workbook (FILE below). Raw files are read, never modified (D-007). Runs locally; no Databricks.
# Writes one CSV with a row per school that does not agree at both levels, to work/ (git-ignored)
# or OUT_DIR: it holds school-level rows, so it is not committed.
#
# Part 2 (EP-12 to EP-16) applies the proposed #91 match rule in config/mappings/integration/deped_school_psgc.json
# and writes a preview of the map, one row per school and level, with the D-029 columns.
#
# Rules applied to the EMISD codes before comparing (all counted):
#   - padded to 10 digits: Excel stored them as numbers and dropped the leading zero (profile O-5);
#   - `#N/A` and blank mean no code (O-6);
#   - "Sulu region": a code missing from PSGC 2Q 2026 whose region `19` read as `09` is in it
#     (Q4 2024 still had Sulu under BARMM; D-029 `code_region_moved`, as for HDX);
#   - a code still missing from PSGC 2Q 2026 is "code not in 2Q 2026" and not used;
#   - a Manila sub-municipality rolls up to the City of Manila, as the name match does.

# %% Setup
import collections
import contextlib
import csv
import hashlib
import io
import json
import os
import re
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet

# Name match of every SY 2023-24 school: the rules, tiers and aliases of cross_source_deped.py.
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")
RAW = deped["RAW"]
schools = deped["schools"]  # (school_id, region, province, municipality, barangay), PSO excluded
loc_result, bgy_result = deped["loc_result"], deped["bgy_result"]
units_by_id = deped["units_by_id"]
city_or_municipality = deped["city_or_municipality"]
name_match, barangay_candidates = deped["match"], deped["barangay_candidates"]

FILE = "SY 2023-2024 School Level Data on Enrollment with PSGC, Longitude and Latitude.xlsx"
SHA256 = "746d69530d228d2324590be10abbe6d75a94176c1745ef74335a4d6db550acd5"
SHEET, HEADER_ROW = "DB", 8
# Columns by number (A = 1), from the deped_enrollment_psgc data dictionary; the header is checked below.
COLUMNS = {"school_id": (4, "BEIS School ID"), "mun": (22, "(PSGC) MUNCIPAL/CITY"), "bgy": (24, "(PSGC) BARANGAY")}
# work/ is git-ignored; set OUT_DIR to write elsewhere.
OUT_DIR = Path(os.environ.get("OUT_DIR", REPO / "work")).expanduser()
OUT = OUT_DIR / "deped_enrollment_psgc_vs_name_match.csv"
MAP_OUT = OUT_DIR / "deped_school_psgc_map_preview.csv"
RULES = json.loads((REPO / "config" / "mappings" / "integration" / "deped_school_psgc.json").read_text(encoding="utf-8"))


def show(finding, text):
    print(f"[{finding}] {text}")


def pct(n, d):
    return f"{n:,} of {d:,} ({100 * n / d:.1f}%)" if d else f"{n:,} of 0"


# %% Load the EMISD codes
path = RAW / "deped" / "original" / FILE
if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{FILE}: SHA-256 does not match the deped_enrollment_psgc card. Stop and re-inventory.")
rows = read_sheet(path, SHEET)
header = dict(rows[HEADER_ROW - 1][1])
for key, (col, name) in COLUMNS.items():
    if re.sub(r"\s+", " ", header.get(col, "")).strip() != name:
        sys.exit(f"{FILE}: column {col} is {header.get(col)!r}, expected {name!r}. The header changed; stop.")

rule_counts = collections.Counter()


def psgc(raw, levels):
    """(tier, unit) for an EMISD code cell, on PSGC 2Q 2026."""
    text = (raw or "").strip()
    if text in ("", "#N/A"):
        return "no code", None
    if not text.isdigit():
        return "code not digits", None
    code = text.zfill(10)
    unit = units_by_id.get(code)
    tier = "code"
    if unit is None and code.startswith("19") and units_by_id.get("09" + code[2:]):
        unit, tier = units_by_id["09" + code[2:]], "code, Sulu region"
    if unit is None:
        return "code not in 2Q 2026", None
    if unit.level not in levels:
        return f"code is a {unit.level}", None
    return tier, unit


emisd = {}
for _, cells in rows[HEADER_ROW:]:
    school_id = cells.get(COLUMNS["school_id"][0], "").strip()
    if school_id:
        emisd[school_id] = (
            psgc(cells.get(COLUMNS["mun"][0]), ("City", "Mun", "SubMun")),
            psgc(cells.get(COLUMNS["bgy"][0]), ("Bgy",)),
        )
show("run", f"{FILE}: {len(emisd):,} school IDs, checksum OK")

# %% Compare, level by level
sga = {s[0] for s in schools if s[1] == "BARMM" and s[2] == "NORTH COTABATO"}  # D-031


def in_taguig(unit):
    """True when a PSGC unit is the City of Taguig or one of its barangays (Embo moved there from Makati)."""
    parents = [unit] + [units_by_id.get(unit.id[:n] + "0" * (10 - n)) for n in (7, 5)]
    return any(u is not None and "Taguig" in u.name for u in parents)


LEVELS = ("city or municipality", "barangay")
outcome = {lvl: collections.Counter() for lvl in LEVELS}
tiers = {lvl: collections.Counter() for lvl in LEVELS}
b_matched = {lvl: 0 for lvl in LEVELS}
b_method = {lvl: collections.Counter() for lvl in LEVELS}
disagree_by_province = {lvl: collections.Counter() for lvl in LEVELS}
out_rows = []

for school_id, region, province, municipality, barangay in schools:
    name_loc = loc_result[(province, municipality)][1]
    name_bgy = bgy_result[(province, municipality, barangay)][1]
    names = {
        "city or municipality": (loc_result[(province, municipality)][0], city_or_municipality(name_loc) if name_loc else None),
        "barangay": (bgy_result[(province, municipality, barangay)][0], name_bgy),
    }
    (mun_tier, mun_unit), (bgy_tier, bgy_unit) = emisd.get(school_id, (("not in workbook", None), ("not in workbook", None)))
    codes = {
        "city or municipality": (mun_tier, city_or_municipality(mun_unit) if mun_unit else None),
        "barangay": (bgy_tier, bgy_unit),
    }
    row = {"school_id": school_id, "deped_region": region, "deped_province": province,
           "deped_municipality": municipality, "deped_barangay": barangay}
    keep = False
    for lvl in LEVELS:
        (c_tier, c_unit), (n_tier, n_unit) = codes[lvl], names[lvl]
        tiers[lvl][c_tier] += 1
        if c_unit and n_unit:
            result = "agree" if c_unit.id == n_unit.id else "disagree"
        elif c_unit:
            result = "code only"
        elif n_unit:
            result = "name only"
        else:
            result = "neither"
        if result == "disagree":
            if school_id in sga:
                result = "disagree: Special Geographic Area"
            elif "MAKATI" in (municipality or "").upper() and in_taguig(c_unit):
                result = "disagree: Embo (Makati to Taguig)"
            else:
                disagree_by_province[lvl][province] += 1
        outcome[lvl][result] += 1
        # Option B: the EMISD code first, the name match as fallback.
        if c_unit:
            b_matched[lvl] += 1
            b_method[lvl]["code, Sulu region" if c_tier == "code, Sulu region" else "code"] += 1
        elif n_unit:
            b_matched[lvl] += 1
            b_method[lvl][f"name: {n_tier}"] += 1
        key = "mun" if lvl == "city or municipality" else "bgy"
        row |= {f"{key}_result": result, f"{key}_code_tier": c_tier, f"{key}_code": c_unit.id if c_unit else "",
                f"{key}_code_name": c_unit.name if c_unit else "", f"{key}_name_tier": n_tier,
                f"{key}_name_code": n_unit.id if n_unit else "", f"{key}_name_name": n_unit.name if n_unit else ""}
        keep = keep or result != "agree"
    if keep:
        out_rows.append(row)

total = len(schools)
show("EP-1", f"schools compared: {total:,} (SY 2023-24, PSO excluded); in the EMISD workbook: "
     f"{pct(sum(1 for s in schools if s[0] in emisd), total)}")
for i, lvl in enumerate(LEVELS):
    show(f"EP-{2 + i}", f"{lvl}, EMISD code: {dict(tiers[lvl].most_common())}")
for i, lvl in enumerate(LEVELS):
    show(f"EP-{4 + i}", f"{lvl}, code vs name: " + "; ".join(f"{k} {pct(v, total)}" for k, v in outcome[lvl].most_common()))
for i, lvl in enumerate(LEVELS):
    show(f"EP-{6 + i}", f"{lvl}, unexplained disagreements by DepEd province (top 10): "
         f"{dict(disagree_by_province[lvl].most_common(10))}")
for i, lvl in enumerate(LEVELS):
    show(f"EP-{8 + i}", f"{lvl}, Option B (code first, name fallback): matched {pct(b_matched[lvl], total)}; "
         f"by method {dict(b_method[lvl].most_common())}")
name_only_full = sum(1 for s in schools if bgy_result[(s[2], s[3], s[4])][1] is not None)
show("EP-10", f"barangay coverage, name match alone {pct(name_only_full, total)} vs Option B {pct(b_matched['barangay'], total)}")

# %% Write the schools that do not agree at both levels
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0]) if out_rows else ["school_id"])
    writer.writeheader()
    writer.writerows(out_rows)
show("EP-11", f"wrote {OUT}: {len(out_rows):,} schools that do not agree at both levels")


# %% Part 2: the proposed #91 match rule (config/mappings/integration/deped_school_psgc.json)
TIER_METHOD = RULES["match_method_from_name_tier"]
OVERRIDES = {(o["level"], o["deped_province"], o["deped_municipality"], o["deped_barangay"]): o for o in RULES["overrides"]}
override_hits = collections.Counter()


def method_of(tier):
    return TIER_METHOD.get(tier, "name_normalized")


def same_barangay_name(deped_barangay, unit):
    """True when DepEd's barangay name matches this PSGC barangay by the DepEd tiers (as HDX does)."""
    return bool(deped_barangay) and unit is not None and name_match(deped_barangay, [unit])[1] is not None


def decide_city(school, c_unit, c_tier, n_unit, n_tier, c_bgy):
    """(status, unit, method, detail) for the city or municipality."""
    school_id, region, province, municipality, barangay = school
    o = OVERRIDES.get(("city_mun", province, municipality, barangay))
    if o:
        override_hits["city_mun"] += 1
        unit = c_unit if o["use"] == "code" else n_unit
        return ("matched" if unit else "unmatched"), unit, o["match_method"], "reviewed override"
    code_method = "code_region_moved" if c_tier == "code, Sulu region" else "code"
    if school_id in sga:
        unit = c_unit if c_unit and same_barangay_name(barangay, c_bgy) else n_unit
        return "excluded", unit, code_method if unit is c_unit and unit else method_of(n_tier), "Special Geographic Area (D-031)"
    if c_unit and n_unit and c_unit.id == n_unit.id:
        return "matched", c_unit, code_method, "code and name agree"
    if c_unit and n_unit:
        if same_barangay_name(barangay, c_bgy):
            return "matched", c_unit, code_method, "code; DepEd barangay name matches the code's barangay"
        return "ambiguous", None, None, "code and name differ"
    if c_unit:
        return "matched", c_unit, code_method, "code only"
    if n_unit:
        return "matched", n_unit, method_of(n_tier), f"name only ({n_tier})"
    return "unmatched", None, None, "no code, no name match"


def decide_barangay(school, city, c_unit, c_tier, n_unit, n_tier):
    school_id, region, province, municipality, barangay = school
    o = OVERRIDES.get(("bgy", province, municipality, barangay))
    if o:
        override_hits["bgy"] += 1
        unit = c_unit if o["use"] == "code" else n_unit
        return ("matched" if unit else "unmatched"), unit, o["match_method"], "reviewed override"
    city_status, city_unit = city[0], city[1]
    if city_status in ("ambiguous", "unmatched"):
        return city_status, None, None, f"city or municipality {city_status}"
    inside = set(u.id for u in barangay_candidates(city_unit)) if city_unit else set()
    code_method = "code_region_moved" if c_tier == "code, Sulu region" else "code"
    candidates = []
    if c_unit and n_unit and c_unit.id == n_unit.id:
        candidates = [(c_unit, code_method, "code and name agree")]
    elif c_unit and same_barangay_name(barangay, c_unit):
        candidates = [(c_unit, code_method, "code; DepEd barangay name matches")]
    elif c_unit and n_unit:
        return "ambiguous", None, None, "code and name differ"
    elif c_unit:
        candidates = [(c_unit, code_method, "code only")]
    elif n_unit:
        candidates = [(n_unit, method_of(n_tier), f"name only ({n_tier})")]
    else:
        return "unmatched", None, None, "no code, no name match"
    unit, method, detail = candidates[0]
    if unit.id not in inside:
        return "ambiguous", None, None, "barangay outside the accepted city or municipality"
    return ("excluded" if city_status == "excluded" else "matched"), unit, method, detail


status = {lvl: collections.Counter() for lvl in ("city_mun", "bgy")}
method = {lvl: collections.Counter() for lvl in ("city_mun", "bgy")}
detail = {lvl: collections.Counter() for lvl in ("city_mun", "bgy")}
map_rows = []
for school in schools:
    school_id, region, province, municipality, barangay = school
    (mun_tier, mun_unit), (bgy_tier, bgy_unit) = emisd.get(school_id, (("not in workbook", None), ("not in workbook", None)))
    c_city = city_or_municipality(mun_unit) if mun_unit else None
    n_loc_tier, n_loc = loc_result[(province, municipality)]
    n_city = city_or_municipality(n_loc) if n_loc else None
    n_bgy_tier, n_bgy = bgy_result[(province, municipality, barangay)]
    city = decide_city(school, c_city, mun_tier, n_city, n_loc_tier, bgy_unit)
    bgy = decide_barangay(school, city, bgy_unit, bgy_tier, n_bgy, n_bgy_tier)
    for lvl, (st, unit, meth, why) in (("city_mun", city), ("bgy", bgy)):
        status[lvl][st] += 1
        method[lvl][meth or "-"] += 1
        detail[lvl][(st, why)] += 1
        map_rows.append({
            "source_id": "deped_enrollment", "source_row_ref": f"{school_id}|2023-2024", "school_id": school_id,
            "deped_region": region, "deped_province": province, "deped_municipality": municipality, "deped_barangay": barangay,
            "source_reference_date": "SY 2023-24", "psgc_version": RULES["psgc_version"],
            "geographic_level": lvl, "psgc_code": unit.id if unit else "", "psgc_name": unit.name if unit else "",
            "match_status": st, "match_method": meth or "", "match_detail": why,
        })

for i, lvl in enumerate(("city_mun", "bgy")):
    show(f"EP-{12 + i}", f"{lvl}, proposed rule: " + "; ".join(f"{k} {pct(v, total)}" for k, v in status[lvl].most_common())
         + f"; by method {dict(method[lvl].most_common())}")
for i, lvl in enumerate(("city_mun", "bgy")):
    show(f"EP-{14 + i}", f"{lvl}, not matched, by reason: "
         + str({f"{st}: {why}": n for (st, why), n in detail[lvl].most_common() if st != "matched"}))
show("EP-16", f"reviewed overrides applied: {dict(override_hits)}; wrote {MAP_OUT}: {len(map_rows):,} rows (school x level)")
with MAP_OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(map_rows[0]))
    writer.writeheader()
    writer.writerows(map_rows)
