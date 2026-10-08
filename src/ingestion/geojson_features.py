"""A delivery that is one GeoJSON FeatureCollection file, read without changing it.

Used for the COD-AB administrative boundaries (hdx_boundaries). The file is not
zipped, so the file itself is the delivery: its SHA-256 identifies it, as an
archive's does for the DepEd zips (D-014). In the contract, `archive` and
`data_member` are both the file name, and both checksums are the file's.

Each feature becomes one Bronze row:

- every property, as text exactly as written. Numbers keep the digits in the
  file ("112.2460" stays "112.2460"), true/false become "true"/"false", and a
  JSON null stays NULL. Nothing is trimmed, typed, or renamed.
- `geometry`: the feature's geometry as the exact characters in the file. It is
  not parsed into a spatial type, simplified, reprojected, or repaired; that is
  Silver's job.
- `source_row_number`: the feature's position in the file, from 1.

The file is scanned one feature at a time: the `features` array is never decoded
as a whole, so memory holds the file's text and the rows, not a Python object for
every coordinate in the country.
"""

import json
import re
from collections import Counter
from json.decoder import scanstring
from pathlib import Path

from src.ingestion import archive
from src.ingestion.contract import match_schema, schema_fingerprint
from src.ingestion.errors import IngestionError
from src.ingestion.reader import decode
from src.ingestion.validate import (
    FAIL, PASS, WARN, CheckResult, PreparedDelivery, check_rows, identify_delivery,
)

GEOMETRY = "geometry"
CRS_WGS84 = ("CRS84", "4326")
_WHITESPACE = re.compile(r"[ \t\n\r]*")
_DECODER = json.JSONDecoder()


# -- Scanning ---------------------------------------------------------------------

def _skip(text, i):
    return _WHITESPACE.match(text, i).end()


def _malformed(name, i, what):
    return IngestionError("parse", "malformed_geojson", f"{name}: {what} at character {i:,}.")


def _value(text, i, name):
    """(start, end, decoded value) of the JSON value at i."""
    start = _skip(text, i)
    try:
        value, end = _DECODER.raw_decode(text, start)
    except json.JSONDecodeError as e:
        raise _malformed(name, e.pos, e.msg)
    return start, end, value


def _object(text, i, name, stream=None):
    """Members of the JSON object at i: ({key: (start, end, value)}, index after '}').

    A key listed in `stream` is handed to its function instead of being decoded;
    that is how the features array is read one feature at a time.
    """
    i = _skip(text, i)
    if text[i:i + 1] != "{":
        raise _malformed(name, i, "expected '{'")
    members = {}
    i = _skip(text, i + 1)
    if text[i:i + 1] == "}":
        return members, i + 1
    while True:
        if text[i:i + 1] != '"':
            raise _malformed(name, i, "expected a key")
        try:
            key, i = scanstring(text, i + 1)
        except json.JSONDecodeError as e:
            raise _malformed(name, e.pos, e.msg)
        if key in members:
            raise _malformed(name, i, f"key {key!r} appears twice in one object")
        i = _skip(text, i)
        if text[i:i + 1] != ":":
            raise _malformed(name, i, f"expected ':' after {key!r}")
        if stream and key in stream:
            start = _skip(text, i + 1)
            members[key] = (start, stream[key](text, start), None)
        else:
            members[key] = _value(text, i + 1, name)
        i = _skip(text, members[key][1])
        if text[i:i + 1] == ",":
            i = _skip(text, i + 1)
        elif text[i:i + 1] == "}":
            return members, i + 1
        else:
            raise _malformed(name, i, "expected ',' or '}'")


def _features(text, i, name, on_feature):
    """Read the array at i, calling on_feature(text, members, number) per element."""
    if text[i:i + 1] != "[":
        raise _malformed(name, i, "expected '[' to open 'features'")
    i = _skip(text, i + 1)
    if text[i:i + 1] == "]":
        return i + 1
    number = 0
    while True:
        number += 1
        members, i = _object(text, i, name)
        on_feature(text, members, number)
        i = _skip(text, i)
        if text[i:i + 1] == ",":
            i = _skip(text, i + 1)
        elif text[i:i + 1] == "]":
            return i + 1
        else:
            raise _malformed(name, i, "expected ',' or ']' between features")


def _as_text(value, name, number, key):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    raise IngestionError("parse", "nested_property",
                         f"{name}: feature {number} property {key!r} is an object or array. Bronze holds "
                         "text only; agree how to keep it before loading this file.")


def parse_feature_collection(text, name):
    """Return (header, rows, facts). Rows are (feature number, [text values]), like a CSV's."""
    header, rows, geometry_types = None, [], Counter()

    def on_feature(text, members, number):
        nonlocal header
        kind = members.get("type", (0, 0, None))[2]
        if kind != "Feature":
            raise IngestionError("parse", "not_a_feature", f"{name}: feature {number} has type {kind!r}.")
        if "properties" not in members or GEOMETRY not in members:
            raise IngestionError("parse", "malformed_feature",
                                 f"{name}: feature {number} lacks 'properties' or 'geometry'.")
        start, end, _ = members["properties"]
        # Decoded again from its own characters so numbers keep the file's digits.
        props = json.loads(text[start:end], parse_float=str, parse_int=str, parse_constant=str)
        if not isinstance(props, dict):
            raise IngestionError("parse", "malformed_feature", f"{name}: feature {number} properties is not an object.")
        columns = [*props, GEOMETRY]
        if header is None:
            header = columns
        elif columns != header:
            raise IngestionError("schema", "unknown_schema_drift",
                                 f"{name}: feature {number} has properties {columns[:-1]}, feature 1 has "
                                 f"{header[:-1]}. Every feature must carry the same properties in the same order.")
        g_start, g_end, geometry = members[GEOMETRY]
        geometry_types[geometry.get("type") if isinstance(geometry, dict) else None] += 1
        raw_geometry = None if geometry is None else text[g_start:g_end]
        rows.append((number, [_as_text(props[k], name, number, k) for k in props] + [raw_geometry]))

    start = 1 if text.startswith("\ufeff") else 0
    top, end = _object(text, start, name,
                       stream={"features": lambda t, i: _features(t, i, name, on_feature)})
    trailing = _skip(text, end)
    if trailing != len(text):
        raise _malformed(name, trailing, "unexpected text after the FeatureCollection")
    if top.get("type", (0, 0, None))[2] != "FeatureCollection" or "features" not in top:
        raise IngestionError("parse", "not_a_feature_collection",
                             f"{name} is not a GeoJSON FeatureCollection with a 'features' array.")
    if header is None:
        raise IngestionError("parse", "empty_file", f"{name} has no features.")
    facts = {"geometry_types": geometry_types, "crs": top.get("crs", (0, 0, None))[2], "byte_order_mark": start == 1}
    return header, rows, facts


# -- Checks -----------------------------------------------------------------------

def geojson_checks(config, delivery, header, rows, facts):
    """Checks specific to a boundary file, on top of the shared row checks. Counts only."""
    checks = []

    def add(name, ok, expected, actual, warn_only=False):
        checks.append(CheckResult(name, PASS if ok else (WARN if warn_only else FAIL), str(expected), str(actual)))

    g = header.index(GEOMETRY)
    missing = sum(1 for _, values in rows if values[g] is None)
    add("geometry_not_null", missing == 0, 0, missing)

    allowed = config["geometry_types"]
    other = {k or "null": n for k, n in facts["geometry_types"].items() if k is not None and k not in allowed}
    add("geometry_types_allowed", not other, allowed,
        ", ".join(f"{k} {n:,}" for k, n in sorted(other.items())) or 0, warn_only=True)

    # The edition is pinned by checksum already; this guards a contract that names
    # the wrong reference date, which would mislabel every row.
    column = config["period_column"]
    p = header.index(column)
    values = Counter(values[p] for _, values in rows)
    period = delivery["school_year"]
    only = next(iter(values)) if len(values) == 1 else None
    add(f"{column}_is_the_approved_period", only is not None and only[:10] == period, period,
        ", ".join(f"{k} {n:,}" for k, n in values.most_common(5)))

    crs = facts["crs"]
    shown = "absent" if crs is None else json.dumps(crs)[:200]
    add("crs_is_wgs84", crs is None or any(tag in json.dumps(crs) for tag in CRS_WGS84),
        "absent (RFC 7946 means WGS 84), CRS84, or EPSG:4326", shown)

    add("no_byte_order_mark", not facts["byte_order_mark"], "absent",
        "present" if facts["byte_order_mark"] else "absent", warn_only=True)
    return checks


# -- The delivery -----------------------------------------------------------------

def prepare_geojson_delivery(config, registry_entry, path):
    """From an approved GeoJSON file to checked rows, or a refusal saying why."""
    delivery, digest = identify_delivery(config, path)
    path = Path(path)
    size = path.stat().st_size
    if size > config["max_uncompressed_bytes"]:
        raise IngestionError("archive", "archive_too_large",
                             f"{path.name} is {size:,} bytes, over the {config['max_uncompressed_bytes']:,} limit "
                             "in the source config.")
    data = path.read_bytes()
    if archive.sha256_bytes(data) != digest:
        raise IngestionError("checksum", "member_checksum_mismatch",
                             f"{path.name} changed while it was being read. Check nothing is writing to it, then run again.")
    text = decode(data, delivery["encoding"], path.name)
    del data
    header, rows, facts = parse_feature_collection(text, path.name)
    del text

    version = match_schema(config, header)
    if version != delivery["schema_version"]:
        raise IngestionError("schema", "schema_version_mismatch",
                             f"properties match schema {version}, but the approved delivery says {delivery['schema_version']}.")

    prepared = PreparedDelivery(
        source_id=config["source_id"],
        school_year=delivery["school_year"],
        delivery_version=delivery["delivery_version"],
        supersedes=delivery["supersedes"],
        archive_path=str(path),
        archive_name=path.name,
        archive_sha256=digest,
        data_member=path.name,
        data_member_sha256=digest,
        encoding=delivery["encoding"],
        schema_version=version,
        schema_fingerprint=schema_fingerprint(header),
        header=header,
        rows=rows,
    )
    prepared.checks = (check_rows(config, header, rows, expected_rows=delivery["row_count"])
                       + geojson_checks(config, delivery, header, rows, facts))
    return prepared