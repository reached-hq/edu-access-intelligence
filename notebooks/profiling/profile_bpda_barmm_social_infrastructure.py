"""Profile the BPDA BARMM Social Infrastructure workbook and regenerate its dictionary."""

import hashlib
import math
import os
import statistics
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet, sheet_names


SOURCE_ID = "bpda_barmm_social_infrastructure"
FILENAME = "BARMM_Social_Infrastructure.xlsx"
EXPECTED_SHA256 = "6af9c99e33d820f99eb554326eb126cf6a2cdb30945e8f11088a0b26197391d3"


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
if len(header) != 33 or len(body) != 9:
    sys.exit(
        f"{FILENAME}: expected 33 columns and 9 data rows; "
        f"found {len(header)} columns and {len(body)} rows."
    )

keys = [row.get(1, "") for row in body]
measure_cells = [row.get(column, "") for row in body for column in range(2, 34)]
numbers = [clean_number(value) for value in measure_cells if clean_number(value) is not None]
dashes = sum(str(value).replace("\u00a0", " ").strip() == "-" for value in measure_cells)
blanks = sum(str(value) == "" for value in measure_cells)
nbsp_cells = sum("\u00a0" in str(value) for value in measure_cells)
non_integers = sum(not math.isclose(value, round(value)) for value in numbers)
zeroes = sum(value == 0 for value in numbers)

madrasah_checks = []
for row in body:
    total, with_pto, traditional = (clean_number(row.get(column, "")) for column in (14, 15, 16))
    if None not in (total, with_pto, traditional):
        madrasah_checks.append((row[1], int(total), int(with_pto + traditional), total == with_pto + traditional))

private_pairs = [(row[1], clean_number(row.get(6, "")), clean_number(row.get(17, ""))) for row in body]
private_same = [area for area, elementary, secondary in private_pairs if elementary == secondary]


def per_school(row, buildings_column, schools_column):
    buildings, schools = clean_number(row.get(buildings_column, "")), clean_number(row.get(schools_column, ""))
    return round(buildings / schools, 1) if buildings is not None and schools else None


building_ratios = [(row[1], per_school(row, 8, 7), per_school(row, 19, 18)) for row in body]

print(
    f"[{SOURCE_ID} run] {FILENAME}: checksum OK; sheets={sheets}; data rows={len(body)}; "
    f"columns={len(header)}; empty formatted rows={len(rows) - len(nonempty)}"
)
print(
    f"[{SOURCE_ID} O-1] duplicate keys={len(keys) - len(set(keys))}; "
    f"fully duplicated rows={len(body) - len({tuple(row.get(c, '') for c in range(1, 34)) for row in body})}"
)
print(
    f"[{SOURCE_ID} O-2] measure cells={len(measure_cells)}; numeric={len(numbers)}; "
    f"dash markers={dashes}; blanks={blanks}; numeric cells containing non-breaking spaces={nbsp_cells}"
)
print(
    f"[{SOURCE_ID} O-3] non-integer numeric measures={non_integers}; explicit zeroes={zeroes}; "
    f"min={min(numbers):.0f}; median={statistics.median(numbers):.0f}; max={max(numbers):.0f}"
)
print(
    f"[{SOURCE_ID} O-4] complete Private Madrasah Elementary components: "
    f"reconciled={sum(check[3] for check in madrasah_checks)} of {len(madrasah_checks)}; checks={madrasah_checks}"
)
print(f"[{SOURCE_ID} O-5] labels={keys}")
print(f"[{SOURCE_ID} O-6] header contains 'as of 20222'; 21 education columns have mixed or missing reference periods")
print(f"[{SOURCE_ID} O-7] classroom measures are labelled classroom buildings, not classrooms or seats")
print(
    f"[{SOURCE_ID} O-8] workbook has no title row, source note, definitions, PSGC, "
    "dash-marker definition, region total, or release date"
)
print(
    f"[{SOURCE_ID} O-10] private elementary equals private secondary in {len(private_same)} of {len(body)} rows "
    f"({private_same}); "
    f"pairs={[(area, int(e), int(s)) for area, e, s in private_pairs]}"
)
print(
    f"[{SOURCE_ID} O-11] permanent classroom buildings per public school (elementary, secondary)={building_ratios}"
)

dictionary_rows = []
for column in range(1, 34):
    name = header[column]
    raw = [row.get(column, "") for row in body]
    if column == 1:
        dictionary_rows.append(
            (
                f"`{name}`",
                "Not stated",
                name,
                "No definition is supplied in the workbook.",
                "**[observed]** The nine values mix provinces, cities, and the Special Geographic Area (SGA); treat them as historical reporting-area labels.",
                "category",
                "100.0%",
                str(len(set(raw))),
                "`Maguindanao`, `Cotabato City`, `SGA`",
            )
        )
        continue
    column_numbers = [clean_number(value) for value in raw if clean_number(value) is not None]
    column_dashes = sum(str(value).replace("\u00a0", " ").strip() == "-" for value in raw)
    column_blanks = sum(str(value) == "" for value in raw)
    interpretation = "**[observed]** Filled numeric values are whole counts; `-` is retained as missing because the publisher does not define it."
    if column == 13:
        interpretation = "**[assumed]** The header is ambiguous; exclude this field until BPDA confirms what is counted."
    if column in (6, 17):
        interpretation += " **[observed]** Private elementary and private secondary are equal in 5 of 9 rows (profile O-10); do not use either until BPDA confirms them."
    if column in (8, 9, 19, 20):
        interpretation += " **[observed]** The header says classroom building, not classroom or seat."
    if column in (8, 19):
        interpretation += " **[observed]** Four buildings-per-school ratios are outliers (profile O-11)."
    sample = (
        f"min {min(column_numbers):.0f}, median {statistics.median(column_numbers):.0f}, max {max(column_numbers):.0f}"
        if column_numbers
        else "no numeric values"
    )
    sample += f"; dash markers {column_dashes}; blanks {column_blanks}"
    dictionary_rows.append(
        (
            f"`{name}`",
            "Not stated",
            name,
            "No unit definition or missing-value definition is supplied.",
            interpretation,
            "whole number with undocumented `-` marker",
            percent(len(column_numbers), len(raw)),
            str(len(set(column_numbers))),
            sample,
        )
    )

dictionary = f"""# {SOURCE_ID}: data dictionary

Generated by [`notebooks/profiling/profile_bpda_barmm_social_infrastructure.py`](../../../notebooks/profiling/profile_bpda_barmm_social_infrastructure.py). Do not edit by hand; rerun the script instead.

- **Publisher descriptions:** the workbook contains no separate documentation; each exact column header is therefore the only publisher description available.
- **Observed columns:** measured from the checksum-verified workbook. `Filled` counts numeric values only; the publisher's undocumented `-` marker and a physical blank are not treated as zero.
- **Scope:** all delivered columns are documented even though the education project will use only the school and education-infrastructure fields.

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
