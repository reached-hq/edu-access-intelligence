# Cross-source checks for deped_enrollment SY 2023-24 (part of #8).
#
# Reproduces every finding in:
#   docs/cross_source/deped_dataset_research.md
# and regenerates:
#   docs/cross_source/generated/deped_psgc_unmatched.md
# Each check prints under its finding ID (A-n: place names to PSGC, B-n: school ID joins).
#
# Runs locally with DuckDB; no Databricks compute. Run cell by cell (# %% markers) or as a whole:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/cross_source_deped.py
#
# RAW_DATA_DIR must contain deped/original/ (the zips in FILES) and
# psa/original/PSGC-2Q-2026-Publication-Datafile.xlsx. Raw files are read, never modified.

# %% Setup
import collections
import csv
import hashlib
import os
import re
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains deped/original/ and psa/original/.")
RAW = Path(raw_dir).expanduser()

# Checksums come from each source card. ELLNA's shared zip was repackaged, so its
# card records the CSV checksum; the CSV is checked for ELLNA and NAT Grade 6.
FILES = {
    "enr": ("Enrollment-in-SY-2023-2024.zip", "a10f4d0f9082919c13b3a091774c8231c99c95b1b1872310714107013b77dbbb", "zip", "enrollment_2023-24.csv"),
    "fac": ("School-Facilities-in-SY-2023-2024.zip", "9317af02b595d3a8d7381715780ef183a92da35354bbe0f3796045490e546609", "zip", "facilities_2023-24.csv"),
    "per": ("School-Personnel-in-SY-2023-2024.zip", "9d1e5adfc33d67244f0d1a796f1b8b1930f5704eadf9f901008da68d7764a817", "zip", "personnel_2023-24.csv"),
    "ellna": ("Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip", "a379ccd0cf48bf3ff1174fc76374627bd92f71d31f49fa73e59c9f57b1390dc2", "csv", "ellna_2023-24_selected.csv"),
    "nat": ("National-Achievement-Test-NAT-Grade-6-2023-2024.zip", "ddd3e019b0ad952cecce95566aff2ecb7b2b4ff4ce1135a2a1575b14f5f939bf", "csv", "nat_2023-24_selected.csv"),
}
PSGC_FILE = "PSGC-2Q-2026-Publication-Datafile.xlsx"
PSGC_SHA256 = "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d"

con = duckdb.connect()
workdir = tempfile.TemporaryDirectory()


def q(sql):
    return con.execute(sql).fetchall()


def one(sql):
    return q(sql)[0][0]


def show(finding, text):
    print(f"[{finding}] {text}")


# %% Verify checksums and load
for table, (zip_name, sha, checked, member) in FILES.items():
    zip_path = RAW / "deped" / "original" / zip_name
    with zipfile.ZipFile(zip_path) as zf:
        data = zf.read(next(n for n in zf.namelist() if n.endswith("/" + member)))
    digest = hashlib.sha256(zip_path.read_bytes() if checked == "zip" else data).hexdigest()
    if digest != sha:
        sys.exit(f"{zip_name}: {checked} SHA-256 {digest} does not match the source card. Stop and re-inventory.")
    copy = Path(workdir.name) / member
    copy.write_bytes(data)
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv('{copy}', all_varchar = true, header = true, strict_mode = true)")
    show("run", f"{table}: {member}, {one(f'SELECT count(*) FROM {table}'):,} rows, {checked} checksum OK")

psgc_path = RAW / "psa" / "original" / PSGC_FILE
if hashlib.sha256(psgc_path.read_bytes()).hexdigest() != PSGC_SHA256:
    sys.exit(f"{PSGC_FILE}: SHA-256 does not match the psa_psgc card. Stop and re-inventory.")
psgc_rows = [cells for _, cells in read_sheet(psgc_path, "PSGC")]
if [psgc_rows[0].get(i, "").strip() for i in (1, 2, 4, 5)] != ["10-digit PSGC", "Name", "Geographic Level", "Old names"]:
    sys.exit(f"{PSGC_FILE}: PSGC sheet header changed; columns cannot be mapped by position.")
Unit = collections.namedtuple("Unit", "id name level old")
units = [Unit(r.get(1, ""), r.get(2, "").strip(), r.get(4, ""), r.get(5, "").strip()) for r in psgc_rows[1:]]
show("run", f"{PSGC_FILE}: {len(units):,} units, checksum OK")

# %% Matching rules
# Rules from the psa_psgc card: match province, then city or municipality inside the
# province, then barangay inside its city or municipality; never use region as a key;
# try the current name, then `Old names`; flag what is left, never force it.
# Extensions made here. Each matching extension is its own tier, counted separately,
# so it can be excluded; every hit must be unique among the candidates.
#   - Before matching, DepEd names with mangled characters ("PEÃ‘A" for "PEÑA") are
#     repaired by re-reading them as UTF-8; the count is reported (A-11).
#   - Names are compared in capitals with spaces collapsed, "City of X" read as "X City",
#     and a trailing "(Capital)" or "(Not a Province)" dropped. DepEd writes capitals.
#   - "folded": accents and the punctuation . - ' are dropped.
#   - "brackets dropped": bracketed text is dropped. DepEd often writes a former name in
#     brackets ("DARAGA (LOCSIN)") where PSGC keeps it in `Old names`.
#   - "word City ignored": as above, with the words CITY and OF dropped ("BACOOR" vs
#     "City of Bacoor", for places that became cities). Not used for provinces.
#   - "truncated at 40": DepEd caps barangay names at 40 characters; a capped name is
#     matched to the one PSGC barangay in its city or municipality that starts with it.
#   - DepEd's four NCR "districts" are not PSGC units; their names are matched against
#     every NCR city, municipality, and Manila sub-municipality (codes starting 13).
#   - DepEd's single "MAGUINDANAO" is matched against its two successor provinces.
#   - A city not found inside its DepEd province is looked up among the 33 independent
#     cities (PSGC gives them province-level codes); if the province itself is unmatched,
#     among every city.


def repair(text):
    if text and "\u00c3" in text:
        try:
            return text.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def base(name):
    text = re.sub(r"\s+", " ", name.upper()).strip()
    text = re.sub(r"\s*\((CAPITAL|NOT A PROVINCE)\)$", "", text)
    city_of = re.match(r"^CITY OF (.+)$", text)
    return f"{city_of.group(1)} CITY" if city_of else text


def fold(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[.\-']", " ", text)).strip()


def no_brackets(text):
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)?", " ", text)).strip()


def no_city(text):
    return re.sub(r"\s+", " ", re.sub(r"\b(CITY|OF)\b", " ", text)).strip()


TIERS = [
    ("exact", "name", base),
    ("old name", "old", base),
    ("folded", "name", lambda t: fold(base(t))),
    ("folded old name", "old", lambda t: fold(base(t))),
    ("brackets dropped", "name", lambda t: no_brackets(fold(base(t)))),
    ("word City ignored", "name", lambda t: no_city(no_brackets(fold(base(t))))),
]


def match(name, candidates, truncatable=False, tiers=TIERS):
    """Return (tier, unit) for a unique hit, ("ambiguous", None), or ("unmatched", None)."""
    for tier, field, key in tiers:
        wanted = key(name)
        hits = [u for u in candidates if getattr(u, field) and key(getattr(u, field)) == wanted]
        if len(hits) == 1:
            return tier, hits[0]
        if len(hits) > 1:
            return "ambiguous", None
    if truncatable and len(name) == 40:
        stem = fold(base(name))
        hits = [u for u in candidates if fold(base(u.name)).startswith(stem)]
        if len(hits) == 1:
            return "truncated at 40", hits[0]
    return "unmatched", None


ISABELA_CONTAINER = "0990100000"  # "City of Isabela (Not a Province)": a province-level row with a blank level
provinces = [u for u in units if u.level == "Prov" or u.id == ISABELA_CONTAINER]
localities = [u for u in units if u.level in ("City", "Mun", "SubMun")]
independent = [u for u in localities if u.level == "City" and u.id[5:] == "00000"]
cities = [u for u in localities if u.level == "City"]
barangays_by_parent = collections.defaultdict(list)
for u in units:
    if u.level == "Bgy":
        barangays_by_parent[u.id[:7]].append(u)
        barangays_by_parent[u.id[:5]].append(u)
SPLITS = {"MAGUINDANAO": ["Maguindanao del Norte", "Maguindanao del Sur"]}


def match_province(name):
    if re.search(r"\bNCR\b", name.upper()):
        return "NCR district", ["13"]
    if name.upper() in SPLITS:
        return "documented split", [u.id[:5] for u in provinces if u.name in SPLITS[name.upper()]]
    # "word City ignored" is not used for provinces: it would turn "CITY OF COTABATO" into Cotabato province.
    tier, unit = match(name, provinces, tiers=[t for t in TIERS if t[0] != "word City ignored"])
    return tier, [unit.id[:5]] if unit else []


def match_locality(name, prefixes):
    tier, unit = match(name, [u for u in localities if any(u.id.startswith(p) for p in prefixes)])
    if tier == "unmatched":
        tier, unit = match(name, independent if prefixes else cities)
        if unit:
            tier = "independent city" if prefixes else "city, province unmatched"
    return tier, unit


def barangay_candidates(locality):
    return barangays_by_parent[locality.id[:5] if locality.id[5:] == "00000" else locality.id[:7]]


# %% A: match every SY 2023-24 school's place names
raw_schools = q("SELECT school_id, region, province, municipality, barangay FROM enr")
schools = [(i, r, repair(p), repair(m), repair(b)) for i, r, p, m, b in raw_schools]
repaired = {(a[2], a[3], a[4]) for a, b in zip(raw_schools, schools) if a[2:] != b[2:]}
truncated = {s[4] for s in raw_schools if s[4] and len(s[4]) == 40}  # the cap applies to the published text
pso = [s for s in schools if s[1] == "PSO"]
schools = [s for s in schools if s[1] != "PSO"]
show("A-1", f"schools {len(schools) + len(pso):,}; Philippine Schools Overseas excluded {len(pso)}; matched below {len(schools):,}")

prov_result = {p: match_province(p) for p in sorted({s[2] for s in schools})}
loc_result = {}
for _, _, prov, mun, _ in schools:
    if (prov, mun) not in loc_result:
        loc_result[(prov, mun)] = match_locality(mun, prov_result[prov][1])
bgy_result = {}
for _, _, prov, mun, bgy in schools:
    key = (prov, mun, bgy)
    if key in bgy_result:
        continue
    locality = loc_result[(prov, mun)][1]
    if bgy is None:
        bgy_result[key] = ("no barangay given", None)
    elif locality is None:
        bgy_result[key] = ("locality unmatched", None)
    else:
        bgy_result[key] = match(bgy, barangay_candidates(locality), truncatable=True)


def tally(results, weights):
    places, school_counts = collections.Counter(), collections.Counter()
    for key, (tier, _) in results.items():
        places[tier] += 1
        school_counts[tier] += weights[key]
    return places, school_counts


w_prov = collections.Counter(s[2] for s in schools)
w_loc = collections.Counter((s[2], s[3]) for s in schools)
w_bgy = collections.Counter((s[2], s[3], s[4]) for s in schools)
for finding, label, results, weights in (("A-2", "provinces", prov_result, w_prov), ("A-3", "cities and municipalities", loc_result, w_loc), ("A-4", "barangays", bgy_result, w_bgy)):
    places, school_counts = tally(results, weights)
    show(finding, f"{label}: {len(results):,} distinct; by tier (places / schools): "
         + "; ".join(f"{t} {places[t]:,} / {school_counts[t]:,}" for t in sorted(places, key=lambda t: -places[t])))

full = sum(1 for s in schools if bgy_result[(s[2], s[3], s[4])][1] is not None)
# Strict: the card's own rules only (exact or old name) at every level; at province level
# the NCR district and Maguindanao split are allowed, since those provinces have no exact match.
STRICT = {"exact", "old name"}
strict_chain = sum(
    1 for s in schools
    if prov_result[s[2]][0] in STRICT | {"NCR district", "documented split"}
    and loc_result[(s[2], s[3])][0] in STRICT and bgy_result[(s[2], s[3], s[4])][0] in STRICT
)
show("A-5", f"schools matched down to barangay {full:,} of {len(schools):,} ({100 * full / len(schools):.1f}%); "
     f"by the strict rule (exact or old name at every level, plus NCR district and split at province) "
     f"{strict_chain:,} ({100 * strict_chain / len(schools):.1f}%)")
show("A-6", "unmatched or ambiguous provinces: " + str({p: (t, w_prov[p]) for p, (t, pre) in prov_result.items() if not pre}))
show("A-7", "unmatched or ambiguous cities and municipalities (province, name, tier, schools): "
     + str(sorted(((p, m, t, w_loc[(p, m)]) for (p, m), (t, u) in loc_result.items() if u is None), key=lambda r: -r[3])))

# Region is never a match key; this only shows where DepEd's SY 2023-24 region and
# the region of the matched 2Q 2026 code differ.
region_names = {u.id[:2]: u.name for u in units if u.level == "Reg"}
DEPED_REGION_CODE = {
    "Region I": "01", "Region II": "02", "Region III": "03", "Region IV-A": "04", "Region V": "05",
    "Region VI": "06", "Region VII": "07", "Region VIII": "08", "Region IX": "09", "Region X": "10",
    "Region XI": "11", "Region XII": "12", "NCR": "13", "CAR": "14", "CARAGA": "16", "MIMAROPA": "17", "BARMM": "19",
}
moved = collections.Counter(
    (s[1], region_names[loc_result[(s[2], s[3])][1].id[:2]])
    for s in schools
    if loc_result[(s[2], s[3])][1] is not None and loc_result[(s[2], s[3])][1].id[:2] != DEPED_REGION_CODE[s[1]]
)
show("A-8", f"matched schools whose PSGC 2Q 2026 region differs from DepEd's SY 2023-24 region: {sum(moved.values()):,}; "
     f"by DepEd region -> PSGC region: {dict(moved.most_common())}")
for label, provs in (("Negros and Siquijor", ("NEGROS OCCIDENTAL", "NEGROS ORIENTAL", "SIQUIJOR")), ("Sulu", ("SULU",))):
    group = [s for s in schools if s[2] in provs]
    matched = sum(1 for s in group if bgy_result[(s[2], s[3], s[4])][1] is not None)
    show("A-9", f"{label}: schools {len(group):,}; matched to barangay {matched:,}; DepEd regions {sorted({s[1] for s in group})}; "
         f"PSGC 2Q 2026 regions of matched localities {sorted({region_names[loc_result[(s[2], s[3])][1].id[:2]] for s in group if loc_result[(s[2], s[3])][1]})}")

show("A-10", f"DepEd place names with mangled characters repaired before matching: {len(repaired)} places, "
     f"{sum(1 for a, b in zip(raw_schools, schools) if a[2:] != b[2:])} schools; barangay names exactly 40 characters long: "
     f"{len(truncated)} names, {sum(1 for s in raw_schools if s[4] in truncated)} schools")
sga = [s for s in schools if s[1] == "BARMM" and s[2] == "NORTH COTABATO"]
show("A-11", f"BARMM schools filed under NORTH COTABATO (the Special Geographic Area): {len(sga)}; "
     f"localities matched {sum(1 for s in sga if loc_result[(s[2], s[3])][1])}; barangays matched "
     f"{sum(1 for s in sga if bgy_result[(s[2], s[3], s[4])][1])}; DepEd municipalities {sorted({s[3] for s in sga})}")

# %% A: write every unmatched or ambiguous name, with its school count
region_of = {}
for s in schools:
    region_of.setdefault((s[2], s[3], s[4]), s[1])
rows = [("Province", "", p, "", "", t, w_prov[p]) for p, (t, pre) in sorted(prov_result.items()) if not pre]
rows += [("City or municipality", "", p, m, "", t, w_loc[(p, m)]) for (p, m), (t, u) in sorted(loc_result.items()) if u is None]
rows += [
    ("Barangay", region_of[(p, m, b)], p, m, b or "", t, w_bgy[(p, m, b)])
    for (p, m, b), (t, u) in sorted(bgy_result.items(), key=lambda kv: tuple(x or "" for x in kv[0]))
    if u is None and t != "locality unmatched"
]


def cell(value):
    return str(value).replace("|", "\\|")


out = REPO / "docs" / "cross_source" / "generated" / "deped_psgc_unmatched.md"
out.write_text(
    "# DepEd SY 2023-24 place names not matched to PSGC 2Q 2026\n\n"
    "Generated by [`notebooks/profiling/cross_source_deped.py`](../../../notebooks/profiling/cross_source_deped.py). "
    "Do not edit by hand; rerun the script instead.\n\n"
    "Every DepEd province, city or municipality, and barangay name that did not match exactly one PSGC unit, "
    "with the number of schools that carry it. Names are shown as DepEd wrote them, after the character repair "
    "described in [deped_dataset_research.md](../deped_dataset_research.md). Barangays inside an unmatched city or "
    "municipality are not listed separately; they are counted in that city or municipality's row.\n\n"
    "| Level | DepEd region | DepEd province | DepEd city or municipality | DepEd barangay | Result | Schools |\n"
    "|---|---|---|---|---|---|---:|\n"
    + "".join("| " + " | ".join(cell(v) for v in row) + " |\n" for row in rows),
    encoding="utf-8",
)
show("A-12", f"wrote {out.relative_to(REPO)}: {len(rows)} rows")

# %% A-13: check every brackets-dropped match against what the bracket says
# DepEd's bracket should be "(POB.)" or a former name. It is a warning sign when the bracket
# is neither of these, or when it names a different PSGC barangay in the same city or municipality.


def bracket_check(name, unit, siblings):
    if len(name) == 40 and name.count("(") > name.count(")"):
        return "bracket cut off at 40"
    inside = [fold(re.sub(r"[(*]", "", b)).strip() for b in re.findall(r"\(([^)]*)\)?", base(name))]
    inside = [b for b in inside if b]
    old = fold(base(unit.old)) if unit.old else ""
    if inside and all(re.match(r"^(POB|POBLACION)\b", b) for b in inside):
        return "(POB.)"
    if inside and old and all(b in old for b in inside):
        return "bracket is a PSGC old name"
    if any(u.id != unit.id and no_brackets(fold(base(u.name))) in inside for u in siblings):
        return "bracket names another barangay"
    return "other"


for level, results, weights in (("cities and municipalities", loc_result, w_loc), ("barangays", bgy_result, w_bgy)):
    checked = collections.Counter()
    flagged = []
    for key, (tier, unit) in results.items():
        if tier != "brackets dropped":
            continue
        siblings = barangay_candidates(loc_result[key[:2]][1]) if len(key) == 3 else []
        result = bracket_check(key[-1], unit, siblings)
        checked[result] += 1
        if result in ("bracket names another barangay", "other"):
            flagged.append((*key[1:], unit.name, unit.old or "-", result, weights[key]))
    show("A-13", f"brackets-dropped {level}, by what the bracket holds (names): {dict(checked)}; "
         f"needing a look (city or municipality, DepEd name, PSGC name, PSGC old names, result, schools): {flagged}")

# %% B: school ID joins against enrollment SY 2023-24
show("B-1", "enrollment by sector: " + str(q("SELECT sector, count(*) FROM enr GROUP BY 1 ORDER BY 2 DESC")))
for finding, table, label in (("B-2", "fac", "facilities"), ("B-3", "per", "personnel")):
    both = one(f"SELECT count(*) FROM {table} t JOIN enr e USING (school_id)")
    only_t = one(f"SELECT count(*) FROM {table} t ANTI JOIN enr e USING (school_id)")
    only_e = one(f"SELECT count(*) FROM enr e ANTI JOIN {table} t USING (school_id)")
    dupes = one(f"SELECT count(*) - count(DISTINCT school_id) FROM {table}")
    sector_diff = one(f"SELECT count(*) FROM {table} t JOIN enr e USING (school_id) WHERE t.sector IS DISTINCT FROM e.sector")
    show(finding, f"{label}: rows {one(f'SELECT count(*) FROM {table}'):,}; duplicate IDs {dupes}; in both {both:,}; "
         f"only in {label} {only_t:,}; only in enrollment {only_e:,}; sector differs on {sector_diff:,} matched schools; "
         f"{label} sectors {q(f'SELECT sector, count(*) FROM {table} GROUP BY 1 ORDER BY 2 DESC')}")
for finding, table, label in (("B-4", "ellna", "ELLNA"), ("B-5", "nat", "NAT Grade 6")):
    both = one(f"SELECT count(*) FROM {table} t JOIN enr e USING (school_id)")
    only_t = q(f"SELECT school_id FROM {table} t ANTI JOIN enr e USING (school_id) ORDER BY 1")
    region_diff = one(f"SELECT count(*) FROM {table} t JOIN enr e USING (school_id) WHERE t.region IS DISTINCT FROM e.region")
    show(finding, f"{label}: rows {one(f'SELECT count(*) FROM {table}'):,}; duplicate IDs {one(f'SELECT count(*) - count(DISTINCT school_id) FROM {table}')}; "
         f"in enrollment {both:,}; not in enrollment {len(only_t)} {[r[0] for r in only_t][:10]}; "
         f"region differs from enrollment on {region_diff} matched schools; regions {q(f'SELECT region, count(*) FROM {table} GROUP BY 1 ORDER BY 1')}; "
         f"BARMM schools {one(f'SELECT count(*) FROM {table} WHERE region = {chr(39)}BARMM{chr(39)}')}")
show("B-6", "ELLNA and NAT Grade 6 schools in both files: "
     f"{one('SELECT count(*) FROM ellna JOIN nat USING (school_id)'):,}; share of enrollment schools in the five regions covered: "
     + str(q("""SELECT e.region, count(*) AS schools, count(l.school_id) AS ellna, count(n.school_id) AS nat
                FROM enr e LEFT JOIN ellna l USING (school_id) LEFT JOIN nat n USING (school_id)
                WHERE e.region IN (SELECT DISTINCT region FROM nat) GROUP BY 1 ORDER BY 1""")))

# %% B-7 BARMM coverage in the DepEd anchor (public schools, SY 2023-24)
# Teacher positions are every personnel column naming a teacher position; the
# `*_teachers_*` columns are funding breakdowns and are left out. "At least one
# teacher" does not depend on which positions the team later counts as teachers.
teacher_cols = [c for (c, *_) in q("DESCRIBE per") if "teacher" in c and "teachers_" not in c]
teacher_sum = " + ".join(f'coalesce(try_cast(p."{c}" AS DOUBLE), 0)' for c in teacher_cols)
coverage = q(f"""
    SELECT CASE WHEN e.region = 'BARMM' THEN 'BARMM' ELSE 'Rest of the Philippines' END AS area,
           count(*) AS schools,
           count(*) FILTER (WHERE coalesce(f.es_classrooms_instructional, f.jhs_classrooms_instructional,
                                           f.shs_classrooms_instructional) IS NOT NULL) AS with_classrooms,
           count(*) FILTER (WHERE ({teacher_sum}) > 0) AS with_teachers
    FROM enr e JOIN fac f USING (school_id) JOIN per p USING (school_id)
    WHERE e.sector = 'Public'
    GROUP BY 1 ORDER BY 1""")
show("B-7", f"teacher-position columns used: {len(teacher_cols)}; public schools, with classroom counts, with at least one teacher: "
     + "; ".join(f"{a} {n:,}, {c:,} ({100 * c / n:.1f}%), {t:,} ({100 * t / n:.1f}%)" for a, n, c, t in coverage))
show("B-7", "BARMM public schools without classroom counts, by DepEd province: " + str(q("""
    SELECT e.province, count(*) FROM enr e JOIN fac f USING (school_id)
    WHERE e.sector = 'Public' AND e.region = 'BARMM'
      AND coalesce(f.es_classrooms_instructional, f.jhs_classrooms_instructional, f.shs_classrooms_instructional) IS NULL
    GROUP BY 1 ORDER BY 2 DESC""")))
