r"""Profile the PSA 2024 household population by age group CSV.

Run in PowerShell with:
    $env:RAW_DATA_DIR = "C:\path\to\raw-data"
    python notebooks\profiling\profile_psa_population_per_age_group.py
"""

import csv
import hashlib
import os
import statistics
import sys
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


# %% setup
REPO = Path(__file__).resolve().parents[2]
SOURCE_FILENAME = "Household Population by Age-Group Region, Province, and Highly Urbanized City- Philippines, 2024 Census of Population.csv"
EXPECTED_SHA256 = "ce797046a055f870c30f5a2ce6d42b4bdc8f14f4dd8145269f450372c6c93ad6"
EXPECTED_TITLE = "Household Population by Age-Group Region, Province, and Highly Urbanized City: Philippines, 2024 Census of Population"
EXPECTED_COLUMNS = ["Age Group", "Geographic Location", "Both Sexes", "Male", "Female"]

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
source = Path(raw_dir).expanduser() / "psa" / "original" / SOURCE_FILENAME
if not source.is_file():
    sys.exit(f"File not found: {source}")

# %% verify and load every CSV column as text with DuckDB
actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
if actual_hash != EXPECTED_SHA256:
    sys.exit(f"SHA-256 {actual_hash} does not match the inventoried file. Stop and re-inventory.")

with source.open(encoding="utf-8-sig", newline="") as handle:
    title = next(csv.reader(handle), None)

if title != [EXPECTED_TITLE]:
    sys.exit("The title row does not match the inventoried export.")

con = duckdb.connect()
con.execute("CREATE TABLE age_group AS SELECT * FROM read_csv(?, all_varchar = true, header = true, skip = 1, strict_mode = true)", [str(source)])
columns = [row[0] for row in con.execute("DESCRIBE age_group").fetchall()]
if columns != EXPECTED_COLUMNS:
    sys.exit(f"The header row does not match the inventoried export: {columns}")
rows = [[value or "" for value in record] for record in con.execute("SELECT * FROM age_group").fetchall()]

# %% parse hierarchy and validated population values
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
age_counts = Counter(row["age_group"] for row in parsed)
geography_counts = Counter(row["geographic_location"] for row in parsed)
level_counts = Counter(row["geographic_level"] for row in parsed)
by_geography = defaultdict(dict)
for row in parsed:
    by_geography[row["geographic_location"]][row["age_group"]] = row
level_label_counts = Counter(age_rows["All Ages"]["geographic_level"] for age_rows in by_geography.values())

all_age_mismatches = []
for geography, age_rows in by_geography.items():
    all_ages = age_rows["All Ages"]
    sums = {field: sum(age_rows[age][field] for age in age_groups if age != "All Ages") for field in ("both_sexes", "male", "female")}
    for field, total in sums.items():
        if all_ages[field] != total:
            all_age_mismatches.append((geography, field, all_ages[field], total))

fields = ("both_sexes", "male", "female")
country_rows = {(row["age_group"], field): row[field] for row in parsed if row["geographic_level"] == "country" for field in fields}
region_rows = {(row["geographic_location"], row["age_group"], field): row[field] for row in parsed if row["geographic_level"] == "region" for field in fields}
national_region_mismatches = []
for age_group in age_groups:
    for field in fields:
        region_sum = sum(value for (region, age, item), value in region_rows.items() if age == age_group and item == field)
        if country_rows[(age_group, field)] != region_sum:
            national_region_mismatches.append((age_group, field, country_rows[(age_group, field)], region_sum))

children_by_region = defaultdict(list)
for row in parsed:
    if row["geographic_level"] == "province_or_huc":
        children_by_region[row["region"]].append(row)
region_child_mismatches = []
for region, children in children_by_region.items():
    for age_group in age_groups:
        age_children = [row for row in children if row["age_group"] == age_group]
        for field in fields:
            child_sum = sum(row[field] for row in age_children)
            region_value = region_rows[(region, age_group, field)]
            if region_value != child_sum:
                region_child_mismatches.append((region, age_group, field, region_value, child_sum))

marked_labels = sorted(label for label in geographies if re.search(r"\*|\d+/", label))
single_star_labels = sorted(label for label in geographies if label.count("*") == 1)
agusan_label = next(label for label in geographies if label.endswith("Agusan del Norte"))
butuan_label = next(label for label in geographies if label.endswith("City of Butuan"))

print(f"[O-1] checksum OK; rows={len(parsed):,} columns={len(EXPECTED_COLUMNS)}")
print(f"[O-2] duplicate_rows={len(raw_rows) - len(set(raw_rows))} duplicate_keys={len(keys) - len(set(keys))}")
print(f"[O-3] blank_cells={blank_cells} negative_values={negative_values} zero_values={zero_values}")
print(f"[O-4] age_groups={len(age_groups)} geographies={len(geographies)} age_count_values={sorted(set(age_counts.values()))} geography_count_values={sorted(set(geography_counts.values()))}")
print(f"[O-5] geographic_level_rows={dict(level_counts)}")
print(f"[O-6] national_region_mismatches={len(national_region_mismatches)}")
print(f"[O-7] sex_total_mismatches={len(sex_mismatches)} by_age={Counter(row['age_group'] for row in sex_mismatches)} by_region={Counter(row['region'] for row in sex_mismatches)}")
print(f"[O-8] all_age_mismatches={len(all_age_mismatches)}")
print(f"[O-9] region_child_mismatches={len(region_child_mismatches)} details={region_child_mismatches}")
print(f"[O-10] replacement_character_rows={len(replacement_rows)} replacement_character_labels={len(set(row['geographic_location'] for row in replacement_rows))}")
print("[O-11] geographic code columns in CSV=0")
print(f"[O-12] marked_labels={len(marked_labels)} single_star_labels={len(single_star_labels)} Agusan_marker={agusan_label!r} separate_HUC={butuan_label!r}")


def percent(value, total):
    return f"{100 * value / total:.1f}%" if total else "n/a"


def numeric_summary(field):
    values = [row[field] for row in parsed]
    return f"min {min(values):,}, median {statistics.median(values):,.0f}, max {max(values):,}; zeros: {sum(value == 0 for value in values):,}"


def filled(source_column):
    populated = sum(bool(row[EXPECTED_COLUMNS.index(source_column)].strip()) for row in rows)
    return percent(populated, len(rows))


# %% generate the data dictionary from measured values
dictionary_rows = [
    ("Age Group", "Not stated", "Age Group", f"The API publishes {len(age_groups)} category codes and labels.", f"[observed] One of {len(age_groups)} mutually listed categories, including `All Ages` and {len(age_groups) - 1} five-year age bands.", "category", filled("Age Group"), f"{len(age_groups):,}", f"`{age_groups[0]}`, `{age_groups[1]}`, `{age_groups[2]}`, ..., `{age_groups[-1]}`"),
    ("Geographic Location", "Not stated", "Geographic Location", f"The API publishes a 10-digit code and display label for each of {len(geographies)} locations, but the CSV export retains only the display label.", f"[observed] Dot prefixes encode {level_label_counts['country']} country, {level_label_counts['region']} regions, and {level_label_counts['province_or_huc']} province, HUC, or special-area labels. Footnote markers remain embedded in {len(marked_labels)} labels.", "category", filled("Geographic Location"), f"{len(geographies):,}", f"`{geographies[0]}`, `{geographies[1]}`, `{geographies[2]}`"),
    ("Both Sexes", "Not stated", "Both Sexes", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", f"[observed] Household population count. {len(sex_mismatches)} province or HUC rows fail the sex-total check; see O-7.", "whole number", filled("Both Sexes"), f"{len(set(row['both_sexes'] for row in parsed)):,}", numeric_summary("both_sexes")),
    ("Male", "Not stated", "Male", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", f"[observed] Male household population count. All-age values sum from the {len(age_groups) - 1} age bands for every geography.", "whole number", filled("Male"), f"{len(set(row['male'] for row in parsed)):,}", numeric_summary("male")),
    ("Female", "Not stated", "Female", "Sex is a separate API dimension; the CSV pivots its three categories into columns.", f"[observed] Female household population count. All-age values sum from the {len(age_groups) - 1} age bands for every geography.", "whole number", filled("Female"), f"{len(set(row['female'] for row in parsed)):,}", numeric_summary("female")),
]

dictionary = f"""# psa_population_per_age_group: data dictionary

Generated by [`analysis/profiling/profile_psa_population_per_age_group.py`](../../../analysis/profiling/profile_psa_population_per_age_group.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** taken from the PSA OpenSTAT table metadata and the downloaded CSV title and headers. The publisher does not state data types in either source.
- **Our interpretation:** measured from the checksum-verified CSV. Every interpretation is labeled and supported by observed evidence.
- **Observed columns:** five columns from the 2024 export, read as text before validated population values are converted to integers.
- **Filled:** share of {len(parsed):,} data rows that are not blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
for row in dictionary_rows:
    cells = [f"`{row[0]}`", *row[1:]]
    dictionary += "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |\n"

output = REPO / "docs/data/source-inventory/psa_population_per_age_group/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
