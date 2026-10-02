r"""Profile the PSA 2024 household population by age group CSV.

Run in PowerShell with:
    $env:PSA_POPULATION_AGE_GROUP_FILE = "C:\path\to\file.csv"
    python notebooks\profiling\profile_psa_population_per_age_group.py
"""

import csv
import hashlib
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = "ce797046a055f870c30f5a2ce6d42b4bdc8f14f4dd8145269f450372c6c93ad6"
EXPECTED_TITLE = "Household Population by Age-Group Region, Province, and Highly Urbanized City: Philippines, 2024 Census of Population"
EXPECTED_COLUMNS = ["Age Group", "Geographic Location", "Both Sexes", "Male", "Female"]

source_value = os.environ.get("PSA_POPULATION_AGE_GROUP_FILE")
if not source_value:
    sys.exit("Set PSA_POPULATION_AGE_GROUP_FILE to the downloaded CSV file.")
source = Path(source_value).expanduser()
if not source.is_file():
    sys.exit(f"File not found: {source}")

actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
if actual_hash != EXPECTED_SHA256:
    sys.exit(f"SHA-256 {actual_hash} does not match the inventoried file. Stop and re-inventory.")

with source.open(encoding="utf-8-sig", newline="") as handle:
    records = list(csv.reader(handle))

if not records or records[0] != [EXPECTED_TITLE]:
    sys.exit("The title row does not match the inventoried export.")
if len(records) < 2 or records[1] != EXPECTED_COLUMNS:
    sys.exit("The header row does not match the inventoried export.")
if any(len(row) != len(EXPECTED_COLUMNS) for row in records[2:]):
    sys.exit("At least one data row does not have five columns.")

rows = records[2:]
parsed = []
current_region = None
for source_row, row in enumerate(rows, start=3):
    age_group, geographic_location, *population_text = row
    prefix_length = len(geographic_location) - len(geographic_location.lstrip("."))
    if prefix_length == 0:
        geographic_level = "country"
        current_region = None
    elif prefix_length == 2:
        geographic_level = "region"
        current_region = geographic_location
    elif prefix_length == 4:
        geographic_level = "province_or_huc"
    else:
        geographic_level = "unknown"
    try:
        populations = [int(value) for value in population_text]
    except ValueError:
        sys.exit(f"Row {source_row} has a non-integer population value: {row}")
    parsed.append({
        "source_row": source_row,
        "age_group": age_group,
        "geographic_location": geographic_location,
        "geographic_level": geographic_level,
        "region": current_region,
        "both_sexes": populations[0],
        "male": populations[1],
        "female": populations[2],
    })

keys = [(row["age_group"], row["geographic_location"]) for row in parsed]
raw_rows = [tuple(row) for row in rows]
blank_cells = sum(value.strip() == "" for row in rows for value in row)
replacement_rows = [row for row in parsed if "\ufffd" in row["geographic_location"]]
sex_mismatches = [row for row in parsed if row["both_sexes"] != row["male"] + row["female"]]
negative_values = sum(value < 0 for row in parsed for value in (row["both_sexes"], row["male"], row["female"]))
zero_values = sum(value == 0 for row in parsed for value in (row["both_sexes"], row["male"], row["female"]))

age_groups = list(dict.fromkeys(row["age_group"] for row in parsed))
geographies = list(dict.fromkeys(row["geographic_location"] for row in parsed))
by_geography = defaultdict(dict)
for row in parsed:
    by_geography[row["geographic_location"]][row["age_group"]] = row

all_age_mismatches = []
for geography, age_rows in by_geography.items():
    all_ages = age_rows["All Ages"]
    sums = {field: sum(age_rows[age][field] for age in age_groups if age != "All Ages") for field in ("both_sexes", "male", "female")}
    for field, total in sums.items():
        if all_ages[field] != total:
            all_age_mismatches.append((geography, field, all_ages[field], total))

print(f"rows={len(parsed):,} columns={len(EXPECTED_COLUMNS)} age_groups={len(age_groups)} geographies={len(geographies)}")
print(f"blank_cells={blank_cells} duplicate_rows={len(raw_rows) - len(set(raw_rows))} duplicate_keys={len(keys) - len(set(keys))}")
print(f"negative_values={negative_values} zero_values={zero_values}")
print(f"replacement_character_rows={len(replacement_rows)} replacement_character_labels={len(set(row['geographic_location'] for row in replacement_rows))}")
print(f"sex_total_mismatches={len(sex_mismatches)} all_age_mismatches={len(all_age_mismatches)}")
print("sex_total_mismatches_by_age=", Counter(row["age_group"] for row in sex_mismatches))
print("sex_total_mismatches_by_region=", Counter(row["region"] for row in sex_mismatches))


def percent(value, total):
    return f"{100 * value / total:.1f}%" if total else "n/a"


def numeric_summary(field):
    values = [row[field] for row in parsed]
    return f"min {min(values):,}, median {statistics.median(values):,.0f}, max {max(values):,}; zeros: {sum(value == 0 for value in values):,}"


dictionary_rows = [
    ("Age Group", "Not stated", "Age Group", "The API publishes 19 category codes and labels.", "[observed] One of 19 mutually listed categories, including `All Ages` and 18 five-year age bands.", "category", "100.0%", "19", "`All Ages`, `Under 5`, `5 - 9`, ..., `85 and over`"),
    ("Geographic Location", "Not stated", "Geographic Location", "The API publishes a 10-digit code and display label for each of 137 locations, but the CSV export retains only the display label.", "[observed] Dot prefixes encode 1 country, 18 regions, and 118 province, HUC, or special-area labels. Footnote markers remain embedded in 25 labels.", "category", "100.0%", "137", "`PHILIPPINES`, `..National Capital Region (NCR)`, `....City of Manila`"),
    ("Both Sexes", "Not stated", "Both Sexes", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", "[observed] Household population count. Thirty-eight province or HUC rows fail the sex-total check; see O-7.", "whole number", "100.0%", f"{len(set(row['both_sexes'] for row in parsed)):,}", numeric_summary("both_sexes")),
    ("Male", "Not stated", "Male", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", "[observed] Male household population count. All-age values sum from the 18 age bands for every geography.", "whole number", "100.0%", f"{len(set(row['male'] for row in parsed)):,}", numeric_summary("male")),
    ("Female", "Not stated", "Female", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", "[observed] Female household population count. All-age values sum from the 18 age bands for every geography.", "whole number", "100.0%", f"{len(set(row['female'] for row in parsed)):,}", numeric_summary("female")),
]

dictionary = """# psa_population_per_age_group: data dictionary

Generated by [`notebooks/profiling/profile_psa_population_per_age_group.py`](../../../notebooks/profiling/profile_psa_population_per_age_group.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** taken from the PSA OpenSTAT table metadata and the downloaded CSV title and headers. The publisher does not state data types in either source.
- **Our interpretation:** measured from the checksum-verified CSV. Every interpretation is labeled and supported by observed evidence.
- **Observed columns:** five columns from the 2024 export, read as text before validated population values are converted to integers.
- **Filled:** share of 2,603 data rows that are not blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
for row in dictionary_rows:
    cells = [f"`{row[0]}`", *row[1:]]
    dictionary += "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |\n"

output = REPO / "docs/source_inventory/psa_population_per_age_group/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
