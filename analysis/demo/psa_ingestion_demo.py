# Demonstration: PSA Poverty Stat ingestion is incremental, idempotent, and traceable.
#
# Runs the real pipeline (src/ingestion), the real control and Bronze SQL (etl/), and the
# real psa_poverty_stat contract's rules, on MADE-UP workbooks in a temporary folder, with
# an in-memory DuckDB. No raw data, no credentials, no Databricks. Safe to run any number
# of times; it leaves nothing behind.
#
# Run it cell by cell in VS Code (# %% cells), or all at once from the repository root:
#
#   python analysis/demo/psa_ingestion_demo.py
#
# The same story is asserted, not just printed, in tests/test_ingestion_psa.py.

# %% Setup: a throwaway repository root and landing folder
import inspect
import sys
import tempfile
from pathlib import Path

REPO = Path(inspect.currentframe().f_code.co_filename).resolve().parents[2]
sys.path[:0] = [str(REPO), str(REPO / "tests")]

from factories.psa_workbooks import (  # noqa: E402  (made-up workbooks shaped like the real one)
    WORKBOOK, add_schema, approve, default_rows, empty_config, fake_repo, write_config, write_workbook,
)
from src.ingestion.pipeline import IngestionRun  # noqa: E402
from src.ingestion.store import DuckDBStore  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="psa_demo_"))
landing, inbox = tmp / "landing", tmp / "landing" / "psa"
config = empty_config()                       # the real contract's rules, no approved deliveries yet
repo = fake_repo(tmp / "repo", config)
store = DuckDBStore()                          # in memory
CONTROL, BRONZE = "edu_access.`01-control`", "edu_access.`02-bronze`.psa_poverty_stat_raw"
REVISION = "demo" + "0" * 36


def run(title, **kwargs):
    summary = IngestionRun(store, repo, "psa_poverty_stat", landing, "local", REVISION, **kwargs).execute()
    print(f"\n== {title}: run {summary.run_id[:8]} {summary.status.upper()}")
    for o in summary.outcomes:
        print(f"   {o.archive_name:44} years={o.school_year or '-':15} {o.action:6} {o.load_type or '-':11} "
              f"{o.outcome:9} inserted={o.rows_inserted if o.rows_inserted is not None else '-'}")
        if o.outcome in ("failed", "blocked"):
            print(f"      reason: {o.message[:160]}")
    return summary


def show(title, sql):
    print(f"\n-- {title}")
    for row in store.query(sql):
        print("  ", row)


def approve_and_save(path, **kwargs):
    approve(config, path, **kwargs)
    write_config(repo, config)      # in real life: a reviewed pull request, never the pipeline


# %% 1-2. First delivery: approve the workbook, load it, record its batch and row counts
first = write_workbook(inbox / "original" / WORKBOOK)
approve_and_save(first)
run("Run 1, first delivery")
show("batch manifest", f"SELECT batch_id, estimate_years_covered, load_type, status, expected_rows, source_rows, bronze_rows "
                       f"FROM {CONTROL}.ingestion_batches")
show("every sheet row lands in Bronze, by kind (title, header, units, banners, footer reconciled separately)",
     f"SELECT source_row_kind, COUNT(*) FROM {BRONZE} GROUP BY 1 ORDER BY 1")

# %% 3-5. The exact same ingestion again: skipped, nothing inserted, and the audit log says so
run("Run 2, same files")
show("attempts log", f"SELECT left(run_id, 8), action, outcome, rows_inserted FROM {CONTROL}.ingestion_batch_attempts "
                     "ORDER BY started_at_utc")
show("pipeline duplicates (expect 0)", f"SELECT COUNT(*) - COUNT(DISTINCT source_sha256 || ':' || source_row_number) FROM {BRONZE}")

# %% 6. A new estimate year (2025) arrives as its own workbook: incremental, nothing rebuilt
add_schema(config, "v2", ["2025"])
new = write_workbook(inbox / "2028-02-15" / "2_2025 SAE_with PSGC_noHUC_01Feb2028.xlsx", years=("2025",),
                     rows=default_rows(("2025",), first_id=99201))
approve_and_save(new, years=("2025",), rows=default_rows(("2025",), first_id=99201),
                 logical_dataset="sae_city_municipal_2025", schema_version="v2")
run("Run 3, new year 2025")
# A later backfill of an older year (2015) behaves the same way, with load_type = backfill.
show("rows per delivery, and the run that inserted them (2018-2023 untouched)",
     f"SELECT estimate_years_covered, COUNT(*), COUNT(DISTINCT run_id) FROM {BRONZE} GROUP BY 1 ORDER BY 1")

# %% 7. Same file name, different bytes (a re-download PSA changed): blocked, not treated as the original
write_workbook(inbox / "2026-12-01" / WORKBOOK, rows=default_rows()[:-1])
run("Run 4, changed workbook under the approved name")
show("nothing overwritten", f"SELECT estimate_years_covered, delivery_version, COUNT(*) FROM {BRONZE} GROUP BY 1, 2 ORDER BY 1")
show("the blocked file", f"SELECT batch_id, status, load_type, error_code FROM {CONTROL}.ingestion_batches WHERE status = 'blocked'")

# %% Failure and recovery: a crash after the Bronze write, then a retry
import shutil  # noqa: E402

shutil.rmtree(inbox / "2026-12-01")           # set the changed file aside for this part
add_schema(config, "v2015", ["2015"])
old = write_workbook(inbox / "2026-11-01" / "2_2015 SAE_with PSGC_noHUC_01Jan2017.xlsx", years=("2015",),
                     rows=default_rows(("2015",), first_id=99301))
approve_and_save(old, years=("2015",), rows=default_rows(("2015",), first_id=99301),
                 logical_dataset="sae_city_municipal_2015", schema_version="v2015")


class Crash(BaseException):
    pass


def crash(stage):
    if stage == "after_bronze_merge":
        raise Crash()


try:
    run("Run 5, backfill 2015, process dies after the MERGE", hook=crash)
except Crash:
    print("\n== Run 5 crashed after writing Bronze, before marking the batch succeeded")
show("the 2015 batch is stuck in 'loading', and downstream cannot see it",
     f"SELECT b.estimate_years_covered, b.status, c.batch_id IS NOT NULL AS visible_downstream "
     f"FROM {CONTROL}.ingestion_batches b LEFT JOIN {CONTROL}.current_batches c USING (batch_id) ORDER BY 1")
run("Run 6, the same command again")
show("recovered without duplicates", f"SELECT estimate_years_covered, COUNT(*), COUNT(DISTINCT source_row_number) "
                                     f"FROM {BRONZE} GROUP BY 1 ORDER BY 1")

# %% Where one Bronze row came from
show("row from Excel line 9 of the first workbook (a unit with no estimates: blank, not 0)", f"SELECT source_file, left(source_sha256, 12), source_sheet, source_row_number, "
     f"source_row_kind, \"PSGC ID\", \"Municipality/City\", \"Poverty Incidence 2023\", left(batch_id, 40), left(run_id, 8) "
     f"FROM {BRONZE} WHERE source_row_number = 9 AND estimate_years_covered = '2018,2021,2023'")
show("known publisher issues recorded as WARN (not corrected)",
     f"SELECT DISTINCT check_name, actual, expected FROM {CONTROL}.data_quality_results WHERE status = 'WARN' ORDER BY 1")

# %% Clean up
store.close()
shutil.rmtree(tmp)
