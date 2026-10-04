"""src/profiling/xlsx.py reads a workbook the way the profiling scripts need.

Each test builds a tiny made-up workbook in a temporary folder, so no data file
is committed.
"""

import zipfile

import pytest

from src.profiling.xlsx import column_letter, column_number, read_sheet, sheet_names, sheet_xml_path

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

SHARED_STRINGS = (
    f'<sst xmlns="{NS}">'
    "<si><t>Name</t></si>"
    '<si><r><t>San Jose</t></r><rPh sb="0" eb="3"><t>SAN HOSE</t></rPh></si>'
    "<si><t>Plain</t><rPh sb=\"0\" eb=\"1\"><t>PHONETIC</t></rPh></si>"
    "</sst>"
)

SHEET = (
    f'<worksheet xmlns="{NS}"><sheetData>'
    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1"><v>42</v></c></row>'
    '<row r="2"><c r="B2"/></row>'
    '<row r="4"><c r="B4" t="inlineStr"><is><t>inline</t><rPh sb="0" eb="1"><t>X</t></rPh></is></c>'
    '<c r="D4" t="s"><v>1</v></c><c r="E4" t="s"><v>2</v></c></row>'
    "</sheetData></worksheet>"
)


def build_xlsx(path, sheets, shared_strings=None, absolute_targets=False):
    """Write a minimal workbook. sheets is a list of (sheet name, sheet XML)."""
    prefix = "/xl/" if absolute_targets else ""
    sheet_tags = "".join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1))
    rel_tags = "".join(
        f'<Relationship Id="rId{i}" Target="{prefix}worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1)
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/workbook.xml", f'<workbook xmlns="{NS}" xmlns:r="{REL_NS}"><sheets>{sheet_tags}</sheets></workbook>')
        zf.writestr("xl/_rels/workbook.xml.rels", f"<Relationships>{rel_tags}</Relationships>")
        for i, (_, xml) in enumerate(sheets, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", xml)
        if shared_strings is not None:
            zf.writestr("xl/sharedStrings.xml", shared_strings)
    return path


@pytest.fixture
def workbook(tmp_path):
    return build_xlsx(tmp_path / "book.xlsx", [("Data", SHEET), ("Other", f'<worksheet xmlns="{NS}"><sheetData/></worksheet>')], SHARED_STRINGS)


@pytest.mark.parametrize("letters, number", [("A", 1), ("Z", 26), ("AA", 27), ("AB", 28), ("AZ", 52), ("XFD", 16384)])
def test_column_letters_and_numbers_agree(letters, number):
    assert column_number(letters) == number
    assert column_letter(number) == letters


def test_column_number_ignores_the_row_part_of_a_cell_reference():
    assert column_number("AB12") == 28


def test_column_letter_is_the_inverse_of_column_number():
    assert all(column_number(column_letter(n)) == n for n in range(1, 1000))


def test_read_sheet_keeps_row_numbers_and_skips_blank_cells(workbook):
    rows = dict(read_sheet(workbook, "Data"))
    assert list(rows) == [1, 2, 4]  # row 3 is not in the file, and row 2 is kept even though it is empty
    assert rows[1] == {1: "Name", 3: "42"}
    assert rows[2] == {}


def test_read_sheet_reads_inline_strings(workbook):
    assert dict(read_sheet(workbook, "Data"))[4][2] == "inline"


def test_read_sheet_skips_phonetic_guides(workbook):
    row = dict(read_sheet(workbook, "Data"))[4]
    assert row[4] == "San Jose"  # not "San JoseSAN HOSE"
    assert row[5] == "Plain"
    assert row[2] == "inline"


def test_read_sheet_works_without_a_shared_strings_part(tmp_path):
    sheet = f'<worksheet xmlns="{NS}"><sheetData><row r="1"><c r="B1"><v>7</v></c></row></sheetData></worksheet>'
    path = build_xlsx(tmp_path / "numbers.xlsx", [("Data", sheet)])
    assert read_sheet(path, "Data") == [(1, {2: "7"})]


def test_read_sheet_counts_position_when_a_row_or_cell_has_no_reference(tmp_path):
    sheet = (
        f'<worksheet xmlns="{NS}"><sheetData>'
        "<row><c><v>1</v></c><c><v>2</v></c></row>"
        '<row r="5"><c r="C5"><v>3</v></c><c><v>4</v></c></row>'
        "<row><c><v>5</v></c></row>"
        "</sheetData></worksheet>"
    )
    path = build_xlsx(tmp_path / "no_refs.xlsx", [("Data", sheet)])
    assert read_sheet(path, "Data") == [(1, {1: "1", 2: "2"}), (5, {3: "3", 4: "4"}), (6, {1: "5"})]


def test_read_sheet_handles_missing_cell_reference_attributes(tmp_path):
    sheet = f'<worksheet xmlns="{NS}"><sheetData><row r="1"><c><v>100</v></c><c><v>200</v></c></row></sheetData></worksheet>'
    path = build_xlsx(tmp_path / "no_r_attr.xlsx", [("Data", sheet)])
    assert read_sheet(path, "Data") == [(1, {1: "100", 2: "200"})]


def test_read_sheet_gives_booleans_and_errors_as_stored(tmp_path):
    sheet = (
        f'<worksheet xmlns="{NS}"><sheetData>'
        '<row r="1"><c r="A1" t="b"><v>1</v></c><c r="B1" t="e"><v>#N/A</v></c></row>'
        "</sheetData></worksheet>"
    )
    path = build_xlsx(tmp_path / "types.xlsx", [("Data", sheet)])
    assert read_sheet(path, "Data") == [(1, {1: "1", 2: "#N/A"})]


def test_read_sheet_names_the_available_sheets_when_the_sheet_is_missing(workbook):
    with pytest.raises(ValueError) as error:
        read_sheet(workbook, "Missing")
    assert "'Missing'" in str(error.value)
    assert "['Data', 'Other']" in str(error.value)


def test_sheet_names_are_in_workbook_order(workbook):
    with zipfile.ZipFile(workbook) as zf:
        assert sheet_names(zf) == ["Data", "Other"]


@pytest.mark.parametrize("absolute", [False, True])
def test_sheet_xml_path_handles_relative_and_absolute_targets(tmp_path, absolute):
    path = build_xlsx(tmp_path / "book.xlsx", [("Data", SHEET), ("Other", SHEET)], SHARED_STRINGS, absolute_targets=absolute)
    with zipfile.ZipFile(path) as zf:
        assert sheet_xml_path(zf, "Data") == "xl/worksheets/sheet1.xml"
        assert sheet_xml_path(zf, "Other") == "xl/worksheets/sheet2.xml"
