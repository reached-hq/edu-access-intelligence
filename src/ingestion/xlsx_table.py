"""Delivery format `xlsx_table`: one workbook, delivered as is, whose data is one
sheet with a single header row (PSA PSGC).

`prepare_delivery` goes from a workbook on disk to rows ready for Bronze, or
refuses it saying why. It never changes the file and never writes to disk. It
has the same shape as validate.prepare_delivery, so pipeline.py runs both alike.

| | DepEd zip (validate.py) | PSGC workbook (here) |
|---|---|---|
| Delivery | zip with one CSV and a README | the xlsx itself (an xlsx is a zip of XML parts) |
| Data | the CSV | one named sheet, header in row 1, data from row 2 |
| Period | school year, from two file names | publication quarter ('2026-Q2'), from the file name, checked against the `Metadata` sheet |
| Row number | data row, from 1 | Excel row, from 2, so a Bronze row points at one line of the sheet |
| Header | publisher names are the Bronze columns | exact publisher text (with its line breaks, and '' for an unnamed column) mapped to Bronze names in the contract |

Every sheet is opened by the shared, safe opener, workbook.open_sheet (the
same one the PSA Poverty Stat format uses): the zip checks of
archive.list_members (no '..', absolute, linked or encrypted parts; under the
contract's size limit), no macros, no XML part with a DTD, entities or a
non-UTF-8 encoding, and no sheet the contract does not list.

Every cell is kept as the text stored in the file, never as Excel displays it:

| Cell | Bronze value |
|---|---|
| text (shared, inline, or a formula's text result) | the text, exactly: trailing spaces, line breaks and Unicode kept |
| number | the stored digits, e.g. '1489', '0'. No thousands separator and no accounting format: PSGC's population format shows 0 as '-', which would be confused with the publisher's '-' text |
| error | its text, e.g. '#N/A' |
| boolean, date | the stored value ('1'/'0', a date serial) |
| empty | '' (never 0, never NULL) |

A number-stored identifier is accepted only when its stored digits already
match the identifier pattern (PSGC: exactly 10 digits). Nothing is ever padded:
a code that lost its leading zero fails the batch.

Problems that make the file untrustworthy (unknown file, checksum, unsafe
workbook, missing sheet, header drift, undeterminable or conflicting period)
raise IngestionError. Problems in the rows are check results: FAIL blocks the
batch, WARN is recorded and the rows still load exactly as received. Results
hold counts, never row values.
"""

import hashlib
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from src.ingestion import archive, workbook
from src.ingestion.errors import IngestionError
from src.ingestion.validate import FAIL, PASS, WARN, CheckResult
from src.profiling.xlsx import column_letter, column_number
from src.profiling.xlsx import sheet_names as profiling_sheet_names

# Columns the pipeline adds to every PSGC Bronze row. source_row_number is the
# Excel row (the header is row 1, so data starts at 2). The workbook is both the
# delivery and the data file, so there is no separate archive.
PROVENANCE_COLUMNS = (
    "source_id",
    "source_system",
    "source_url",
    "publication_period",
    "publication_date",
    "delivery_version",
    "source_file",
    "source_sha256",
    "source_sheet",
    "source_row_number",
    "schema_version",
    "schema_fingerprint",
    "batch_id",
    "run_id",
    "ingested_at_utc",
    "code_revision",
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
PERIOD = re.compile(r"^(?P<year>[0-9]{4})-Q(?P<quarter>[1-4])$")
ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
RANGE = re.compile(r"^A1:(?P<column>[A-Z]{1,3})(?P<row>[1-9][0-9]*)$")
BRONZE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_FORMATS = ("%d %B %Y", "%B %d, %Y", "%B %d %Y", "%d %b %Y", "%Y-%m-%d")

CONFIG_FIELDS = {
    "source_id", "format", "bronze_table", "landing_dir", "workbook_pattern", "data_sheet", "expected_sheets",
    "period_source", "max_uncompressed_bytes", "identifier_column", "identifier_pattern", "required_columns",
    "master_reference_period", "schema_versions", "quality_checks", "deliveries",
}
DELIVERY_FIELDS = {
    "publication_period", "publication_date", "delivery_version", "supersedes", "workbook", "workbook_sha256",
    "sheet", "range", "schema_version", "row_count", "retrieved_at_utc",
}


def _config_error(message):
    return IngestionError("config", "invalid_config", message)


# --- Periods -------------------------------------------------------------------

def quarter_of(day):
    return f"{day.year}-Q{(day.month - 1) // 3 + 1}"


def period_from_name(config, name):
    """'PSGC-2Q-2026-Publication-Datafile.xlsx' -> '2026-Q2'; None if the name does not match."""
    match = re.match(config["workbook_pattern"], name)
    return f"{match['year']}-Q{match['quarter']}" if match else None


def schema_fingerprint(source_headers):
    """SHA-256 of the exact header cells. JSON, because a header can itself hold a line break."""
    return hashlib.sha256(json.dumps(source_headers, ensure_ascii=False).encode("utf-8")).hexdigest()


# --- The contract ----------------------------------------------------------------

def validate_contract(config, registry_entry):
    """Refuse an xlsx_table contract that could load something ambiguous. Raises on the first problem."""
    missing = CONFIG_FIELDS - config.keys()
    if missing:
        raise _config_error(f"missing fields {sorted(missing)}.")
    if config["source_id"] != registry_entry.get("source_id"):
        raise _config_error("source_id differs from the registry entry.")
    for name in ("source_system", "acquisition"):
        if not registry_entry.get(name):
            raise _config_error(f"registry entry for {config['source_id']} has no {name!r}; provenance would be blank.")
    try:
        pattern = re.compile(config["workbook_pattern"])
        re.compile(config["identifier_pattern"])
    except re.error as e:
        raise _config_error(f"invalid pattern: {e}.")
    if not {"quarter", "year"} <= set(pattern.groupindex):
        raise _config_error("workbook_pattern must name the groups 'quarter' and 'year'.")
    if config["data_sheet"] not in config["expected_sheets"]:
        raise _config_error(f"data_sheet {config['data_sheet']!r} is not in expected_sheets.")
    if not {"sheet", "label"} <= set(config["period_source"]):
        raise _config_error("period_source must name the 'sheet' and the 'label' of the publication date.")

    versions = config["schema_versions"]
    if not versions:
        raise _config_error("no schema versions.")
    for name, version in versions.items():
        columns, headers = version.get("columns") or [], version.get("source_headers")
        if not columns:
            raise _config_error(f"schema {name} has no columns.")
        if not isinstance(headers, list) or len(headers) != len(columns):
            raise _config_error(f"schema {name}: source_headers must list the exact header cell of every column.")
        if len(set(columns)) != len(columns):
            raise _config_error(f"schema {name} repeats a column name.")
        bad = [c for c in columns if not BRONZE_NAME.match(c)]
        if bad:
            raise _config_error(f"schema {name}: Bronze column names must be snake_case: {bad}.")
        clash = sorted(set(columns) & set(PROVENANCE_COLUMNS))
        if clash:
            raise _config_error(f"schema {name} has publisher columns named like provenance fields: {clash}.")
        absent = [c for c in config["required_columns"] + [config["identifier_column"]] if c not in columns]
        if absent:
            raise _config_error(f"schema {name} lacks required column(s) {absent}.")
    fingerprints = [schema_fingerprint(v["source_headers"]) for v in versions.values()]
    if len(set(fingerprints)) != len(fingerprints):
        raise _config_error("two schema versions have identical source headers.")

    known_columns = {c for v in versions.values() for c in v["columns"]}
    for check in config["quality_checks"]:
        label = f"quality check {check.get('name')!r}"
        for key in ("name", "check", "column", "profiled", "finding"):
            if key not in check:
                raise _config_error(f"{label} is missing {key!r}.")
        if check["check"] not in QUALITY_CHECKS:
            raise _config_error(f"{label}: check {check['check']!r} is not one of {sorted(QUALITY_CHECKS)}.")
        if check["column"] not in known_columns:
            raise _config_error(f"{label} names unknown column {check['column']!r}.")
    for block, keys in (("national_summary", ("sheet", "total_row_label", "level_labels", "population_label_prefix")),
                        ("hierarchy", ("level_column", "population_column", "levels"))):
        if block in config and not set(keys) <= set(config[block]):
            raise _config_error(f"{block} must name {list(keys)}.")

    seen_sha, seen_version, by_period = set(), set(), {}
    for d in config["deliveries"]:
        label = f"delivery {d.get('workbook')!r}"
        missing = DELIVERY_FIELDS - d.keys()
        if missing:
            raise _config_error(f"{label} is missing {sorted(missing)}.")
        if not SHA256.match(str(d["workbook_sha256"])):
            raise _config_error(f"{label}: workbook_sha256 is not a lowercase SHA-256.")
        if not PERIOD.match(str(d["publication_period"])):
            raise _config_error(f"{label}: publication_period {d['publication_period']!r} is not like '2026-Q2'.")
        named = period_from_name(config, d["workbook"])
        if named is None:
            raise _config_error(f"{label}: name does not match workbook_pattern, so it would not be discovered.")
        if named != d["publication_period"]:
            raise _config_error(f"{label}: the file name says {named}, the delivery says {d['publication_period']}.")
        if not ISO_DATE.match(str(d["publication_date"])) or \
                quarter_of(date.fromisoformat(d["publication_date"])) != d["publication_period"]:
            raise _config_error(f"{label}: publication_date must be an ISO date inside {d['publication_period']}.")
        if d["sheet"] != config["data_sheet"]:
            raise _config_error(f"{label}: sheet {d['sheet']!r} is not the contract's data_sheet {config['data_sheet']!r}.")
        if d["schema_version"] not in versions:
            raise _config_error(f"{label}: schema_version {d['schema_version']!r} is not defined.")
        if not isinstance(d["row_count"], int) or d["row_count"] <= 0:
            raise _config_error(f"{label}: row_count must be a positive whole number.")
        rng = RANGE.match(str(d["range"]))
        width = len(versions[d["schema_version"]]["columns"])
        if not rng or column_number(rng["column"]) != width or int(rng["row"]) != d["row_count"] + 1:
            raise _config_error(f"{label}: range must be 'A1:{column_letter(width)}{d['row_count'] + 1}' "
                                "(the header row plus row_count data rows, one column per schema column).")
        if d["workbook_sha256"] in seen_sha:
            raise _config_error(f"{label}: workbook_sha256 is approved twice.")
        key = (d["publication_period"], d["delivery_version"])
        if key in seen_version:
            raise _config_error(f"{label}: delivery_version {d['delivery_version']} for {d['publication_period']} is used twice.")
        seen_sha.add(d["workbook_sha256"])
        seen_version.add(key)
        by_period.setdefault(d["publication_period"], []).append(d)

    # Versions of one quarter count up from 1, and each revision names the workbook
    # it replaces: PSA re-issuing a quarter is never silently a second "v1".
    for period, deliveries in by_period.items():
        deliveries.sort(key=lambda d: d["delivery_version"])
        for i, d in enumerate(deliveries, start=1):
            if d["delivery_version"] != i:
                raise _config_error(f"{period}: delivery versions must be 1, 2, 3...; found {[x['delivery_version'] for x in deliveries]}.")
            previous = deliveries[i - 2]["workbook_sha256"] if i > 1 else None
            if d["supersedes"] != previous:
                want = f"supersedes = {previous!r}" if previous else "supersedes = null"
                raise _config_error(f"{period} version {i} must have {want}.")

    # The master reference (D-012) is a team decision written in the contract, never
    # inferred from what was loaded last: a backfilled or newer quarter cannot change it.
    master = config["master_reference_period"]
    if by_period and master not in by_period:
        raise _config_error(f"master_reference_period {master!r} is not an approved publication_period.")
    if not by_period and master is not None:
        raise _config_error("master_reference_period must be null while no delivery is approved.")


# --- Reading the workbook: through the shared, safe opener (workbook.open_sheet) ---

def open_sheet(config, path, sheet_name):
    """One sheet, read by workbook.open_sheet: the zip checks, no macros, no DTDs or entities, UTF-8
    XML only, and no sheet the contract does not list. Cells are {row: {column: (text, stored type)}}."""
    return workbook.open_sheet(path, sheet_name, config["expected_sheets"], config["max_uncompressed_bytes"])


def sheet_names(path):
    """Sheet names in workbook order. Called only after open_sheet has checked the file."""
    with zipfile.ZipFile(path) as zf:
        return profiling_sheet_names(zf)


def cell_text(sheet, row, column):
    return sheet.cells.get(row, {}).get(column, ("", ""))[0]


def cell_kind(sheet, row, column):
    """'number', 'error', 'text', or 'blank', from the cell's stored type (`t`)."""
    cell = sheet.cells.get(row, {}).get(column)
    if cell is None:
        return "blank"
    return {"n": "number", "e": "error"}.get(cell[1], "text")


def last_row(sheet):
    return max(sheet.cells, default=0)


def last_column(sheet):
    return max((c for row in sheet.cells.values() for c in row), default=0)


# --- The publication period --------------------------------------------------------

def _parse_publication_date(text, kind):
    if kind == "number":  # an Excel date serial
        try:
            return date(1899, 12, 30) + timedelta(days=int(float(text)))
        except (ValueError, OverflowError):
            return None
    text = " ".join(text.split())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def read_publication_date(config, path, names):
    """The publication date on the metadata sheet: the value right of the label in column A."""
    source = config["period_source"]
    if source["sheet"] not in names:
        raise IngestionError("period", "period_undeterminable",
                             f"{Path(path).name} has no {source['sheet']!r} sheet, so its publication date cannot be checked.")
    sheet = open_sheet(config, path, source["sheet"])
    label = source["label"].strip().lower()
    for row in sorted(sheet.cells):
        if cell_text(sheet, row, 1).strip().lower() == label:
            found = _parse_publication_date(cell_text(sheet, row, 2), cell_kind(sheet, row, 2))
            if found is None:
                raise IngestionError("period", "period_undeterminable",
                                     f"{Path(path).name}: {source['sheet']!r} row {row} has {source['label']!r} but no "
                                     f"readable date ({cell_text(sheet, row, 2)!r}).")
            return found
    raise IngestionError("period", "period_undeterminable",
                         f"{Path(path).name}: no {source['label']!r} row in {source['sheet']!r}, so the quarter cannot be confirmed.")


# --- Data-quality checks: recorded, never corrections ----------------------------------

QUALITY_CHECKS = {
    "blank": lambda v, arg: v == "",
    "not_blank": lambda v, arg: v != "",
    "equals": lambda v, arg: v == arg,
    "ends_with": lambda v, arg: v.endswith(arg),
    "not_whole_number": lambda v, arg: v != "" and not re.fullmatch(r"-?[0-9]+", v),
}


def read_national_summary(config, path, names):
    """{'Prov': 82, ..., 'population': 112729484} from the workbook's own summary sheet, or (None, reason)."""
    spec = config["national_summary"]
    if spec["sheet"] not in names:
        return None, f"no {spec['sheet']!r} sheet"
    sheet = open_sheet(config, path, spec["sheet"])

    def norm(text):
        return " ".join(text.split())

    def row_texts(r):
        return {norm(text) for text, _ in sheet.cells[r].values()}

    wanted = set(spec["level_labels"].values())
    header = next((r for r in sorted(sheet.cells) if wanted <= row_texts(r)), None)
    total = next((r for r in sorted(sheet.cells) if spec["total_row_label"] in row_texts(r)), None)
    if header is None or total is None:
        return None, f"header row with {sorted(wanted)} or the {spec['total_row_label']!r} row not found"
    columns = {norm(text): col for col, (text, _) in sheet.cells[header].items()}
    population = next((col for name, col in columns.items() if name.startswith(spec["population_label_prefix"])), None)
    if population is None:
        return None, f"no column starting {spec['population_label_prefix']!r}"
    found = {level: columns[label] for level, label in spec["level_labels"].items()}
    found["population"] = population
    values = {}
    for key, col in found.items():
        text = cell_text(sheet, total, col).strip()
        if not re.fullmatch(r"[0-9]+", text):
            return None, f"{spec['total_row_label']!r} row has no whole number under {key!r}"
        values[key] = int(text)
    return values, None


def mojibake(text):
    """True if text looks like UTF-8 read as Windows-1252 ('Ã±' for 'ñ') or holds a replacement character."""
    if "�" in text:
        return True
    if "Ã" not in text and "Â" not in text:
        return False
    try:
        return text.encode("cp1252").decode("utf-8") != text
    except UnicodeError:
        return False


# --- The prepared delivery -----------------------------------------------------------

@dataclass
class PreparedWorkbook:
    source_id: str
    publication_period: str
    publication_date: str
    delivery_version: int
    supersedes: str
    archive_path: str
    archive_name: str
    archive_sha256: str
    sheet: str
    schema_version: str
    schema_fingerprint: str
    header: list                   # Bronze column names, in sheet order
    source_header: list            # the exact header cells, as the publisher wrote them
    rows: list                     # [(Excel row number, [text per column])]
    kinds: dict = field(default_factory=dict)   # {Excel row: [cell kind per column]}
    checks: list = field(default_factory=list)
    encoding = "utf-8"             # xlsx XML parts; any other encoding is refused by the opener

    @property
    def school_year(self):
        return self.publication_period   # the control tables' period column (D-019)

    @property
    def data_member(self):
        return self.archive_name         # the workbook is the data file

    @property
    def data_member_sha256(self):
        return self.archive_sha256

    @property
    def failed_checks(self):
        return [c for c in self.checks if c.status == FAIL]

    def provenance(self, registry_entry):
        return {
            "source_id": self.source_id,
            "source_system": registry_entry["source_system"],
            "source_url": registry_entry["acquisition"],
            "publication_period": self.publication_period,
            "publication_date": self.publication_date,
            "delivery_version": self.delivery_version,
            "source_file": self.archive_name,
            "source_sha256": self.archive_sha256,
            "source_sheet": self.sheet,
            "schema_version": self.schema_version,
            "schema_fingerprint": self.schema_fingerprint,
        }

    def row_provenance(self, number):
        return {}


def identify_delivery(config, path):
    """Return (approved delivery, workbook SHA-256), or stop if the file is not approved."""
    path = Path(path)
    if not path.is_file():
        raise IngestionError("identify", "missing_archive",
                             f"{path} does not exist. Upload the approved workbook to raw storage, then run again.")
    digest = archive.sha256_file(path)
    delivery = next((d for d in config["deliveries"] if d["workbook_sha256"] == digest), None)
    if delivery:
        return delivery, digest
    same_name = [d for d in config["deliveries"] if d["workbook"] == path.name]
    if same_name:
        approved = ", ".join(f"{d['publication_period']} v{d['delivery_version']} {d['workbook_sha256'][:12]}" for d in same_name)
        raise IngestionError("identify", "checksum_mismatch",
                             f"{path.name} has SHA-256 {digest}, which is not approved (approved: {approved}). "
                             "If the download is damaged, download it again. If PSA re-issued the quarter, profile it "
                             "and approve it as the next delivery_version with 'supersedes' set; the earlier version is kept.")
    raise IngestionError("identify", "unregistered_delivery",
                         f"{path.name} (SHA-256 {digest}) is not an approved delivery. "
                         "Profile it, then add it to the source config in a pull request.")


def match_header(config, header, approved_version):
    """Return the schema version whose exact source headers equal the header, or stop on drift."""
    for name, version in config["schema_versions"].items():
        if header == version["source_headers"]:
            if name != approved_version:
                raise IngestionError("schema", "schema_version_mismatch",
                                     f"header is schema {name}, but the approved delivery says {approved_version}.")
            return name
    known = config["schema_versions"][approved_version]["source_headers"]
    width = max(len(known), len(header))
    changed = [f"{column_letter(i + 1)}: expected {known[i] if i < len(known) else '(none)'!r}, "
               f"found {header[i] if i < len(header) else '(none)'!r}"
               for i in range(width)
               if (known[i] if i < len(known) else None) != (header[i] if i < len(header) else None)]
    raise IngestionError("schema", "unknown_schema_drift",
                         f"header matches no schema version ({'; '.join(changed)}). If the change is real "
                         "(for example a new DOF order in the income header), add a schema version to the "
                         "contract in a pull request; nothing is loaded until then.")


def prepare_delivery(config, registry_entry, path):
    delivery, digest = identify_delivery(config, path)
    path = Path(path)
    sheet = open_sheet(config, path, delivery["sheet"])  # safety checks, missing_sheet, unexpected_sheet
    if not sheet.cells:
        raise IngestionError("parse", "empty_sheet", f"{path.name}: sheet {delivery['sheet']!r} has no cells, not even a header.")
    names = sheet_names(path)

    # The quarter: from the name, from the Metadata sheet, and in the approval. All three must agree.
    named = period_from_name(config, path.name)
    if named is None:
        raise IngestionError("period", "period_undeterminable",
                             f"{path.name} does not match {config['workbook_pattern']!r}, so its quarter is unknown.")
    published = read_publication_date(config, path, names)
    if quarter_of(published) != named:
        raise IngestionError("period", "period_mismatch",
                             f"the file name says {named} but {config['period_source']['sheet']!r} gives publication "
                             f"date {published.isoformat()} ({quarter_of(published)}). Check the file before loading.")
    if named != delivery["publication_period"] or published.isoformat() != delivery["publication_date"]:
        raise IngestionError("period", "period_mismatch",
                             f"the workbook is {named}, published {published.isoformat()}; the approved delivery says "
                             f"{delivery['publication_period']}, published {delivery['publication_date']}.")

    # The header: every cell of row 1, exactly as stored, to the last column used in that row.
    version = config["schema_versions"][delivery["schema_version"]]
    width = max(len(version["columns"]), max(sheet.cells.get(1, {}), default=0))
    header = [cell_text(sheet, 1, c) for c in range(1, width + 1)]
    schema = match_header(config, header, delivery["schema_version"])
    columns = version["columns"]

    rows, kinds = [], {}
    for number in range(2, last_row(sheet) + 1):   # every row up to the last one holding a value, blanks kept
        rows.append((number, [cell_text(sheet, number, c) for c in range(1, len(columns) + 1)]))
        kinds[number] = [cell_kind(sheet, number, c) for c in range(1, len(columns) + 1)]

    prepared = PreparedWorkbook(
        source_id=config["source_id"],
        publication_period=named,
        publication_date=published.isoformat(),
        delivery_version=delivery["delivery_version"],
        supersedes=delivery["supersedes"],
        archive_path=str(path),
        archive_name=path.name,
        archive_sha256=digest,
        sheet=delivery["sheet"],
        schema_version=schema,
        schema_fingerprint=schema_fingerprint(header),
        header=list(columns),
        source_header=header,
        rows=rows,
        kinds=kinds,
    )
    prepared.checks = check_workbook(config, delivery, path, names, sheet, prepared)
    return prepared


def check_workbook(config, delivery, path, names, sheet, prepared):
    checks = []

    def add(name, ok, expected, actual, warn_only=False):
        status = PASS if ok else (WARN if warn_only else FAIL)
        checks.append(CheckResult(name, status, str(expected), str(actual)))

    def profiled(name, count, expected, finding=None):
        """A known characteristic: PASS at its profiled count, WARN when the count changes, never FAIL."""
        expected = 0 if expected is None else expected
        label = f"{expected} (profiled{', ' + finding if finding else ''})"
        add(name, count == expected, label, count, warn_only=True)

    rows, header = prepared.rows, prepared.header
    n = len(rows)

    # Shape: exactly what was profiled and approved.
    actual_range = f"A1:{column_letter(max(last_column(sheet), len(header)))}{last_row(sheet)}"
    add("row_count_nonzero", n > 0, "> 0", n)
    add("row_count_matches_approved", n == delivery["row_count"], delivery["row_count"], n)
    add("range_matches_approved", actual_range == delivery["range"], delivery["range"], actual_range)
    missing = [c for c in config["required_columns"] if c not in header]
    add("required_columns_present", not missing, config["required_columns"], f"missing {missing}" if missing else "all present")
    # A sheet the contract does not list already stopped the batch (unexpected_sheet); a missing documentation sheet is a WARN.
    add("sheets_match_contract", names == config["expected_sheets"], config["expected_sheets"], names, warn_only=True)

    # The identifier: present, exactly the pattern as stored, never padded.
    key = config["identifier_column"]
    i = header.index(key)
    pattern = re.compile(config["identifier_pattern"])
    ids = [values[i] for _, values in rows]
    stored_as_number = [values[i] for number, values in rows if prepared.kinds[number][i] == "number"]
    add(f"{key}_not_blank", all(v != "" for v in ids), 0, sum(1 for v in ids if v == ""))
    add(f"{key}_format", all(pattern.fullmatch(v) for v in ids if v != ""),
        f"0 not matching {config['identifier_pattern']}", sum(1 for v in ids if v != "" and not pattern.fullmatch(v)))
    add(f"{key}_number_cells_match_format", all(pattern.fullmatch(v) for v in stored_as_number),
        "0 number-stored codes that lost digits", sum(1 for v in stored_as_number if not pattern.fullmatch(v)))
    profiled(f"{key}_stored_as_number", len(stored_as_number), config.get("identifier_number_cells_profiled"),
             "accepted only when the stored digits match; never padded")
    # Source duplicates are kept in Bronze and recorded; Silver stops on any (docs: Handoff to Silver).
    add(f"{key}_unique_in_file", len(set(ids)) == n, 0, sum(c - 1 for c in Counter(ids).values() if c > 1), warn_only=True)
    add("duplicate_rows_in_file", len({tuple(v) for _, v in rows}) == n, 0, n - len({tuple(v) for _, v in rows}), warn_only=True)

    # Text: Unicode as stored; text decoded twice ('Ã±' for 'ñ') means a broken file, not a name.
    texts = [v for _, values in rows for v in values] + prepared.source_header
    add("text_mojibake", not any(mojibake(t) for t in texts), 0, sum(1 for t in texts if mojibake(t)))

    # Cells: nothing is recalculated here; a formula's cached result is what is loaded.
    errors = sum(1 for number in prepared.kinds for k in prepared.kinds[number] if k == "error")
    profiled("formula_cells", sheet.formulas, 0)
    profiled("error_cells", errors, config.get("error_cells_profiled"))

    # Known publisher characteristics: PASS at the profiled count, WARN when it changes.
    for check in config["quality_checks"]:
        if check["column"] not in header:
            continue
        index = header.index(check["column"])
        count = sum(1 for _, values in rows if QUALITY_CHECKS[check["check"]](values[index], check.get("value")))
        profiled(f"dq_{check['name']}", count, check["profiled"], check["finding"])

    if "national_summary" in config and "hierarchy" in config:
        checks.extend(reconcile_with_workbook(config, delivery, path, names, prepared))
    return checks


def reconcile_with_workbook(config, delivery, path, names, prepared):
    """WARN-level checks against the workbook itself: its National Summary and the code hierarchy (profile O-4, O-5, O-10)."""
    checks = []

    def add(name, ok, expected, actual):
        checks.append(CheckResult(name, PASS if ok else WARN, str(expected), str(actual)))

    spec = config["hierarchy"]
    header = prepared.header
    code_i = header.index(config["identifier_column"])
    level_i = header.index(spec["level_column"])
    pop_i = header.index(spec["population_column"])
    levels = spec["levels"]
    units = [(values[code_i], values[level_i], values[pop_i]) for _, values in prepared.rows]
    by_level = Counter(level for _, level, _ in units)
    codes = {code for code, _, _ in units}

    summary, reason = read_national_summary(config, path, names)
    if summary is None:
        add("national_summary_readable", False, "readable", reason)
    else:
        for level in config["national_summary"]["level_labels"]:
            add(f"level_count_{level.lower()}_matches_national_summary", by_level[level] == summary[level],
                summary[level], by_level[level])
        regions = sum(int(p) for _, level, p in units if level == levels["region"] and re.fullmatch(r"[0-9]+", p))
        documented = delivery.get("documented_population_abroad", 0)
        add("region_population_reconciles_to_national", summary["population"] - regions == documented,
            f"national - regions = {documented} (documented, e.g. Notes D.2)", summary["population"] - regions)

    region, province = levels["region"], levels["province"]
    city, municipality, barangay = levels["city"], levels["municipality"], levels["barangay"]
    ncr = spec.get("no_province_region_prefix")
    orphan_bgy = sum(1 for code, level, _ in units if level == barangay and code[:7] + "000" not in codes)
    orphan_region = sum(1 for code, level, _ in units
                        if level in (province, city, municipality) and code[:2] + "0" * 8 not in codes)
    orphan_mun = sum(1 for code, level, _ in units
                     if level == municipality and code[:2] != ncr and code[:5] + "0" * 5 not in codes)
    ncr_provinces = sum(1 for code, level, _ in units if level == province and code[:2] == ncr)
    add("hierarchy_barangays_without_city_or_municipality", orphan_bgy == 0, 0, orphan_bgy)
    add("hierarchy_units_without_region", orphan_region == 0, 0, orphan_region)
    add("hierarchy_municipalities_without_province", orphan_mun == 0, 0, orphan_mun)
    if ncr:
        add("hierarchy_no_province_region_has_no_provinces", ncr_provinces == 0, 0, ncr_provinces)
    return checks
