# Cross-source checks for hdx_boundaries (COD-AB v03) against PSGC 2Q 2026 (part of #8).
#
# Prints the findings labelled HB-n in:
#   docs/data/cross-source/coverage.md
# and regenerates:
#   docs/data/cross-source/generated/hdx_boundaries_psgc_unmatched.md
#
# Reuses the PSGC 2Q 2026 matching rules of cross_source_deped.py by running it first (its
# output is hidden here; it also rewrites generated/deped_psgc_unmatched.md, unchanged).
#
# Runs locally; no Databricks compute. Only the attributes of each feature are parsed; the
# geometry is skipped, so the 1.27 GB of GeoJSON is read line by line in little memory:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_hdx_boundaries.py
#
# RAW_DATA_DIR needs the files of cross_source_deped.py plus admin_boundaries/original/ with
# phl_admin3.geojson and phl_admin4.geojson (checksums from the hdx_boundaries card, #38).

# %% Setup
import collections
import contextlib
import hashlib
import io
import json
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")
RAW, match = deped["RAW"], deped["match"]
units = {u.id: u for u in deped["units"]}
correspondence = {}
for row in deped["psgc_rows"][1:]:
    code = row.get(3, "").strip()
    if code:
        correspondence[code] = row.get(1, "")

FILES = {
    "adm3": ("phl_admin3.geojson", "f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41"),
    "adm4": ("phl_admin4.geojson", "4ebb5e3cf7b3245c659ea5886725e6a77ffc2d4bcbe3963d8f704d5adc5523d2"),
}


def show(finding, text):
    print(f"[{finding}] {text}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def properties(path):
    """Yield each feature's properties. The files hold one feature per line."""
    marker = ',"geometry":'
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith('{"type":"Feature"'):
                head = line[: line.index(marker)] + "}"
                yield json.loads(head)["properties"]


layers = {}
for layer, (name, sha) in FILES.items():
    path = RAW / "admin_boundaries" / "original" / name
    if sha256(path) != sha:
        sys.exit(f"{name}: SHA-256 does not match the hdx_boundaries card. Stop and re-inventory.")
    layers[layer] = list(properties(path))
    show("HB-1", f"{name}: {len(layers[layer]):,} features, checksum OK; valid_on {sorted({p['valid_on'] for p in layers[layer]})}; "
         f"version {sorted({p['version'] for p in layers[layer]})}; regions {len({p['adm1_pcode'] for p in layers[layer]})}")


# %% Code rules
# A P-code is "PH" plus PSGC-style digits: region (2), province (3), city or municipality (2),
# and for ADM4 barangay (3). Padded with zeros it is a 10-digit PSGC-style code. Rules, in order,
# each counted:
#   - "exact code": that code is in PSGC 2Q 2026 at the same level;
#   - "Correspondence Code": the old 9-digit form (region 2, the last 2 province digits,
#     city or municipality 2, barangay 3) equals a PSGC `Correspondence Code` (S-2 on the PSGC
#     card). This catches the Negros Island Region units, still coded under Regions VI and VII;
#   - "Sulu region": region 19 written as 09 (Sulu moved from BARMM to Region IX);
#   - "name in parent": the name matched with the DepEd rules inside the same PSGC province
#     or city found for the parent code.
LEVELS = {"adm3": ("City", "Mun"), "adm4": ("Bgy",)}


def ten_digit(pcode):
    digits = pcode[2:]
    return digits.ljust(10, "0")


def old_nine(code):
    return code[:2] + code[3:5] + code[5:7] + code[7:10]


def same_name(name, code):
    """True when the feature's name matches the PSGC unit's name or old name, by the DepEd tiers."""
    return match(name, [units[code]])[1] is not None


def resolve(layer, props, parent_codes):
    """Return (tier, PSGC code). A code rule counts only if the names agree: in Maguindanao the
    same code numbers belong to different municipalities in COD-AB and PSGC 2Q 2026."""
    pcode, name = props[f"{layer}_pcode"], props[f"{layer}_name"]
    code = ten_digit(pcode)
    level_ok = lambda c: c in units and units[c].level in LEVELS[layer]
    by_code = []
    if level_ok(code):
        by_code.append(("exact code", code))
    if code[2] == "0" and old_nine(code) in correspondence and level_ok(correspondence[old_nine(code)]):
        by_code.append(("Correspondence Code", correspondence[old_nine(code)]))
    if code.startswith("19") and level_ok("09" + code[2:]):
        by_code.append(("Sulu region", "09" + code[2:]))
    for tier, found in by_code:
        if same_name(name, found):
            return tier, found
    if layer == "adm3":
        province = ten_digit(props["adm2_pcode"])
        province = correspondence.get(old_nine(province), province) if province not in units else province
        candidates = [u for u in units.values() if u.level in LEVELS[layer] and u.id[:5] == province[:5]]
        candidates = candidates or [u for u in units.values() if u.level in LEVELS[layer]]
    else:
        parent = parent_codes.get(props["adm3_pcode"])
        if parent is None:
            return "parent not matched", None
        candidates = deped["barangay_candidates"](units[parent])
    tier, unit = match(name, candidates)
    if unit:
        prefix = "code names another unit; " if by_code else ""
        return f"{prefix}name in parent, {tier}", unit.id
    if by_code:
        return f"{by_code[0][0]}, name differs", by_code[0][1]
    return tier, None


# %% HB-2: ADM3
adm3 = {}
for props in layers["adm3"]:
    adm3[props["adm3_pcode"]] = resolve("adm3", props, {})
tiers3 = collections.Counter(t for t, c in adm3.values() if c)
left3 = [(p["adm3_pcode"], p["adm3_name"], p["adm2_name"], adm3[p["adm3_pcode"]][0]) for p in layers["adm3"] if adm3[p["adm3_pcode"]][1] is None]
codes3 = collections.Counter(c for _, c in adm3.values() if c)
psgc3 = [u for u in units.values() if u.level in LEVELS["adm3"]]
show("HB-2", f"ADM3 {len(adm3):,}: matched {sum(tiers3.values()):,} by tier {dict(tiers3.most_common())}; PSGC codes matched twice "
     f"{[c for c, k in codes3.items() if k > 1]}; not matched {len(left3)} {left3}; PSGC cities and municipalities with no ADM3 unit "
     f"{[(u.id, u.name) for u in psgc3 if u.id not in codes3]}")

# %% HB-3: ADM4
parents = {p: c for p, (t, c) in adm3.items() if c}
adm4 = {}
for props in layers["adm4"]:
    adm4[props["adm4_pcode"]] = resolve("adm4", props, parents)
tiers4 = collections.Counter(t for t, c in adm4.values() if c)
left4 = [(p["adm4_pcode"], p["adm4_name"], p["adm3_name"], p["adm2_name"], adm4[p["adm4_pcode"]][0]) for p in layers["adm4"] if adm4[p["adm4_pcode"]][1] is None]
codes4 = collections.Counter(c for _, c in adm4.values() if c)
psgc4 = [u for u in units.values() if u.level == "Bgy"]
missing4 = [u for u in psgc4 if u.id not in codes4]
show("HB-3", f"ADM4 {len(adm4):,}: matched {sum(tiers4.values()):,} ({100 * sum(tiers4.values()) / len(adm4):.1f}%) by tier {dict(tiers4.most_common())}; "
     f"PSGC codes matched more than once {sum(1 for k in codes4.values() if k > 1)}; not matched {len(left4):,} by reason "
     f"{dict(collections.Counter(r[-1] for r in left4))}, by province {dict(collections.Counter(r[3] for r in left4).most_common(10))}; "
     f"PSGC barangays with no ADM4 unit {len(missing4):,}; matched by name although the code names another PSGC barangay "
     f"{dict(collections.Counter(p['adm2_name'] for p in layers['adm4'] if adm4[p['adm4_pcode']][0].startswith('code names another')).most_common())}")

# %% Write the list
def cell(value):
    return str(value or "").replace("|", "\\|")


lines = [
    "# COD-AB boundaries (HDX): units not matched to PSGC 2Q 2026",
    "",
    "Generated by [`cross_source_hdx_boundaries.py`](../../../../analysis/cross_source/cross_source_hdx_boundaries.py). Do not edit by hand; change the script and rerun. Part of #8.",
    "",
    "## ADM3 (cities and municipalities)",
    "",
    "| P-code | Name | Province | Reason |",
    "|---|---|---|---|",
]
lines += [f"| {c} | {cell(n)} | {cell(p)} | {r} |" for c, n, p, r in left3]
lines += ["", "## ADM4 (barangays)", "", "| P-code | Name | City or municipality | Province | Reason |", "|---|---|---|---|---|"]
lines += [f"| {c} | {cell(n)} | {cell(m)} | {cell(p)} | {r} |" for c, n, m, p, r in left4]
review = [(p["adm4_pcode"], p["adm4_name"], p["adm3_name"], p["adm2_name"], adm4[p["adm4_pcode"]]) for p in layers["adm4"] if "name differs" in adm4[p["adm4_pcode"]][0]]
lines += ["", "## ADM4 matched by code although the name differs (to review)", "",
          f"{len(review)} rows. Most are spellings; a few may be renamed barangays or a code given to another barangay.", "",
          "| P-code | COD-AB name | City or municipality | Province | PSGC code | PSGC name |", "|---|---|---|---|---|---|"]
lines += [f"| {c} | {cell(n)} | {cell(m)} | {cell(p)} | {code} | {cell(units[code].name)} |" for c, n, m, p, (t, code) in review]
(REPO / "docs" / "data" / "cross-source" / "generated" / "hdx_boundaries_psgc_unmatched.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
show("run", f"wrote docs/data/cross-source/generated/hdx_boundaries_psgc_unmatched.md: ADM3 {len(left3)}, ADM4 {len(left4):,} unmatched and {len(review)} to review")
