"""Checks a delivery must pass before any of it reaches Bronze.

`prepare_delivery` goes from an archive on disk to rows ready to load. Problems
that make the file untrustworthy (unknown file, checksum, unsafe archive,
encoding, schema drift) raise `IngestionError` and nothing is loaded. Problems
in the rows are returned as check results, so they can be written to
`data_quality_results`: FAIL blocks the batch, WARN is recorded and the rows
are still loaded exactly as received.

Source duplicates are a WARN, not a FAIL. If the publisher repeats a school,
Bronze keeps both rows as evidence and Silver decides which one counts.
Results hold counts only, never row values.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from src.ingestion import archive
from src.ingestion.contract import find_delivery, match_schema, resolve_school_year, schema_fingerprint
from src.ingestion.errors import IngestionError
from src.ingestion.reader import decode, parse_csv

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class CheckResult:
    check_name: str
    status: str
    expected: str
    actual: str


@dataclass
class PreparedDelivery:
    source_id: str
    school_year: str
    delivery_version: int
    supersedes: str
    archive_path: str
    archive_name: str
    archive_sha256: str
    data_member: str
    data_member_sha256: str
    encoding: str
    schema_version: str
    schema_fingerprint: str
    header: list
    rows: list
    checks: list = field(default_factory=list)

    @property
    def failed_checks(self):
        return [c for c in self.checks if c.status == FAIL]


def identify_delivery(config, archive_path):
    """Return (approved delivery, archive SHA-256), or stop if the file is not approved."""
    path = Path(archive_path)
    if not path.is_file():
        raise IngestionError("identify", "missing_archive", f"{path} does not exist.")
    digest = archive.sha256_file(path)
    delivery = find_delivery(config, digest)
    if delivery:
        return delivery, digest
    repackaged = _approved_data_member(config, path)
    if repackaged:
        raise IngestionError("identify", "repackaged_delivery",
                             f"{path.name} is a different zip around the approved data file of {repackaged['archive']} "
                             f"(SY {repackaged['school_year']} v{repackaged['delivery_version']}). Its rows are already "
                             "identified by that file's SHA-256, so it is skipped.")
    same_name = [d for d in config["deliveries"] if d["archive"] == path.name]
    if same_name:
        approved = ", ".join(f"v{d['delivery_version']} {d['archive_sha256'][:12]}" for d in same_name)
        raise IngestionError("identify", "checksum_mismatch",
                             f"{path.name} has SHA-256 {digest}, which is not approved (approved: {approved}). "
                             "If the download is damaged, download it again. If the publisher revised the file, "
                             "approve it as the next delivery_version with 'supersedes' set; the earlier version is kept.")
    raise IngestionError("identify", "unregistered_delivery",
                         f"{path.name} (SHA-256 {digest}) is not an approved delivery. "
                         "Profile it, then add it to the source config in a pull request.")


def _approved_data_member(config, path):
    """The approved delivery whose data file this unapproved zip contains, if any."""
    try:
        members = archive.list_members(path, config["max_uncompressed_bytes"])
        data_member, _ = archive.resolve_members(members, config["data_member_pattern"], config["document_members"])
        digest = archive.sha256_bytes(archive.read_member(path, data_member))
    except IngestionError:
        return None
    return next((d for d in config["deliveries"] if d["data_member_sha256"] == digest), None)


def prepare_delivery(config, registry_entry, archive_path):
    delivery, digest = identify_delivery(config, archive_path)
    path = Path(archive_path)

    members = archive.list_members(path, config["max_uncompressed_bytes"])
    data_member, documents = archive.resolve_members(
        members, config["data_member_pattern"], config["document_members"])
    if PurePosixPath(data_member).name != delivery["data_member"]:
        raise IngestionError("archive", "missing_data_member",
                             f"expected {delivery['data_member']!r}, found {data_member!r}.")
    for name, member in documents.items():
        actual = archive.sha256_bytes(archive.read_member(path, member))
        if actual != delivery["document_sha256"][name]:
            raise IngestionError("checksum", "document_checksum_mismatch",
                                 f"{name} in {path.name} has SHA-256 {actual}, not the approved {delivery['document_sha256'][name]}.")

    data = archive.read_member(path, data_member)
    data_sha = archive.sha256_bytes(data)
    if data_sha != delivery["data_member_sha256"]:
        raise IngestionError("checksum", "member_checksum_mismatch",
                             f"{data_member} has SHA-256 {data_sha}, not the approved {delivery['data_member_sha256']}.")

    school_year = resolve_school_year(config, path.name, data_member, expected=delivery["school_year"])
    text = decode(data, delivery["encoding"], data_member)
    header, rows = parse_csv(text, data_member)
    version = match_schema(config, header)
    if version != delivery["schema_version"]:
        raise IngestionError("schema", "schema_version_mismatch",
                             f"header is schema {version}, but the approved delivery says {delivery['schema_version']}.")

    prepared = PreparedDelivery(
        source_id=config["source_id"],
        school_year=school_year,
        delivery_version=delivery["delivery_version"],
        supersedes=delivery["supersedes"],
        archive_path=str(path),
        archive_name=path.name,
        archive_sha256=digest,
        data_member=data_member,
        data_member_sha256=data_sha,
        encoding=delivery["encoding"],
        schema_version=version,
        schema_fingerprint=schema_fingerprint(header),
        header=header,
        rows=rows,
    )
    prepared.checks = check_rows(config, header, rows, expected_rows=delivery["row_count"])
    return prepared


def check_rows(config, header, rows, expected_rows):
    checks = []
    n = len(rows)

    def add(name, ok, expected, actual, warn_only=False):
        status = PASS if ok else (WARN if warn_only else FAIL)
        checks.append(CheckResult(name, status, str(expected), str(actual)))

    add("row_count_nonzero", n > 0, "> 0", n)
    add("row_count_matches_approved", n == expected_rows, expected_rows, n)

    missing = [c for c in config["required_columns"] if c not in header]
    add("required_columns_present", not missing, config["required_columns"], f"missing {missing}" if missing else "all present")

    key = header.index(config["identifier_column"])
    ids = [values[key] for _, values in rows]
    pattern = re.compile(config["identifier_pattern"])
    blank = sum(1 for v in ids if v.strip() == "")
    malformed = sum(1 for v in ids if v.strip() != "" and not pattern.match(v))
    repeated = sum(c - 1 for c in Counter(ids).values() if c > 1)
    duplicate_rows = n - len({tuple(values) for _, values in rows})

    add(f"{config['identifier_column']}_not_blank", blank == 0, 0, blank)
    add(f"{config['identifier_column']}_format", malformed == 0, f"0 not matching {config['identifier_pattern']}", malformed, warn_only=True)
    add(f"{config['identifier_column']}_unique_in_file", repeated == 0, 0, repeated, warn_only=True)
    add("duplicate_rows_in_file", duplicate_rows == 0, 0, duplicate_rows, warn_only=True)
    return checks
