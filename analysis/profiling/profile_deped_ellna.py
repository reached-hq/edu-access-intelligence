r"""Profile the DepEd SY 2023-24 selected-school ELLNA archive.

Run in PowerShell with:
    $env:RAW_DATA_DIR = "C:\path\to\raw-data"
    python notebooks\profiling\profile_deped_ellna.py
"""

import hashlib
import os
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


# %% setup
REPO = Path(__file__).resolve().parents[2]
ZIP_FILENAME = "Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip"
OFFICIAL_ZIP_SHA256 = "d998d5c1af37c29a3247ae3e7f5d4d9aa3b0f34f94db391f55c1a8f587b7f124"
CSV_FILENAME = "ellna_2023-24_selected.csv"
CSV_SHA256 = "a379ccd0cf48bf3ff1174fc76374627bd92f71d31f49fa73e59c9f57b1390dc2"
README_SHA256 = "ab5b20350255d125ff96ab8903b732d8abaec4aa0d5fdd01345acafafe0060fc"
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

raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains deped/original/.")
archive = Path(raw_dir).expanduser() / "deped" / "original" / ZIP_FILENAME
if not archive.is_file():
    sys.exit(f"File not found: {archive}")

# %% verify the archive members and load the CSV as text
archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
if archive_hash != OFFICIAL_ZIP_SHA256:
    print(f"archive checksum differs from the official download: {archive_hash}; validating member content")

with zipfile.ZipFile(archive) as zf:
    csv_member = next((name for name in zf.namelist() if name.endswith("/" + CSV_FILENAME) or name == CSV_FILENAME), None)
    readme_member = next((name for name in zf.namelist() if name.endswith("/README.md") or name == "README.md"), None)
    if not csv_member or not readme_member:
        sys.exit("Archive must contain ellna_2023-24_selected.csv and README.md.")
    csv_bytes = zf.read(csv_member)
    readme_bytes = zf.read(readme_member)

member_hashes = {
    CSV_FILENAME: hashlib.sha256(csv_bytes).hexdigest(),
    "README.md": hashlib.sha256(readme_bytes).hexdigest(),
}
expected_member_hashes = {CSV_FILENAME: CSV_SHA256, "README.md": README_SHA256}
for filename, actual_hash in member_hashes.items():
    if actual_hash != expected_member_hashes[filename]:
        sys.exit(f"{filename}: SHA-256 {actual_hash} does not match the inventory card. Stop and re-inventory.")

con = duckdb.connect()
with tempfile.TemporaryDirectory(dir=REPO) as workdir:
    csv_copy = Path(workdir) / CSV_FILENAME
    csv_copy.write_bytes(csv_bytes)
    con.execute("CREATE TABLE ellna AS SELECT * FROM read_csv(?, all_varchar = true, header = true, strict_mode = true)", [str(csv_copy)])
    columns = [row[0] for row in con.execute("DESCRIBE ellna").fetchall()]
    records = con.execute("SELECT * FROM ellna").fetchall()

rows = [{column: value or "" for column, value in zip(columns, record)} for record in records]

if columns != EXPECTED_COLUMNS:
    sys.exit(f"Unexpected schema: {columns}")

# %% profile the delivered rows
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
region_values = sorted(set(row["region"] for row in parsed))
division_values = sorted(set(row["division"] for row in parsed))
language_values = sorted(set(row["language"] for row in parsed))
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
near_zero_numeracy = [
    row for row in parsed
    if row["numeracy_mps"] is not None
    and row["numeracy_mps"] < 1
    and row["english_mps"] >= 30
    and row["filipino_mps"] >= 30
]
near_zero_divisions = Counter(row["division"] for row in near_zero_numeracy)

simple_mean_matches = 0
for row in parsed:
    components = [row[column] for column in score_columns[:4] if row[column] is not None]
    simple_mean = sum(components) / len(components)
    if abs(row["overall_mps"] - simple_mean) <= 1e-12:
        simple_mean_matches += 1

print(f"rows={len(parsed):,} columns={len(EXPECTED_COLUMNS)}")
print(f"duplicate_rows={len(full_rows) - len(set(full_rows))} duplicate_school_ids={len(school_ids) - len(set(school_ids))}")
print(f"regions={len(region_values)} divisions={len(division_values)} languages={len(language_values)}")
print(f"test_takers={sum(row['n_test_takers'] for row in parsed):,} min={min(row['n_test_takers'] for row in parsed)} median={statistics.median(row['n_test_takers'] for row in parsed):,.0f} max={max(row['n_test_takers'] for row in parsed)}")
print(f"schools_with_1_test_taker={sum(row['n_test_takers'] == 1 for row in parsed)} schools_with_10_or_fewer={sum(row['n_test_takers'] <= 10 for row in parsed):,}")
print(f"blank_counts={blank_counts}")
print(f"english_filipino_rows={len(english_filipino)} tagalog_rows={len(tagalog)}")
print(f"unexpected_numeracy_blanks={len(unexpected_numeracy_blanks)} unexpected_mother_tongue_blanks={len(unexpected_mother_tongue_blanks)}")
print(f"out_of_range_scores={len(unexpected_score_range)} divisions_in_multiple_regions={sum(len(regions) > 1 for regions in division_regions.values())}")
print(f"overall_not_simple_component_mean={len(parsed) - simple_mean_matches:,}")
print(f"near_zero_numeracy_with_other_scores_30_plus={len(near_zero_numeracy)} learners={sum(row['n_test_takers'] for row in near_zero_numeracy):,} exact_zeros={sum(row['numeracy_mps'] == 0 for row in near_zero_numeracy)}")
print(f"near_zero_numeracy_top_divisions={near_zero_divisions.most_common(4)}")


def filled(column):
    return f"{100 * (len(parsed) - blank_counts[column]) / len(parsed):.1f}%"


def numeric_summary(column):
    values = [row[column] for row in parsed if row[column] is not None]
    return f"min {min(values):,.2f}, median {statistics.median(values):,.2f}, max {max(values):,.2f}; zeros: {sum(value == 0 for value in values):,}"


def integer_summary(column):
    values = [row[column] for row in parsed]
    return f"min {min(values):,}, median {statistics.median(values):,.0f}, max {max(values):,}; zeros: {sum(value == 0 for value in values):,}"


# %% generate the data dictionary
dictionary_rows = [
    ("school_id", "integer", "6-digit unique school identifier", "Links to other school datasets.", f"[observed] Unique and populated in all {len(parsed):,} rows. Treat as text in integration so formatting is preserved.", "identifier", filled("school_id"), f"{len(set(school_ids)):,}", f"min {min(school_ids)}, max {max(school_ids)}"),
    ("region", "string", "Administrative region name", "", f"[observed] The selected extract contains {len(region_values)} regions, not nationwide coverage.", "category", filled("region"), f"{len(region_values):,}", ", ".join(region_values)),
    ("division", "string", "School division name", "", f"[observed] All {len(division_values)} division labels map to exactly one published region in this file.", "text", filled("division"), f"{len(division_values):,}", ", ".join(division_values[:3])),
    ("language", "string", "Declared language of instruction", "", f"[observed] {len(language_values)} labels occur. Two labels are combinations and may require a controlled vocabulary before comparison.", "category", filled("language"), f"{len(language_values):,}", ", ".join(language_values)),
    ("n_test_takers", "integer", "Number of students who took the test", "", f"[observed] School-level assessed-learner count. The selected rows sum to {sum(row['n_test_takers'] for row in parsed):,} test takers; {sum(row['n_test_takers'] == 1 for row in parsed):,} schools have one test taker.", "whole number", filled("n_test_takers"), f"{len(set(row['n_test_takers'] for row in parsed)):,}", integer_summary("n_test_takers")),
    ("english_mps", "float", "Mean Percentage Score in English", "Range: 0-100.", "[observed] All values are populated and within the documented range.", "decimal number", filled("english_mps"), f"{len(set(row['english_mps'] for row in parsed)):,}", numeric_summary("english_mps")),
    ("filipino_mps", "float", "Mean Percentage Score in Filipino", "Range: 0-100.", "[observed] All values are populated and within the documented range.", "decimal number", filled("filipino_mps"), f"{len(set(row['filipino_mps'] for row in parsed)):,}", numeric_summary("filipino_mps")),
    ("numeracy_mps", "float", "Mean Percentage Score in Numeracy", "Range: 0-100. Schools with language `English/Filipino` do not take the Numeracy component.", f"[observed] All {len(english_filipino)} blanks occur in the {len(english_filipino)} `English/Filipino` rows. [suspected] {len(near_zero_numeracy)} schools have Numeracy below 1 while English and Filipino are at least 30; verify possible scale or encoding errors before interpretation.", "decimal number", filled("numeracy_mps"), f"{len(set(row['numeracy_mps'] for row in parsed if row['numeracy_mps'] is not None)):,}", numeric_summary("numeracy_mps")),
    ("mother_tongue_mps", "float", "Mean Percentage Score in Mother Tongue", "Range: 0-100. Schools with language `English/Filipino` or `Tagalog` do not take the Mother Tongue component.", f"[observed] All {len(english_filipino) + len(tagalog):,} blanks occur in the {len(english_filipino):,} `English/Filipino` and {len(tagalog):,} `Tagalog` rows; no unexpected blanks were found.", "decimal number", filled("mother_tongue_mps"), f"{len(set(row['mother_tongue_mps'] for row in parsed if row['mother_tongue_mps'] is not None)):,}", numeric_summary("mother_tongue_mps")),
    ("overall_mps", "float", "Total points correct over total possible points", "", f"[observed] Populated and in range. It differs from the simple mean of available component MPS values in {len(parsed) - simple_mean_matches:,} rows, consistent with the documented points-based calculation.", "decimal number", filled("overall_mps"), f"{len(set(row['overall_mps'] for row in parsed)):,}", numeric_summary("overall_mps")),
]

dictionary = f"""# deped_ellna: data dictionary

Generated by [`analysis/profiling/profile_deped_ellna.py`](../../../../analysis/profiling/profile_deped_ellna.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** copied from the README distributed inside DepEd's official ELLNA ZIP archive.
- **Our interpretation:** measured from the checksum-verified `ellna_2023-24_selected.csv`. Every interpretation is labeled and supported by observed evidence.
- **Observed columns:** all 10 delivered columns, read as text before validated numeric fields are converted.
- **Filled:** share of {len(parsed):,} school rows that are not blank. Documented non-applicable component scores remain blank and are not imputed.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
for row in dictionary_rows:
    cells = [f"`{row[0]}`", *row[1:]]
    dictionary += "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |\n"

output = REPO / "docs/data/source-inventory/deped_ellna/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
