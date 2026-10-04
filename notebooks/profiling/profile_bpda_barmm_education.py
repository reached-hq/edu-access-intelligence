"""Profile the BPDA BARMM Education workbook and regenerate its dictionary."""

import hashlib
import os
import statistics
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet, sheet_names


SOURCE_ID = "bpda_barmm_education"
FILENAME = "BARMM_Education.xlsx"
EXPECTED_SHA256 = "5f08cb21ab1abaa2e13277eea429293782c3984447f7217bacce08c1eb44eeca"


def env_value(name):
    if os.environ.get(name):
        return os.environ[name]
    env = REPO / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == name and value.strip():
            return value.strip()
    return None


def clean_number(value):
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ").strip()
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


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
if sheets != ["Sheet1"]:
    sys.exit(f"{FILENAME}: unexpected worksheets: {sheets}")

rows = read_sheet(path, "Sheet1")
nonempty = [(row_number, cells) for row_number, cells in rows if cells]
header = nonempty[0][1]
body = [cells for _, cells in nonempty[1:]]
if len(header) != 21 or len(body) != 10:
    sys.exit(
        f"{FILENAME}: expected 21 columns and 10 data rows; "
        f"found {len(header)} columns and {len(body)} rows."
    )

keys = [row.get(1, "") for row in body]
values = [clean_number(row.get(column, "")) for row in body for column in range(2, 22)]
numbers = [value for value in values if value is not None]
blank_cells = [
    (row.get(1, ""), header[column])
    for row in body
    for column in range(2, 22)
    if clean_number(row.get(column, "")) is None
]
over_100 = [
    (row.get(1, ""), header[column], clean_number(row.get(column, "")))
    for row in body
    for column in range(2, 22)
    if clean_number(row.get(column, "")) is not None and clean_number(row.get(column, "")) > 1
]
at_100 = [
    (row.get(1, ""), header[column])
    for row in body
    for column in range(2, 22)
    if clean_number(row.get(column, "")) == 1
]

print(
    f"[{SOURCE_ID} run] {FILENAME}: checksum OK; sheets={sheets}; "
    f"data rows={len(body)}; columns={len(header)}"
)
print(
    f"[{SOURCE_ID} O-1] duplicate keys={len(keys) - len(set(keys))}; "
    f"fully duplicated rows={len(body) - len({tuple(row.get(c, '') for c in range(1, 22)) for row in body})}"
)
print(
    f"[{SOURCE_ID} O-2] rate cells={len(values)}; numeric={len(numbers)}; "
    f"blank={len(blank_cells)}; min={min(numbers):.4f}; "
    f"median={statistics.median(numbers):.5f}; max={max(numbers):.4f}"
)
print(f"[{SOURCE_ID} O-3] blank cells={blank_cells}")
print(
    f"[{SOURCE_ID} O-4] values above 100%="
    f"{[(area, field, f'{value:.2%}') for area, field, value in over_100]}"
)
print(f"[{SOURCE_ID} O-5] labels={keys}")
print(
    f"[{SOURCE_ID} O-6] workbook has no title row, source note, definitions, "
    "PSGC, denominators, region total, or release date"
)
print(f"[{SOURCE_ID} O-7] values exactly 100%={at_100}")

dictionary_rows = []
for column in range(1, 22):
    name = header[column]
    raw = [row.get(column, "") for row in body]
    if column == 1:
        dictionary_rows.append(
            (
                f"`{name}`",
                "Not stated",
                name,
                "No definition is supplied in the workbook.",
                "**[observed]** The ten values mix province-like labels, city divisions, and numbered school divisions; treat them as historical reporting-area labels, not current provinces.",
                "category",
                "100.0%",
                str(len(set(raw))),
                "`Basilan`, `Lanao Del Sur I`, `Cotabato City`",
            )
        )
        continue
    column_values = [clean_number(value) for value in raw]
    column_numbers = [value for value in column_values if value is not None]
    dictionary_rows.append(
        (
            f"`{name}`",
            "Not stated",
            name,
            "No formula, numerator, denominator, population coverage, or missing-value definition is supplied.",
            "**[observed]** Filled values are stored as decimal fractions and interpreted as rates because the publisher's header calls the field a rate.",
            "percentage stored as decimal fraction",
            percent(len(column_numbers), len(raw)),
            str(len(set(column_numbers))),
            f"min {min(column_numbers):.2%}, median {statistics.median(column_numbers):.2%}, max {max(column_numbers):.2%}; blanks {len(raw) - len(column_numbers)}",
        )
    )

dictionary = f"""# {SOURCE_ID}: data dictionary

Generated by [`notebooks/profiling/profile_bpda_barmm_education.py`](../../../notebooks/profiling/profile_bpda_barmm_education.py). Do not edit by hand; rerun the script instead.

- **Publisher descriptions:** the workbook contains no separate documentation; each exact column header is therefore the only publisher description available.
- **Observed columns:** measured from the checksum-verified workbook, read as stored text. `Filled` is the share of the 10 reporting-area rows with a numeric value.
- **Rates:** raw decimals are shown as percentages in the samples below; no weighting or denominator is inferred.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
dictionary += "\n".join(
    "| " + " | ".join(markdown_cell(cell) for cell in row) + " |" for row in dictionary_rows
) + "\n"
output = REPO / "docs" / "source_inventory" / SOURCE_ID / "data_dictionary.md"
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
