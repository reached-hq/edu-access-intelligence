"""hdx_boundaries ADM3: one GeoJSON file per delivery, through the same pipeline as DepEd.

Made-up files (tests/factories/hdx_geojson.py) are approved into a copy of the
real contract, inside a throwaway repository root that runs the real etl/ SQL on
an in-memory DuckDB.
"""

import pytest

from factories.deped_deliveries import empty_config, fake_repo, registry_entry
from factories.hdx_geojson import GEOMETRY_TEXT, approve, columns, make_geojson, write_text
from src.ingestion.contract import validate_config
from src.ingestion.errors import IngestionError
from src.ingestion.geojson_features import prepare_geojson_delivery
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore
from src.ingestion.validate import FAIL, PASS

SOURCE = "hdx_boundaries"
REVISION = "c" * 40
BRONZE = "edu_access.`02-bronze`.hdx_adm3_raw"
CONTROL = "edu_access.`01-control`"


def prepare(config, path):
    return prepare_geojson_delivery(config, registry_entry(SOURCE), path)


def refused(code, fn, *args):
    with pytest.raises(IngestionError) as e:
        fn(*args)
    assert e.value.code == code, e.value
    return e.value


@pytest.fixture
def env(tmp_path):
    config = empty_config(SOURCE)
    landing = tmp_path / "landing"
    return config, landing, landing / "admin_boundaries", tmp_path / "repo"


def run(store, config, landing, repo_root, rerun=()):
    repo = fake_repo(repo_root, config)
    return IngestionRun(store, repo, SOURCE, landing, "local", REVISION, rerun_batch_ids=rerun).execute()


# --- One file, checked --------------------------------------------------------------

def test_a_delivery_passes_every_check(tmp_path):
    config = empty_config(SOURCE)
    path = make_geojson(tmp_path)
    approve(config, path, 3)
    prepared = prepare(config, path)
    assert (prepared.school_year, prepared.schema_version, len(prepared.header), len(prepared.rows)) == (
        "2025-02-13", "v1", 32, 3)
    assert [n for n, _ in prepared.rows] == [1, 2, 3]
    assert all(c.status == PASS for c in prepared.checks), prepared.checks


def test_values_are_kept_as_written(tmp_path):
    config = empty_config(SOURCE)
    path = make_geojson(tmp_path)
    approve(config, path, 3)
    prepared = prepare(config, path)
    row = dict(zip(prepared.header, prepared.rows[0][1]))
    assert row["area_sqkm"] == "112.2460"       # the file's digits, not a float
    assert row["geometry"] == GEOMETRY_TEXT     # the file's characters, not re-serialized
    assert row["adm3_name1"] is None            # JSON null stays NULL
    assert row["adm3_pcode"] == "PH9900001"


def test_property_order_drift_stops_the_delivery(tmp_path):
    config = empty_config(SOURCE)
    header = columns()
    header[0], header[4] = header[4], header[0]
    path = make_geojson(tmp_path, header=header)
    approve(config, path, 3)
    refused("unknown_schema_drift", prepare, config, path)


def test_a_wrong_reference_date_fails(tmp_path):
    config = empty_config(SOURCE)
    path = make_geojson(tmp_path, period="2024-01-01")
    approve(config, path, 3)  # approved as 2025-02-13
    checks = {c.check_name: c for c in prepare(config, path).checks}
    assert checks["valid_on_is_the_approved_period"].status == FAIL


def test_malformed_json_is_refused(tmp_path):
    config = empty_config(SOURCE)
    path = write_text(tmp_path / "phl_admin3.geojson", '{"type": "FeatureCollection", "features": [{"type": ')
    approve(config, path, 1)
    refused("malformed_geojson", prepare, config, path)


def test_a_feature_collection_is_required(tmp_path):
    config = empty_config(SOURCE)
    path = write_text(tmp_path / "phl_admin3.geojson", '{"type": "Feature", "properties": {}, "geometry": null}')
    approve(config, path, 1)
    refused("not_a_feature_collection", prepare, config, path)


def test_contract_refuses_a_geometry_column_that_is_not_last():
    config = empty_config(SOURCE)
    config["schema_versions"]["v1"]["columns"].insert(0, config["schema_versions"]["v1"]["columns"].pop())
    refused("invalid_config", validate_config, config, registry_entry(SOURCE))


# --- Through the pipeline -------------------------------------------------------------

def test_loads_once_and_a_rerun_skips(env):
    config, landing, inbox, repo = env
    approve(config, make_geojson(inbox), 3)
    store = DuckDBStore()

    first = run(store, config, landing, repo)
    assert (first.status, first.outcomes[0].action, first.outcomes[0].rows_inserted) == ("succeeded", "load", 3)
    second = run(store, config, landing, repo)
    assert (second.status, second.outcomes[0].action, second.outcomes[0].rows_inserted) == ("succeeded", "skip", 0)

    assert store.query(f"SELECT COUNT(*) FROM {BRONZE}")[0][0] == 3
    assert store.query(f"SELECT DISTINCT geometry FROM {BRONZE}") == [(GEOMETRY_TEXT,)]
    assert store.query(f"SELECT COUNT(*) FROM {BRONZE} WHERE adm3_name1 IS NULL")[0][0] == 3
    assert store.query(f"SELECT DISTINCT school_year, source_file FROM {BRONZE}") == [("2025-02-13", "phl_admin3.geojson")]


def test_rows_are_merged_in_chunks_without_duplicates(env):
    config, landing, inbox, repo = env
    config["max_stage_bytes"] = 1  # every row in its own MERGE
    approve(config, make_geojson(inbox, n=5), 5)
    store = DuckDBStore()
    assert run(store, config, landing, repo).status == "succeeded"
    bid = store.query(f"SELECT batch_id FROM {CONTROL}.ingestion_batches")[0][0]
    rerun = run(store, config, landing, repo, rerun=[bid])
    assert (rerun.outcomes[0].action, rerun.outcomes[0].rows_inserted) == ("rerun", 0)
    assert store.query(f"SELECT COUNT(*), COUNT(DISTINCT source_row_number) FROM {BRONZE}")[0] == (5, 5)


def test_an_unapproved_file_is_blocked(env):
    config, landing, inbox, repo = env
    make_geojson(inbox)  # not approved
    store = DuckDBStore()
    summary = run(store, config, landing, repo)
    assert (summary.outcomes[0].outcome, summary.status) == ("blocked", "failed")
    assert store.query(f"SELECT error_code FROM {CONTROL}.ingestion_batches")[0][0] == "unregistered_delivery"
    assert store.query(f"SELECT COUNT(*) FROM {BRONZE}")[0][0] == 0


def test_the_admin4_file_beside_it_is_ignored(env):
    config, landing, inbox, repo = env
    approve(config, make_geojson(inbox), 3)
    make_geojson(inbox, name="phl_admin4.geojson")
    summary = run(DuckDBStore(), config, landing, repo)
    assert [o.archive_name for o in summary.outcomes] == ["phl_admin3.geojson"]