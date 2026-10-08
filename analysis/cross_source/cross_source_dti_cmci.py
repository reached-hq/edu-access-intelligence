# Cross-source checks for dti_cmci against PSGC 2Q 2026 (part of #8).
#
# Prints the findings labelled CM-n in:
#   docs/data/cross-source/coverage.md
# and regenerates:
#   docs/data/cross-source/generated/dti_cmci_psgc_match.md
#
# Reuses the PSGC 2Q 2026 matching rules of cross_source_deped.py by running it first (its
# output is hidden here; it also rewrites generated/deped_psgc_unmatched.md, unchanged).
#
# Runs locally; no Databricks compute:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_dti_cmci.py
#
# RAW_DATA_DIR needs the files of cross_source_deped.py plus dti/original/cmci_lgu_list.csv
# (checksum from the dti_cmci card, #35). Raw files are read, never modified.

# %% Setup
import collections
import contextlib
import csv
import hashlib
import io
import re
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    deped = runpy.run_path(str(HERE / "cross_source_deped.py"), run_name="__main__")
RAW, TIERS, base, fold, no_brackets, no_city = (deped[n] for n in ("RAW", "TIERS", "base", "fold", "no_brackets", "no_city"))
units = deped["units"]
localities = [u for u in units if u.level in ("City", "Mun")]
independent = deped["independent"]
province_name = {u.id[:5]: u.name for u in units if u.level == "Prov"}

LGU_FILE = RAW / "dti" / "original" / "cmci_lgu_list.csv"
LGU_SHA256 = "187931b652b0912a5fa176b9743f107d6bb8c020004b132e42b753a1afabbebb"
if hashlib.sha256(LGU_FILE.read_bytes()).hexdigest() != LGU_SHA256:
    sys.exit("cmci_lgu_list.csv: SHA-256 does not match the dti_cmci card. Stop and re-inventory.")
lgus = [row["lgu"] for row in csv.DictReader(LGU_FILE.open(encoding="utf-8-sig"))]


def show(finding, text):
    print(f"[{finding}] {text}")


def split(name):
    found = re.match(r"^(.*?)\s*\(([A-Z]{2,3})\)$", name.strip())
    return (found.group(1), found.group(2)) if found else (name.strip(), None)


show("CM-1", f"CMCI LGUs {len(lgus):,} (checksum OK); with a two- or three-letter suffix {sum(1 for n in lgus if split(n)[1]):,}; "
     f"PSGC 2Q 2026 cities and municipalities {len(localities):,}")

# %% Matching tiers
# The DepEd tiers, reordered so that every current-name tier comes before the old-name
# tiers. Without a province to scope the search, an old name can steal a match: CMCI's
# "San Pedro" would match Bulalacao (old name San Pedro) instead of the City of San Pedro.
# Two tiers are added, each counted: common abbreviations written out, and letters only.
ABBREVIATIONS = {"STO": "SANTO", "STA": "SANTA", "ST": "SAINT", "GEN": "GENERAL", "SEN": "SENATOR", "PRES": "PRESIDENT"}


def expand(text):
    return " ".join(ABBREVIATIONS.get(w, w) for w in fold(base(text)).split())


def letters(text):
    return re.sub(r"[^A-Z]", "", expand(text))


CURRENT = [t for t in TIERS if t[1] == "name"] + [
    ("abbreviations written out", "name", lambda t: no_city(no_brackets(expand(t)))),
    ("letters only", "name", lambda t: letters(no_city(no_brackets(base(t))))),
]
OLD = [t for t in TIERS if t[1] == "old"]


def match(name, candidates):
    for tier, field, key in CURRENT + OLD:
        wanted = key(name)
        hits = [u for u in candidates if getattr(u, field) and key(getattr(u, field)) == wanted]
        if len(hits) == 1:
            return tier, hits[0]
        if len(hits) > 1:
            return "ambiguous", None
    return "unmatched", None


def all_hits(name, candidates):
    return {u for _, field, key in CURRENT + OLD for u in candidates if getattr(u, field) and key(getattr(u, field)) == key(name)}


# %% Suffix to province
# A suffix gets the province holding the most of its LGUs' names, when that province holds
# more than half of them and at least two. Suffixes the data cannot settle (one LGU, or a
# tie) take a reviewed reading of the abbreviation. The card has no published list (UNVERIFIED),
# so every reviewed reading is counted and must still lead to a unique match.
REVIEWED = {
    "AO": ["14081"], "BA": ["19007"], "BAS": ["19007", "09901"], "BS": ["04010"], "CV": ["11082"], "DDO": ["11082"],
    "DN": ["11023"], "DO": ["11025"], "DS": ["11024"], "GS": ["06079"], "IN": ["01028"], "KA": ["14032"],
    "LS": ["19036"], "MA": ["19087", "19088"], "MM": ["13"], "MP": ["14044"], "NO": ["18045"], "PA": ["03054"],
    "PN": ["17053"], "SK": ["12065"], "SR": ["18061"], "SU": ["09066"], "ZN": ["09072"],
}
by_suffix = collections.defaultdict(list)
for name in lgus:
    lgu_base, suffix = split(name)
    if suffix:
        by_suffix[suffix].append(lgu_base)
lookup, source = {}, {}
for suffix, bases in by_suffix.items():
    counts = collections.Counter(p for b in bases for p in {u.id[:5] for u in all_hits(b, localities)})
    top = counts.most_common(2)
    if len(bases) >= 2 and top and top[0][1] > len(bases) / 2 and (len(top) == 1 or top[0][1] > top[1][1]):
        lookup[suffix], source[suffix] = [top[0][0]], "from the data"
    elif suffix in REVIEWED:
        lookup[suffix], source[suffix] = REVIEWED[suffix], "reviewed"
unread = sorted(set(by_suffix) - set(lookup))
show("CM-2", f"suffixes {len(by_suffix)}: from the data {sum(1 for s in source.values() if s == 'from the data')}, "
     f"reviewed {sum(1 for s in source.values() if s == 'reviewed')}, unread {unread}; "
     f"from the data: {dict(sorted((s, province_name.get(p[0], p[0])) for s, p in lookup.items() if source[s] == 'from the data'))}")
disagree = {s: (REVIEWED[s], lookup[s]) for s in REVIEWED if s in lookup and source[s] == "from the data" and REVIEWED[s] != lookup[s]}
if disagree:
    sys.exit(f"Reviewed suffix readings disagree with the data: {disagree}")

# %% Reviewed aliases for LGUs whose CMCI name differs from PSGC beyond the tiers
# Each maps a CMCI LGU to one PSGC code: a renamed LGU, a differently written name, or (for
# Santa Maria (DS)) an LGU now in Davao Occidental that CMCI still tags as Davao del Sur.
ALIASES = {
    "Bacungan Leon B. Postigo": "0907226000",  # Leon T. Postigo
    "Bantayan Island": "0702209000",  # Bantayan
    "Bulakan": "0301405000",  # Bulacan, Bulacan
    "Datu Blah Sinsuat": "1908704000",  # Datu Blah T. Sinsuat
    "Don Victoriano Chiongbian": "1004217000",  # Don Victoriano
    "E. B. Magalona": "1804508000",  # Enrique B. Magalona
    "Igacos": "1102317000",  # Island Garden City of Samal
    "Pigcawayan": "1204711000",  # Pigkawayan
    "Pio V Corpuz": "0504116000",  # Pio V. Corpus
    "President Garcia": "0701235000",  # President Carlos P. Garcia
    "R.T. Lim": "0908312000",  # Roseller Lim
    "Rizal (PN)": "1705323000",  # Dr. Jose P. Rizal, Palawan
    "Roxas (ZN)": "0907211000",  # Pres. Manuel A. Roxas, Zamboanga del Norte
    "San Isidro (DN)": "1102324000",  # Sawata, Davao del Norte
    "Santa Maria (DS)": "1108604000",  # Santa Maria, Davao Occidental
    "Sergio Osmena": "0907214000",  # Sergio Osmeña Sr.
}
by_code = {u.id: u for u in localities}
if set(ALIASES.values()) - set(by_code):
    sys.exit("An alias points to a code that is not a PSGC city or municipality.")

# %% Match every CMCI LGU
results = {}
for name in lgus:
    lgu_base, suffix = split(name)
    scope = localities if not suffix else [u for u in localities + independent if any(u.id.startswith(p) for p in lookup.get(suffix, []))]
    if suffix and suffix not in lookup:
        results[name] = ("suffix unread", None)
    elif name in ALIASES:
        results[name] = ("reviewed alias", by_code[ALIASES[name]])
    else:
        tier, unit = match(lgu_base, scope)
        if unit is None and suffix:
            # An HUC has its own province-level code, outside its province's range (Bacolod).
            tier, unit = match(lgu_base, independent)
            tier = f"independent city, {tier}" if unit else tier
        results[name] = (tier, unit)

# Names that fit several units (CMCI writes one of them without a suffix) are settled by
# elimination: the one candidate no other CMCI LGU has claimed.
claimed = collections.Counter(u.id for _, u in results.values() if u)
for name, (tier, unit) in list(results.items()):
    if tier == "ambiguous":
        free = [u for u in all_hits(split(name)[0], localities) if u.id not in claimed]
        if len(free) == 1:
            results[name] = ("by elimination", free[0])
            claimed[free[0].id] += 1

tiers = collections.Counter(t for t, u in results.values() if u)
missing = sorted((n, t) for n, (t, u) in results.items() if u is None)
twice = {c: [n for n, (t, u) in results.items() if u and u.id == c] for c, k in claimed.items() if k > 1}
unclaimed = [(u.id, u.name) for u in localities if u.id not in claimed]
show("CM-3", f"matched {sum(tiers.values()):,} of {len(lgus):,} ({100 * sum(tiers.values()) / len(lgus):.1f}%) by tier {dict(tiers.most_common())}; "
     f"not matched {missing}; PSGC codes claimed twice {twice}")
show("CM-4", f"PSGC cities and municipalities with no CMCI LGU: {len(unclaimed)} {unclaimed}")

# %% Write the list
lines = [
    "# CMCI LGUs: match to PSGC 2Q 2026",
    "",
    "Generated by [`cross_source_dti_cmci.py`](../../../../analysis/cross_source/cross_source_dti_cmci.py). Do not edit by hand; change the script and rerun. "
    "Lists every CMCI LGU not matched by its exact name, and every suffix. Part of #8.",
    "",
    "## Suffixes",
    "",
    "| Suffix | Read as | How |",
    "|---|---|---|",
]
lines += [f"| {s} | {', '.join(province_name.get(p, 'NCR' if p == '13' else 'City of Isabela' if p == '09901' else p) for p in lookup[s])} | {source[s]} |" for s in sorted(lookup)]
lines += ["", "## LGUs not matched by exact name", "", "| CMCI LGU | How | PSGC code | PSGC name |", "|---|---|---|---|"]
lines += [f"| {n} | {t} | {u.id if u else ''} | {u.name if u else ''} |" for n, (t, u) in sorted(results.items()) if t != "exact"]
lines += ["", "## PSGC cities and municipalities with no CMCI LGU", "", "| PSGC code | Name |", "|---|---|"]
lines += [f"| {c} | {n} |" for c, n in unclaimed]
(REPO / "docs" / "data" / "cross-source" / "generated" / "dti_cmci_psgc_match.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
show("run", "wrote docs/data/cross-source/generated/dti_cmci_psgc_match.md")
