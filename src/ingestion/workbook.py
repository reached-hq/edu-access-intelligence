"""Checks an xlsx delivery (format `xlsx_sheet`) must pass before any of it reaches Bronze.

The PSA Poverty Stat workbook is not a plain table: one sheet holds a title, a
five-row merged header, data rows that mix city/municipality rows with region
banner rows, and a footer of notes. `prepare_workbook` turns it into rows for
Bronze, or refuses it, saying why. It never changes the file and never writes
to disk.

What it reads, and how:

- The workbook is a zip of XML parts. It is opened with the same safety checks
  as a DepEd zip (archive.list_members: no `..`, absolute paths, links,
  encryption, or size beyond the contract's limit), and any part with a
  document type declaration is refused, so no XML entity tricks are possible.
- Every cell is kept as the text stored in the file: a number cell gives its
  stored digits ('12801', '-2.4063453271442992E-2'), so no precision is lost
  or invented, and leading zeros Excel already dropped stay dropped. A blank
  cell stays '' (never 0, never NULL). Text is Unicode as stored.
- Column names are built from the merged header the way the profile built
  them (dictionary_psa_poverty.py): the group in the group row, filled across
  its merge; the sub-label row for the columns that have one; then the year.
  They must equal a schema version in the contract, or the batch stops.
- Every row of the sheet's used range goes to Bronze, so no worksheet row is
  dropped: `title` (above the header), `header`, then the body (from the
  layout's first data row to the row before the footer marker 'Notes:'),
  then `footer`. A body row is a `unit` (an identifier), a `region_banner`
  (only a label), `blank`, or `unclassified` (anything else, which fails).
  Rows are numbered by their Excel row, so a Bronze row points at the exact
  line of the sheet, and the body, units and banners are reconciled
  separately from the whole sheet.

Problems that make the file untrustworthy (unknown file, checksum, unsafe
zip, missing sheet, header drift, no footer) raise `IngestionError`. Problems
in the rows are check results: FAIL blocks the batch, WARN is recorded and the
rows still load exactly as received. The publisher's known quirks (profile
O-2 to O-9) are WARN results with the profiled count beside them, never
corrections: Bronze does not pad, clip, round, or impute anything.
"""

import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.ingestion import archive
from src.ingestion.contract import (
    delivery_file, delivery_sha256, estimate_years_of, find_delivery, match_schema, schema_fingerprint,
    years_label,
)
from src.ingestion.errors import IngestionError
from src.ingestion.validate import FAIL, PASS, WARN, CheckResult
from src.profiling.xlsx import M, R, column_letter, column_number, rich_text

REQUIRED_PARTS = ("[Content_Types].xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels")
UNIT, BANNER, BLANK, UNCLASSIFIED = "unit", "region_banner", "blank", "unclassified"
TITLE, HEADER, FOOTER = "title", "header", "footer"


# --- Opening the workbook safely ---------------------------------------------

def _xml(path, member, members):
    if member not in members:
        raise IngestionError("workbook", "corrupt_workbook", f"{Path(path).name}: part {member!r} is missing.")
    data = archive.read_member(path, member)
    # A part in UTF-16 would hide a declaration from the byte search below.
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in data[:4]:
        raise IngestionError("workbook", "unsafe_workbook", f"{Path(path).name}: part {member!r} is not UTF-8 XML.")
    if b"<!DOCTYPE" in data[:4096].upper() or b"<!ENTITY" in data.upper():
        raise IngestionError("workbook", "unsafe_workbook",
                             f"{Path(path).name}: part {member!r} declares a DTD or entities. Nothing was parsed.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise IngestionError("workbook", "corrupt_workbook", f"{Path(path).name}: part {member!r} is not valid XML ({e}).")


@dataclass
class Sheet:
    cells: dict          # {row: {column: (text, cell type)}}, blank cells omitted
    max_row: int         # highest <row> in the sheet XML, empty or not
    dimension: str       # the sheet's declared used range, e.g. 'A1:S1641' ('' if absent)
    merges: list         # [(first row, first column, last row, last column)]
    formulas: int
    errors: int


def _merge_range(ref):
    a, _, b = ref.partition(":")
    b = b or a

    def split(cell):
        m = re.match(r"([A-Z]+)([0-9]+)$", cell)
        return int(m.group(2)), column_number(m.group(1))

    (r1, c1), (r2, c2) = split(a), split(b)
    return r1, c1, r2, c2


def open_sheet(path, sheet_name, expected_sheets, max_uncompressed_bytes):
    """Read one sheet after checking the workbook is safe and has exactly the expected sheets."""
    members = set(archive.list_members(path, max_uncompressed_bytes))  # missing/corrupt/unsafe/too large
    macros = [m for m in members if Path(m).name.lower() == "vbaproject.bin"]
    if macros:
        raise IngestionError("workbook", "macro_enabled_workbook",
                             f"{Path(path).name} contains macros ({macros[0]}). Macro-enabled workbooks are not loaded.")
    for part in REQUIRED_PARTS:
        if part not in members:
            raise IngestionError("workbook", "corrupt_workbook",
                                 f"{Path(path).name} is a zip but not an xlsx workbook (no {part!r}).")
    workbook = _xml(path, "xl/workbook.xml", members)
    sheets = workbook.find(M + "sheets")
    names = [s.get("name") for s in (sheets if sheets is not None else [])]
    if sheet_name not in names:
        raise IngestionError("workbook", "missing_sheet",
                             f"{Path(path).name} has no sheet {sheet_name!r}; sheets: {names}.")
    unexpected = [n for n in names if n not in expected_sheets]
    if unexpected:
        raise IngestionError("workbook", "unexpected_sheet",
                             f"{Path(path).name} has sheet(s) {unexpected} the approved delivery does not list. "
                             "A new sheet may hold data (for example the excluded cities); profile it before loading.")
    rels = {r.get("Id"): r.get("Target") for r in _xml(path, "xl/_rels/workbook.xml.rels", members)}
    sheet = next(s for s in sheets if s.get("name") == sheet_name)
    target = (rels.get(sheet.get(R + "id")) or "").lstrip("/")
    target = target if target.startswith("xl/") else "xl/" + target
    root = _xml(path, target, members)

    strings = []
    if "xl/sharedStrings.xml" in members:
        strings = [rich_text(si) for si in _xml(path, "xl/sharedStrings.xml", members).findall(M + "si")]

    cells, formulas, errors, row_number = {}, 0, 0, 0
    for row in root.iter(M + "row"):
        row_number = int(row.get("r", row_number + 1))
        values, column = {}, 0
        for c in row.findall(M + "c"):
            ref = c.get("r")
            column = column_number(ref) if ref else column + 1
            kind = c.get("t") or "n"
            v = c.find(M + "v")
            if c.find(M + "f") is not None:
                formulas += 1
            if kind == "s" and v is not None:
                try:
                    text = strings[int(v.text)]
                except (IndexError, ValueError):
                    raise IngestionError("workbook", "corrupt_workbook",
                                         f"{Path(path).name}: cell {column_letter(column)}{row_number} points at a missing shared string.")
            elif kind == "inlineStr":
                inline = c.find(M + "is")
                text = rich_text(inline) if inline is not None else ""
            else:
                text = (v.text or "") if v is not None else ""
            if kind == "e":
                errors += 1
            if text != "":
                values[column] = (text, kind)
        if values:
            cells[row_number] = values
    max_row = max([int(r.get("r", 0)) for r in root.iter(M + "row")] + list(cells) + [0])
    dimension_node = root.find(M + "dimension")
    dimension = dimension_node.get("ref", "") if dimension_node is not None else ""
    merge_parent = root.find(M + "mergeCells")
    merges = [_merge_range(m.get("ref")) for m in (merge_parent if merge_parent is not None else [])]
    return Sheet(cells, max_row, dimension, merges, formulas, errors)


# --- The layout ---------------------------------------------------------------

def header_names(sheet, layout):
    """Column names from the merged header, built as the profile built them.

    Group row: the label at the start of a merged group, carried across the
    group (from `group_fill_from_column` on). Sub row: only for the columns in
    `sub_row_columns` (the ID, and Lower/Upper Limit). Year row: the year.
    """
    def text(row, column):
        return sheet.cells.get(row, {}).get(column, ("", ""))[0]

    names, groups, group, start = [], [], "", None
    for i in range(1, layout["width"] + 1):
        top = text(layout["group_row"], i)
        if i >= layout["group_fill_from_column"]:
            if top:
                if group:
                    groups.append((group, start, i - 1))
                group, start = top, i
            top = group
        sub = text(layout["sub_row"], i) if i in layout["sub_row_columns"] else ""
        year = text(layout["year_row"], i)
        names.append(" ".join(x for x in (top, sub, year) if x))
    if group:
        groups.append((group, start, layout["width"]))
    return names, groups


def unmerged_groups(sheet, layout, groups):
    """Header groups whose label is not on a merged range spanning the whole group."""
    row = layout["group_row"]
    bad = []
    for label, first, last in groups:
        if first == last:
            continue
        if not any(r1 <= row <= r2 and c1 <= first and c2 >= last for r1, c1, r2, c2 in sheet.merges):
            bad.append(f"{label!r} ({column_letter(first)}{row}:{column_letter(last)}{row})")
    return bad


def find_footer(sheet, layout):
    first = layout["first_data_row"]
    for row in sorted(r for r in sheet.cells if r >= first):
        if sheet.cells[row].get(1, ("", ""))[0].startswith(layout["footer_marker"]):
            return row
    raise IngestionError("layout", "footer_not_found",
                         f"no row from {first} on starts with {layout['footer_marker']!r} in column A, so the end of "
                         "the data cannot be found. The layout changed; profile the file before loading.")


def classify(values, id_index, label_index):
    if all(v == "" for v in values):
        return BLANK
    if values[id_index].strip() != "":
        return UNIT
    others = [v for i, v in enumerate(values) if i not in (id_index, label_index)]
    if values[label_index].strip() != "" and all(v == "" for v in others):
        return BANNER
    return UNCLASSIFIED


# --- Known publisher issues: flagged, never corrected --------------------------

def _number(text):
    try:
        return float(text)
    except ValueError:
        return None


def _identifier_shorter_than(header, units, issue, config, layout):
    i = header.index(config["identifier_column"])
    return sum(1 for v in units if len(v[i].strip()) < issue["length"])


def _unit_rows_all_values_blank(header, units, issue, config, layout):
    start = layout["value_columns_from"] - 1
    return sum(1 for v in units if all(x == "" for x in v[start:]))


def _label_equals(header, units, issue, config, layout):
    i = header.index(issue["columns"][0])
    return sum(1 for v in units if v[i] == issue["value"])


def _number_at_most(header, units, issue, config, layout):
    idx = [header.index(c) for c in issue["columns"]]
    return sum(1 for v in units for i in idx if (n := _number(v[i])) is not None and n <= issue["limit"])


def _number_above(header, units, issue, config, layout):
    idx = [header.index(c) for c in issue["columns"]]
    return sum(1 for v in units for i in idx if (n := _number(v[i])) is not None and n > issue["limit"])


def _se_disagrees_with_cv(header, units, issue, config, layout):
    """|SE - estimate x CV / 100| > tolerance (workbook footnote 1; profile O-8)."""
    estimate, cv, se = (header.index(c) for c in issue["columns"])
    count = 0
    for v in units:
        e, c, s = _number(v[estimate]), _number(v[cv]), _number(v[se])
        if None not in (e, c, s) and abs(s - e * c / 100) > issue["tolerance"]:
            count += 1
    return count


KNOWN_ISSUE_CHECKS = {
    "identifier_shorter_than": _identifier_shorter_than,
    "unit_rows_all_values_blank": _unit_rows_all_values_blank,
    "label_equals": _label_equals,
    "number_at_most": _number_at_most,
    "number_above": _number_above,
    "se_disagrees_with_cv": _se_disagrees_with_cv,
}


# --- The prepared delivery ------------------------------------------------------

@dataclass
class PreparedWorkbook:
    source_id: str
    logical_dataset: str
    estimate_years: list
    delivery_version: int
    supersedes: str
    archive_path: str
    archive_name: str
    archive_sha256: str
    sheet: str
    schema_version: str
    schema_fingerprint: str
    header: list
    rows: list                      # [(Excel row number, values)]
    row_kinds: dict                 # {Excel row: title | header | unit | region_banner | blank | unclassified | footer}
    footer_rows: int
    checks: list = field(default_factory=list)
    school_year = None
    encoding = None

    @property
    def data_member(self):
        return self.archive_name    # the workbook is the source file

    @property
    def data_member_sha256(self):
        return self.archive_sha256

    @property
    def failed_checks(self):
        return [c for c in self.checks if c.status == FAIL]

    def kind_counts(self):
        return Counter(self.row_kinds.values())

    def provenance(self, registry_entry):
        return {
            "source_id": self.source_id,
            "source_system": registry_entry["source_system"],
            "source_url": registry_entry["acquisition"],
            "logical_dataset": self.logical_dataset,
            "estimate_years_covered": years_label(self.estimate_years),
            "delivery_version": self.delivery_version,
            "source_file": self.archive_name,
            "source_sha256": self.archive_sha256,
            "source_sheet": self.sheet,
            "schema_version": self.schema_version,
            "schema_fingerprint": self.schema_fingerprint,
        }

    def row_provenance(self, number):
        return {"source_row_kind": self.row_kinds[number]}


def used_range_last_row(delivery):
    """Last row of the approved used range: 'A1:S1641' -> 1641."""
    return int(re.search(r"([0-9]+)$", delivery["used_range"]).group(1))


def identify_workbook(config, path):
    """Return (approved delivery, workbook SHA-256), or stop if the file is not approved."""
    path = Path(path)
    if not path.is_file():
        raise IngestionError("identify", "missing_archive", f"{path} does not exist.")
    digest = archive.sha256_file(path)
    delivery = find_delivery(config, digest)
    if delivery:
        return delivery, digest
    same_name = [d for d in config["deliveries"] if delivery_file(d) == path.name]
    if same_name:
        approved = ", ".join(f"{d['logical_dataset']} v{d['delivery_version']} {delivery_sha256(d)[:12]}" for d in same_name)
        raise IngestionError("identify", "checksum_mismatch",
                             f"{path.name} has SHA-256 {digest}, which is not approved (approved: {approved}). "
                             "If the download is damaged, download it again. If PSA revised the file, profile it and "
                             "approve it as the next delivery_version with 'supersedes' set; the earlier version is kept.")
    raise IngestionError("identify", "unregistered_delivery",
                         f"{path.name} (SHA-256 {digest}) is not an approved delivery. "
                         "Profile it, then add it to the source config in a pull request.")


def peek_estimate_years(config, path):
    """Best effort, for a file that is not approved: the estimate years its header names, or None.

    Used only to label a blocked file (a changed workbook for years already
    loaded is a likely revision). Never used to load anything.
    """
    try:
        layout = next(iter(config["schema_versions"].values()))["layout"]
        members = set(archive.list_members(path, config["max_uncompressed_bytes"]))
        names = [s.get("name") for s in _xml(path, "xl/workbook.xml", members).find(M + "sheets")]
        sheet = open_sheet(path, names[0], names, config["max_uncompressed_bytes"])
        return estimate_years_of(header_names(sheet, layout)[0]) or None
    except Exception:  # noqa: BLE001 - a label, never a decision to load
        return None


def prepare_workbook(config, registry_entry, path):
    delivery, digest = identify_workbook(config, path)
    path = Path(path)
    version = config["schema_versions"][delivery["schema_version"]]
    layout = version["layout"]

    sheet = open_sheet(path, delivery["sheet"], delivery.get("expected_sheets", [delivery["sheet"]]),
                       config["max_uncompressed_bytes"])
    header, groups = header_names(sheet, layout)
    schema = match_schema(config, header)  # unknown drift stops here
    if schema != delivery["schema_version"]:
        raise IngestionError("schema", "schema_version_mismatch",
                             f"header is schema {schema}, but the approved delivery says {delivery['schema_version']}.")
    years = estimate_years_of(header)
    if years != delivery["estimate_years"]:
        raise IngestionError("schema", "estimate_years_mismatch",
                             f"the header covers estimate years {years}; the approved delivery says {delivery['estimate_years']}.")
    unmerged = unmerged_groups(sheet, layout, groups)
    if unmerged:
        raise IngestionError("layout", "unexpected_header_layout",
                             f"header group(s) {unmerged} are not merged across their columns as profiled. "
                             "The header changed; profile the file before loading.")

    footer = find_footer(sheet, layout)
    first, width = layout["first_data_row"], layout["width"]
    id_index = header.index(config["identifier_column"])
    label_index = header.index(config["label_column"])
    rows, kinds = [], {}
    for number in range(1, sheet.max_row + 1):  # the whole sheet: nothing dropped
        cells = sheet.cells.get(number, {})
        values = [cells.get(c, ("", ""))[0] for c in range(1, width + 1)]
        rows.append((number, values))
        if number < layout["group_row"]:
            kinds[number] = TITLE
        elif number < first:
            kinds[number] = HEADER
        elif number >= footer:
            kinds[number] = FOOTER
        else:
            kinds[number] = classify(values, id_index, label_index)

    prepared = PreparedWorkbook(
        source_id=config["source_id"],
        logical_dataset=delivery["logical_dataset"],
        estimate_years=years,
        delivery_version=delivery["delivery_version"],
        supersedes=delivery["supersedes"],
        archive_path=str(path),
        archive_name=path.name,
        archive_sha256=digest,
        sheet=delivery["sheet"],
        schema_version=schema,
        schema_fingerprint=schema_fingerprint(header),
        header=header,
        rows=rows,
        row_kinds=kinds,
        footer_rows=sheet.max_row - footer + 1,
    )
    prepared.checks = check_workbook(config, delivery, layout, sheet, prepared, footer)
    return prepared


def check_workbook(config, delivery, layout, sheet, prepared, footer):
    checks = []

    def add(name, ok, expected, actual, warn_only=False):
        status = PASS if ok else (WARN if warn_only else FAIL)
        checks.append(CheckResult(name, status, str(expected), str(actual)))

    counts = prepared.kind_counts()
    header = prepared.header
    body = [(n, v) for n, v in prepared.rows if layout["first_data_row"] <= n < footer]
    units = [values for number, values in body if prepared.row_kinds[number] == UNIT]
    first, last = delivery["body_rows"]["first"], delivery["body_rows"]["last"]
    width = layout["width"]

    # Layout and counts: every one must match what was profiled and approved.
    add("used_range_matches_approved", sheet.dimension == delivery["used_range"], delivery["used_range"], sheet.dimension or "(none)")
    add("row_count_nonzero", counts[UNIT] > 0, "> 0 unit rows", counts[UNIT])
    add("row_count_matches_approved", len(prepared.rows) == used_range_last_row(delivery),
        f"{used_range_last_row(delivery)} (rows 1..{used_range_last_row(delivery)})", f"{len(prepared.rows)} (rows 1..{sheet.max_row})")
    add("body_rows_match_approved", len(body) == last - first + 1, f"{last - first + 1} (rows {first}..{last})",
        f"{len(body)} (rows {first}..{footer - 1})")
    add("unit_rows_match_approved", counts[UNIT] == delivery["unit_rows"], delivery["unit_rows"], counts[UNIT])
    add("region_banner_rows_match_approved", counts[BANNER] == delivery["banner_rows"], delivery["banner_rows"], counts[BANNER])
    add("blank_rows_match_approved", counts[BLANK] == delivery.get("blank_rows", 0), delivery.get("blank_rows", 0), counts[BLANK])
    add("unclassified_rows", counts[UNCLASSIFIED] == 0, 0, counts[UNCLASSIFIED])
    add("footer_rows_match_approved", prepared.footer_rows == delivery["footer_rows"], delivery["footer_rows"],
        f"{prepared.footer_rows} (rows {footer}..{sheet.max_row})")

    ignored = set(layout["ignored_columns"])
    in_ignored = sum(1 for r, cells in sheet.cells.items() if r < footer for c in cells if c in ignored)
    outside = sum(1 for r, cells in sheet.cells.items() if r < footer for c in cells if c > width and c not in ignored)
    letters = ",".join(column_letter(c) for c in sorted(ignored)) or "none"
    add("ignored_columns_empty", in_ignored == 0, f"0 values in column(s) {letters}", in_ignored)
    add("no_cells_outside_layout", outside == 0, f"0 values right of column {column_letter(width)}", outside)

    missing = [c for c in config["required_columns"] if c not in header]
    add("required_columns_present", not missing, config["required_columns"], f"missing {missing}" if missing else "all present")

    # The identifier: required and well formed on unit rows. Region banners are exempt.
    key = config["identifier_column"]
    i = header.index(key)
    pattern = re.compile(config["identifier_pattern"])
    malformed = sum(1 for v in units if not pattern.fullmatch(v[i]))
    repeated = sum(n - 1 for n in Counter(v[i] for v in units).values() if n > 1)
    duplicate_rows = len(body) - len({tuple(v) for _, v in body if any(v)})
    duplicate_rows -= sum(1 for _, v in body if not any(v))  # blank rows are counted by their own check
    add(f"{key}_format_on_unit_rows", malformed == 0, f"0 not matching {config['identifier_pattern']}", malformed)
    add(f"{key}_unique_in_file", repeated == 0, 0, repeated, warn_only=True)
    add("duplicate_rows_in_file", duplicate_rows == 0, 0, duplicate_rows, warn_only=True)

    # Cell-level signals, recorded and loaded as received.
    start = layout["value_columns_from"] - 1
    non_numeric = sum(1 for v in units for x in v[start:] if x != "" and _number(x) is None)
    add("non_numeric_estimate_values", non_numeric == 0, 0, non_numeric, warn_only=True)
    add("formula_cells", sheet.formulas == 0, 0, sheet.formulas, warn_only=True)
    add("error_cells", sheet.errors == 0, 0, sheet.errors, warn_only=True)

    # Known publisher issues: WARN with the profiled count, so a change in the count is visible.
    # A check about columns this workbook does not have (another year's CV, say) does not apply.
    for issue in config["known_issues"]:
        if any(c not in header for c in issue.get("columns", [])):
            continue
        n = KNOWN_ISSUE_CHECKS[issue["check"]](header, units, issue, config, layout)
        add(f"known_issue_{issue['name']}", n == 0, f"0 (profiled: {issue['profiled']}, {issue['finding']})", n, warn_only=True)
    return checks
