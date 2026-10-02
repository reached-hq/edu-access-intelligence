# deped_personnel: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-02 |
| Profiled by | @mafelisilda |
| Tool | Python standard library, run locally: [`notebooks/profiling/profile_deped_personnel.py`](../../../notebooks/profiling/profile_deped_personnel.py) |
| Files profiled (SHA-256) | `personnel_2023-24.csv`: `5d0dd4a244fc13401787d32f84f21ab5af295bf808f037a3f762efff7d6ed6c5`; official ZIP `README.md`: `e2aecfdb0a94d748e75d9d3b2846012185ba68533be0ce66b964bd7ae81afb93` |
| How files were read | CSV columns read as UTF-8 text with strict checksum verification; whitespace trimmed only for profiling; blanks retained as missing, not zero |
| Official-source verification | Official ZIP: `9d1e5adfc33d67244f0d1a796f1b8b1930f5704eadf9f901008da68d7764a817`; both ZIP members are byte-identical to the supplied files |
| Additional documentation reviewed | [School Characteristics Technical Notes](https://www.deped.gov.ph/wp-content/uploads/School-Characteristics-Technical-Notes.pdf), SHA-256 `a0cb8728a4b175e6eba493fa0d06146c10db9064bc3c71807162fd9266f39cbc` |

## How to rerun

```powershell
$env:DEPED_PERSONNEL_DIR = "<folder-containing-personnel-csv-and-readme>"
$env:DEPED_ENROLLMENT_CSV = "<path-to-enrollment_2023-24.csv>"
python notebooks/profiling/profile_deped_personnel.py
```

The enrollment input is optional for dictionary generation and required to reproduce finding O-2.

## Summary

Usable for SY 2023-24 public-school staffing analysis after outlier quarantine and explicit missing-value handling. The source has a clean school key and complete alignment with SY 2023-24 enrollment, but public-only measure coverage, ambiguous blanks, inconsistent SHS principal totals, and extreme locally funded counts prevent unqualified production acceptance.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | `school_id` is a clean candidate key | 60,167 rows; 0 blank or invalid six-digit IDs; 0 duplicate IDs; 0 fully duplicate rows | Supports one row per school | Assert format and uniqueness on every load; fail on violation |
| O-2 | One-to-one alignment with SY 2023-24 enrollment | 60,167 shared IDs; 0 personnel-only; 0 enrollment-only; 0 differences in `sector`, `school_management`, or the three `offers_*` flags | Enrollment can provide geography and ratio denominators | Enforce referential integrity and school-year equality in integration |
| O-3 | Personnel measures cover public schools only | Technical Notes p. 12 says the data refer to personnel actually working in public schools. Public: 47,817 of 47,818 rows have at least one filled measure and 47,702 have a nonzero measure. Private: 0 of 12,113; SUC/LUC: 0 of 203; PSO: 0 of 33 | Non-public staffing comparisons are unsupported | Enforce the documented public-school scope |
| O-4 | Measure cells are sparse and dominated by recorded zeros | Across 19,313,607 measure cells, 5,372,726 are filled and 13,940,881 are blank. Of filled cells, 5,108,840 are zero and 263,886 are nonzero | Simplistic averages and blanket zero-filling will be biased | Preserve blank and zero separately; report coverage with every aggregate |
| O-5 | Level applicability is internally consistent | 0 filled ES, JHS, or SHS measure cells occur where the corresponding `offers_*` flag is false | Offering flags can support applicability validation | Keep this as a load-time assertion |
| O-6 | Numeric domains are structurally valid | Across 321 personnel columns, 0 non-whole-number cells and 0 negative cells | Values can be typed as nullable integers | Cast after validation; retain raw text in Bronze |
| O-7 | One documented field is entirely blank | `shs_master_teacher_iv`: 0 filled values among 60,167 rows and among 12,793 SHS-offering schools | The role cannot be analyzed | Alert on all-blank columns |
| O-8 | The SHS principal total is not a simple sum of documented components | Of 7,741 populated `shs_total_school_principal` rows, 6,651 equal the sum of grades I–IV and 1,090 are exactly one greater | Recomputed totals would disagree with the publisher field | Retain both values; flag discrepancies; seek the total's business rule |
| O-9 | Extreme locally funded counts indicate likely accuracy errors | Maxima: `es_learning_support_aide_other_funding` 5,000; `jhs_administrative_aide_other_funding` 7,435; `shs_administrative_aide_lgu_funding` 20,104; `shs_administrative_assistant_lgu_funding` 27,573. Nationally funded maxima are far lower, led by `jhs_teacher_i` at 330 | A few values can dominate sums and ratios | Quarantine extreme records pending source confirmation; monitor robust percentiles and maxima |
| O-10 | Documentation covers all 327 delivered columns | 159 columns are individually listed and 168 follow the documented `LEVEL_ROLE_FUNDING-SOURCE` convention | Column meaning and BEIS lineage are traceable, but extraction metadata remain absent | Generate convention-based descriptions and preserve documentation checksums |
| O-11 | No direct personal data is present | Fields contain school identifiers, school categories, offering flags, and aggregate counts only | Low privacy risk relative to person-level personnel data | Classify as public aggregate institutional data, pending license verification |
| O-12 | BEIS is the upstream personnel source | Technical Notes p. 1 states that BEIS collects school-level personnel data; pp. 2–3 identify profile forms and school heads as the responsible encoders starting SY 2023-24 | Lineage and accuracy risk are now attributable to a named source and collection process | Record `BEIS` in provenance; retain extract and load metadata |
| O-13 | These are working-personnel counts, not plantilla inventory | Technical Notes p. 12 distinguishes BEIS human-resource data from DBM PSIPOP records generated in GMIS | Vacancy, authorized-position, and plantilla analyses would be invalid | Label measures as personnel actually working; do not infer authorized or vacant posts |
| O-14 | DepEd's teacher-learner ratio requires annex consolidation | Technical Notes p. 8 defines the ratio as total enrollment divided by total teachers and requires annex values to be added to the mother school first | Direct row-level ratios can diverge from DepEd's method | Require a verified annex-to-mother crosswalk and aggregate both numerator and denominator before division |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | Blank and zero carry different operational meanings, but blanks combine not-applicable and unavailable cases | Obtain DepEd's extraction rules and compare a sample with source-system records | open |
| S-2 | Extreme locally funded values are data-entry, misplaced-decimal, or unit errors | Verify the source records and compare with adjacent school years or jurisdiction totals | open |
| S-3 | `shs_total_school_principal` includes a principal category not represented by the four grade fields | Obtain the total's calculation rule and inspect the 1,090 discrepant schools against source records | open |
| S-4 | The one public school with every personnel measure blank is an incomplete report rather than a true zero-staff school | Cross-check its enrollment, operating status, and source submission status | open |

## Changes across files or years

Only SY 2023-24 was supplied, so schema and value drift cannot be assessed.

## Questions for the publisher or mentor

- What extraction date and publication schedule apply to the BEIS personnel extract?
- Precisely when does blank mean not applicable, not collected, suppressed, or unknown, and when is zero explicitly reported?
- Why is `shs_master_teacher_iv` present but entirely blank?
- What does `shs_total_school_principal` include beyond the four documented component grades?
- Are counts headcounts, full-time equivalents, positions, assignments, or occupied plantilla items, and can one person appear in more than one field?
