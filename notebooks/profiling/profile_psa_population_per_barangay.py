r"""Profile all regional PSA 2024 population-by-barangay workbooks.

Run in PowerShell with:
    $env:RAW_DATA_DIR = "C:\path\to\raw-data"
    python notebooks\profiling\profile_psa_population_per_barangay.py
"""

import hashlib
import os
import re
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import duckdb


# %% setup
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from src.profiling.xlsx import read_sheet


FILES = {
    "NCR_2.xlsx": ("NCR", "9a336a2548ac3b41a84fa982a5915d8d1d0d467669449e2257e602130e97d773"),
    "CAR_0.xlsx": ("CAR", "dea26637d31269e6de78b41823af0485443c8de3d0d66168d16b6becba9057a2"),
    "Region I_1.xlsx": ("Region I", "0e08d47b19f719f91354a7d021aebea0fa87fbc6b45eb4e1558b42e070bd0944"),
    "Region II_1.xlsx": ("Region II", "bcc8f0608d5f88ce464fb20db1bbb9c266fd0c309dece6bb646ac74a8bdbd314"),
    "Region III_1.xlsx": ("Region III", "e159e508be3bfce8e655f81b63a83513dfb7a0b8de7b7f64a0d96ccca4b82afc"),
    "CALABARZON_0.xlsx": ("CALABARZON", "463dd9f7b5c72ddc57dca2080940b740b56af04d5b98ce43560480f8c517cde3"),
    "MIMAROPA_1.xlsx": ("MIMAROPA", "2c310dce1199ef06f9c82e9391a0ea0674ceea54568c8beea0ecc963ec5e4aad"),
    "Region V_1.xlsx": ("Region V", "bfaff9fd7303c9c8ed694313293712b947c844cbdc35b23917d0c11f23bedddd"),
    "Region VI_1.xlsx": ("Region VI", "55364452f3329ca73b8eb6afb32a49ba5910eea8f47a1f7d10bd09bf83479958"),
    "Region VII_1.xlsx": ("Region VII", "5d139e888b98152a04e3d4c09c113d3b858a8bc5449f11c238e4906817e029b4"),
    "Region VIII_0.xlsx": ("Region VIII", "0c7d1cf30fe54b30f2b4a34cdde049bb87ff8999a65bf5c8163ad11207bffd8d"),
    "NIR_0.xlsx": ("NIR", "2e68254acb31e46b374cdf5dfca6dac405d86911ab759938383d7378d53cb4dd"),
    "Region IX_1.xlsx": ("Region IX", "bd54fbdc780b8c530b41b78fe56fc28b5e9a61d478498e420320f5a5b81eec15"),
    "Region X_0.xlsx": ("Region X", "e45d6ad39666353e2b31563483fb7da33d8e027f1ba89f16adf73c5a36b593cd"),
    "Region XI_1.xlsx": ("Region XI", "b5870cfd30b134f6db0cbfe1ec57e08bdf2587ae92cb1133731d37956e51efb4"),
    "Region XII_1.xlsx": ("Region XII", "7e54ed1874d1db871a6e35c0051ba7cb31ce28bf4a6c2c39e9f56efedeaf77e9"),
    "Caraga_0.xlsx": ("Caraga", "df1d4cd93d6433ca05e6ffd94fbc2f9cd3d46f3cdc964504296fea5c16eb6f8d"),
    "BARMM_1.xlsx": ("BARMM", "c7111b353ec133c7cc8cfe558f03d893b1e24a36d1bf57159cb44624752132a9"),
}
raw_dir = os.environ.get("RAW_DATA_DIR")
if not raw_dir:
    sys.exit("Set RAW_DATA_DIR to the folder that contains psa/original/.")
SOURCE_DIR = Path(raw_dir).expanduser() / "psa" / "original"

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workbook_sheets(path):
    with zipfile.ZipFile(path) as workbook:
        root = ET.fromstring(workbook.read("xl/workbook.xml"))
    return [(sheet.get("name"), sheet.get("state", "visible")) for sheet in root.find(MAIN + "sheets")]


def cleaned_name(value):
    return re.sub(r"\s+", " ", value).strip()


def data_rows(path, sheet):
    source_rows = list(read_sheet(path, sheet))
    numeric_row_numbers = [
        row_number for row_number, cells in source_rows
        if cells.get(2, "") and re.fullmatch(r"\d+", cells.get(4, ""))
    ]
    if not numeric_row_numbers:
        return [], []
    first_data_row = min(numeric_row_numbers)
    rows = []
    invalid_population_rows = []
    for row_number, cells in source_rows:
        name = cells.get(2, "")
        population = cells.get(4, "")
        if name and re.fullmatch(r"\d+", population):
            rows.append({"source_row": row_number, "source_name": name, "name": cleaned_name(name), "population": int(population)})
        elif name and row_number >= first_data_row:
            invalid_population_rows.append((path.name, sheet, row_number, name, population))
    return rows, invalid_population_rows


def parse_sheet(path, region, sheet):
    rows, invalid_population_rows = data_rows(path, sheet)
    if not rows:
        return [], [], None, invalid_population_rows
    sheet_total = {**rows[0], "region": region, "sheet": sheet, "file": path.name}
    grouped = len(rows) > 1 and rows[1]["source_row"] - rows[0]["source_row"] > 1
    parent = sheet_total["name"]
    parent_population = sheet_total["population"]
    parents = []
    barangays = []
    previous_row = rows[0]["source_row"]
    for row in rows[1:]:
        if grouped and row["source_row"] - previous_row > 1:
            parent = row["name"]
            parent_population = row["population"]
            parents.append({**row, "region": region, "sheet": sheet, "file": path.name})
        else:
            barangays.append({
                **row,
                "region": region,
                "sheet": sheet,
                "parent_area": parent,
                "parent_population": parent_population,
                "file": path.name,
            })
        previous_row = row["source_row"]
    return parents, barangays, sheet_total, invalid_population_rows


all_parents = []
all_barangays = []
sheet_totals = []
hidden_sheets = []
file_metrics = []
invalid_population_rows = []
# %% verify and parse every workbook
for filename, (region, expected_hash) in FILES.items():
    path = SOURCE_DIR / filename
    if not path.exists():
        sys.exit(f"Missing required workbook: {path}")
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        sys.exit(f"{filename}: SHA-256 {actual_hash} does not match the inventoried file. Stop and re-inventory.")
    visible_count = 0
    region_barangays = []
    region_total = 0
    for sheet, state in workbook_sheets(path):
        if state != "visible":
            hidden_sheets.append((filename, sheet, state))
            continue
        visible_count += 1
        parents, barangays, sheet_total, invalid_rows = parse_sheet(path, region, sheet)
        invalid_population_rows.extend(invalid_rows)
        if sheet_total is None:
            continue
        all_parents.extend(parents)
        all_barangays.extend(barangays)
        sheet_totals.append(sheet_total)
        region_barangays.extend(barangays)
        region_total += sheet_total["population"]
    file_metrics.append((filename, region, path.stat().st_size, visible_count, len(region_barangays), region_total))

print(f"[O-5] named data rows with blank or non-integer population={len(invalid_population_rows)}")
if invalid_population_rows:
    print("[O-5] affected rows=", invalid_population_rows[:20])
    sys.exit("Stop: named data rows with blank or non-integer populations would otherwise be dropped.")

# %% load normalized barangay records into DuckDB
con = duckdb.connect()
con.execute("""CREATE TABLE barangays (
    region VARCHAR, source_file VARCHAR, source_sheet VARCHAR, source_row BIGINT,
    parent_area VARCHAR, barangay VARCHAR, source_name VARCHAR, total_population BIGINT
)""")
con.executemany(
    "INSERT INTO barangays VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [
        (row["region"], row["file"], row["sheet"], row["source_row"], row["parent_area"], row["name"], row["source_name"], row["population"])
        for row in all_barangays
    ],
)


def one(sql):
    return con.execute(sql).fetchone()[0]


# %% compute findings and reconciliation controls
parent_groups = {}
for row in all_barangays:
    key = (row["file"], row["sheet"], row["parent_area"])
    parent_groups.setdefault(key, []).append(row)
parent_lookup = {(row["file"], row["sheet"], row["name"]): row for row in all_parents}
for total in sheet_totals:
    key = (total["file"], total["sheet"], total["name"])
    if key not in parent_lookup:
        parent_lookup[key] = total

parent_mismatches = []
for key, children in parent_groups.items():
    expected = parent_lookup[key]["population"]
    actual = sum(row["population"] for row in children)
    if expected != actual:
        parent_mismatches.append((key, expected, actual, actual - expected))

sheet_mismatches = []
parents_by_sheet = {}
for parent in all_parents:
    parents_by_sheet.setdefault((parent["file"], parent["sheet"]), []).append(parent)
for total in sheet_totals:
    key = (total["file"], total["sheet"])
    children = parents_by_sheet.get(key)
    actual = sum(row["population"] for row in children) if children else sum(
        row["population"] for row in all_barangays if (row["file"], row["sheet"]) == key
    )
    if total["population"] != actual:
        sheet_mismatches.append((key, total["population"], actual, actual - total["population"]))

populations = [row["population"] for row in all_barangays]
trailing_names = sum(row["source_name"] != row["source_name"].rstrip() for row in all_barangays)
name_counts = Counter(row["name"] for row in all_barangays)
repeated_names = sum(count > 1 for count in name_counts.values())
rows_with_repeated_names = sum(count for count in name_counts.values() if count > 1)
duplicate_keys = one("""SELECT coalesce(sum(row_count - 1), 0) FROM (
    SELECT count(*) AS row_count FROM barangays GROUP BY region, trim(source_sheet), parent_area, barangay
)""")
duplicate_rows = one("SELECT count(*) - (SELECT count(*) FROM (SELECT DISTINCT * FROM barangays)) FROM barangays")
zero_population = one("SELECT count(*) FROM barangays WHERE total_population = 0")
national_total = sum(total["population"] for total in sheet_totals)
zero_rows = [(row["region"], row["sheet"], row["parent_area"], row["name"]) for row in all_barangays if row["population"] == 0]
largest_rows = sorted(all_barangays, key=lambda row: row["population"], reverse=True)[:5]

print(f"[O-1] files={len(FILES)} checksums verified; visible_sheets={len(sheet_totals)}")
print(f"[O-2] barangays={len(all_barangays):,} parent_areas={len(parent_groups):,} duplicate_keys={duplicate_keys} duplicate_rows={duplicate_rows}")
print(f"[O-3] hidden_sheets={len(hidden_sheets)} details={hidden_sheets}")
print(f"[O-4] parent_total_mismatches={len(parent_mismatches)} sheet_total_mismatches={len(sheet_mismatches)}")
print(f"[O-5] population_min={min(populations):,} median={statistics.median(populations):,.0f} max={max(populations):,} zeros={zero_population}")
print(f"[O-6] national_total_from_sheet_totals={national_total:,}")
print(f"[O-8] barangay_names_with_trailing_space={trailing_names:,} repeated_names={repeated_names:,} rows_with_repeated_names={rows_with_repeated_names:,}")
print(f"[O-10] zero_population_rows={zero_rows}")
print("[O-11] largest_barangays=", [(row["region"], row["sheet"], row["parent_area"], row["name"], row["population"]) for row in largest_rows])
print("[O-4] parent_mismatches=", parent_mismatches[:20])
print("[O-4] sheet_mismatches=", sheet_mismatches[:20])
print("[O-1] file_metrics=", file_metrics)


def percent(value, total):
    return f"{100 * value / total:.1f}%" if total else "n/a"


def field_metrics(field):
    filled, distinct = con.execute(
        f"SELECT count({field}), count(DISTINCT {field}) FROM barangays"
    ).fetchone()
    return percent(filled, len(all_barangays)), f"{distinct:,}"


def samples(field, count=3):
    values = [row[0] for row in con.execute(f"SELECT DISTINCT {field} FROM barangays ORDER BY {field} LIMIT {count}").fetchall()]
    return ", ".join(f"`{value}`" for value in values)


region_filled, region_distinct = field_metrics("region")
file_filled, file_distinct = field_metrics("source_file")
sheet_filled, sheet_distinct = field_metrics("source_sheet")
row_filled, row_distinct = field_metrics("source_row")
parent_filled, parent_distinct = field_metrics("parent_area")
barangay_filled, barangay_distinct = field_metrics("barangay")
population_filled, population_distinct = field_metrics("total_population")
source_row_min, source_row_max = con.execute("SELECT min(source_row), max(source_row) FROM barangays").fetchone()

# %% generate the data dictionary from measured values
dictionary_rows = [
    ("region", "Not stated", "**Not in the publisher's documentation (undocumented)**", "Derived lineage field based on the publisher's regional file grouping.", f"[observed] One of {region_distinct} regional file groups.", "category", region_filled, region_distinct, samples("region")),
    ("source_file", "Not stated", "**Not in the publisher's documentation (undocumented)**", "Derived lineage field, not an original workbook column.", "[observed] Exact workbook name received; each file checksum is verified before reading.", "category", file_filled, file_distinct, samples("source_file")),
    ("source_sheet", "Not stated", "**Not in the publisher's documentation (undocumented)**", "Derived lineage field, not an original workbook column.", "[observed] Visible worksheet containing the published row. Hidden calculation sheets are excluded and listed in profile finding O-3.", "category", sheet_filled, sheet_distinct, samples("source_sheet")),
    ("source_row", "Not stated", "**Not in the publisher's documentation (undocumented)**", "Derived lineage field, not an original workbook column.", "[observed] Original Excel row number, retained for reproducible trace-back.", "whole number", row_filled, row_distinct, f"min {source_row_min:,}, max {source_row_max:,}"),
    ("parent_area", "Not stated", "Province, City, Municipality, and Barangay", "The workbook combines geographic levels in one hierarchy column.", "[observed] Nearest published city, municipality, sub-municipality, or sheet-level parent total preceding the barangay row.", "text", parent_filled, parent_distinct, samples("parent_area")),
    ("barangay", "Not stated", "Province, City, Municipality, and Barangay", "The workbook combines geographic levels in one hierarchy column.", "[observed] A populated hierarchy row below its parent total. The parser preserves source text and uses a whitespace-normalized value for keys.", "text", barangay_filled, barangay_distinct, samples("barangay")),
    ("total_population", "Not stated", "Total Population", "Workbook title states the count is as of 01 July 2024.", f"[observed] Every barangay value is a nonnegative whole number; {zero_population} values are zero.", "whole number", population_filled, population_distinct, f"min {min(populations):,}, median {statistics.median(populations):,.0f}, max {max(populations):,}; zeros: {zero_population:,}"),
]

dictionary = """# psa_population_per_barangay: data dictionary

Generated by [`notebooks/profiling/profile_psa_population_per_barangay.py`](../../../notebooks/profiling/profile_psa_population_per_barangay.py). Do not edit by hand; rerun the script instead.

- **Description, publisher type, and publisher notes:** taken only from the regional workbooks' title, header, file grouping, and visible sheet structure. The publisher does not state data types in the files.
- **Our interpretation:** the normalized field meaning used by the profiler. Every claim is labeled **[observed]** because it is measured from the delivered workbooks.
- **Observed columns:** the workbooks publish one hierarchy column and one population column. The remaining fields below are derived lineage fields needed to make one barangay-level table reproducible.
- **Filled:** share of the normalized barangay records populated after parsing all visible published sheets.

See [profile.md](profile.md) for findings and [README.md](README.md) for the source card.

| Column | Publisher type | Description (publisher) | Publisher notes | Our interpretation | Observed kind | Filled | Distinct | Samples or range |
|---|---|---|---|---|---|---|---|---|
"""
dictionary_lines = []
for row in dictionary_rows:
    cells = [f"`{row[0]}`", *row[1:]]
    dictionary_lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
dictionary += "\n".join(dictionary_lines) + "\n"

output = REPO / "docs/source_inventory/psa_population_per_barangay/data_dictionary.md"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(dictionary, encoding="utf-8")
print(f"wrote {output}")
