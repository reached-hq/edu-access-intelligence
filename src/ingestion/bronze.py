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

# The team group owns every object the job creates (D-009). Unity Catalog makes
# the creator the owner, and a dev job runs as whoever deployed it, so without
# this only that one person could read the table or load into it.
OWNER_GROUP = "reached-hq"

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
        f"ALTER SCHEMA edu_access.`{SCHEMA}` OWNER TO `{OWNER_GROUP}`;",
        "",
        f"CREATE TABLE IF NOT EXISTS {bronze_table(config)} (",
    ]
    columns = bronze_columns(config)
    for i, (name, kind) in enumerate(columns):
        null = " NOT NULL" if name in PROVENANCE_COLUMNS else ""
        comma = "," if i < len(columns) - 1 else ""
        lines.append(f"  `{name}` {kind}{null}{comma}")
    props = ",\n".join(f"  '{k}' = '{v}'" for k, v in TABLE_PROPERTIES.items())
    lines += [")", "USING DELTA", f"TBLPROPERTIES (\n{props}\n);", "",
              "-- Owned by the team group, not by whoever ran the job first (D-009).",
              f"ALTER TABLE {bronze_table(config)} OWNER TO `{OWNER_GROUP}`;", ""]
    return "\n".join(lines)


GATE_TEMPLATE = """-- Bronze gate for {SOURCE}. Generated from config/ingestion/{SOURCE}.json:
--   python -m src.ingestion.cli gate --source {SOURCE}
-- Do not edit by hand; tests/test_ingestion_pipeline.py fails if it differs.
--
-- Runs after every load, over the whole table. Each check writes one row to
-- data_quality_results. The last statement fails on any FAIL recorded for this
-- run (including a batch's own checks), so nothing downstream runs on an
-- unreconciled table.
--
-- Parameters, supplied by the job (or the local CLI):
--   :run_id         the ingestion run being checked
--   :code_revision  the commit that ran, from the job parameter; never a literal

-- The same source row twice means a load ran twice without the MERGE guard.
INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, '{SOURCE}', 'bronze', 'edu_access.02-bronze.{TABLE}',
       'no_pipeline_duplicates', CASE WHEN extra = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(extra AS STRING),
       current_timestamp(), :code_revision
FROM (
  SELECT COUNT(*) - COUNT(DISTINCT source_sha256 || ':' || CAST(source_row_number AS STRING)) AS extra
  FROM edu_access.`02-bronze`.{TABLE}
) AS t;

-- Every Bronze row must point to a batch the control table knows about.
INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, '{SOURCE}', 'bronze', 'edu_access.02-bronze.{TABLE}',
       'rows_have_a_known_batch', CASE WHEN orphans = 0 THEN 'PASS' ELSE 'FAIL' END, '0', CAST(orphans AS STRING),
       current_timestamp(), :code_revision
FROM (
  SELECT COUNT(*) AS orphans
  FROM edu_access.`02-bronze`.{TABLE} AS r
  LEFT JOIN edu_access.`01-control`.ingestion_batches AS b ON r.batch_id = b.batch_id
  WHERE b.batch_id IS NULL
) AS t;

-- Every succeeded batch has exactly as many Bronze rows as its file had.
INSERT INTO edu_access.`01-control`.data_quality_results
  (run_id, batch_id, source_id, layer, table_name, check_name, status, expected, actual, checked_at_utc, code_revision)
SELECT :run_id, NULL, '{SOURCE}', 'bronze', 'edu_access.02-bronze.{TABLE}',
       'succeeded_batches_reconcile', CASE WHEN mismatched = 0 THEN 'PASS' ELSE 'FAIL' END, '0',
       CAST(mismatched AS STRING), current_timestamp(), :code_revision
FROM (
  SELECT COUNT(*) AS mismatched
  FROM edu_access.`01-control`.ingestion_batches AS b
  LEFT JOIN (
    SELECT source_sha256, COUNT(*) AS n
    FROM edu_access.`02-bronze`.{TABLE}
    GROUP BY source_sha256
  ) AS r ON r.source_sha256 = b.source_sha256
  WHERE b.source_id = '{SOURCE}' AND b.status = 'succeeded'
    AND (r.n IS NULL OR r.n <> b.source_rows OR b.source_rows <> b.expected_rows)
) AS t;

-- Stop here if anything failed in this run.
SELECT CASE WHEN COUNT(*) > 0
            THEN raise_error('Bronze gate failed for {SOURCE}: ' || CAST(COUNT(*) AS STRING)
                             || ' FAIL result(s) in data_quality_results for run ' || :run_id)
       END
FROM edu_access.`01-control`.data_quality_results
WHERE run_id = :run_id AND source_id = '{SOURCE}' AND status = 'FAIL';
"""


def bronze_gate(config):
    """The Bronze gate SQL for a source: the same checks for every source, so it is generated, not copied."""
    return GATE_TEMPLATE.replace("{TABLE}", config["bronze_table"]).replace("{SOURCE}", config["source_id"])


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
