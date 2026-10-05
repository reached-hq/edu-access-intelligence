# Ingestion contracts

One file per source that is ingested, `<source_id>.json`. It says what an approved delivery of that source looks like, and lists every delivery the team has approved. The ingestion code (`src/ingestion/`) refuses anything else.

The source's name, system, and URL stay in the registry (`config/sources.json`); a contract does not repeat them, and does not change the source's `status`.

## What a contract holds

| Field | Meaning |
|---|---|
| `archive_pattern` | Publisher file name, with the school year in it, e.g. `Enrollment-in-SY-2025-2026.zip` |
| `data_member_pattern` | Name of the one data file inside the archive, matched on the base name because the publisher's folder inside the zip changes between years |
| `document_members` | Publisher documents that must be in the archive (checksummed, not loaded) |
| `max_uncompressed_bytes` | Refuse an archive that expands beyond this |
| `identifier_column`, `identifier_pattern`, `required_columns` | The row identifier and the columns a delivery cannot lack |
| `schema_versions` | Each version is the exact, ordered list of the publisher's column names |
| `deliveries` | The approved deliveries (below) |

Each approved delivery pins:

| Field | Meaning |
|---|---|
| `school_year` | e.g. `2025-26`. It must agree with both the archive name and the data file name |
| `delivery_version`, `supersedes` | `1` for the first delivery of a school year. A revised file for the same year is `2`, with `supersedes` set to version 1's `archive_sha256` |
| `archive`, `archive_sha256` | The zip as downloaded |
| `data_member`, `data_member_sha256` | The CSV inside it |
| `document_sha256` | Each publisher document inside it |
| `encoding` | `utf-8` or `cp1252`, as profiled for these exact bytes |
| `schema_version` | Which schema version the header must equal |
| `row_count` | Data rows (excluding the header) found when profiling; Bronze must reconcile to it |
| `retrieved_at_utc` | When the file was downloaded |

## Approving a delivery

A delivery is approved by merging its entry in a reviewed pull request, never by the pipeline. To add one, for example a new school year:

1. Download the official zip into raw storage under its original name; do not change the file.
2. Profile it (`notebooks/profiling/`) and update the source card with its checksums, encoding, and row count.
3. If the header matches no schema version, add a new version here with the exact new column list, and record the change in `profile.md`. The loader stops on any header it does not recognize.
4. Add the delivery entry, copying the values from the source card. `tests/test_ingestion_validate.py` fails if a checksum or row count here is not also on the card.

A file whose name matches an approved delivery but whose SHA-256 does not is refused as `checksum_mismatch`. It is either damaged (download it again) or revised by the publisher (approve it as the next `delivery_version`; the earlier version is kept).
