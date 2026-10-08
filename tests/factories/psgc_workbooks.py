"""Made-up PSA PSGC workbooks (format xlsx_table) for tests.

Builds xlsx files shaped like the publisher's: six sheets (Metadata, National
Summary, Prov Sum, PSGC, Notes, Coding Structure), the PSGC header in row 1
with its two line breaks and the empty, styled J1, data from row 2. Codes and
names are invented (regions '00' and '20' do not exist); no PSGC row is copied.
Zip entries get a fixed timestamp, so the same arguments always give the same
SHA-256.

A cell in `rows` is a str (stored as a shared string), an int (stored as a
number, the way PSA stores 84 codes and every population), ("error", text) for
an error cell such as '#N/A', ("inline", text) for an inline string, or '' for
an empty cell.
"""

import copy
import hashlib
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from src.profiling.xlsx import column_letter

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = "psa_psgc"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SHEETS = ["Metadata", "National Summary", "Prov Sum", "PSGC", "Notes", "Coding Structure"]
QUARTER_END = {"1": "31 March", "2": "30 June", "3": "30 September", "4": "31 December"}
POPULATION_ABROAD = 7   # the made-up "Notes D.2" gap between the regions and the national total

#                code           name                      corr          level    old    class  income  u/r   pop     J                                 status
UNITS = [
    ["0000000000", "Rehiyon Sero",            "000000000", "Reg",  "",     "",    "",     "",   1000,   "1/",                              ""],
    ["0000100000", "Lalawigan ng Pagsubok",   "000100000", "Prov", "",     "",    "1st",  "",   600,    "(excluding CITY OF PAGSUBOK) ",   ""],
    ["0000101000", "Bayan ng Halimbawa",      "000101000", "Mun",  "Luma", "",    "2nd*", "",   600,    "",                                "Capital"],
    ["0000101001", "Doña Prueba",             "000101001", "Bgy",  "",     "",    "",     "R",  400,    "",                                "Pob."],
    ["0000101002", "Poblacion Test ",         "",          "Bgy",  "",     "",    "",     "-",  200,    "",                                "Pob."],
    [2000000000,   "Rehiyon Dalawampu",       "200000000", "Reg",  "",     "",    "",     "",   500,    "",                                ""],
    ["2000102000", "Lungsod ng Halimbawa",    "200102000", "City", "",     "HUC", "-",    "",   500,    "",                                ""],
    ["2000102001", "Ñañong Test",             "200102001", "Bgy",  "",     "",    "",     "U",  0,      "",                                ""],
    ["2099900000", "Special Test Area",       "",          "",     "",     "",    "",     "",   ("error", "#N/A"), "",                     ""],
]
LEVELS = {"Prov": 1, "City": 1, "Mun": 1, "Bgy": 3}
NATIONAL_POPULATION = 1000 + 500 + POPULATION_ABROAD


def real_config():
    return json.loads((REPO_ROOT / "config" / "ingestion" / f"{SOURCE}.json").read_text(encoding="utf-8"))


def registry_entry():
    registry = json.loads((REPO_ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
    return next(s for s in registry["sources"] if s["source_id"] == SOURCE)


def headers(schema_version="v1"):
    return list(real_config()["schema_versions"][schema_version]["source_headers"])


def default_rows():
    return copy.deepcopy(UNITS)


def workbook_name(period):
    year, quarter = period.split("-Q")
    return f"PSGC-{quarter}Q-{year}-Publication-Datafile.xlsx"


def quarter_end(period):
    year, quarter = period.split("-Q")
    return f"{QUARTER_END[quarter]} {year}"


class _Strings:
    def __init__(self):
        self.items, self.index = [], {}

    def add(self, text):
        if text not in self.index:
            self.index[text] = len(self.items)
            self.items.append(text)
        return self.index[text]

    def xml(self):
        body = "".join(f'<si><t xml:space="preserve">{escape(t)}</t></si>' for t in self.items)
        return f'<sst xmlns="{NS}" count="{len(self.items)}" uniqueCount="{len(self.items)}">{body}</sst>'


def _cell(ref, value, strings, styled_empty=False):
    if value == "" or value is None:
        return f'<c r="{ref}" s="1"/>' if styled_empty else ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    if isinstance(value, tuple):
        kind, text = value
        if kind == "error":
            return f'<c r="{ref}" t="e"><v>{escape(text)}</v></c>'
        if kind == "inline":
            return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
        if kind == "formula":  # a formula cell with no cached result
            return f'<c r="{ref}"><f>{escape(text)}</f></c>'
        raise ValueError(kind)
    return f'<c r="{ref}" t="s"><v>{strings.add(value)}</v></c>'


def sheet_xml(rows, strings, styled_empty_header=True):
    """rows: list of lists, row 1 first. An empty header cell is written styled, as in the real J1."""
    body = []
    for r, values in enumerate(rows, start=1):
        cells = "".join(_cell(f"{column_letter(c)}{r}", v, strings, styled_empty=(r == 1 and styled_empty_header))
                        for c, v in enumerate(values, start=1))
        body.append(f'<row r="{r}">{cells}</row>')
    return f'<worksheet xmlns="{NS}"><sheetData>{"".join(body)}</sheetData></worksheet>'


def make_workbook(folder, period="2026-Q2", rows=None, header=None, publication_date=None, sheets=None,
                  name=None, national=None, extra_parts=None, part_override=None):
    """Write a PSGC-shaped workbook into `folder` and return its path.

    publication_date: the Metadata value (text, or an int date serial); default the quarter's end.
    national: {'Prov': n, 'City': n, 'Mun': n, 'Bgy': n, 'population': n}; default consistent with UNITS.
    extra_parts / part_override: {zip path: bytes} to add or replace, for safety tests.
    """
    strings = _Strings()
    rows = default_rows() if rows is None else rows
    header = headers() if header is None else header
    national = {**LEVELS, "population": NATIONAL_POPULATION, **(national or {})}
    published = quarter_end(period) if publication_date is None else publication_date
    content = {
        "Metadata": [["Title:", "Philippine Standard Geographic Code (PSGC), made up for tests"],
                     ["Publication date:", published], ["Progress:", "Ongoing (updated quarterly)"]],
        "National Summary": [["REGION", "PROV.", "CITIES", "MUN.", "BGY.", "POPULATION\n(2024 POPCEN)"],
                             ["PHILIPPINES", national["Prov"], national["City"], national["Mun"], national["Bgy"],
                              national["population"]]],
        "Prov Sum": [["Made-up province summary"]],
        "PSGC": [header, *rows],
        "Notes": [["A. Made-up notes"]],
        "Coding Structure": [],
    }
    names = SHEETS if sheets is None else sheets
    parts = {}
    for i, sheet in enumerate(names, start=1):
        parts[f"xl/worksheets/sheet{i}.xml"] = sheet_xml(content.get(sheet, []), strings, styled_empty_header=sheet == "PSGC")
    sheet_tags = "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, start=1))
    rel_tags = "".join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(names) + 1))
    parts["[Content_Types].xml"] = '<?xml version="1.0" encoding="UTF-8"?><Types/>'
    parts["xl/workbook.xml"] = f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets>{sheet_tags}</sheets></workbook>'
    parts["xl/_rels/workbook.xml.rels"] = f"<Relationships>{rel_tags}</Relationships>"
    parts["xl/sharedStrings.xml"] = strings.xml()
    parts = {k: v.encode("utf-8") for k, v in parts.items()}
    parts.update(part_override or {})
    parts.update(extra_parts or {})

    path = Path(folder) / (name or workbook_name(period))
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member, data in parts.items():
            info = zipfile.ZipInfo(member, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return path


def approve(config, path, period="2026-Q2", row_count=None, delivery_version=1, supersedes=None,
            schema_version="v1", publication_date=None, documented_population_abroad=POPULATION_ABROAD):
    """Add an approved-delivery entry for a fixture workbook, as a reviewer would."""
    n = row_count if row_count is not None else len(UNITS)
    width = len(config["schema_versions"][schema_version]["columns"])
    year, quarter = period.split("-Q")
    end = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}[quarter]
    entry = {
        "publication_period": period,
        "publication_date": publication_date or f"{year}-{end}",
        "delivery_version": delivery_version,
        "supersedes": supersedes,
        "workbook": Path(path).name,
        "workbook_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "sheet": "PSGC",
        "range": f"A1:{column_letter(width)}{n + 1}",
        "schema_version": schema_version,
        "row_count": n,
        "documented_population_abroad": documented_population_abroad,
        "retrieved_at_utc": "2026-01-01T00:00:00Z",
    }
    config["deliveries"].append(entry)
    if config["master_reference_period"] is None:
        config["master_reference_period"] = period
    return entry


def empty_config():
    """The real contract with no approved deliveries (and so no master reference yet)."""
    config = copy.deepcopy(real_config())
    config["deliveries"] = []
    config["master_reference_period"] = None
    return config
