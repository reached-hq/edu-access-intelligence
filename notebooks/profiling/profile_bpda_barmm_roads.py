"""Profile the BPDA BARMM Roads workbook.

Run with:
    RAW_DATA_DIR=~/Projects/reached-hq/raw-data \
      python notebooks/profiling/profile_bpda_barmm_roads.py

The script verifies the inventoried file before reading it, prints every
quantitative finding cited in the source profile, and regenerates the data
dictionary. The raw workbook is read as received and is never modified.
"""

import hashlib
import os
import statistics
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet, sheet_names


SOURCE_ID = "bpda_barmm_roads"
FILENAME = "BARMM_Roads.xlsx"
EXPECTED_SHA256 = "5e36f1c36db08617d511d900a9052bc58b73f521d00e9b1712a4ab841cf63cc9"


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


def clean_number(value):
    """Return a float for a numeric cell; physical blanks and '-' stay missing."""
    if value is None:
        return None
    text = str(value).strip()
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
if sheets != ["BARMM Roads", "Charts BARMM Roads"]:
    sys.exit(f"{FILENAME}: unexpected worksheets: {sheets}")

all_rows = read_sheet(path, "BARMM Roads")
nonempty = [(row_number, cells) for row_number, cells in all_rows if cells]
header = nonempty[0][1]
body = [cells for _, cells in nonempty[1:]]
if len(header) != 21 or len(body) != 9:
    sys.exit(
        f"{FILENAME}: expected 21 columns and 9 data rows; "
        f"found {len(header)} columns and {len(body)} rows."
    )

keys = [row.get(1, "") for row in body]
measure_cells = [row.get(column, "") for row in body for column in range(2, 22)]
numbers = [clean_number(value) for value in measure_cells if clean_number(value) is not None]
dashes = [
    (row.get(1, ""), header[column])
    for row in body
    for column in range(2, 22)
    if str(row.get(column, "")).strip() == "-"
]
blank_count = sum(value == "" for value in measure_cells)
zero_count = sum(value == 0 for value in numbers)

# Columns B:E are published overall local-road lengths by surface. Columns F:U
# repeat the same four surfaces for provincial, municipal, barangay, and city
# roads. Only compare a total when all four published component cells are numeric.
reconciliation = []
for row in body:
    for total_column in range(2, 6):
        total = clean_number(row.get(total_column, ""))
        components = [clean_number(row.get(total_column + offset, "")) for offset in (4, 8, 12, 16)]
        if total is not None and all(value is not None for value in components):
            reconciliation.append(
                (
                    row[1],
                    header[total_column].split(":")[-1].strip(),
                    total,
                    sum(components),
                    round(total - sum(components), 2),
                )
            )

close_checks = [check for check in reconciliation if abs(check[4]) <= 0.02]
material_differences = [check for check in reconciliation if abs(check[4]) > 0.02]

# A single published component larger than its total is impossible whatever the
# blank or `-` cells mean, so check it even where the full reconciliation is skipped.
component_over_total = [
    (row[1], header[total_column + offset], clean_number(row.get(total_column + offset, "")), total)
    for row in body
    for total_column in range(2, 6)
    if (total := clean_number(row.get(total_column, ""))) is not None
    for offset in (4, 8, 12, 16)
    if (clean_number(row.get(total_column + offset, "")) or 0) > total + 0.02
]

print(
    f"[{SOURCE_ID} run] {FILENAME}: checksum OK; sheets={sheets}; "
    f"data rows={len(body)}; columns={len(header)}"
)
print(
    f"[{SOURCE_ID} O-1] duplicate reporting-area keys={len(keys) - len(set(keys))}; "
    f"fully duplicated rows={len(body) - len({tuple(row.get(c, '') for c in range(1, 22)) for row in body})}"
)
print(
    f"[{SOURCE_ID} O-2] measure cells={len(measure_cells)}; numeric={len(numbers)}; "
    f"blank={blank_count}; dash markers={len(dashes)}; explicit zeroes={zero_count}; "
    f"min={min(numbers):.2f}; median={statistics.median(numbers):.3f}; max={max(numbers):.2f}"
)
print(f"[{SOURCE_ID} O-3] dash locations={dashes}")
print(
    f"[{SOURCE_ID} O-4] complete total/component checks={len(reconciliation)}; "
    f"within 0.02 km={len(close_checks)}; differences above 0.02 km={material_differences}"
)
print(f"[{SOURCE_ID} O-8] components above their total by more than 0.02 km={component_over_total}")
print(
    f"[{SOURCE_ID} O-5] labels={keys}; workbook supplies no reference date, "
    "PSGC, geometry, endpoints, travel speeds, source note, or missing-marker definition"
)

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
                "No geographic definition or code is supplied.",
                "**[observed]** Historical reporting-area label mixing provinces, cities, and the Special Geographic Area; preserve exactly as published.",
                "category",
                "100.0%",
                str(len(set(raw))),
                "`Maguindanao`, `Cotabato City`, `SGA`",
            )
        )
        continue

    column_numbers = [clean_number(value) for value in raw if clean_number(value) is not None]
    column_dashes = sum(str(value).strip() == "-" for value in raw)
    column_blanks = sum(value == "" for value in raw)
    if 2 <= column <= 5:
        interpretation = "**[observed]** Published overall local-road length for this surface, in kilometres."
    else:
        interpretation = "**[observed]** Published road length for the administrative road class and surface named in the header, in kilometres."
    interpretation += " The file has no geometry, route, endpoint, or travel-time field."
    sample = (
        f"min {min(column_numbers):.2f}, median {statistics.median(column_numbers):.2f}, "
        f"max {max(column_numbers):.2f}; dash markers {column_dashes}; blanks {column_blanks}"
        if column_numbers
        else f"no numeric values; dash markers {column_dashes}; blanks {column_blanks}"
    )
    dictionary_rows.append(
        (
            f"`{name}`",
            "Not stated",
            name,
            "The header states kilometres. No reference date, collection method, precision rule, or missing-value definition is supplied.",
            interpretation,
            "non-negative decimal kilometres with blank or undocumented `-` marker",
            percent(len(column_numbers), len(raw)),
            str(len(set(column_numbers))),
            sample,
        )
    )

dictionary = f"""# {SOURCE_ID}: data dictionary

Generated by [`notebooks/profiling/profile_bpda_barmm_roads.py`](../../../notebooks/profiling/profile_bpda_barmm_roads.py). Do not edit by hand; rerun the script instead.

- **Publisher descriptions:** the workbook contains no separate documentation; each exact column header is the only publisher description available.
- **Observed columns:** measured from the checksum-verified workbook, read as stored text. `Filled` counts numeric values only; physical blanks and the publisher's undocumented `-` marker remain missing.
- **Units:** every measure header states kilometres. No conversion or rounding was applied.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
dictionary += "\n".join(
    "| " + " | ".join(markdown_cell(cell) for cell in row) + " |" for row in dictionary_rows
) + "\n"
output = REPO / "docs" / "source_inventory" / SOURCE_ID / "data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
