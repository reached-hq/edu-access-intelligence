# Failure recovery and downstream rerun, local

## Scope

- Issue: #101
- Environment: local DuckDB only
- Data: made-up test deliveries, no repository or production data
- Command: `python -m pytest tests/test_local_job.py::test_a_gate_code_bug_is_fixed_and_recovered_by_rerun tests/test_local_job.py::test_a_second_run_changes_nothing tests/test_silver_hdx.py::test_a_rerun_builds_the_same_rows tests/test_gold_fact_school_enrollment.py::test_rerun_gives_the_same_table -q`
- Commit: the reviewed commit for this pull request

## Rehearsed failure

The local job test deliberately injects a made-up code bug into the DepEd enrollment Bronze gate after first publishing a good complete job build.

1. **Detect:** `90_validate_deped_enrollment_raw` returns failed and the whole local job exits nonzero.
2. **Diagnose:** `data_quality_results` records `made_up_code_bug` as FAIL for the enrollment lane and identifies the run, source, table, expected state, actual state, and code revision.
3. **Impact:** the failed lane's Silver task and every downstream task that depends on it are `upstream_failed`. The last good published Silver and Gold tables remain byte-for-byte equal at their business columns.
4. **Recover:** the gate is restored to its reviewed implementation and the same job is run again against the same isolated database. No control row, raw row, or published table is manually edited.
5. **Verify:** the repaired run succeeds with zero FAIL results, and the affected published Silver and Gold content equals the content from the initial good run.

This behavior is asserted by `test_a_gate_code_bug_is_fixed_and_recovered_by_rerun`.

## Same-input rerun at Silver and Gold

`test_a_second_run_changes_nothing` runs the complete enabled job twice against the same made-up deliveries and database. The second run succeeds, all eight Bronze deliveries are recorded as `skip`, and Bronze remains at three enrollment rows. The run also rebuilds and validates every enabled Silver and Gold task through the same job graph.

The layer-specific deterministic rebuild tests add direct checks of published contents:

- Silver: `tests/test_silver_hdx.py::test_a_rerun_builds_the_same_rows` rebuilds from the same current Bronze inputs and compares the published rows after both runs.
- Gold enrollment: `tests/test_gold_fact_school_enrollment.py::test_rerun_gives_the_same_table` rebuilds and validates the fact twice, then compares the full published table.
- Gold dimensions and other facts have the same rerun contract in their respective `tests/test_gold_*.py` modules.

## Result

- Focused result: 4 passed in 118.61 seconds.

- Observed: the failure is detected by a gate and contained to its dependency path.
- Observed: recovery uses the same idempotent job path, without manual table edits.
- Observed: the same current input produces the same published Silver and Gold content on rerun.
- Not tested here: Databricks-specific capacity timeout behavior or a `prod` recovery. The repository has no `prod` target until #99 is completed.
