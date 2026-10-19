# AP1 school-provision local validation

Issue #144 · local DuckDB · 2026-10-19 · made-up public data only

## Scope

The real Gold prerequisites are being reviewed in #193, #195, and #196, so this
record does not claim real-data results. It exercises the Analytics build and
gate with deliberately small Gold-shaped tables and is **observed local test
evidence**. A real local and Databricks run remain required after those branches
merge.

## Command and result

- `python -m pytest tests/test_analytics_ap1.py -q -p no:cacheprovider`
- 7 passed
- `python -m pytest tests -q`
- 1,095 passed, 1 skipped in 1,255.60 seconds

## Cases proved

- Two active public schools in one LGU count once at `ALL`; the annex also
  counts, and the school with incomplete JHS enrollment is excluded from the
  all-level learner numerator and denominator but retained in coverage.
- Level rows count the active multi-level schools in each offered level.
- Population is fixed to reference year 2024 and divides by the full active
  public-school count, not the level-specific count.
- Two regular barangays reconcile as one served and one without a matched
  active public ES school. An active ES school on `<city>-UNKNOWN` makes the
  result an upper bound without serving a regular barangay.
- An LGU with no active public school and unavailable population is retained
  with NULL ratios and an explicit reason.
- A changed but internally plausible school count fails the independent fact
  reconciliation and leaves the last good published output unchanged.
- Changed barangay and population values fail their independent Gold
  reconciliations even when the derived percentage or ratio is changed with them.
- Running the same input twice produces identical ordered rows.

## Pending real-data evidence

- Merge #193 (`dim_city_municipality`, `dim_barangay`), #195
  (`fact_city_population`), and #196 (`fact_school_enrollment`).
- Run the full local job twice and record output rows, school and learner
  reconciliation, barangay totals, upper-bound LGUs, PASS/WARN/FAIL counts, and
  an ordered-table checksum.
- Run the exact reviewed commit on Databricks `dev` and record the job run ID.
