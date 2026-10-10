"""Personnel Silver typing, flags, quarantine, reconciliation, and publishing."""

import uuid

from factories.deped_deliveries import approve, columns, empty_config, fake_repo, make_delivery, make_rows, write_config
from src.ingestion.pipeline import IngestionRun
from src.ingestion.store import DuckDBStore

REVISION = "c" * 40
CONTROL = "edu_access.`01-control`"
CLEAN = "edu_access.`03-silver`.deped_personnel_clean"
QUARANTINE = "edu_access.`03-silver`.deped_personnel_quarantine"


def blank_measures(source, rows):
    header = columns("v1", source)
    dimensions = {"school_id", "school_name", "region", "division", "province", "school_district", "legislative_district",
                  "municipality", "barangay", "street_address", "sector", "school_management", "annex_status",
                  "Modified Curricular Offering Classification", "offers_es", "offers_jhs", "offers_shs"}
    for row in rows:
        for i, column in enumerate(header):
            if column not in dimensions:
                row[i] = ""
    return header, rows


def set_values(header, row, values):
    for column, value in values.items():
        row[header.index(column)] = value


def test_personnel_silver_preserves_values_flags_findings_and_reconciles(tmp_path):
    landing = tmp_path / "landing"
    enrollment_config = empty_config("deped_enrollment")
    enrollment_header, enrollment_rows = blank_measures("deped_enrollment", make_rows(columns("v1", "deped_enrollment")))
    for row, total in zip(enrollment_rows, (10, 10, 3)):
        set_values(enrollment_header, row, {"g1_male": str(total)})
    enrollment_zip = make_delivery(landing / "deped" / "original", "2023-24", source_id="deped_enrollment",
                                   header=enrollment_header, rows=enrollment_rows)
    approve(enrollment_config, enrollment_zip, "2023-24")

    personnel_config = empty_config("deped_personnel")
    personnel_header, personnel_rows = blank_measures("deped_personnel", make_rows(columns("v1", "deped_personnel")))
    set_values(personnel_header, personnel_rows[0], {"es_master_teacher_i": "0"})
    set_values(personnel_header, personnel_rows[1], {"offers_shs": "True", "shs_school_principal_i": "1",
                                                     "shs_total_school_principal": "2"})
    set_values(personnel_header, personnel_rows[2], {"es_master_teacher_i": "5"})
    personnel_zip = make_delivery(landing / "deped" / "original", "2023-24", source_id="deped_personnel",
                                  header=personnel_header, rows=personnel_rows)
    approve(personnel_config, personnel_zip, "2023-24")

    repo = fake_repo(tmp_path / "repo", personnel_config)
    write_config(repo, enrollment_config)
    store = DuckDBStore()
    for source in ("deped_enrollment", "deped_personnel"):
        summary = IngestionRun(store, repo, source, landing, "local", REVISION).execute()
        assert summary.status == "succeeded"

    params = {"run_id": str(uuid.uuid4()), "code_revision": REVISION, "environment": "local"}
    silver = repo / "etl" / "03_silver"
    store.run_file(silver / "01_clean_deped_enrollment.sql", params)
    store.run_file(silver / "90_validate_deped_enrollment_clean.sql", params)
    params["run_id"] = str(uuid.uuid4())
    store.run_file(silver / "03_clean_deped_personnel.sql", params)
    store.run_file(silver / "90_validate_deped_personnel_clean.sql", params)

    assert store.query(f"SELECT COUNT(*) FROM {CLEAN}") == [(2,)]
    assert store.query(f"SELECT COUNT(*) FROM {QUARANTINE}") == [(1,)]
    assert store.query(f"SELECT es_master_teacher_i FROM {CLEAN} WHERE school_id = '900001'") == [(0,)]
    assert store.query(f"SELECT shs_master_teacher_iv, shs_master_teacher_iv_unavailable FROM {CLEAN} ORDER BY school_id") == [(None, True), (None, True)]
    assert store.query(f"SELECT shs_total_school_principal, shs_school_principal_calculated, shs_principal_total_discrepancy FROM {CLEAN} WHERE school_id = '900002'") == [(2, 1, True)]
    assert store.query(f"SELECT array_contains(quarantine_reasons, 'personnel_exceeds_enrollment'), enrollment_outlier_fields[1] FROM {QUARANTINE}") == [(True, "es_master_teacher_i")]
    assert store.query(f"SELECT check_name, actual FROM {CONTROL}.data_quality_results WHERE run_id = '{params['run_id']}' AND check_name IN ('principal_total_discrepancies', 'enrollment_outlier_rows') ORDER BY check_name") == [("enrollment_outlier_rows", "1"), ("principal_total_discrepancies", "1")]
