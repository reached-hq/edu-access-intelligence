# deped_facilities: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-09-29 |
| Profiled by | @hyenalouise |
| Tool | DuckDB 1.4.5 (Python), run locally: [`notebooks/profiling/profile_deped.py`](../../../notebooks/profiling/profile_deped.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if a zip's checksum differs |
| How files were read | Straight from the original zip, all columns as text (`all_varchar`), strict CSV parsing |

## How to rerun

```bash
RAW_DATA_DIR=~/Projects/reached-hq/raw-data python notebooks/profiling/profile_deped.py
```

The same script profiles `deped_enrollment`, because the join (O-2) and learners-per-room (O-8) checks need SY 2023-24 enrollment.

## Summary

Usable for public-school capacity in SY 2023-24. It joins one-to-one with SY 2023-24 enrollment on `school_id`, and every count is a valid whole number. Blanks are ambiguous (not applicable, missing, or possibly zero), and the "instructional classroom" definition differs from DepEd's official classroom-learner ratio.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | `school_id` is clean | 0 blank, 0 non-numeric, 0 not 6 digits, 0 duplicates, 0 fully duplicated rows | Safe primary key | Assert uniqueness in Bronze validation |
| O-2 | One-to-one with SY 2023-24 enrollment | 60,167 in both files; 0 only in enrollment; 0 only in facilities. `sector`, `school_management`, and `offers_*` agree for every school | Location can be taken from enrollment | Referential integrity check in integration |
| O-3 | Facility measures are public-only | Public: 47,818 rows, 38,677 with elementary classrooms, 47,817 with building counts. Private (12,113), SUC/LUC (203), PSO (33): 0 values in any facility count | Capacity analysis cannot include non-public schools | Scope the question to public schools; confirmed by Technical Notes p. 3, 12 |
| O-4 | Public elementary schools without a classroom count | 669 of 39,346 public schools offering elementary (1.7%) have a blank `es_classrooms_instructional`. Public schools offering JHS or SHS: 0 blanks | These schools would look like missing capacity | Flag, never treat as zero; count them in validation |
| O-5 | Zero elementary classrooms never recorded | 0 rows have `es_classrooms_instructional` = 0, while JHS has 1,030 zeros and SHS 286 | A blank might mean zero for elementary | Treated as ambiguous (see S-2) |
| O-6 | All counts are valid | 0 non-integer and 0 negative values in all 21 numeric columns | Safe to type as integers | Type in Silver; keep a range check |
| O-7 | Yes/no columns | Values are only `True`, `False`, or blank; 34.6% to 96.1% blank per column | Low coverage for amenity and access fields | Use only with coverage reported |
| O-8 | Learners per elementary instructional room (public schools, observed distribution only) | Using SY 2023-24 elementary enrollment: p5 11.5, median 25.9, p95 67.6, p99 127.0, max 987.0 (38,677 schools with rooms > 0). 3 schools have rooms but 0 elementary learners | Extreme values distort area averages | Investigate the upper tail before aggregating (S-1); no threshold is applied |
| O-9 | Instructional classroom definition | README counts ALS rooms, audio-visual, computer rooms, and laboratories as instructional; Technical Notes p. 11 uses Kindergarten to Grade 12 classrooms only | Ratios will understate crowding compared with DepEd's official figure | Name the metric by its NSBI definition; record in limitations |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The upper tail of learners per room (e.g. the 987 maximum) comes from classroom undercounts or shift-based schools, not real crowding | Inspect the top 1% of schools: annex status, temporary learning spaces, makeshift rooms | open |
| S-2 | A blank elementary classroom count sometimes means zero rooms | Check whether the 669 schools report temporary learning spaces or makeshift rooms | open |
| S-3 | Annex schools share classrooms with their mother school | Compare mother and annex schools' room counts and enrollment | open |

## Changes across files or years

Only SY 2023-24 is published, so no cross-year comparison is possible.

## Questions for the publisher or mentor

- Are facilities data for other school years available anywhere else?
- Does a blank `es_classrooms_instructional` mean "not reported" or "zero"?
