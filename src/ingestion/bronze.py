"""Bronze: every delivery's rows as received, plus where each row came from.

One table per source holds every school year and every delivery version. Its
columns are the provenance fields, then the union of the publisher columns of
all schema versions in the contract, in the order they first appeared. A
column a year's file does not have is NULL for that year's rows; a blank in
the file stays ''. So "not published that year" and "published blank" remain
different.

A row's identity is (source_sha256, source_row_number): the data file's
SHA-256 and its row number. The insert-only MERGE on that pair means loading
the same file again adds nothing, while two identical rows from the publisher
(different row numbers) are both kept. A hash of the row's content would merge
those publisher duplicates; the archive's SHA-256 would load a re-zipped copy
twice.
"""

from src.ingestion.contract import PROVENANCE_COLUMNS
from src.ingestion.errors import IngestionError
from src.ingestion.store import table_name

SCHEMA = "02-bronze"

PROVENANCE_TYPES = {
    "delivery_version": "INT",
    "source_row_number": "BIGINT",
    "ingested_at_utc": "TIMESTAMP",
}

# Delta needs column mapping to store a column name with spaces, such as
# 'Modified Curricular Offering Classification', unchanged.
TABLE_PROPERTIES = {
    "delta.columnMapping.mode": "name",
    "delta.minReaderVersion": "2",
    "delta.minWriterVersion": "5",
}


def source_columns(config):
    seen = []
    for version in config["schema_versions"].values():
        seen.extend(c for c in version["columns"] if c not in seen)
    return seen


def bronze_columns(config):
    """[(name, Databricks type)] in table order."""
    provenance = [(c, PROVENANCE_TYPES.get(c, "STRING")) for c in PROVENANCE_COLUMNS]
    return provenance + [(c, "STRING") for c in source_columns(config)]


def bronze_table(config):
    return table_name(SCHEMA, config["bronze_table"])


def bronze_ddl(config):
    source_id = config["source_id"]
    lines = [
        f"-- Bronze table for {source_id}. Generated from config/ingestion/{source_id}.json:",
        f"--   python -m src.ingestion.cli ddl --source {source_id}",
        "-- Do not edit by hand; tests/test_ingestion_pipeline.py fails if it differs.",
        "--",
        "-- Provenance columns first, then every publisher column of every schema",
        "-- version as text. NULL means the column is not in that year's file; ''",
        "-- means the publisher left it blank.",
        f"CREATE SCHEMA IF NOT EXISTS edu_access.`{SCHEMA}`;",
        "",
        f"CREATE TABLE IF NOT EXISTS {bronze_table(config)} (",
    ]
    columns = bronze_columns(config)
    for i, (name, kind) in enumerate(columns):
        null = " NOT NULL" if name in PROVENANCE_COLUMNS else ""
        comma = "," if i < len(columns) - 1 else ""
        lines.append(f"  `{name}` {kind}{null}{comma}")
    props = ",\n".join(f"  '{k}' = '{v}'" for k, v in TABLE_PROPERTIES.items())
    lines += [")", "USING DELTA", f"TBLPROPERTIES (\n{props}\n);", ""]
    return "\n".join(lines)


def add_missing_columns(store, config):
    """Add publisher columns from a newly approved schema version.

    The table only grows from the reviewed contract, never from a file's
    header, so a column cannot appear in Bronze without a pull request.
    """
    existing = [c for c, _ in store.columns(SCHEMA, config["bronze_table"])]
    expected = [c for c, _ in bronze_columns(config)]
    unknown = [c for c in existing if c not in expected]
    if unknown:
        raise IngestionError("setup", "bronze_has_unknown_columns",
                             f"{bronze_table(config)} has columns not in the contract: {unknown}. "
                             "A schema version was removed from the contract; restore it.")
    for name in expected:
        if name not in existing:
            store.sql(f"ALTER TABLE {bronze_table(config)} ADD COLUMN `{name}` STRING")


def build_rows(prepared, registry_entry, batch_id, run_id, ingested_at_utc, code_revision, columns):
    provenance = {
        "source_id": prepared.source_id,
        "source_system": registry_entry["source_system"],
        "source_url": registry_entry["acquisition"],
        "school_year": prepared.school_year,
        "delivery_version": prepared.delivery_version,
        "source_archive": prepared.archive_name,
        "source_archive_sha256": prepared.archive_sha256,
        "source_file": prepared.data_member,
        "source_sha256": prepared.data_member_sha256,
        "schema_version": prepared.schema_version,
        "schema_fingerprint": prepared.schema_fingerprint,
        "batch_id": batch_id,
        "run_id": run_id,
        "ingested_at_utc": ingested_at_utc,
        "code_revision": code_revision,
    }
    absent = {c: None for c in columns if c not in provenance and c not in prepared.header}
    for number, values in prepared.rows:
        row = dict(zip(prepared.header, values))
        row.update(absent)
        row.update(provenance)
        row["source_row_number"] = number
        yield row


def count_file_rows(store, config, source_sha256):
    return store.query(
        f"SELECT COUNT(*) FROM {bronze_table(config)} WHERE source_sha256 = '{source_sha256}'")[0][0]


def merge_rows(store, config, rows):
    """Insert rows whose (source_sha256, source_row_number) is not already in Bronze."""
    columns = store.columns(SCHEMA, config["bronze_table"])
    store.stage("bronze_stage", columns, list(rows))
    store.sql(
        f"MERGE INTO {bronze_table(config)} AS t USING bronze_stage AS s "
        "ON t.source_sha256 = s.source_sha256 AND t.source_row_number = s.source_row_number "
        "WHEN NOT MATCHED THEN INSERT *"
    )


def reconcile(store, config, prepared):
    """Post-load checks for one file: [(check_name, ok, expected, actual)]."""
    sha = prepared.data_member_sha256
    n = len(prepared.rows)
    nulls = " OR ".join(f"`{c}` IS NULL" for c in PROVENANCE_COLUMNS)
    total, distinct, low, high, missing_provenance = store.query(
        f"SELECT COUNT(*), COUNT(DISTINCT source_row_number), MIN(source_row_number), MAX(source_row_number), "
        f"COUNT(CASE WHEN {nulls} THEN 1 END) "
        f"FROM {bronze_table(config)} WHERE source_sha256 = '{sha}'")[0]
    return [
        ("bronze_rows_match_source", total == n, n, total),
        ("no_pipeline_duplicates", total == distinct, 0, total - distinct),
        ("row_numbers_complete", (low, high) == ((1, n) if n else (None, None)), f"1..{n}", f"{low}..{high}"),
        ("provenance_complete", missing_provenance == 0, 0, missing_provenance),
    ]
