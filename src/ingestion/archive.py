"""Reading a publisher's zip without trusting it.

Members are read into memory and never extracted to disk, so a path like
`../../etc/x` cannot write anywhere. Unsafe entries are still refused, because
an archive that contains them is not the archive the publisher meant to send.
The zip itself is opened read-only and never modified.
"""

import hashlib
import re
import stat
import zipfile
from pathlib import PurePosixPath

from src.ingestion.errors import IngestionError

CHUNK = 1024 * 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _unsafe_reason(info):
    name = info.filename
    if "\\" in name:
        return "contains a backslash"
    path = PurePosixPath(name)
    if path.is_absolute() or re.match(r"^[A-Za-z]:", name):
        return "is an absolute path"
    if ".." in path.parts:
        return "climbs out of the archive with '..'"
    if stat.S_ISLNK(info.external_attr >> 16):
        return "is a symbolic link"
    if info.flag_bits & 0x1:
        return "is encrypted"
    return None


def list_members(path, max_uncompressed_bytes):
    """Return the archive's file entries (directories skipped) after safety checks."""
    try:
        zf = zipfile.ZipFile(path)
    except FileNotFoundError:
        raise IngestionError("archive", "missing_archive", f"{path} does not exist.")
    except zipfile.BadZipFile as e:
        raise IngestionError("archive", "corrupt_archive",
                             f"{path} is not a readable zip ({e}). Download it again and compare its SHA-256.")
    with zf:
        infos = zf.infolist()
    total = 0
    files = []
    for info in infos:
        reason = _unsafe_reason(info)
        if reason:
            raise IngestionError("archive", "unsafe_member",
                                 f"{path}: member {info.filename!r} {reason}. Nothing was read; report it to the publisher.")
        if info.is_dir():
            continue
        total += info.file_size
        files.append(info.filename)
    if total > max_uncompressed_bytes:
        raise IngestionError("archive", "archive_too_large",
                             f"{path} expands to {total:,} bytes, over the {max_uncompressed_bytes:,} limit in the source config.")
    return files


def resolve_members(members, data_member_pattern, document_members):
    """Find the one data file and the expected documents by file name.

    Matching is on the base name because the publisher's folder inside the zip
    is not stable ('Enrollment in SY 2023-2024/' vs 'Enrollment-in-SY-2025-2026/').
    Any other file is unexpected and stops the load.
    """
    by_name = {}
    for member in members:
        base = PurePosixPath(member).name
        if base in by_name:
            raise IngestionError("archive", "duplicate_member",
                                 f"two members are named {base!r}: {by_name[base]!r} and {member!r}.")
        by_name[base] = member

    pattern = re.compile(data_member_pattern)
    data = [m for base, m in by_name.items() if pattern.match(base)]
    if not data:
        raise IngestionError("archive", "missing_data_member",
                             f"no member matches {data_member_pattern!r}; found {sorted(by_name)}.")
    if len(data) > 1:
        raise IngestionError("archive", "ambiguous_data_member",
                             f"more than one member matches {data_member_pattern!r}: {sorted(data)}.")

    missing_docs = [d for d in document_members if d not in by_name]
    if missing_docs:
        raise IngestionError("archive", "missing_document_member",
                             f"expected publisher document(s) {missing_docs} are not in the archive.")

    expected = {PurePosixPath(data[0]).name, *document_members}
    unexpected = sorted(base for base in by_name if base not in expected)
    if unexpected:
        raise IngestionError("archive", "unexpected_member",
                             f"unexpected member(s) {unexpected}. Inspect the delivery and update the source config if they are legitimate.")
    return data[0], {d: by_name[d] for d in document_members}


def read_member(path, member):
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.read(member)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError) as e:
        raise IngestionError("archive", "corrupt_archive", f"{path}: could not read {member!r} ({e}).")
