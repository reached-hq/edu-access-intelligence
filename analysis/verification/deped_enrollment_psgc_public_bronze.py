"""Reconcile the public-school scope of deped_enrollment_psgc_raw on a local DuckDB that already holds it.

Bronze keeps every sector (D-015); the public scope is `sector = 'Public'` on unit rows, the filter Gold and
Analytics apply (D-022). This counts that scope as Bronze holds it, so an evidence record can compare it with
the source card and profile. First load Bronze, from the repository root, with RAW_DATA_DIR set:

    python -m src.ingestion.cli ingest --source deped_enrollment_psgc --db <scratch>/emisd.duckdb

then:

    python analysis/verification/deped_enrollment_psgc_public_bronze.py --db <scratch>/emisd.duckdb

Only rows of current batches are read. It prints counts, never row values, and writes nothing. The
coordinate number pattern and Philippine box are Silver's (config/mappings/deped_enrollment_psgc.json),
so Bronze and Silver count the same way; nothing is typed, padded or corrected.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.ingestion.store import DuckDBStore  # noqa: E402
from src.job.local_run import DEFAULT_DB  # noqa: E402

SOURCE = "deped_enrollment_psgc"
BRONZE = "edu_access.`02-bronze`.deped_enrollment_psgc_raw"
CONTROL = "edu_access.`01-control`"
PUBLIC = "Public"


def _config(kind):
    return json.loads((REPO_ROOT / "config" / kind / f"{SOURCE}.json").read_text(encoding="utf-8"))


def _one(store, sql):
    return store.query(sql)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    store = DuckDBStore(args.db)

    columns = _config("ingestion")["schema_versions"]["v1"]["columns"]
    counts = columns[columns.index("latitude") + 1:]
    coords = _config("mappings")["coordinates"]
    box, number = coords["box"], coords["number_pattern"]
    current = (f"FROM {BRONZE} AS r JOIN {CONTROL}.current_batches AS b ON r.batch_id = b.batch_id "
               f"WHERE b.source_id = '{SOURCE}'")
    unit = f"{current} AND r.source_row_kind = 'unit'"
    public = f"{unit} AND r.sector = '{PUBLIC}'"

    print("batches (current):")
    for r in store.records(f"SELECT i.batch_id, i.school_year, i.delivery_version, i.source_sha256, i.expected_rows, "
                           f"i.source_rows, i.bronze_rows, i.status FROM {CONTROL}.ingestion_batches AS i "
                           f"JOIN {CONTROL}.current_batches AS b ON i.batch_id = b.batch_id WHERE b.source_id = '{SOURCE}'"):
        print(f"  {r['batch_id']} {r['school_year']} v{r['delivery_version']} sha256 {r['source_sha256']} "
              f"expected {r['expected_rows']} source {r['source_rows']} bronze {r['bronze_rows']} {r['status']}")

    print("rows by kind:")
    for kind, n in store.query(f"SELECT r.source_row_kind, COUNT(*) {current} GROUP BY 1 ORDER BY 1"):
        print(f"  {kind:<14} {n:>7,}")

    # Every published sector label, exactly as stored, so a variant such as 'Public ' cannot hide.
    print("unit rows by sector (as stored):")
    for sector, n in store.query(f"SELECT r.sector, COUNT(*) {unit} GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {sector!r:<14} {n:>7,}")
    near = _one(store, f"SELECT COUNT(*) {unit} AND lower(trim(r.sector)) = 'public' AND r.sector <> '{PUBLIC}'")[0]
    print(f"  near-'Public' labels not equal to it: {near}")

    total, ids, malformed = _one(store, f"SELECT COUNT(*), COUNT(DISTINCT r.school_id), "
                                        f"COUNT(*) FILTER (WHERE NOT regexp_full_match(r.school_id, '[0-9]{{6}}')) {public}")
    repeated = _one(store, f"SELECT COALESCE(SUM(n - 1), 0) FROM (SELECT r.school_id, COUNT(*) AS n {public} "
                           "GROUP BY 1 HAVING COUNT(*) > 1)")[0]
    print(f"public unit rows {total:,}; distinct school_id {ids:,}; not 6 digits {malformed}; "
          f"extra rows of a repeated school_id {repeated}")

    def classify(column):
        return (f"CASE WHEN r.{column} = '#N/A' THEN '#N/A' WHEN r.{column} = '' THEN 'blank' "
                f"WHEN regexp_full_match(r.{column}, '[0-9]{{10}}') THEN '10 digits' "
                f"WHEN regexp_full_match(r.{column}, '[0-9]{{9}}') THEN '9 digits' ELSE 'other' END")

    for column in ("psgc_city_municipality", "psgc_barangay"):
        print(f"public {column}:")
        for label, n in store.query(f"SELECT {classify(column)}, COUNT(*) {public} GROUP BY 1 ORDER BY 2 DESC"):
            print(f"  {label:<10} {n:>7,}")

    lon, lat = "TRY_CAST(r.longitude AS DOUBLE)", "TRY_CAST(r.latitude AS DOUBLE)"
    numeric = f"regexp_full_match(r.longitude, '{number}') AND regexp_full_match(r.latitude, '{number}')"
    inside = (f"{lon} BETWEEN {box['longitude_min']} AND {box['longitude_max']} "
              f"AND {lat} BETWEEN {box['latitude_min']} AND {box['latitude_max']}")
    status = (f"CASE WHEN r.longitude = '#N/A' OR r.latitude = '#N/A' THEN '#N/A' "
              f"WHEN r.longitude = '' OR r.latitude = '' THEN 'blank' "
              f"WHEN NOT ({numeric}) THEN 'not a number' "
              f"WHEN {lon} = 0 AND {lat} = 0 THEN 'zero' "
              f"WHEN NOT ({inside}) THEN 'outside box' ELSE 'inside box' END")
    print("public coordinates (pair):")
    for label, n in store.query(f"SELECT {status}, COUNT(*) {public} GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {label:<13} {n:>7,}")
    located = _one(store, f"SELECT COUNT(*) {public} AND regexp_full_match(r.psgc_barangay, '[0-9]{{9,10}}') "
                          f"AND {numeric}")[0]
    print(f"public rows with a numeric barangay code and numeric coordinates: {located:,}")

    blank = " + ".join(f"CAST(r.{c} = '' AS INT)" for c in counts)
    bad = " + ".join(f"CAST(r.{c} <> '' AND NOT regexp_full_match(r.{c}, '[0-9]+') AS INT)" for c in counts)
    learners = " + ".join(f"COALESCE(TRY_CAST(r.{c} AS BIGINT), 0)" for c in counts)
    blank_cells, bad_cells, total_learners = _one(store, f"SELECT SUM({blank}), SUM({bad}), SUM({learners}) {public}")
    print(f"public count cells ({len(counts)} columns): blank {blank_cells}, not a whole number {bad_cells}; "
          f"learners {total_learners:,}")

    provenance = ("source_id", "school_year", "source_file", "source_sha256", "source_sheet", "source_row_number",
                  "source_row_kind", "schema_version", "schema_fingerprint", "batch_id", "run_id",
                  "ingested_at_utc", "code_revision")
    nulls = " OR ".join(f"r.{c} IS NULL" for c in provenance)
    lineage = _one(store, f"SELECT COUNT(*) FILTER (WHERE {nulls}), "
                          "COUNT(*) - COUNT(DISTINCT r.source_sha256 || ':' || CAST(r.source_row_number AS VARCHAR)), "
                          f"COUNT(DISTINCT r.school_year) {public}")
    print(f"public rows with a NULL provenance column {lineage[0]}; repeated (sha256, row number) {lineage[1]}; "
          f"school years {lineage[2]}")
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
