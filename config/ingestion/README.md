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

## Workbook contracts (`"format": "xlsx_sheet"`)

`psa_poverty_stat.json` describes one xlsx workbook per delivery instead of a zip (D-018). It has `workbook_pattern` instead of the archive and member patterns, `label_column` (the column that alone fills a region banner row), and `known_issues`. Each schema version adds a `layout`:

| Layout field | Meaning (PSA v1) |
|---|---|
| `first_data_row` | First body row (6) |
| `group_row`, `group_fill_from_column` | Row of the merged group labels (2), carried across the group from column D on |
| `sub_row`, `sub_row_columns` | Row 4 labels used only in these columns (A: `ID`; M to R: `Lower Limit`/`Upper Limit`) |
| `year_row` | Row of the years (5) |
| `width`, `ignored_columns` | 18 columns (A to R); column S must be empty |
| `footer_marker` | The body ends before the first row whose column A starts with `Notes:` |
| `value_columns_from` | First estimate column (D) |

Each approved workbook pins `logical_dataset`, `estimate_years` (must equal the years in its schema's column names), `delivery_version`, `supersedes`, `workbook`, `workbook_sha256`, `sheet` (and `expected_sheets` if it has more than one), `used_range` (the sheet's declared range, e.g. `A1:S1641`; every row of it is loaded), `schema_version`, `body_rows` (`first`, `last`), `unit_rows`, `banner_rows`, optional `blank_rows`, `footer_rows`, and `retrieved_at_utc`. Versions count 1, 2, 3 per `logical_dataset`; two datasets may not share an estimate year, so a republished year is approved as a revision with `supersedes`. A revision must keep every estimate year of the version it supersedes (it may add years); `current_batches` makes one version per dataset current, so a dropped year would disappear from Silver. `tests/test_ingestion_validate.py` fails unless the workbook's name, checksum, sheet, and row counts are on its source card row.

`known_issues` lists publisher quirks found in profiling. Each is recorded as a WARN with its profiled count beside the actual count; none blocks a batch, and none changes a value. Checks available: `identifier_shorter_than`, `unit_rows_all_values_blank`, `label_equals`, `number_at_most`, `number_above`, `se_disagrees_with_cv` (see `src/ingestion/workbook.py`).

## GeoJSON contracts (`"format": "geojson_features"`)

`hdx_boundaries.json` describes one GeoJSON FeatureCollection per delivery, not zipped (D-020). It uses the same fields as a zip contract, with these differences:

- `archive_pattern` and `data_member_pattern` both match the file itself (`^phl_admin3\.geojson$`), and `document_members` is `[]`.
- `geometry_types`: the expected geometry types (`Polygon`, `MultiPolygon`); any other type is a WARN.
- `period_column`: the property every feature's value must equal the delivery's period (`valid_on`).
- `max_stage_bytes` (optional): rows are merged in chunks of at most this many bytes of text (64,000,000), because one polygon can be megabytes.
- Each schema version lists the properties in file order, then `geometry` last.

Each approved delivery pins the same fields as a zip delivery, but `archive` and `data_member` are both the file name, `archive_sha256` and `data_member_sha256` are both the file's SHA-256, `document_sha256` is `{}`, and `school_year` holds the file's reference date (`2025-02-13`), not a school year.

