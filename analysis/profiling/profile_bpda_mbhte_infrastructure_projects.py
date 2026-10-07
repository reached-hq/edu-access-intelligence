"""Profile the BPDA monitoring file for MBHTE infrastructure projects.

Run with:
    RAW_DATA_DIR=~/Projects/reached-hq/raw-data \
      python analysis/profiling/profile_bpda_mbhte_infrastructure_projects.py

The script verifies the inventoried file, prints the quantitative findings used
in the source profile, and regenerates the data dictionary. It never modifies
the raw workbook.
"""

import collections
import hashlib
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet, sheet_names


SOURCE_ID = "bpda_mbhte_infrastructure_projects"
FILENAME = "BARMM_MBHTE_Infrastructure_Projects.xlsx"
EXPECTED_SHA256 = "9a21113c97a773bdbeba66d23cb7855b563ff91bfa8f320268b6c0b687fee734"
DATA_SHEET = "Monitored Projects by MBHTE"
EXPECTED_SHEETS = [DATA_SHEET, "Dashboard", "Copy of Dashboard"]
M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def env_value(name):
    """Read a variable from the environment, else from the repo's ignored .env."""
    if os.environ.get(name):
        return os.environ[name]
    env = REPO / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip()
    return None


def excel_date(serial):
    """Convert a whole-day serial from a 1900-date-system workbook."""
    return date(1899, 12, 30) + timedelta(days=int(float(serial)))


def percent(numerator, denominator):
    return f"{100 * numerator / denominator:.1f}%" if denominator else "n/a"


def markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", "<br>")


raw_dir = env_value("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains bpda/original/.")
path = Path(raw_dir).expanduser() / "bpda" / "original" / FILENAME
if not path.is_file():
    sys.exit(f"Missing required workbook: {path}")
actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
if actual_sha256 != EXPECTED_SHA256:
    sys.exit(f"{FILENAME}: SHA-256 does not match the inventory card. Stop and re-inventory.")

with zipfile.ZipFile(path) as workbook:
    sheets = sheet_names(workbook)
    workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
    workbook_properties = workbook_xml.find(M + "workbookPr")
    uses_1904_dates = workbook_properties is not None and workbook_properties.get("date1904") in ("1", "true")
if sheets != EXPECTED_SHEETS:
    sys.exit(f"{FILENAME}: unexpected worksheets: {sheets}")
if uses_1904_dates:
    sys.exit(f"{FILENAME}: unexpected 1904 date system; review date conversion.")

all_rows = read_sheet(path, DATA_SHEET)
nonempty = [(row_number, cells) for row_number, cells in all_rows if cells]
header = nonempty[0][1]
body = [cells for _, cells in nonempty[1:]]
if len(header) != 10 or len(body) != 16:
    sys.exit(
        f"{FILENAME}: expected 10 columns and 16 data rows; "
        f"found {len(header)} columns and {len(body)} rows."
    )

project_names = [row.get(4, "") for row in body]
years = [int(float(row[6])) for row in body if row.get(6, "")]
monitor_dates = [excel_date(row[7]).isoformat() for row in body if row.get(7, "")]


def site_key(name):
    """School or site named in a project, ignoring case, the action word, and the classroom token."""
    text = re.sub(r"^(CONSTRUCTION|REPAIR) OF\s+", "", name.upper().strip())
    return re.sub(r"\s+", " ", re.sub(r"\s*\d+\s*CL\b", "", text)).strip()


same_site = collections.defaultdict(list)
for row in body:
    same_site[(site_key(row.get(4, "")), row.get(5, ""), row.get(6, ""))].append(row.get(4, ""))
possible_duplicates = {key: names for key, names in same_site.items() if len(names) > 1}

actions = collections.Counter(
    (row.get(4, "").upper().split(" ", 1)[0], row.get(8, "")) for row in body
)
missing_field_headers = [
    header[column] for column in range(1, 11)
    if re.search(r"\bID\b|CODE|PSGC|LATITUDE|LONGITUDE|COORDINAT|COST|BUDGET|AMOUNT|PROGRESS|START|COMPLET|BENEFICIAR", header[column].upper())
]
classroom_tokens = sum(bool(re.search(r"\d+\s*CL\b", row.get(4, "").upper())) for row in body)

print(
    f"[{SOURCE_ID} run] {FILENAME}: checksum OK; sheets={sheets}; "
    f"data rows={len(body)}; columns={len(header)}; empty formatted rows={len(all_rows) - len(nonempty)}"
)
print(
    f"[{SOURCE_ID} O-1] duplicate exact project names={len(project_names) - len(set(project_names))}; "
    f"fully duplicated rows={len(body) - len({tuple(row.get(c, '') for c in range(1, 11)) for row in body})}"
)
print(
    f"[{SOURCE_ID} O-2] province={collections.Counter(row.get(1, '') for row in body)}; "
    f"municipalities={collections.Counter(row.get(2, '') for row in body)}"
)
print(f"[{SOURCE_ID} O-3] barangay filled={sum(bool(row.get(3, '')) for row in body)} of {len(body)}")
print(
    f"[{SOURCE_ID} O-4] program={collections.Counter(row.get(5, '') for row in body)}; "
    f"funding year={collections.Counter(years)} plus blanks={sum(not row.get(6, '') for row in body)}"
)
print(
    f"[{SOURCE_ID} O-5] monitoring date={collections.Counter(monitor_dates)}; "
    f"date cells filled={len(monitor_dates)} of {len(body)}"
)
print(f"[{SOURCE_ID} O-6] remarks={collections.Counter(row.get(8, '') for row in body)}")
print(
    f"[{SOURCE_ID} O-7] project type={collections.Counter(row.get(9, '') for row in body)}; "
    f"monitored by={collections.Counter(row.get(10, '') for row in body)}"
)
print(
    f"[{SOURCE_ID} O-8] headers naming an ID, code, coordinates, cost, budget, progress, start, completion, "
    f"or beneficiaries={missing_field_headers}; complete columns="
    f"{[header[c] for c in range(1, 11) if all(row.get(c, '') != '' for row in body)]}"
)
print(f"[{SOURCE_ID} O-9] same site, program, and funding year in more than one row={possible_duplicates}")
print(f"[{SOURCE_ID} O-10] action word by status={dict(sorted(actions.items()))}; names with a classroom token={classroom_tokens}")

interpretations = {
    1: "**[observed]** Province label; every delivered record is `BASILAN`.",
    2: "**[observed]** Municipality or city label; four distinct values are present.",
    3: "**[observed]** Intended barangay field; all 16 records are physically blank.",
    4: "**[observed]** Free-text project name; unique in this file but not a governed project identifier.",
    5: "**[observed]** Program acronym; three records are blank and the workbook supplies no acronym definitions.",
    6: "**[observed]** Funding year stored as a numeric value; three records are blank.",
    7: "**[observed]** Monitoring date stored as an Excel serial with date formatting; decoded using the workbook's 1900 date system.",
    8: "**[observed]** Free-text project status as published; includes `COMPLETED`, `ON GOING`, and `ABANDONED`.",
    9: "**[observed]** Published project-type category; 15 building projects and one covered court.",
    10: "**[observed]** Monitoring organization; every delivered record is `BPDA`.",
}

dictionary_rows = []
for column in range(1, 11):
    name = header[column]
    raw = [row.get(column, "") for row in body]
    filled = [value for value in raw if value != ""]
    if column == 7:
        samples = ", ".join(f"`{value}` ({count})" for value, count in collections.Counter(monitor_dates).items())
        kind = "Excel date serial"
        distinct = len(set(monitor_dates))
    elif column == 6:
        samples = ", ".join(str(value) for value in sorted(set(years))) + f"; blanks {len(raw) - len(filled)}"
        kind = "whole-number year stored as numeric"
        distinct = len(set(years))
    else:
        counts = collections.Counter(filled)
        samples = "; ".join(f"`{value}` ({count})" for value, count in counts.most_common(5))
        if len(counts) > 5:
            samples += f"; {len(counts) - 5} other values"
        if len(raw) - len(filled):
            samples += f"; blanks {len(raw) - len(filled)}"
        kind = "text"
        distinct = len(counts)
    dictionary_rows.append(
        (
            f"`{name}`",
            "Not stated",
            name,
            "No separate definition is supplied in the workbook.",
            interpretations[column],
            kind,
            percent(len(filled), len(raw)),
            str(distinct),
            samples or "all values blank",
        )
    )

dictionary = f"""# {SOURCE_ID}: data dictionary

Generated by [`analysis/profiling/profile_bpda_mbhte_infrastructure_projects.py`](../../../analysis/profiling/profile_bpda_mbhte_infrastructure_projects.py). Do not edit by hand; rerun the script instead.

- **Publisher descriptions:** the workbook contains no separate codebook; each exact column header is the only publisher description available.
- **Observed columns:** measured from the checksum-verified workbook. Physical blanks remain null and are never converted to zero or a category.
- **Dates:** raw Excel serials are decoded only after verifying that the workbook uses the 1900 date system.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
dictionary += "\n".join(
    "| " + " | ".join(markdown_cell(cell) for cell in row) + " |" for row in dictionary_rows
) + "\n"
output = REPO / "docs" / "data" / "source-inventory" / SOURCE_ID / "data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
