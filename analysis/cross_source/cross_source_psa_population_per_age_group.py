# Cross-source checks for psa_population_per_age_group against PSGC 2Q 2026 (part of #8).
#
# Prints the findings labelled AG-n in:
#   docs/data/cross-source/coverage.md
#
# The CSV has place names only. The OpenSTAT API metadata of the same table (0201A6DPAG0)
# carries one 10-digit code per place; this script checks those codes against PSGC 2Q 2026
# and ties each CSV label to its code.
#
# Runs locally; no Databricks compute:
#   RAW_DATA_DIR=~/Projects/reached-hq/raw-data python analysis/cross_source/cross_source_psa_population_per_age_group.py
#
# RAW_DATA_DIR/psa/original/ needs the CSV from the psa_population_per_age_group card, the
# PSGC 2Q 2026 workbook, and 0201A6DPAG0_metadata.json, saved on 2026-10-06 from
# https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/PO_2024/0201A6DPAG0.px (GET, no query).

# %% Setup
import collections
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
ORIGINAL = Path(raw_dir).expanduser() / "psa" / "original"
FILES = {
    "csv": ("Household Population by Age-Group Region, Province, and Highly Urbanized City- Philippines, 2024 Census of Population.csv",
            "ce797046a055f870c30f5a2ce6d42b4bdc8f14f4dd8145269f450372c6c93ad6"),
    "metadata": ("0201A6DPAG0_metadata.json", "040697a4c1663d208ef7c040c38cc018c0bd5a2895451736e9fae87efb5fe113"),
    "psgc": ("PSGC-2Q-2026-Publication-Datafile.xlsx", "31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d"),
}
for name, sha in FILES.values():
    if hashlib.sha256((ORIGINAL / name).read_bytes()).hexdigest() != sha:
        sys.exit(f"{name}: SHA-256 does not match. Stop and re-inventory.")


def show(finding, text):
    print(f"[{finding}] {text}")


metadata = json.loads((ORIGINAL / FILES["metadata"][0]).read_text(encoding="utf-8"))
geo = next(v for v in metadata["variables"] if v["text"] == "Geographic Location")
places = list(zip(geo["values"], geo["valueTexts"]))
psgc = {}
for _, cells in list(read_sheet(ORIGINAL / FILES["psgc"][0], "PSGC"))[1:]:
    psgc[cells.get(1, "")] = (cells.get(2, "").strip(), cells.get(4, "").strip(), cells.get(9, ""))
with (ORIGINAL / FILES["csv"][0]).open(encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))
header = next(i for i, r in enumerate(rows) if r and r[0] == "Age Group")
data = [r for r in rows[header + 1:] if len(r) == 5]


def label(text):
    """Display label without hierarchy dots, footnote markers, or asterisks."""
    text = re.sub(r"\s*(\d+/|\*+)\s*", " ", text.lstrip(".")).strip()
    return re.sub(r"\s+\d+$", "", text)  # a bare footnote digit, as in "Special Geographic Area 8"


def comparable(name):
    return re.sub(r"\W", "", re.sub(r"\s*\([^)]*\)$", "", name).upper())


show("AG-1", f"table {metadata['title']!r}: places in the metadata {len(places)}; CSV rows {len(data):,}; checksums OK")

# %% AG-2: metadata codes against PSGC 2Q 2026
found = [(c, t) for c, t in places if c in psgc]
missing = [(c, t) for c, t in places if c not in psgc]
name_differs = [(c, label(t), psgc[c][0]) for c, t in found
                if comparable(label(t)) != comparable(psgc[c][0])]
levels = collections.Counter(psgc[c][1] or "(blank level)" for c, _ in found)
show("AG-2", f"codes found in PSGC 2Q 2026: {len(found)} of {len(places)}, by PSGC level {dict(levels)}; not found {missing}; "
     f"found with a different name (code, table, PSGC): {name_differs}")

# %% AG-3: every CSV label ties to one metadata code
by_label = collections.defaultdict(set)
for code, text in places:
    by_label[text].add(code)
csv_labels = {r[1] for r in data}
damaged = {t for t in csv_labels if "�" in t}
repaired = {t: [m for m in by_label if re.fullmatch(re.escape(t).replace("�", "."), m)] for t in damaged}
unknown = {t for t in csv_labels if t not in by_label and t not in damaged}
show("AG-3", f"CSV labels {len(csv_labels)}: equal to a metadata label {len(csv_labels & set(by_label))}; with U+FFFD {len(damaged)}, each tied to "
     f"{sorted(len(v) for v in repaired.values())} metadata label(s) when the damaged character is a wildcard: {repaired}; not found {sorted(unknown)}; "
     f"metadata labels on more than one code {[t for t, c in by_label.items() if len(c) > 1]}")

# %% AG-4: household population against PSGC total population, same code
code_of = {t: next(iter(c)) for t, c in by_label.items()}
for t, matches in repaired.items():
    code_of[t] = next(iter(by_label[matches[0]]))
household = {code_of[r[1]]: int(r[2]) for r in data if r[0] == "All Ages"}


def as_int(value):
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


compare = [(c, household[c], as_int(psgc[c][2])) for c in household if c in psgc and as_int(psgc[c][2]) is not None]
above = [(c, psgc[c][0], h, t) for c, h, t in compare if h > t]
shares = sorted(h / t for _, h, t in compare if t)
show("AG-4", f"places with both values {len(compare)}: household above PSGC total population {len(above)} {above}; "
     f"household as a share of total: min {shares[0]:.3f}, median {shares[len(shares) // 2]:.3f}, max {shares[-1]:.3f}")
