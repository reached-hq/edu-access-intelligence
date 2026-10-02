"""Profile DepEd personnel data and generate its source data dictionary.

Run with:
    DEPED_PERSONNEL_DIR=/path/to/School-Personnel-in-SY-2023-2024 python notebooks/profiling/profile_deped_personnel.py
"""

import csv
import hashlib
import os
import re
import sys
from collections import Counter
from pathlib import Path


SOURCE_SHA256 = "5d0dd4a244fc13401787d32f84f21ab5af295bf808f037a3f762efff7d6ed6c5"
README_SHA256 = "e2aecfdb0a94d748e75d9d3b2846012185ba68533be0ce66b964bd7ae81afb93"
REPO = Path(__file__).resolve().parents[2]
source_dir = os.environ.get("DEPED_PERSONNEL_DIR")
if not source_dir:
    sys.exit("Set DEPED_PERSONNEL_DIR to the folder containing personnel_2023-24.csv and README.md.")
SOURCE_DIR = Path(source_dir).expanduser()
CSV_PATH = SOURCE_DIR / "personnel_2023-24.csv"
README_PATH = SOURCE_DIR / "README.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for path, expected in ((CSV_PATH, SOURCE_SHA256), (README_PATH, README_SHA256)):
    actual = digest(path)
    if actual != expected:
        sys.exit(f"{path.name}: SHA-256 {actual} does not match {expected}. Stop and re-inventory.")


def readme_variables(text):
    out = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|(.*)\|?\s*$", line)
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(2).rstrip("|").split("|")]
        if len(cells) >= 2:
            out[match.group(1)] = (cells[0], cells[1], cells[2] if len(cells) > 2 else "")
    return out


LEVELS = {"es": "Elementary School", "jhs": "Junior High School", "shs": "Senior High School"}
ROLES = {
    "learning_support_aide": "Learning Support Aide",
    "administrative_officer": "Administrative Officer",
    "administrative_assistant": "Administrative Assistant",
    "administrative_aide": "Administrative Aide",
    "project_development_officer": "Project Development Officer/Program Officer",
    "school_doctor": "Medical Officer/School Doctor",
    "school_dentist": "School Dentist",
    "school_nurse": "School Nurse",
    "librarian": "Librarian",
    "library_assistant": "Library Assistant/Aide",
    "guidance_counselor": "Guidance Counselor",
    "guidance_advocate": "Guidance Advocate",
    "guidance_assistant": "Guidance Assistant/Aide",
    "computer_technician": "Computer Technician/ICT Services/ICT Assistant",
}
FUNDING = {
    "sef_provincial": "Provincial SEF",
    "sef_municipal_city": "Municipal/City SEF",
    "lgu_funding": "Local Government Unit",
    "other_funding": "other sources",
}


def generated_documentation(column):
    for level, level_name in LEVELS.items():
        for role, role_name in ROLES.items():
            prefix = f"{level}_{role}_"
            if column.startswith(prefix) and column[len(prefix):] in FUNDING:
                funding = FUNDING[column[len(prefix):]]
                return "nullable integer", f"Number of {role_name} assigned to {level_name}, funded by {funding}", "Derived from DepEd's documented LEVEL_ROLE_FUNDING-SOURCE convention"
    return "", "**Not in DepEd's README (undocumented)**", ""


def applicable(column, row):
    if column.startswith("shs_"):
        return row["offers_shs"] == "True"
    if column.startswith("jhs_"):
        return row["offers_jhs"] == "True"
    if column.startswith(("es_", "kinder_")):
        return row["offers_es"] == "True"
    return True


def whole_number(value):
    return bool(re.fullmatch(r"-?\d+(?:\.0+)?", value.strip()))


readme_text = README_PATH.read_text(encoding="utf-8")
documentation = readme_variables(readme_text)
with CSV_PATH.open(encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    columns = reader.fieldnames
    counts = {column: Counter() for column in columns}
    applicable_rows = Counter()
    applicable_filled = Counter()
    rows = []
    for row in reader:
        rows.append(row)
        for column in columns:
            value = row[column].strip()
            if value:
                counts[column][value] += 1
            if applicable(column, row):
                applicable_rows[column] += 1
                if value:
                    applicable_filled[column] += 1

row_count = len(rows)
identifier_columns = {"school_id"}
school_columns = {"school_id", "sector", "school_management", "offers_es", "offers_jhs", "offers_shs"}
measure_columns = [column for column in columns if column not in school_columns]


def numeric_value(value):
    return int(float(value))


def describe(column):
    counter = counts[column]
    filled = sum(counter.values())
    distinct = len(counter)
    if not filled:
        return "all blank", "no values"
    if column in identifier_columns and distinct == filled and all(whole_number(value) for value in counter):
        return "identifier (unique)", ", ".join(f"`{value}`" for value in sorted(counter)[:3])
    if all(whole_number(value) for value in counter):
        numbers = sorted((numeric_value(value), count) for value, count in counter.items())
        middle = (filled - 1) // 2
        cumulative = 0
        median = numbers[0][0]
        for number, count in numbers:
            cumulative += count
            if cumulative > middle:
                median = number
                break
        zeros = sum(count for value, count in counter.items() if numeric_value(value) == 0)
        return "whole number", f"min {numbers[0][0]:,}, median {median:,}, max {numbers[-1][0]:,}; zeros: {zeros:,}"
    if set(counter) <= {"True", "False"}:
        return "yes/no", ", ".join(f"`{value}` {count:,}" for value, count in counter.most_common())
    if distinct <= 20:
        return "category", ", ".join(f"`{value}` {count:,}" for value, count in counter.most_common())
    return "text", "most common: " + ", ".join(f"`{value}` {count:,}" for value, count in counter.most_common(3))


def md_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


dictionary_rows = []
for column in columns:
    deped_type, description, notes = documentation.get(column, generated_documentation(column))
    kind, sample = describe(column)
    filled = sum(counts[column].values())
    filled_pct = 100 * filled / row_count
    app_total = applicable_rows[column]
    app_pct = 100 * applicable_filled[column] / app_total if app_total else 0
    interpretation = ""
    if column not in school_columns:
        level = "shs" if column.startswith("shs_") else "jhs" if column.startswith("jhs_") else "es" if column.startswith(("es_", "kinder_")) else None
        if level:
            outside = sum(1 for row in rows if not applicable(column, row) and row[column].strip())
            interpretation = f"[observed] Applicability tested against `offers_{level}`; {outside:,} filled values occur outside that level. Blank remains ambiguous between zero and unavailable per DepEd's note."
    dictionary_rows.append(
        f"| `{column}` | {md_cell(deped_type)} | {md_cell(description)} | {md_cell(notes)} | {md_cell(interpretation)} | {kind} | {filled_pct:.1f}% | {app_pct:.1f}% | {len(counts[column]):,} | {sample} |"
    )

dictionary = """# deped_personnel: data dictionary

Generated by [`notebooks/profiling/profile_deped_personnel.py`](../../../notebooks/profiling/profile_deped_personnel.py). Do not edit by hand; rerun the script instead.

- **Description, DepEd type, and DepEd notes:** copied from DepEd's supplied `README.md`. Descriptions for the locally funded personnel fields are expanded from DepEd's documented `LEVEL_ROLE_FUNDING-SOURCE` convention.
- **Source-wide publisher context:** DepEd's School Characteristics Technical Notes identifies BEIS as the source and limits these measures to personnel actually working in public schools, distinct from DBM's PSIPOP/GMIS plantilla records (pp. 1, 12).
- **Our interpretation:** measured applicability and blank-value cautions, kept separate from publisher statements.
- **Observed columns:** measured from `personnel_2023-24.csv`, read as text. "Filled" is the share of all rows that are not blank. "Filled (applicable)" uses the corresponding `offers_es`, `offers_jhs`, or `offers_shs` flag for level-specific fields.
- **Kinds:** identifier (unique whole numbers), whole number (min, median, max, zeros), yes/no, category (up to 20 values, all listed), text (the three most common values), all blank.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | DepEd type | Description (DepEd) | DepEd notes | Our interpretation | Observed kind | Filled | Filled (applicable) | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(dictionary_rows) + "\n"
output = REPO / "docs/source_inventory/deped_personnel/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")

duplicate_ids = row_count - len(counts["school_id"])
duplicate_rows = row_count - len({tuple(row[column] for column in columns) for row in rows})
invalid_ids = sum(count for value, count in counts["school_id"].items() if not re.fullmatch(r"\d{6}", value))
non_numeric = sum(count for column in measure_columns for value, count in counts[column].items() if not whole_number(value))
negative = sum(count for column in measure_columns for value, count in counts[column].items() if whole_number(value) and numeric_value(value) < 0)
all_blank = [column for column in measure_columns if not counts[column]]
outside_level = {}
for level in LEVELS:
    level_columns = [column for column in measure_columns if column.startswith(level + "_")]
    outside_level[level] = sum(1 for row in rows for column in level_columns if row[f"offers_{level}"] != "True" and row[column].strip())
measure_cells = row_count * len(measure_columns)
filled_measure_cells = sum(sum(counts[column].values()) for column in measure_columns)
zero_measure_cells = sum(count for column in measure_columns for value, count in counts[column].items() if whole_number(value) and numeric_value(value) == 0)
nonzero_measure_cells = filled_measure_cells - zero_measure_cells
rows_without_measures = Counter()
for row in rows:
    if not any(row[column].strip() for column in measure_columns):
        rows_without_measures[row["sector"]] += 1
sector_measure_coverage = {}
for sector in counts["sector"]:
    sector_rows = [row for row in rows if row["sector"] == sector]
    sector_measure_coverage[sector] = {
        "rows": len(sector_rows),
        "with_any_filled_measure": sum(any(row[column].strip() for column in measure_columns) for row in sector_rows),
        "with_any_nonzero_measure": sum(any(row[column].strip() and numeric_value(row[column]) != 0 for column in measure_columns) for row in sector_rows),
    }

principal_components = [f"shs_school_principal_{grade}" for grade in ("iv", "iii", "ii", "i")]
principal_checked = 0
principal_mismatches = 0
principal_differences = Counter()
for row in rows:
    if row["shs_total_school_principal"].strip():
        principal_checked += 1
        component_total = sum(numeric_value(row[column]) for column in principal_components if row[column].strip())
        difference = numeric_value(row["shs_total_school_principal"]) - component_total
        principal_differences[difference] += 1
        if difference:
            principal_mismatches += 1

largest_maxima = sorted(
    ((max(numeric_value(value) for value in counts[column]), column) for column in measure_columns if counts[column]),
    reverse=True,
)[:10]

readme_documented = sum(column in documentation or generated_documentation(column)[1] != "**Not in DepEd's README (undocumented)**" for column in columns)
join_metrics = "not run"
enrollment_path = os.environ.get("DEPED_ENROLLMENT_CSV")
if enrollment_path:
    with Path(enrollment_path).expanduser().open(encoding="utf-8", newline="") as handle:
        enrollment = {row["school_id"]: row for row in csv.DictReader(handle)}
    personnel = {row["school_id"]: row for row in rows}
    shared = personnel.keys() & enrollment.keys()
    identity_columns = ["sector", "school_management", "offers_es", "offers_jhs", "offers_shs"]
    join_metrics = {
        "shared": len(shared),
        "personnel_only": len(personnel.keys() - enrollment.keys()),
        "enrollment_only": len(enrollment.keys() - personnel.keys()),
        "identity_value_mismatches": {column: sum(personnel[key][column] != enrollment[key][column] for key in shared) for column in identity_columns},
    }
summary = {
    "rows": row_count,
    "columns": len(columns),
    "duplicate_ids": duplicate_ids,
    "duplicate_rows": duplicate_rows,
    "invalid_ids": invalid_ids,
    "non_numeric_measure_cells": non_numeric,
    "negative_measure_cells": negative,
    "all_blank_columns": all_blank,
    "outside_level_filled_cells": outside_level,
    "measure_cells": measure_cells,
    "filled_measure_cells": filled_measure_cells,
    "zero_measure_cells": zero_measure_cells,
    "nonzero_measure_cells": nonzero_measure_cells,
    "rows_without_measures_by_sector": rows_without_measures,
    "sector_measure_coverage": sector_measure_coverage,
    "shs_principal_total_checked": principal_checked,
    "shs_principal_total_mismatches": principal_mismatches,
    "shs_principal_total_difference_counts": principal_differences,
    "largest_column_maxima": largest_maxima,
    "readme_documented_columns": readme_documented,
    "enrollment_join": join_metrics,
    "sectors": counts["sector"],
    "management": counts["school_management"],
}
print(summary)
print(f"wrote {output} with {len(columns)} columns")
