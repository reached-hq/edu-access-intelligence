"""DepEd personnel contract, Bronze loading, and rerun behavior."""

from factories.deped_deliveries import approve, columns, empty_config, fake_repo, make_delivery, make_rows
from src.ingestion import control
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore
from src.ingestion.validate import PASS, prepare_delivery
from factories.deped_deliveries import registry_entry

SOURCE = "deped_personnel"
REVISION = "c" * 40
PERSONNEL = "edu_access.`02-bronze`.deped_personnel_raw"


def deliver(landing, config, rows=None):
    path = make_delivery(landing / "deped" / "original", "2023-24", source_id=SOURCE, rows=rows)
    approve(config, path, "2023-24")
    return path


def run(store, repo, landing):
    return IngestionRun(store, repo, SOURCE, landing, "local", REVISION).execute()


def test_a_personnel_delivery_passes_every_check(tmp_path):
    config = empty_config(SOURCE)
    path = deliver(tmp_path, config)
    prepared = prepare_delivery(config, registry_entry(SOURCE), path)
    assert (prepared.school_year, prepared.schema_version, len(prepared.header)) == ("2023-24", "v1", 327)
    assert all(check.status == PASS for check in prepared.checks), prepared.checks


def test_personnel_loads_once_preserves_blanks_and_has_provenance(tmp_path):
    config = empty_config(SOURCE)
    header = columns("v1", SOURCE)
    rows = make_rows(header)
    measure = header.index("es_master_teacher_iv")
    rows[0][measure] = ""
    rows[1][measure] = "0"
    deliver(tmp_path, config, rows)
    repo = fake_repo(tmp_path / "repo", config)
    store = DuckDBStore()

    first = run(store, repo, tmp_path)
    assert (first.status, first.outcomes[0].action, first.outcomes[0].rows_inserted) == ("succeeded", "load", 3)
    second = run(store, repo, tmp_path)
    assert (second.status, second.outcomes[0].action, second.outcomes[0].rows_inserted) == ("succeeded", "skip", 0)

    assert store.query(f"SELECT COUNT(*) FROM {PERSONNEL}")[0][0] == 3
    assert store.query(f"SELECT COUNT(*) FROM {PERSONNEL} WHERE es_master_teacher_iv = ''")[0][0] == 1
    assert store.query(f"SELECT COUNT(*) FROM {PERSONNEL} WHERE es_master_teacher_iv = '0'")[0][0] == 1
    provenance = [
        "source_id", "source_system", "source_url", "school_year", "delivery_version", "source_archive",
        "source_archive_sha256", "source_file", "source_sha256", "source_row_number", "schema_version",
        "schema_fingerprint", "batch_id", "run_id", "ingested_at_utc", "code_revision",
    ]
    missing = " OR ".join(f"{column} IS NULL" for column in provenance)
    assert store.query(f"SELECT COUNT(*) FROM {PERSONNEL} WHERE {missing}")[0][0] == 0


def test_personnel_load_tolerates_new_nullable_control_columns(tmp_path):
    """The shared Databricks control tables may be upgraded by another branch first."""
    config = empty_config(SOURCE)
    deliver(tmp_path, config)
    repo = fake_repo(tmp_path / "repo", config)
    store = DuckDBStore()
    control.create_tables(store, repo)
    store.sql("ALTER TABLE edu_access.`01-control`.pipeline_runs ADD COLUMN future_nullable STRING")

    summary = run(store, repo, tmp_path)

    assert summary.status == "succeeded"
    assert store.query("SELECT future_nullable FROM edu_access.`01-control`.pipeline_runs") == [(None,)]
