"""DepEd facilities loads through the same pipeline as enrollment, from its own contract.

Made-up facilities zips (tests/fixtures/deped.py) are approved into a copy of
the real facilities contract, inside a throwaway repository root that runs the
real etl/ SQL on an in-memory DuckDB.
"""

from fixtures.deped import (
    approve, columns, empty_config, fake_repo, make_delivery, make_rows, registry_entry, write_config,
)
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore
from src.ingestion.validate import PASS, prepare_delivery

SOURCE = "deped_facilities"
REVISION = "b" * 40
CONTROL = "edu_access.`01-control`"
FACILITIES = "edu_access.`02-bronze`.deped_facilities_raw"
ENROLLMENT = "edu_access.`02-bronze`.deped_enrollment_raw"


def deliver(landing, config, school_year="2023-24", source_id=SOURCE, **kwargs):
    path = make_delivery(landing / "deped" / "original", school_year, source_id=source_id, **kwargs)
    approve(config, path, school_year)
    return path


def run(store, repo, landing, source_id=SOURCE):
    return IngestionRun(store, repo, source_id, landing, "local", REVISION).execute()


def test_a_facilities_delivery_passes_every_check(tmp_path):
    config = empty_config(SOURCE)
    path = deliver(tmp_path, config)
    prepared = prepare_delivery(config, registry_entry(SOURCE), path)
    assert (prepared.school_year, prepared.schema_version, len(prepared.header)) == ("2023-24", "v1", 87)
    assert all(c.status == PASS for c in prepared.checks), prepared.checks


def test_facilities_loads_once_and_a_rerun_skips(tmp_path):
    config = empty_config(SOURCE)
    rows = make_rows(columns("v1", SOURCE))
    rows[0][columns("v1", SOURCE).index("es_classrooms_instructional")] = ""  # blank, not zero (profile O-4, O-5)
    deliver(tmp_path, config, rows=rows)
    repo = fake_repo(tmp_path / "repo", config)
    store = DuckDBStore()

    first = run(store, repo, tmp_path)
    assert (first.status, first.outcomes[0].action, first.outcomes[0].rows_inserted) == ("succeeded", "load", 3)
    second = run(store, repo, tmp_path)
    assert (second.status, second.outcomes[0].action, second.outcomes[0].rows_inserted) == ("succeeded", "skip", 0)

    assert store.query(f"SELECT COUNT(*) FROM {FACILITIES}")[0][0] == 3
    assert store.query(f"SELECT COUNT(*) FROM {FACILITIES} WHERE es_classrooms_instructional = ''")[0][0] == 1
    assert store.query(f"SELECT DISTINCT school_year, source_id FROM {FACILITIES}") == [("2023-24", SOURCE)]


def test_sources_share_the_control_tables_but_not_bronze(tmp_path):
    """Each source has its own Bronze table and its own gate; one control layer records both."""
    facilities, enrollment = empty_config(SOURCE), empty_config("deped_enrollment")
    deliver(tmp_path, facilities, n_rows=4)
    deliver(tmp_path, enrollment, source_id="deped_enrollment", n_rows=3)
    repo = fake_repo(tmp_path / "repo", facilities)
    write_config(repo, enrollment)
    store = DuckDBStore()

    assert run(store, repo, tmp_path, "deped_enrollment").status == "succeeded"
    assert run(store, repo, tmp_path, SOURCE).status == "succeeded"

    assert store.query(f"SELECT COUNT(*) FROM {ENROLLMENT}")[0][0] == 3
    assert store.query(f"SELECT COUNT(*) FROM {FACILITIES}")[0][0] == 4
    assert store.query(f"SELECT source_id, status FROM {CONTROL}.ingestion_batches ORDER BY 1") == [
        ("deped_enrollment", "succeeded"), (SOURCE, "succeeded")]
    gates = store.query(f"SELECT DISTINCT source_id FROM {CONTROL}.data_quality_results "
                        "WHERE check_name = 'no_pipeline_duplicates' ORDER BY 1")
    assert gates == [("deped_enrollment",), (SOURCE,)]
