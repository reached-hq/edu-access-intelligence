"""The source contract: what an approved delivery of a source looks like.

`config/ingestion/<source_id>.json` holds, per source:

- the schema versions, each an ordered list of the publisher's column names;
- the approved deliveries, each pinned to its archive and data-file SHA-256,
  encoding, schema version, and row count.

A delivery is approved by merging its entry in a reviewed pull request. The
pipeline never adds or edits an entry, so a file it has never been told about
is refused rather than guessed at. The source's name, system, and URL come from
the registry (`config/sources.json`) so they are written down once.
"""

import hashlib
import json
import re
from pathlib import Path

from src.ingestion.errors import IngestionError

SUPPORTED_ENCODINGS = {"utf-8", "cp1252"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SCHOOL_YEAR = re.compile(r"^[0-9]{4}-[0-9]{2}$")

# Columns the pipeline adds to every Bronze row. A publisher column with one of
# these names would be overwritten, so the contract may not contain one.
PROVENANCE_COLUMNS = (
    "source_id",
    "source_system",
    "source_url",
    "school_year",
    "delivery_version",
    "source_archive",
    "source_archive_sha256",
    "source_file",
    "source_sha256",
    "source_row_number",
    "schema_version",
    "schema_fingerprint",
    "batch_id",
    "run_id",
    "ingested_at_utc",
    "code_revision",
)

DELIVERY_FIELDS = {
    "school_year", "delivery_version", "supersedes", "archive", "archive_sha256",
    "data_member", "data_member_sha256", "document_sha256", "encoding",
    "schema_version", "row_count", "retrieved_at_utc",
}
CONFIG_FIELDS = {
    "source_id", "bronze_table", "archive_pattern", "data_member_pattern",
    "document_members", "max_uncompressed_bytes", "identifier_column",
    "identifier_pattern", "required_columns", "schema_versions", "deliveries",
}


def _config_error(message):
    return IngestionError("config", "invalid_config", message)


def schema_fingerprint(columns):
    """SHA-256 of the ordered column names: any rename, addition, or reorder changes it."""
    return hashlib.sha256("\n".join(columns).encode("utf-8")).hexdigest()


def load_source_config(repo_root, source_id):
    root = Path(repo_root)
    path = root / "config" / "ingestion" / f"{source_id}.json"
    if not path.is_file():
        raise _config_error(f"{path} does not exist; {source_id} has no ingestion contract.")
    config = json.loads(path.read_text(encoding="utf-8"))
    registry = json.loads((root / "config" / "sources.json").read_text(encoding="utf-8"))
    entries = [s for s in registry["sources"] if s.get("source_id") == source_id]
    if len(entries) != 1:
        raise _config_error(f"{source_id} must appear exactly once in config/sources.json.")
    validate_config(config, entries[0])
    return config, entries[0]


def validate_config(config, registry_entry):
    """Refuse a contract that could load something ambiguous. Returns nothing; raises on the first problem."""
    missing = CONFIG_FIELDS - config.keys()
    if missing:
        raise _config_error(f"missing fields {sorted(missing)}.")
    if config["source_id"] != registry_entry.get("source_id"):
        raise _config_error("source_id differs from the registry entry.")
    for field in ("source_system", "acquisition"):
        if not registry_entry.get(field):
            raise _config_error(f"registry entry for {config['source_id']} has no {field!r}; provenance would be blank.")

    versions = config["schema_versions"]
    if not versions:
        raise _config_error("no schema versions.")
    for name, version in versions.items():
        columns = version.get("columns") or []
        if not columns:
            raise _config_error(f"schema {name} has no columns.")
        if len(set(columns)) != len(columns):
            raise _config_error(f"schema {name} repeats a column name.")
        clash = sorted(set(columns) & set(PROVENANCE_COLUMNS))
        if clash:
            raise _config_error(f"schema {name} has publisher columns named like provenance fields: {clash}.")
        absent = [c for c in config["required_columns"] if c not in columns]
        if absent:
            raise _config_error(f"schema {name} lacks required column(s) {absent}.")
    fingerprints = [schema_fingerprint(v["columns"]) for v in versions.values()]
    if len(set(fingerprints)) != len(fingerprints):
        raise _config_error("two schema versions have identical columns.")

    seen_archive, seen_member, seen_version = set(), set(), set()
    by_year = {}
    for d in config["deliveries"]:
        label = f"delivery {d.get('archive')!r}"
        missing = DELIVERY_FIELDS - d.keys()
        if missing:
            raise _config_error(f"{label} is missing {sorted(missing)}.")
        if not SCHOOL_YEAR.match(d["school_year"]):
            raise _config_error(f"{label}: school_year {d['school_year']!r} is not like '2023-24'.")
        checksums = [("archive_sha256", d["archive_sha256"]), ("data_member_sha256", d["data_member_sha256"])]
        checksums += [(f"document_sha256[{k}]", v) for k, v in d["document_sha256"].items()]
        for field, value in checksums:
            if not SHA256.match(str(value)):
                raise _config_error(f"{label}: {field} is not a lowercase SHA-256.")
        if sorted(d["document_sha256"]) != sorted(config["document_members"]):
            raise _config_error(f"{label}: document_sha256 must list exactly {config['document_members']}.")
        if d["encoding"] not in SUPPORTED_ENCODINGS:
            raise _config_error(f"{label}: encoding {d['encoding']!r} is not one of {sorted(SUPPORTED_ENCODINGS)}.")
        if d["schema_version"] not in versions:
            raise _config_error(f"{label}: schema_version {d['schema_version']!r} is not defined.")
        if not isinstance(d["row_count"], int) or d["row_count"] <= 0:
            raise _config_error(f"{label}: row_count must be a positive whole number.")
        if d["archive_sha256"] in seen_archive:
            raise _config_error(f"{label}: archive_sha256 is approved twice.")
        if d["data_member_sha256"] in seen_member:
            raise _config_error(f"{label}: the same data file is approved twice; a re-zipped copy needs no new entry.")
        key = (d["school_year"], d["delivery_version"])
        if key in seen_version:
            raise _config_error(f"{label}: delivery_version {d['delivery_version']} for {d['school_year']} is used twice.")
        seen_archive.add(d["archive_sha256"])
        seen_member.add(d["data_member_sha256"])
        seen_version.add(key)
        by_year.setdefault(d["school_year"], []).append(d)
        try:
            resolve_school_year(config, d["archive"], d["data_member"], expected=d["school_year"])
        except IngestionError as e:
            raise _config_error(f"{label}: {e.message}")

    # Versions of one school year count up from 1, and each revision names the
    # delivery it replaces, so a changed file is never silently a second "v1".
    for year, deliveries in by_year.items():
        deliveries.sort(key=lambda d: d["delivery_version"])
        for i, d in enumerate(deliveries, start=1):
            if d["delivery_version"] != i:
                raise _config_error(f"{year}: delivery versions must be 1, 2, 3...; found {[x['delivery_version'] for x in deliveries]}.")
            previous = deliveries[i - 2]["archive_sha256"] if i > 1 else None
            if d["supersedes"] != previous:
                want = f"supersedes = {previous!r}" if previous else "supersedes = null"
                raise _config_error(f"{year} version {i} must have {want}.")


def resolve_school_year(config, archive_name, member_name, expected=None):
    """Read the school year from the archive name and from the data file name.

    The file has no school-year column (README: 'School year comes from the file
    name'), so two independent names must agree before a year is trusted.
    """
    a = re.match(config["archive_pattern"], archive_name)
    if not a:
        raise IngestionError("identify", "unrecognized_archive_name",
                             f"{archive_name!r} does not match {config['archive_pattern']!r}.")
    m = re.match(config["data_member_pattern"], Path(member_name).name)
    if not m:
        raise IngestionError("identify", "unrecognized_member_name",
                             f"{member_name!r} does not match {config['data_member_pattern']!r}.")
    start, end = int(a["start"]), int(a["end"])
    if end != start + 1:
        raise IngestionError("identify", "school_year_mismatch", f"{archive_name!r} is not one school year ({start}-{end}).")
    year = f"{start}-{str(end)[-2:]}"
    member_year = f"{m['start']}-{m['end']}"
    if member_year != year:
        raise IngestionError("identify", "school_year_mismatch",
                             f"archive says {year} but the data file says {member_year}.")
    if expected is not None and year != expected:
        raise IngestionError("identify", "school_year_mismatch",
                             f"file names say {year} but the approved delivery says {expected}.")
    return year


def match_schema(config, header):
    """Return the schema version whose columns equal the header, or stop on drift."""
    for name, version in config["schema_versions"].items():
        if header == version["columns"]:
            return name
    nearest = max(config["schema_versions"].items(),
                  key=lambda kv: len(set(kv[1]["columns"]) & set(header)))
    known = nearest[1]["columns"]
    added = [c for c in header if c not in known]
    removed = [c for c in known if c not in header]
    detail = f"added {added}, removed {removed}" if added or removed else "same columns in a different order"
    raise IngestionError("schema", "unknown_schema_drift",
                         f"header matches no schema version; nearest is {nearest[0]} ({detail}). "
                         "If the change is real, add a new schema version to the source config in a pull request.")


def find_delivery(config, archive_sha256):
    for d in config["deliveries"]:
        if d["archive_sha256"] == archive_sha256:
            return d
    return None
