# Evidence: deped_psgc_coordinates Silver reconciles to Bronze on the real workbook, keeps only school locations, and rebuilds identically

Issue #217 · local run (DuckDB) only; nothing has run on Databricks · 2026-10-21 · checked by @catweyine

## The claim

On the real public-only workbook, `deped_psgc_coordinates_clean` has one row per public school, 47,818, with 0 quarantined. Every row reconciles to its Bronze row. All 35 gate checks pass, and a second build gives identical content. It keeps 15 value columns: the key, the four PSGC codes and their flags, and the coordinates. The 73 other workbook columns stay in Bronze; each one is shown below to repeat another source or to be unused. Every PSGC code it keeps is in the PSGC 2Q 2026 master.

**Not claimed:** anything on Databricks, and anything about whether a coordinate is the right place (profile S-1).

## What was run

Commit `6b31e5e51d9982f61e0f09c171e851392c2f0536` on `feat/217-deped-psgc-coordinates-silver`, clean worktree. macOS 26.4.1, Python 3.12.14, DuckDB 1.4.5. A new, empty DuckDB file in a scratch folder.

1. Bronze, the real workbook (SHA-256 `edf7ba68…fc8a1`, checked by the loader): `python -m src.ingestion.cli ingest --source deped_psgc_coordinates`. Result: `load initial succeeded`, 47,818 rows inserted, all of kind `unit`.
2. PSGC master, for the reference check only: `python -m src.ingestion.cli ingest --source psa_psgc`. Result: `2026-Q2`, 43,768 rows.
3. Silver, twice, with `run_id` `silver-ev-1` then `silver-ev-2` and `code_revision` = the commit: `etl/03_silver/09_clean_deped_psgc_coordinates.sql`, then `etl/03_silver/90_validate_deped_psgc_coordinates_clean.sql`.

## Results

### Rows and the gate

| | Run 1 | Run 2 |
|---|---|---|
| Bronze unit rows | 47,818 | 47,818 |
| Clean / quarantine | 47,818 / 0 | 47,818 / 0 |
| Gate checks | 35 PASS | 35 PASS |
| `pipeline_runs` | `succeeded` | `succeeded` |
| Content hash (all columns except the run stamp) | `a477eb4d576a…` | `a477eb4d576a…` (identical) |

The FAIL checks that passed:
- `rows_reconcile`: Bronze unit rows = clean + quarantine.
- `rows_resolve_to_current_bronze`.
- `values_reconcile`: every value recomputed from its Bronze row.
- `coordinates_reconcile`, `school_id_unique`, `school_id_format`, `codes_ten_digits`, `code_values_recognized`, `region_province_values_recognized`, `null_reason_matches_code`, `levels_null_together`, `coordinates_in_pairs`, `coordinate_values_recognized`.
- `rows_in_scope`: no clean row outside SY 2023-24 or `Public`.
- `lineage_complete`, `rows_built_by_this_run`, `current_batch_present`, `quarantine_rate`.

All rows carry one `batch_id`, one `run_id` and the commit as `code_revision`.

### What the rules did (each is also a profiled gate check)

| Rule | Rows |
|---|---:|
| Barangay code padded from 9 to 10 digits | 28,811 |
| City and barangay code `#N/A` → NULL, `source_na` | 204 |
| Sulu recoded (`19066…` → `09066…`) | 446 |
| Barangay outside its city or municipality (flagged, kept) | 2 |
| `coordinate_flag` NULL / `missing` / `outside_philippines` / `zero` | 47,080 / 679 / 54 / 5 |
| Quarantined: malformed or repeated ID, other school year, not `Public` | 0 |

### PSGC codes against the master

Silver makes no join; Integration does (D-049). This check was run separately, against `psa_psgc_raw` 2026-Q2 (43,768 codes, 0 repeated):

| | With a code | In PSGC 2Q 2026 |
|---|---:|---:|
| Barangay | 47,614 | 47,614 |
| City or municipality | 47,614 | 47,614 |
| Recoded Sulu barangays | 446 | 446 |

A left join of the clean table to the master on the barangay code keeps 47,818 rows: no school is multiplied.

### Coordinates are each school's point

Of the 47,080 unflagged points, 126 coordinate pairs are shared by more than one school (254 schools); every other school has a point of its own. With the profile's O-6 (40,046 within 10 km of their own city or municipality), this is consistent with school locations, not municipal centres. The workbook's note names the National School Building Inventory as of 2025-07-07.

### Columns not carried, and why (checked school by school against `deped_enrollment` SY 2023-24)

All 47,818 schools are in `enrollment_2023-24.csv` (0 missing).

| Workbook columns | Compared with `deped_enrollment` | Result |
|---|---|---|
| 58 counts (`pbm` = `maritime`) | the same 58 columns | equal for every school, 0 differences; the CSV's four `unique` columns are blank for all of them |
| `region`, `division`, `legislative_district`, `sector` | same columns | equal for every school |
| `school_name`, `district`, `province`, `municipality`, `barangay` | same columns (`district` = `school_district`) | equal ignoring case and spacing for all but 12 names (quote marks: `"Cory"` vs `'Cory'`) |
| `street_address` | same column | equal, except `-`, `n/a` and `N/A` where the CSV is blank |
| `school_subclassification`, `school_type` | `school_management`, `annex_status` | relabels: `DepED Managed`/`DepEd` 47,802, `School with no Annexes`/`Standalone School` 45,611, … |
| `modified_coc` | `offers_es`, `offers_jhs`, `offers_shs` | one to one for every school (e.g. `Purely ES` = True/False/False, 36,999) |
| `psgc_*_name`, `urban_rural`, `income_class`, `income_class_long` | `psa_psgc` through the code | reference data, already in Silver and Gold |
| `urp`, `implementing_unit`, `curricular_offering_classification` | none | unused by AP1 to AP4 |

## Same issues in other Silver tables

These were checked on 2026-10-21 and **not changed in this PR**, because each table has another owner.

1. **`deped_enrollment_psgc_clean` repeats `deped_enrollment` and keeps mojibake.**
   - It carries 14 published text columns: names, place names, `sector`, `urp`, and the four PSGC names. Integration (`01_map_deped_school_psgc`) reads only `school_id`, `psgc_city_municipality`, `psgc_barangay`, `psgc_recoded` and lineage from it.
   - Built locally from the real all-sector workbook, those columns hold **274 mojibake cells** (`barangay` 262, `school_name` 12). Its profile (O-13) proposed repairing them in Silver, but its rules keep the text unchanged.
   - Dropping the 14 columns, as done here, removes both problems.
2. **Two sets of coordinates for the same public schools.**
   - `deped_enrollment_psgc_clean` has usable coordinates for 38,688 of its 47,831 public schools; this table has them for 47,080.
   - For 47,536 schools the two differ, 35,866 by over 10 km (profile X-1).
   - Nothing downstream reads either yet. Which one Gold uses is a team decision.
3. **A delivery missing from the landing folder only WARNs in 7 of 9 contracts.** Only `psa_psgc` and this source set `require_approved_deliveries`.
   - Every Silver gate fails when a source has no current batch (`current_batch_present`), so a source with nothing loaded cannot pass.
   - A source with several deliveries can, though: `deped_enrollment` (6 school years) or `psa_school_age_population` (2 censuses) with one file missing would pass Silver with fewer years. Gold's `fact_school_year_source_availability` shows the gap, but no gate fails on it.
4. **No repeated columns in `deped_facilities_clean` or `deped_personnel_clean`.** They keep only `sector` and the `offers_*` flags from the shared columns, and Gold uses those for their own public-school filters.
5. **Leading zeros are kept everywhere checked.** `school_id` stays text in every DepEd Silver table, and `psa_psgc` accepts a code stored as a number only when it already has 10 digits.

## Not checked here

- The Databricks `dev` run of `09_clean_deped_psgc_coordinates` and its gate.
- Whether any coordinate is the right place: boundary test, profile S-1.
