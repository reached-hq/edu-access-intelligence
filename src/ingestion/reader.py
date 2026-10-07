"""Turning a data file's bytes into rows, changing nothing.

- The encoding is the one approved for this exact file (by its SHA-256), never
  guessed: SY 2025-26 enrollment is Windows-1252 and the earlier years UTF-8
  (enrollment profile O-6). Decoding is strict, so a wrong encoding fails
  instead of quietly corrupting names like 'Doña'.
- Values are kept as text exactly as written. A blank stays '' (it is not NULL
  and not 0); trimming, relabeling, and typing are Silver's job.
- Row numbers count data rows from 1, after the header. Together with the
  file's SHA-256 they identify each Bronze row.
"""

import csv
import io

from src.ingestion.errors import IngestionError


def decode(data, encoding, name):
    try:
        return data.decode(encoding, errors="strict")
    except LookupError:
        raise IngestionError("decode", "unsupported_encoding", f"{name}: encoding {encoding!r} is not known to Python.")
    except UnicodeDecodeError as e:
        raise IngestionError("decode", "encoding_mismatch",
                             f"{name} is not valid {encoding} (byte offset {e.start}). "
                             "The approved encoding no longer fits this file; re-profile it before loading.")


def parse_csv(text, name):
    """Return (header, rows), where rows is a list of (row_number, values)."""
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise IngestionError("parse", "empty_file", f"{name} has no header row.")
    except csv.Error as e:
        raise IngestionError("parse", "malformed_csv", f"{name}: header could not be parsed ({e}).")

    rows = []
    try:
        for number, values in enumerate(reader, start=1):
            if len(values) != len(header):
                raise IngestionError("parse", "ragged_row",
                                     f"{name}: data row {number} has {len(values)} fields; the header has {len(header)}.")
            rows.append((number, values))
    except csv.Error as e:
        raise IngestionError("parse", "malformed_csv", f"{name}: could not parse after data row {len(rows)} ({e}).")
    return header, rows
