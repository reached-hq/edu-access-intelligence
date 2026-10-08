"""Made-up PSA Poverty Stat workbooks (xlsx_sheet) for tests.

Builds a workbook shaped like `2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx` as
profiled (profile.md O-1): a title in B1, a merged header in rows 2 to 5 from
which the column names are built, data rows from row 6 that mix region banner
rows with city/municipality rows, an empty column S, and a footer that starts
with 'Notes:'. Places, IDs and numbers are invented (IDs from 99xxx); no PSA
record is copied. Written with the standard library, with fixed zip
timestamps, so the same arguments always give the same SHA-256.

The default rows carry one of each publisher quirk the contract flags, so
tests can see each WARN: a 5-digit ID, a unit with no estimates, a
'(Continued)' label, a negative lower limit, a high CV, a standard error that
disagrees with CV, Unicode names, and full-precision numbers stored as text.
"""

import copy
import hashlib
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from factories.deped_deliveries import REPO_ROOT, fake_repo, registry_entry, write_config  # noqa: F401 (re-exported)
from src.profiling.xlsx import column_letter

SOURCE = "psa_poverty_stat"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
SHEET = "2023_NoHUC_Maguindanao grouped"
WORKBOOK = "2_2023 SAE_with PSGC_noHUC_06Feb2026.xlsx"
MEASURES = ("Poverty Incidence", "Coefficient of Variation", "Standard Error")
CI = "90% Confidence Interval"
TITLE = "Annex 1. Made-up statistical table for tests"
FOOTER = [
    "Notes:",
    "1/ Made-up footnote one.",
    "2/ Made-up footnote two.",
    "3/ No estimate was generated for No Estimate Town (made up).",
    "",
    "Source: made up for tests",
]


def real_config():
    return json.loads((REPO_ROOT / "config" / "ingestion" / f"{SOURCE}.json").read_text(encoding="utf-8"))


def empty_config():
    config = copy.deepcopy(real_config())
    config["deliveries"] = []
    return config


def columns_for(years):
    """The 3 + 5 x years column names, in the publisher's order (profile, data dictionary)."""
    names = ["PSGC ID", "Region/Province", "Municipality/City"]
    for measure in MEASURES:
        names += [f"{measure} {y}" for y in years]
    for y in years:
        names += [f"{CI} Lower Limit {y}", f"{CI} Upper Limit {y}"]
    return names


def add_schema(config, name, years):
    """A schema version for another set of estimate years, laid out like v1."""
    version = copy.deepcopy(config["schema_versions"]["v1"])
    version["columns"] = columns_for(years)
    version["layout"]["width"] = len(version["columns"])
    version["layout"]["sub_row_columns"] = [1] + list(range(4 + 3 * len(years), 4 + 5 * len(years)))
    version["layout"]["ignored_columns"] = [len(version["columns"]) + 1]
    config["schema_versions"][name] = version
    return version


def header_rows(years):
    """Rows 1-5 as {row: {column: text}} and the merged ranges, so header_names() rebuilds columns_for(years)."""
    n = len(years)
    rows = {1: {2: TITLE}, 2: {1: "PSGC", 2: "Region/Province", 3: "Municipality/City"}, 4: {1: "ID"}, 5: {}}
    merges = ["B2:B5", "C2:C5"]
    col = 4
    for measure in MEASURES:
        rows[2][col] = measure
        merges.append(f"{column_letter(col)}2:{column_letter(col + n - 1)}3")
        for y in years:
            rows[5][col] = y
            col += 1
    rows[2][col] = CI
    merges.append(f"{column_letter(col)}2:{column_letter(col + 2 * n - 1)}3")
    for y in years:
        for limit in ("Lower Limit", "Upper Limit"):
            rows[4][col] = limit
            rows[5][col] = y
            col += 1
    return rows, merges


def unit(psgc_id, name, years, label="", seed=1.0, blank=False, overrides=None):
    """One city/municipality row: estimate, CV, SE and limits per year, as stored text."""
    values = {"PSGC ID": psgc_id, "Region/Province": label, "Municipality/City": name}
    for k, y in enumerate(years):
        if blank:
            continue
        pi = round(10 + seed * 3.5 + k, 4)
        cv = 12.5
        se = round(pi * cv / 100, 4)
        values[f"Poverty Incidence {y}"] = str(pi)
        values[f"Coefficient of Variation {y}"] = str(cv)
        values[f"Standard Error {y}"] = str(se)
        values[f"{CI} Lower Limit {y}"] = str(round(pi - 1.645 * se, 4))
        values[f"{CI} Upper Limit {y}"] = str(round(pi + 1.645 * se, 4))
    values.update(overrides or {})
    return values


def banner(label):
    return {"Region/Province": label}


def default_rows(years=("2018", "2021", "2023"), first_id=99101):
    """Two regions, seven units: one of each quirk the contract flags."""
    y0 = years[0]
    return [
        banner("Test Region Alpha"),
        unit(str(first_id), "Doña Test", years, label="Province of Test", seed=1),          # 5-digit ID, ñ
        unit(str(first_id + 1), "San Test (Old Town)", years, seed=2,
             overrides={f"{CI} Lower Limit {years[-1]}": "-2.4063453271442992E-2",          # negative, full precision
                        f"Poverty Incidence {years[-1]}": "0.69430000000000003"}),
        unit(str(first_id + 2), "No Estimate Town", years, blank=True),                     # no estimates, not zero
        banner("Test Region Beta"),
        unit(str(990000 + first_id % 1000 + 1), "Pañabolong", years, label="(Continued)", seed=3,  # 6-digit ID
             overrides={f"Coefficient of Variation {y0}": "25.25"}),                         # CV over 20
        unit(str(990000 + first_id % 1000 + 2), "Ciudad de Prueba", years, seed=4,
             overrides={f"Standard Error {y0}": "9.99"}),                                    # SE disagrees with CV
        unit(str(990000 + first_id % 1000 + 3), "Test City", years, seed=5),
    ]


def _cell(ref, text, strings):
    """A cell as Excel stores it: numbers as <v>, text through the shared strings table."""
    try:
        float(text)
        if text.strip() != text or text.lower() in ("nan", "inf", "-inf", "infinity"):
            raise ValueError
        return f'<c r="{ref}"><v>{escape(text)}</v></c>'
    except ValueError:
        if text not in strings:
            strings.append(text)
        return f'<c r="{ref}" t="s"><v>{strings.index(text)}</v></c>'


def workbook_bytes(years=("2018", "2021", "2023"), rows=None, footer=None, sheet=SHEET, extra_sheets=(),
                   merges=None, header=None, extra_cells=None, header_override=None, column_names=None):
    """The workbook as bytes. extra_cells: {(row, column): text} written over everything else."""
    names = column_names or columns_for(years)
    head, default_merges = header_rows(years)
    for (r, c), text in (header_override or {}).items():
        head.setdefault(r, {})[c] = text
    rows = default_rows(years) if rows is None else rows
    footer = FOOTER if footer is None else footer
    grid = {r: dict(cells) for r, cells in (header or head).items()}
    r = 6
    for values in rows:
        grid[r] = {i + 1: values[n] for i, n in enumerate(names) if values.get(n, "") != ""}
        r += 1
    for line in footer:
        grid[r] = {1: line} if line else {}
        r += 1
    last = r - 1
    for (row, col), text in (extra_cells or {}).items():
        grid.setdefault(row, {})[col] = text

    strings = []
    xml_rows = []
    for row in range(1, max(grid) + 1):
        cells = "".join(_cell(f"{column_letter(c)}{row}", t, strings) for c, t in sorted(grid.get(row, {}).items()))
        xml_rows.append(f'<row r="{row}">{cells}</row>')
    merge_list = default_merges if merges is None else merges
    merge_xml = (f'<mergeCells count="{len(merge_list)}">' + "".join(f'<mergeCell ref="{m}"/>' for m in merge_list)
                 + "</mergeCells>") if merge_list else ""
    width = len(names) + 1  # through the empty column S, as in the publisher's filter range
    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 f'<dimension ref="A1:{column_letter(width)}{last}"/><sheetData>' + "".join(xml_rows)
                 + "</sheetData>" + merge_xml + "</worksheet>")
    shared = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" '
              f'uniqueCount="{len(strings)}">' + "".join(f"<si><t>{escape(s)}</t></si>" for s in strings) + "</sst>")

    all_sheets = [sheet, *extra_sheets]
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(all_sheets, 1))
                + "</sheets></workbook>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                      f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(all_sheets) + 1))
            + f'<Relationship Id="rId{len(all_sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            + "</Relationships>")
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                               for i in range(1, len(all_sheets) + 1))
                     + '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                     "</Types>")
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 "</Relationships>")
    empty_sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>')
    parts = {
        "[Content_Types].xml": content_types,
        "_rels/.rels": root_rels,
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": rels,
        "xl/sharedStrings.xml": shared,
        "xl/worksheets/sheet1.xml": sheet_xml,
        **{f"xl/worksheets/sheet{i}.xml": empty_sheet for i in range(2, len(all_sheets) + 1)},
    }
    return parts


def write_workbook(path, parts=None, **kwargs):
    parts = parts if parts is not None else workbook_bytes(**kwargs)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, text.encode("utf-8") if isinstance(text, str) else text)
    return path


def approve(config, path, years=("2018", "2021", "2023"), logical_dataset="sae_city_municipal_2018_2021_2023",
            schema_version="v1", delivery_version=1, supersedes=None, rows=None, footer=None, **overrides):
    """Add an approved-delivery entry for a fixture workbook, as a reviewer would after profiling it."""
    rows = default_rows(years) if rows is None else rows
    units = sum(1 for r in rows if r.get("PSGC ID"))
    blanks = sum(1 for r in rows if not any(v for v in r.values()))
    entry = {
        "logical_dataset": logical_dataset,
        "estimate_years": sorted(years),
        "delivery_version": delivery_version,
        "supersedes": supersedes,
        "workbook": Path(path).name,
        "workbook_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "sheet": SHEET,
        "used_range": f"A1:{column_letter(len(columns_for(years)) + 1)}{5 + len(rows) + len(FOOTER if footer is None else footer)}",
        "schema_version": schema_version,
        "body_rows": {"first": 6, "last": 5 + len(rows)},
        "unit_rows": units,
        "banner_rows": len(rows) - units - blanks,
        "footer_rows": len(FOOTER if footer is None else footer),
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
    }
    if blanks:
        entry["blank_rows"] = blanks
    entry.update(overrides)
    config["deliveries"].append(entry)
    return entry
