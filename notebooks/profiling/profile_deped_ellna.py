r"""Profile the DepEd SY 2023-24 selected-school ELLNA CSV.

Run in PowerShell with:
    $env:DEPED_ELLNA_FILE = "C:\path\to\ellna_2023-24_selected.csv"
    python notebooks\profiling\profile_deped_ellna.py
"""

import csv
import hashlib
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EXPECTED_SHA256 = "a379ccd0cf48bf3ff1174fc76374627bd92f71d31f49fa73e59c9f57b1390dc2"
EXPECTED_COLUMNS = [
    "school_id",
    "region",
    "division",
    "language",
    "n_test_takers",
    "english_mps",
    "filipino_mps",
    "numeracy_mps",
    "mother_tongue_mps",
    "overall_mps",
]

source_value = os.environ.get("DEPED_ELLNA_FILE")
if not source_value:
    sys.exit("Set DEPED_ELLNA_FILE to ellna_2023-24_selected.csv.")
source = Path(source_value).expanduser()
if not source.is_file():
    sys.exit(f"File not found: {source}")

actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
if actual_hash != EXPECTED_SHA256:
    sys.exit(f"SHA-256 {actual_hash} does not match the inventoried file. Stop and re-inventory.")

with source.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    rows = list(reader)
    columns = reader.fieldnames

if columns != EXPECTED_COLUMNS:
    sys.exit(f"Unexpected schema: {columns}")

integer_columns = ["school_id", "n_test_takers"]
score_columns = ["english_mps", "filipino_mps", "numeracy_mps", "mother_tongue_mps", "overall_mps"]
parsed = []
for source_row, row in enumerate(rows, start=2):
    parsed_row = {**row, "source_row": source_row}
    try:
        for column in integer_columns:
            parsed_row[column] = int(row[column])
        for column in score_columns:
            parsed_row[column] = float(row[column]) if row[column].strip() else None
    except ValueError:
        sys.exit(f"Row {source_row} has an invalid numeric value: {row}")
    parsed.append(parsed_row)

school_ids = [row["school_id"] for row in parsed]
full_rows = [tuple(row[column] for column in EXPECTED_COLUMNS) for row in rows]
blank_counts = {column: sum(not row[column].strip() for row in rows) for column in EXPECTED_COLUMNS}
unexpected_score_range = [
    (row["source_row"], column, row[column])
    for row in parsed
    for column in score_columns
    if row[column] is not None and not 0 <= row[column] <= 100
]
division_regions = defaultdict(set)
for row in parsed:
    division_regions[row["division"]].add(row["region"])

english_filipino = [row for row in parsed if row["language"] == "English/Filipino"]
tagalog = [row for row in parsed if row["language"] == "Tagalog"]
unexpected_numeracy_blanks = [row for row in parsed if row["numeracy_mps"] is None and row["language"] != "English/Filipino"]
unexpected_mother_tongue_blanks = [
    row for row in parsed
    if row["mother_tongue_mps"] is None and row["language"] not in {"English/Filipino", "Tagalog"}
]

simple_mean_matches = 0
for row in parsed:
    components = [row[column] for column in score_columns[:4] if row[column] is not None]
    simple_mean = sum(components) / len(components)
    if abs(row["overall_mps"] - simple_mean) <= 1e-12:
        simple_mean_matches += 1

print(f"rows={len(parsed):,} columns={len(EXPECTED_COLUMNS)}")
print(f"duplicate_rows={len(full_rows) - len(set(full_rows))} duplicate_school_ids={len(school_ids) - len(set(school_ids))}")
print(f"regions={len(set(row['region'] for row in parsed))} divisions={len(set(row['division'] for row in parsed))} languages={len(set(row['language'] for row in parsed))}")
print(f"test_takers={sum(row['n_test_takers'] for row in parsed):,} min={min(row['n_test_takers'] for row in parsed)} median={statistics.median(row['n_test_takers'] for row in parsed):,.0f} max={max(row['n_test_takers'] for row in parsed)}")
print(f"schools_with_1_test_taker={sum(row['n_test_takers'] == 1 for row in parsed)} schools_with_10_or_fewer={sum(row['n_test_takers'] <= 10 for row in parsed):,}")
print(f"blank_counts={blank_counts}")
print(f"english_filipino_rows={len(english_filipino)} tagalog_rows={len(tagalog)}")
print(f"unexpected_numeracy_blanks={len(unexpected_numeracy_blanks)} unexpected_mother_tongue_blanks={len(unexpected_mother_tongue_blanks)}")
print(f"out_of_range_scores={len(unexpected_score_range)} divisions_in_multiple_regions={sum(len(regions) > 1 for regions in division_regions.values())}")
print(f"overall_not_simple_component_mean={len(parsed) - simple_mean_matches:,}")


def filled(column):
    return f"{100 * (len(parsed) - blank_counts[column]) / len(parsed):.1f}%"


def numeric_summary(column):
    values = [row[column] for row in parsed if row[column] is not None]
    return f"min {min(values):,.2f}, median {statistics.median(values):,.2f}, max {max(values):,.2f}; zeros: {sum(value == 0 for value in values):,}"


def integer_summary(column):
    values = [row[column] for row in parsed]
    return f"min {min(values):,}, median {statistics.median(values):,.0f}, max {max(values):,}; zeros: {sum(value == 0 for value in values):,}"


dictionary_rows = [
    ("school_id", "integer", "6-digit unique school identifier", "Links to other school datasets.", "[observed] Unique and populated in all 5,752 rows. Treat as text in integration so formatting is preserved.", "identifier", filled("school_id"), f"{len(set(school_ids)):,}", f"min {min(school_ids)}, max {max(school_ids)}"),
    ("region", "string", "Administrative region name", "", "[observed] The selected extract contains 5 regions, not nationwide coverage.", "category", filled("region"), "5", ", ".join(sorted(set(row["region"] for row in parsed)))),
    ("division", "string", "School division name", "", "[observed] All 44 division labels map to exactly one published region in this file.", "text", filled("division"), "44", "Candon City, Baguio City, Leyte"),
    ("language", "string", "Declared language of instruction", "", "[observed] Nine labels occur. Two labels are combinations and may require a controlled vocabulary before comparison.", "category", filled("language"), "9", ", ".join(sorted(set(row["language"] for row in parsed)))),
    ("n_test_takers", "integer", "Number of students who took the test", "", "[observed] School-level assessed-learner count. The selected rows sum to 218,296 test takers; 26 schools have one test taker.", "whole number", filled("n_test_takers"), f"{len(set(row['n_test_takers'] for row in parsed)):,}", integer_summary("n_test_takers")),
    ("english_mps", "float", "Mean Percentage Score in English", "Range: 0-100.", "[observed] All values are populated and within the documented range.", "decimal number", filled("english_mps"), f"{len(set(row['english_mps'] for row in parsed)):,}", numeric_summary("english_mps")),
    ("filipino_mps", "float", "Mean Percentage Score in Filipino", "Range: 0-100.", "[observed] All values are populated and within the documented range.", "decimal number", filled("filipino_mps"), f"{len(set(row['filipino_mps'] for row in parsed)):,}", numeric_summary("filipino_mps")),
    ("numeracy_mps", "float", "Mean Percentage Score in Numeracy", "Range: 0-100. Schools with language `English/Filipino` do not take the Numeracy component.", "[observed] All 154 blanks occur in the 154 `English/Filipino` rows; no unexpected blanks were found.", "decimal number", filled("numeracy_mps"), f"{len(set(row['numeracy_mps'] for row in parsed if row['numeracy_mps'] is not None)):,}", numeric_summary("numeracy_mps")),
    ("mother_tongue_mps", "float", "Mean Percentage Score in Mother Tongue", "Range: 0-100. Schools with language `English/Filipino` or `Tagalog` do not take the Mother Tongue component.", "[observed] All 1,925 blanks occur in the 154 `English/Filipino` and 1,771 `Tagalog` rows; no unexpected blanks were found.", "decimal number", filled("mother_tongue_mps"), f"{len(set(row['mother_tongue_mps'] for row in parsed if row['mother_tongue_mps'] is not None)):,}", numeric_summary("mother_tongue_mps")),
    ("overall_mps", "float", "Total points correct over total possible points", "", f"[observed] Populated and in range. It differs from the simple mean of available component MPS values in {len(parsed) - simple_mean_matches:,} rows, consistent with the documented points-based calculation.", "decimal number", filled("overall_mps"), f"{len(set(row['overall_mps'] for row in parsed)):,}", numeric_summary("overall_mps")),
]

dictionary = """# deped_ellna: data dictionary

Generated by [`notebooks/profiling/profile_deped_ellna.py`](../../../notebooks/profiling/profile_deped_ellna.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** copied from the README distributed inside DepEd's official ELLNA ZIP archive.
- **Our interpretation:** measured from the checksum-verified `ellna_2023-24_selected.csv`. Every interpretation is labeled and supported by observed evidence.
- **Observed columns:** all 10 delivered columns, read as text before validated numeric fields are converted.
- **Filled:** share of 5,752 school rows that are not blank. Documented non-applicable component scores remain blank and are not imputed.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
for row in dictionary_rows:
    cells = [f"`{row[0]}`", *row[1:]]
    dictionary += "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |\n"

output = REPO / "docs/source_inventory/deped_ellna/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
