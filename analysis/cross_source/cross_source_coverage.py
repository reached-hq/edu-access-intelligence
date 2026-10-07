# Cross-source checks for the coverage matrix (part of #8).
#
# Reproduces the findings labelled C-n in:
#   docs/data/cross-source/coverage.md
#
# Reuses the SY 2023-24 DepEd to PSGC match from cross_source_deped.py by running it
# first (its output is hidden here; it also rewrites generated/deped_psgc_unmatched.md, unchanged).
#
# Runs locally; no Databricks compute:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_coverage.py
#
# RAW_DATA_DIR needs the same files as cross_source_deped.py. Raw files are read, never modified.

# %% Setup: run the DepEd match
import collections
import contextlib
import io
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")

schools = deped["schools"]  # SY 2023-24, Philippine Schools Overseas already excluded
loc_result = deped["loc_result"]
sector = dict(deped["q"]("SELECT school_id, sector FROM enr"))
psgc = deped["psgc_rows"]
if [psgc[0].get(i, "").strip() for i in (6, 9)] != ["City Class", "2024 Population"]:
    sys.exit("PSGC sheet header changed; columns cannot be mapped by position.")
rows = psgc[1:]


def show(finding, text):
    print(f"[{finding}] {text}")


def level(r):
    return (r.get(4) or "").strip()


def population(r):
    try:
        return int(float(str(r.get(9)).replace(",", "")))
    except ValueError:
        return None


# %% C-1: schools in a city or municipality with no poverty estimate
# The psa_poverty_stat profile (X-1) names the 44 PSGC units missing from the file:
# 33 HUCs, City of Isabela, City of Cotabato, Pateros, and the 8 Special Geographic Area
# municipalities (codes starting 19999). The poverty file itself is not needed here.
no_poverty = {}
for r in rows:
    pid, name = r.get(1, ""), (r.get(2) or "").strip()
    if level(r) not in ("City", "Mun"):
        continue
    if (r.get(6) or "").strip() == "HUC":
        no_poverty[pid] = "HUC"
    elif name in ("City of Isabela", "City of Cotabato", "Pateros"):
        no_poverty[pid] = name
    elif pid.startswith("19999"):
        no_poverty[pid] = "Special Geographic Area"
if len(no_poverty) != 44:
    sys.exit(f"Expected the 44 units named in psa_poverty_stat X-1, found {len(no_poverty)}.")

located = [(sid, loc_result[(prov, mun)][1]) for sid, _, prov, mun, _ in schools if loc_result[(prov, mun)][1]]
gap = collections.Counter(no_poverty[u.id] for _, u in located if u.id in no_poverty)
gap_public = collections.Counter(no_poverty[u.id] for sid, u in located if u.id in no_poverty and sector[sid] == "Public")
public = sum(1 for s in sector.values() if s == "Public")
show("C-1", f"units with no poverty estimate: {len(no_poverty)}; schools with a matched city or municipality: {len(located):,}; "
     f"of those in a unit with no estimate: {sum(gap.values()):,} ({sum(gap.values()) / len(located):.1%}): {dict(gap.most_common())}; "
     f"public: {sum(gap_public.values()):,} of {public:,} public schools: {dict(gap_public.most_common())}")

# %% C-2: where the Special Geographic Area schools match at city or municipality level
# DepEd SY 2023-24 files these schools under region BARMM, province NORTH COTABATO (A-9, A-11).
sga = collections.Counter()
for sid, region, prov, mun, _ in schools:
    if region == "BARMM" and prov == "NORTH COTABATO":
        unit = loc_result[(prov, mun)][1]
        sga[f"{unit.name} ({unit.id})" if unit else "unmatched"] += 1
show("C-2", f"Special Geographic Area schools: {sum(sga.values())}; matched city or municipality: {dict(sga.most_common())}")

# %% C-3: PSGC 2024 population against the psa_population_per_barangay profile
# The barangay workbooks are not read here; the comparison is with their profile:
# geographic total 112,727,776 (O-7) and 12 zero-population barangays by region (O-10).
regions = {r.get(1, "")[:2]: (r.get(2) or "").strip() for r in rows if level(r) == "Reg"}
barangays = [r for r in rows if level(r) == "Bgy"]
zeros = collections.Counter(regions[r.get(1, "")[:2]] for r in barangays if population(r) == 0)
show("C-3", f"PSGC barangays: {len(barangays):,}; their 2024 population sums to {sum(population(r) or 0 for r in barangays):,}; "
     f"zero-population barangays: {sum(zeros.values())}: {dict(zeros)}")
