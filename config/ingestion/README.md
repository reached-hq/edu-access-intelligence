# Ingestion contracts

One file per source that is ingested, `<source_id>.json`. It says what an approved delivery of that source looks like, and lists every delivery the team has approved. The ingestion code (`src/ingestion/`) refuses anything else.

The source's name, system, and URL stay in the registry (`config/sources.json`); a contract does not repeat them, and does not change the source's `status`.

## What a contract holds

| Field | Meaning |
|---|---|
| `landing_dir` | Publisher folder under the raw landing root that is searched for deliveries (e.g. `deped`), in any subfolder |
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
2. Profile it (`analysis/profiling/`) and update the source card with its checksums, encoding, and row count.
3. If the header matches no schema version, add a new version here with the exact new column list, and record the change in `profile.md`. The loader stops on any header it does not recognize.
4. Add the delivery entry, copying the values from the source card. `tests/test_ingestion_validate.py` fails unless each value here matches the card row of its own file: the zip's name and checksum, and the CSV's name, checksum, row count, and encoding.

A file whose name matches an approved delivery but whose SHA-256 does not is refused as `checksum_mismatch`. It is either damaged (download it again) or revised by the publisher (approve it as the next `delivery_version`; the earlier version is kept).

## Workbook contracts (`format: xlsx_table`)

`psa_psgc.json` describes one xlsx workbook per publication quarter, delivered as is (no zip around it). The rules are in `src/ingestion/xlsx_table.py`; the decision is D-019.

| Field | Meaning |
|---|---|
| `format` | `xlsx_table`. Absent means `zip_csv`, the DepEd shape above |
| `workbook_pattern` | Publisher file name with named groups `quarter` and `year`, e.g. `PSGC-2Q-2026-Publication-Datafile.xlsx`. Searched for under `landing_dir` at any depth |
| `data_sheet`, `expected_sheets` | The sheet that holds the data, and every sheet the workbook should have (a different list is a WARN: a new sheet may hold data) |
| `period_source` | Where the publication date is: the sheet and the label in column A (`Metadata`, `Publication date:`). Its quarter must equal the file name's |
| `identifier_column`, `identifier_pattern` | Bronze name of the code and its exact pattern as stored text (`^[0-9]{10}$`). A code stored as a number passes only if its stored digits already match; nothing is padded |
| `identifier_number_cells_profiled` | How many codes the profile found stored as numbers (shown beside the WARN) |
| `require_approved_deliveries` | `true`: an approved workbook missing from the landing folder fails the run |
| `master_reference_period` | The quarter the team uses as the master geographic reference (D-012). Must be an approved quarter; changed only by a team decision, never by loading |
| `schema_versions` | Each version has `columns` (snake_case Bronze names) and `source_headers` (the exact header cells, line breaks included; `""` for an empty header cell), in the same order. The header must equal one version's `source_headers` exactly |
| `quality_checks` | Known publisher characteristics, recorded as WARN with their profiled count: `blank`, `not_blank`, `equals`, `ends_with`, `not_whole_number` on one column |
| `national_summary`, `hierarchy` | How to read the workbook's own summary sheet and the levels, for the WARN checks against it and the code-prefix hierarchy |

Each approved workbook pins:

| Field | Meaning |
|---|---|
| `publication_period` | e.g. `2026-Q2`. Must equal the quarter in the file name |
| `publication_date` | ISO date from the `Metadata` sheet, inside that quarter |
| `delivery_version`, `supersedes` | `1` for the first delivery of a quarter. A re-issued file for the same quarter is `2`, with `supersedes` set to version 1's `workbook_sha256` |
| `workbook`, `workbook_sha256` | The file as downloaded |
| `sheet`, `range` | The data sheet and its exact used range, e.g. `A1:K43769`: the header row plus `row_count` rows, one column per schema column |
| `schema_version`, `row_count` | Which header it has, and its data rows; Bronze must reconcile to it |
| `documented_population_abroad` | The publisher's documented gap between the regions and the national population (`Notes` D.2: 1,708) |
| `retrieved_at_utc` | When the file was downloaded |

To approve a new quarter, follow the PSGC runbook in [docs/operations/ingestion.md](../../docs/operations/ingestion.md#runbook-psgc). `tests/test_ingestion_validate.py` fails unless the workbook's name, checksum, row count and range sit on one row of the source card.
