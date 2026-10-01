"""Read one sheet of an xlsx workbook with the standard library (D-007).

The profiling scripts read raw workbooks without openpyxl, so this code was copied
between scripts. It lives here once, so a fix is made once.

    from src.profiling.xlsx import read_sheet

    for row_number, cells in read_sheet(path, "PSGC"):
        cells.get(1)  # column A as text; blank cells are not in the dict
"""

import re
import xml.etree.ElementTree as ET
import zipfile

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def column_number(cell_ref):
    """Column number of a cell reference: "A1" is 1, "AB12" is 28."""
    n = 0
    for ch in re.match(r"[A-Z]+", cell_ref).group():
        n = n * 26 + ord(ch) - 64
    return n


def column_letter(n):
    """Column letters of a column number: 1 is "A", 28 is "AB"."""
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def rich_text(node):
    """Text of a shared or inline string. Skips phonetic guides (rPh), which also hold <t> elements."""
    parts = [t.text or "" for t in node.findall(M + "t")]
    for run in node.findall(M + "r"):
        parts += [t.text or "" for t in run.findall(M + "t")]
    return "".join(parts)


def sheet_names(zf):
    """Sheet names of an open workbook, in workbook order."""
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    return [s.get("name") for s in workbook.find(M + "sheets")]


def sheet_xml_path(zf, sheet_name):
    """Path inside the workbook zip of the XML for a sheet. Raises ValueError if there is no such sheet."""
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    sheet = next((s for s in workbook.find(M + "sheets") if s.get("name") == sheet_name), None)
    if sheet is None:
        raise ValueError(f"No sheet named {sheet_name!r}. Sheets in the workbook: {sheet_names(zf)}")
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))}
    target = rels[sheet.get(R + "id")].lstrip("/")
    return target if target.startswith("xl/") else "xl/" + target


def read_sheet(path, sheet_name):
    """Return a list of (row number, {column number: text}) for a sheet. Blank cells are omitted.

    Values are read as text, exactly as stored: a number cell gives its stored digits
    (leading zeros that Excel dropped stay dropped), and dates give their serial number.
    A TRUE or FALSE cell gives "1" or "0", and an error cell gives its text, such as "#N/A".

    The row and cell reference (the r attribute) is optional in the xlsx format. A row or
    cell without one counts as the one after the previous row or cell.
    """
    with zipfile.ZipFile(path) as zf:
        sheet_xml = zf.read(sheet_xml_path(zf, sheet_name))
        try:
            shared = zf.read("xl/sharedStrings.xml")
        except KeyError:  # a workbook with no text cells has no shared strings part
            strings = []
        else:
            strings = [rich_text(si) for si in ET.fromstring(shared).findall(M + "si")]

    rows = []
    row_number = 0
    for row in ET.fromstring(sheet_xml).iter(M + "row"):
        row_number = int(row.get("r", row_number + 1))
        cells = {}
        column = 0
        for c in row.findall(M + "c"):
            ref = c.get("r")
            column = column_number(ref) if ref else column + 1
            v = c.find(M + "v")
            if c.get("t") == "s" and v is not None:
                text = strings[int(v.text)]
            elif c.get("t") == "inlineStr":
                inline = c.find(M + "is")
                text = rich_text(inline) if inline is not None else ""
            else:
                text = (v.text or "") if v is not None else ""
            if text != "":
                cells[column] = text
        rows.append((row_number, cells))
    return rows
