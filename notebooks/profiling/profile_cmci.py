# Profiles the two CMCI indicator extracts used by the project:
#   css = Capacity of School Services, edu = Education
# plus cmci_lgu_list.csv as the reference list of LGUs.
#
# Writes docs/source_inventory/cmci/profile.md. Every number in the profile is
# computed here, so rerunning the script regenerates the evidence. Impact,
# Proposed handling, the suspected findings and the questions are fixed text
# in this file: edit them here, not in profile.md.
#
# Runs locally with DuckDB. Open it in VS Code to run cell by cell (# %% markers),
# or run the whole file:
#   RAW_DATA_DIR=~/Documents/GitHub/raw-data python notebooks/profiling/profile_cmci.py
#
# RAW_DATA_DIR (environment or the repo's .env) must contain dti/original/ with
# the files listed in FILES. In Databricks, with RAW_DATA_DIR unset, the files are read
# from /Volumes/edu_access/00-source/raw/cmci/. Raw files are read, never modified.
# Profile date is generated automatically; profiled by is recorded below.

# %% Setup
import hashlib
import os
import sys
from datetime import date
from pathlib import Path

import duckdb

def find_repo():
    """Repo root: from this file's location, or by searching upward from the working
    folder when run cell by cell (VS Code interactive window, notebook), where
    __file__ does not exist."""
    try:
        return Path(__file__).resolve().parents[2]
    except NameError:
        here = Path.cwd().resolve()
        for folder in [here, *here.parents]:
            if (folder / "config" / "sources.json").exists() or (folder / ".git").exists():
                return folder
        sys.exit("Open the repo folder in VS Code (or cd into it) before running cell by cell.")

REPO = find_repo()
OUTPUT = REPO / "docs" / "source_inventory" / "dti_cmci" / "profile.md"

def env_value(name):
    """Read a variable from the environment, else from the repo's git-ignored .env."""
    if os.environ.get(name):
        return os.environ[name]
    env = REPO / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip()
    return None

PROFILED_DATE = date.today().isoformat()
PROFILED_BY = "saraevcldn"

# Locally: RAW_DATA_DIR/dti/original/ (D-007). In the Databricks workspace there is no
# local raw-data folder; the same files sit in the source volume, so use it when
# RAW_DATA_DIR is not set.
DATABRICKS_VOLUME = Path("/Volumes/edu_access/00-source/raw/cmci")
raw_dir = env_value("RAW_DATA_DIR")
if raw_dir:
    ORIGINAL = Path(raw_dir).expanduser() / "dti" / "original"
elif DATABRICKS_VOLUME.exists():
    ORIGINAL = DATABRICKS_VOLUME
else:
    sys.exit("Set RAW_DATA_DIR to the folder that contains dti/original/ (or run in Databricks with the source volume).")
print(f"Reading raw files from {ORIGINAL}")

# What arrived, as recorded in docs/source_inventory/cmci/README.md.
# Paste each SHA-256 from the inventory card. While a value is still the
# placeholder, the script prints the real checksum and stops.
PENDING = "PASTE_SHA256_FROM_README"
FILES = {
    "css": ("cmci_capacity_of_school_services_2023_2024.csv", "a9258fede279e1194e53a0ffeefd596df33505e82558e928f3adaee9791214e4"),
    "edu": ("cmci_education_2023_2024.csv", "6267b77a1043dbcd63f37957ec7c01cc4eb9fcba1bf88ed9c6247c6a8e7de102"),
    "lgu": ("cmci_lgu_list.csv", "187931b652b0912a5fa176b9743f107d6bb8c020004b132e42b753a1afabbebb"),
}
EXPECTED_COLUMNS = {
    "css": ["lgu", "year", "capacity_of_school_services", "status"],
    "edu": ["lgu", "year", "education", "status"],
    "lgu": ["lgu"],
}
INDICATORS = {"css": "capacity_of_school_services", "edu": "education"}
LABEL = {"css": "CSS", "edu": "Education"}
YEARS = ["2023", "2024"]

con = duckdb.connect()

def q(sql):
    return con.execute(sql).fetchall()

def columns(table):
    return [r[0] for r in q(f"DESCRIBE {table}")]

def num(col, alias=None):
    """Score as a number; blank text stays NULL, never 0."""
    ref = f'{alias}."{col}"' if alias else f'"{col}"'
    return f"try_cast(nullif(trim({ref}), '') AS DOUBLE)"

def cell(value):
    return str(value).replace("|", "/").replace("\n", " ")

def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(out)

def items(values, limit=10):
    """Short inline list for a table cell."""
    values = [v if isinstance(v, str) else ", ".join(str(x) for x in v) for v in values]
    if not values:
        return "none"
    shown = "; ".join(values[:limit])
    return shown + (f"; (+{len(values) - limit} more)" if len(values) > limit else "")

def pair(fn):
    """'CSS <x>; Education <y>' for a per-indicator value."""
    return "; ".join(f"{LABEL[t]} {fn(t)}" for t in INDICATORS)

# %% Verify checksums and expected columns, then load every column as text
# A changed file must stop the run, not silently produce new numbers
# under the old checksum.
pending = []
for key, (name, sha) in FILES.items():
    path = ORIGINAL / name
    if not path.exists():
        sys.exit(f"Missing file: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha == PENDING:
        pending.append((name, actual))
    elif actual != sha:
        sys.exit(f"{name}: SHA-256 does not match the inventory card. Stop and re-inventory.")
if pending:
    lines = "\n".join(f"  {name}: {actual}" for name, actual in pending)
    sys.exit(f"No SHA-256 recorded yet for {len(pending)} file(s). Computed:\n{lines}\n"
             "Add each to the inventory card and to FILES, then run again.")

for key, (name, _) in FILES.items():
    con.execute(f"CREATE TABLE {key} AS SELECT * FROM read_csv('{ORIGINAL / name}', "
                "all_varchar = true, header = true, strict_mode = true)")
    observed = columns(key)
    if observed != EXPECTED_COLUMNS[key]:
        sys.exit(f"{name}: columns changed. Expected {EXPECTED_COLUMNS[key]}, found {observed}.")
    print(f"{key}: {q(f'SELECT count(*) FROM {key}')[0][0]} rows, columns {observed}, checksum OK")

# %% Evidence per indicator
ev = {}
n_lgu = q("SELECT count(DISTINCT trim(lgu)) FROM lgu")[0][0]
expected_set = ("SELECT trim(l.lgu) AS lgu, y.year FROM (SELECT DISTINCT lgu FROM lgu) l "
                f"CROSS JOIN (SELECT unnest({YEARS}) AS year) y")

for t, col in INDICATORS.items():
    e = {}
    v = num(col)
    e["rows"], distinct = q(f"SELECT count(*), count(DISTINCT (trim(lgu), year)) FROM {t}")[0]
    e["dupes"] = e["rows"] - distinct
    e["by_year"] = q(f"SELECT year, count(*), count(DISTINCT trim(lgu)) FROM {t} GROUP BY 1 ORDER BY 1")
    e["bad_years"] = [y for y, _, _ in e["by_year"] if y not in YEARS]
    e["missing"] = q(f"SELECT * FROM ({expected_set}) EXCEPT SELECT trim(lgu), year FROM {t} ORDER BY 1, 2")
    e["extra"] = q(f"SELECT trim(lgu), year FROM {t} EXCEPT SELECT * FROM ({expected_set}) ORDER BY 1, 2")
    e["statuses"] = q(f"SELECT status, count(*) FROM {t} GROUP BY 1 ORDER BY 1")
    e["nonvalid"] = q(f"SELECT trim(lgu), year, status FROM {t} WHERE status <> 'valid' ORDER BY 1, 2")
    e["bad_valid"] = q(f"SELECT count(*) FROM {t} WHERE status = 'valid' AND {v} IS NULL")[0][0]
    e["bad_other"] = q(f"SELECT count(*) FROM {t} WHERE status <> 'valid' AND nullif(trim(\"{col}\"), '') IS NOT NULL")[0][0]
    e["stats"] = q(f"""SELECT year,
                              count(*) FILTER (WHERE status = 'valid'),
                              count(*) FILTER (WHERE status = 'valid' AND {v} = 0),
                              min({v}) FILTER (WHERE status = 'valid'),
                              max({v}) FILTER (WHERE status = 'valid'),
                              quantile_cont({v}, [0.5, 0.9, 0.99]) FILTER (WHERE status = 'valid')
                       FROM {t} GROUP BY 1 ORDER BY 1""")
    e["errors"] = [r[0] for r in q(f"SELECT DISTINCT trim(lgu) FROM {t} WHERE status = 'cmci_server_error' ORDER BY 1")]
    e["not_in_list"] = [r[0] for r in q(f"SELECT DISTINCT trim(lgu) FROM {t} EXCEPT SELECT trim(lgu) FROM lgu ORDER BY 1")]
    e["list_not_in"] = [r[0] for r in q(f"SELECT trim(lgu) FROM lgu EXCEPT SELECT DISTINCT trim(lgu) FROM {t} ORDER BY 1")]
    ev[t] = e

# %% Evidence across indicators and for LGU names
both_zero = q(f"""SELECT c.year, count(*) FROM css c JOIN edu e ON trim(c.lgu) = trim(e.lgu) AND c.year = e.year
                  WHERE c.status = 'valid' AND e.status = 'valid'
                    AND {num('capacity_of_school_services', 'c')} = 0 AND {num('education', 'e')} = 0
                  GROUP BY 1 ORDER BY 1""")
css_not_edu = q("SELECT trim(lgu), year FROM css EXCEPT SELECT trim(lgu), year FROM edu ORDER BY 1, 2")
edu_not_css = q("SELECT trim(lgu), year FROM edu EXCEPT SELECT trim(lgu), year FROM css ORDER BY 1, 2")

name_stats = {}
for t in ["lgu", "css", "edu"]:
    names = f"(SELECT DISTINCT lgu FROM {t})"
    name_stats[t] = (
        q(f"SELECT count(*) FROM {names}")[0][0],
        q(f"SELECT count(*) FROM {names} WHERE lgu <> trim(lgu)")[0][0],
        q(f"SELECT count(*) FROM {names} WHERE lgu LIKE '%''%'")[0][0],
        q(f"SELECT count(*) FROM {names} WHERE lgu LIKE '%’%'")[0][0],
    )
suffixed = [r[0] for r in q("SELECT trim(lgu) FROM lgu WHERE lgu LIKE '%(%' ORDER BY 1")]
base_dupes = q("""SELECT base, count(*) FROM (SELECT trim(regexp_replace(trim(lgu), '\\s*\\([^)]*\\)$', '')) AS base FROM lgu)
                  GROUP BY 1 HAVING count(*) > 1 ORDER BY 1""")
apostrophe_errors = {t: [n for n in ev[t]["errors"] if "'" in n or "’" in n] for t in INDICATORS}

# %% Build the profile
expected_rows = n_lgu * len(YEARS)
all_clean = all(not e["missing"] and not e["extra"] and not e["dupes"] for e in ev.values())
zeros_total = {t: sum(r[2] for r in ev[t]["stats"]) for t in INDICATORS}
nonvalid_total = {t: len(ev[t]["nonvalid"]) for t in INDICATORS}

summary = (
    f"Two CMCI indicators (Capacity of School Services, Education) for {n_lgu:,} LGUs in {', '.join(YEARS)}, "
    f"one score per LGU, year and indicator. "
    + ("Both files cover every expected LGU-year with no duplicates. " if all_clean
       else "Coverage or uniqueness problems were found (O-1, O-2). ")
    + "LGUs are identified by name only; there is no PSGC code. "
    + f"Records without a score: {pair(lambda t: nonvalid_total[t])}. "
    + f"Valid scores of exactly 0: {pair(lambda t: zeros_total[t])}; whether 0 is a real score needs a decision (S-2)."
)

def ev_grain(t):
    return f"{ev[t]['rows']:,} rows, {ev[t]['dupes']} duplicate keys"

def ev_coverage(t):
    e = ev[t]
    return f"{len(e['missing'])} LGU-years missing, {len(e['extra'])} unexpected, years outside {YEARS}: {e['bad_years'] or 'none'}"

def ev_consistency(t):
    return f"{ev[t]['bad_valid']} valid rows without a numeric score, {ev[t]['bad_other']} non-valid rows with a score"

def ev_reference(t):
    e = ev[t]
    return f"names not in reference list {len(e['not_in_list'])}, reference names not in file {len(e['list_not_in'])}"

def ev_apostrophe(t):
    return f"{len(apostrophe_errors[t])} of {len(ev[t]['errors'])}"

observed = [
    ("O-1", "lgu + year is the grain of each file",
     f"{pair(ev_grain)}; expected {expected_rows:,} rows ({n_lgu:,} LGUs x {len(YEARS)} years)",
     "Safe primary key if there are 0 duplicates", "Assert uniqueness in Bronze validation"),
    ("O-2", "Coverage against the expected set (reference list x years)",
     pair(ev_coverage),
     "Gaps would break year-over-year comparison", "Keep the check in Bronze validation"),
    ("O-3", "Records without a score",
     pair(lambda t: f"{nonvalid_total[t]} ({', '.join(f'{s} {n}' for s, n in ev[t]['statuses'] if s != 'valid') or 'none'}): "
                    f"{items([f'{n} {y}' for n, y, _ in ev[t]['nonvalid']])}"),
     "Blank is not zero", "Keep as null with status; never impute 0"),
    ("O-4", "status and score agree",
     pair(ev_consistency),
     "Status can be trusted when both counts are 0", "Filter on status = 'valid' in Silver"),
    ("O-5", "Exact zeros among valid scores",
     pair(lambda t: ", ".join(f"{y}: {z} of {n}" for y, n, z, *_ in ev[t]["stats"]))
     + f"; LGU-years that are 0 in both indicators: {', '.join(f'{y}: {n}' for y, n in both_zero) or 'none'}",
     "Zero may mean \"no data submitted\" (S-2), which would make the score a missing value",
     "Keep as reported; flag zeros in Silver until S-2 is resolved"),
    ("O-6", "Observed scores extend above 1.0",
    pair(lambda t: "min {} max {}".format(
     min((r[3] for r in ev[t]["stats"] if r[3] is not None), default=None),
     max((r[4] for r in ev[t]["stats"] if r[4] is not None), default=None))),
    "The score should not be interpreted as a percentage or direct count without methodology verification",
    "Use as contextual information only; do not rescale or interpret the score without methodology verification"),
    ("O-7", "LGU is a name only",
     f"Columns are {', '.join(columns('css'))}; reference list columns: {', '.join(columns('lgu'))}; "
     f"names with a parenthetical suffix: {len(suffixed)} ({items(suffixed, 6)}); "
     f"base names shared by more than one LGU: {len(base_dupes)} ({items(base_dupes, 6)})",
     "No PSGC join key; names can collide", "Map names to PSGC in integration with a reviewed crosswalk"),
    ("O-8", "Name formatting (distinct names / leading-trailing spaces / straight apostrophe / curly apostrophe)",
     "; ".join(f"{t}: {a} / {b} / {c} / {d}" for t, (a, b, c, d) in name_stats.items()),
     "Joins on raw names are fragile", "Use normalized names for matching while retaining the original LGU name"),
    ("O-9", "The two indicators and the reference list agree",
     f"LGU-years in CSS not Education: {len(css_not_edu)}; in Education not CSS: {len(edu_not_css)}; "
     + pair(ev_reference),
     "CSS and Education can be joined on (lgu, year) only if the first two counts are 0", "Join on (lgu, year) in Silver"),
]

if any(apostrophe_errors.values()):
    s1_names = items(sorted({n for names in apostrophe_errors.values() for n in names}))
    s1 = (f"The server errors are extraction failures, not source gaps: {pair(ev_apostrophe)} "
          f"server-error LGUs have an apostrophe in the name ({s1_names})")
else:
    s1 = "The server errors are extraction failures, not source gaps (no apostrophe pattern in this run)"

suspected = [
    ("S-1", s1, "Re-request with encoded names; check the portal by hand", "open"),
    ("S-2", "An exact 0 means \"no data submitted\", not a real score of 0",
     "Compare zero LGUs with the portal and the DTI methodology; check whether zeros cluster by region or LGU class", "open"),
    ("S-3", "The two years are comparable", "Read the methodology for each edition", "open"),
    ("S-4", "The score construction or scale may differ by indicator, so levels should not be compared across indicators until the DTI methodology is verified", "Read the DTI methodology and indicator definitions", "open"),
]

def fmt(x):
    return "" if x is None else f"{x:.4f}".rstrip("0").rstrip(".")

dist_rows = []
for t in INDICATORS:
    for y, n, z, lo, hi, qs in ev[t]["stats"]:
        p = [fmt(x) for x in qs] if qs else ["", "", ""]
        dist_rows.append((LABEL[t], y, n, z, fmt(lo), fmt(hi), *p))

profile = f"""# cmci: profile

_Generated by notebooks/profiling/profile_cmci.py. Do not edit by hand; change the script and rerun._

## Run details

| Field | Value |
|---|---|
| Date profiled | {PROFILED_DATE} |
| Profiled by | {PROFILED_BY} |
| Tool | DuckDB 1.4.5 (Python), run locally: [notebooks/profiling/profile_cmci.py](../../../notebooks/profiling/profile_cmci.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if any checksum differs |
| How files were read | All columns as text (all_varchar), strict CSV parsing |

## How to rerun

Download the three CSVs from /Volumes/edu_access/00-source/raw/ into <RAW_DATA_DIR>/dti/original/, then:

```bash
RAW_DATA_DIR=/path/to/raw-data python notebooks/profiling/profile_cmci.py
```

## Summary

{summary}

## Observed findings

{md_table(["ID", "Finding", "Evidence", "Impact", "Proposed handling"], observed)}

## Suspected findings

{md_table(["ID", "Suspicion", "How to test", "Status"], suspected)}

## Score distribution by year (valid records only)

{md_table(["Indicator", "Year", "Valid", "Exact zeros", "Min", "Max", "p50", "p90", "p99"], dist_rows)}

## Changes across files or years

One file per indicator, each covering {', '.join(YEARS)}. Whether the method or the indicator definitions differ between the two editions is not yet verified (S-3).

## Questions for the publisher or mentor

- Is a score of 0 a real value, or does it indicate "no data submitted"?
- Are the missing scores source-side, or could they be caused by portal/extraction behavior (O-3)?
- What exactly does each score measure, and what is the scoring scale or calculation method?
- Are the 2023 and 2024 scores directly comparable, or did the methodology or indicator definition change between years?
- Is there a downloadable official export or documentation for these indicators, and what are the reuse terms? """

# %% Write profile
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(profile, encoding="utf-8")
print(f"Profile written to {OUTPUT}")