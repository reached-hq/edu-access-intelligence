# deped_ellna: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-03 |
| Profiled by | @mafelisilda |
| Tool | DuckDB and Python: [`analysis/profiling/profile_deped_ellna.py`](../../../../analysis/profiling/profile_deped_ellna.py) |
| Files profiled (SHA-256) | `ellna_2023-24_selected.csv`: `a379ccd0cf48bf3ff1174fc76374627bd92f71d31f49fa73e59c9f57b1390dc2` |
| How files were read | ZIP members verified independently; CSV loaded into DuckDB as UTF-8 text; all fields initially retained as text; exact schema validated before integer and score conversion |

## How to rerun

```powershell
$env:RAW_DATA_DIR = "C:\path\to\raw-data"
python notebooks\profiling\profile_deped_ellna.py
```

Place `Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip` in `$env:RAW_DATA_DIR\deped\original\`. The script reports an outer-ZIP checksum difference, then independently verifies the CSV and README members. This permits detection of repackaging without accepting changed source content.

## Summary

Usable as a school-level profile of the selected SY 2023-24 ELLNA results after preserving structural nulls and applying small-n safeguards. The 5,752 rows have unique school identifiers, valid numeric types, no unexpected score nulls, and all scores within 0 to 100. The main limitations are undocumented selection, coverage of only five regions, 1,016 schools with 10 or fewer test takers, insufficient inputs to independently recalculate `overall_mps`, and a suspected Numeracy scale or encoding anomaly affecting 98 schools.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | The supplied CSV has verified official lineage | Its SHA-256 is identical to `ellna_2023-24_selected.csv` inside the official DepEd ZIP; the archive checksum is recorded in the source card | Supports traceability to the publisher delivery | Stop on checksum mismatch and re-inventory publisher revisions |
| O-2 | The apparent school grain is unique | 5,752 rows, 5,752 distinct six-digit `school_id` values, 0 duplicate candidate keys, and 0 duplicate full rows | Supports one row per selected school | Enforce uniqueness before loading |
| O-3 | The selected extract is geographically incomplete | 5 regions: CAR, I, III, VIII, and IX; 44 divisions. Region counts are 527, 1,107, 1,364, 1,962, and 792 respectively | Results cannot be generalized nationally from this file | Publish a coverage matrix and block national claims |
| O-4 | The underlying administration and public extract have different scopes | Technical Notes page 3 describes SY 2023-24 as census of schools and learners; the official archive README says the file contains selected schools only | The public subset may not represent the assessment population | Obtain the selection method, inclusion criteria, and complete population counts |
| O-5 | Required identifiers and dimensions are complete | 0 blanks in `school_id`, `region`, `division`, `language`, and `n_test_takers`; every division label maps to one region in this file | No imputation is required for identifying fields | Fail on missing identifiers or division-region ambiguity |
| O-6 | Score blanks follow documented non-applicability rules | `numeracy_mps`: 154 blanks, exactly the 154 `English/Filipino` rows. `mother_tongue_mps`: 1,925 blanks, exactly 154 `English/Filipino` plus 1,771 `Tagalog` rows. No unexpected blanks | Nulls have semantic meaning and are not failed or zero scores | Preserve as not applicable and test the rules on refresh |
| O-7 | Numeric values pass domain checks | 0 invalid numeric values; all five MPS fields are within 0 to 100; `n_test_takers` ranges from 1 to 674 with no zero or negative values | Supports numeric typing | Make type and range checks blocking controls |
| O-8 | The extract represents 218,296 reported test takers | Sum of `n_test_takers` across the 5,752 selected school rows is 218,296; median 24 | Provides a selected-extract denominator, not a national learner count | Label all aggregates as selected-school results |
| O-9 | Small denominators are common | 26 schools report 1 test taker, 329 report 5 or fewer, and 1,016 report 10 or fewer | School MPS is unstable for small groups and may disclose an individual result when n=1 | Apply approved minimum-n reporting and access controls |
| O-10 | Scores use excessive display precision | MPS text contains as many as 16 decimal places | Raw computational precision can imply false measurement certainty | Preserve raw values; derive rounded presentation values under an explicit rule |
| O-11 | Overall MPS is not a simple component average | `overall_mps` differs from the unweighted mean of available English, Filipino, Numeracy, and Mother Tongue MPS in 5,595 of 5,752 rows. The README defines it as total points correct over total possible points | Recomputing it as an average would silently change the measure | Use the published value; obtain raw point totals and weighting rules for independent validation |
| O-12 | Language labels need governance | 9 distinct values; `Ilokano/Iloko-Pangasinense` and `Yakan` each occur once, and `English/Filipino` is a distinct documented non-applicability group | Uncontrolled normalization could change null rules or group meaning | Preserve raw labels and obtain an official controlled vocabulary |
| O-13 | The file lacks row-level temporal and release provenance | School year and selected status occur in the filename or README, not in the 10 CSV columns; no release version or assessment date is present | Combining deliveries can lose lineage | Add derived lineage columns during ingestion |
| O-14 | No direct personal identifiers are published, but small cells remain sensitive | Rows contain institutional identifiers and aggregate scores; 26 rows have one test taker | Public availability does not eliminate re-identification or reputational risk | Classify as Public with small-cell safeguards |
| O-15 | Near-zero Numeracy values form a concentrated, cross-component anomaly | 98 schools covering 3,157 test takers have `numeracy_mps` below 1 while English and Filipino are at least 30. Of these, 27 are exact zero and 71 are nonzero values below 1. The largest clusters are Ifugao (19), Zamboanga del Norte (17), Samar (Western) (12), and Leyte (11). School `106410`, for example, reports 169 test takers, English 86.42, Filipino 84.40, Numeracy 0, and Mother Tongue 0.07 | The pattern may reflect genuine scores, inconsistent percentage scaling, or another encoding issue; the published file alone cannot distinguish them | Retain the published values, flag the 98 rows, and exclude them from Numeracy comparisons until DepEd confirms their meaning |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The five-region selection may be purposive rather than probabilistic | Obtain the publisher's selection documentation and compare the 5,752 IDs with the full SY 2023-24 ELLNA school universe | open |
| S-2 | Some `school_id` values may refer to schools whose current region, division, or operational status has changed | Join to a school master effective at the assessment date and compare with current DepEd master data | open |
| S-3 | Compound language labels may represent multilingual administration, a combined test form, or a local encoding convention | Request the publisher's language codebook and test-form mapping | open |
| S-4 | Decimal proficiency boundaries may require rules not stated in the Technical Notes | Ask BEA how values between integer labels, such as 89.5, are categorized and whether MPS is rounded before classification | open |
| S-5 | Public reporting of rows with one test taker may require suppression despite the source being publicly downloadable | Confirm applicable DepEd disclosure-control and assessment-data-use policies | open |
| S-6 | The 98 near-zero Numeracy values may use a 0-to-1 scale or another encoding in rows otherwise expressed on a 0-to-100 scale | Ask DepEd BEA to validate the affected school IDs against source scoring records and confirm the unit, missing-value convention, and correction policy | open |

## Changes across files or years

Only the selected SY 2023-24 CSV was supplied and profiled. The Technical Notes document material changes in administration across years: ELLNA used sampled schools with census learners in SY 2016-17 and 2017-18; assessments were disrupted or postponed during the pandemic; the SY 2021-22 administration used test materials intended for SY 2018-19; no assessment occurred in SY 2022-23; and SY 2023-24 was administered in May 2024 as a census of schools and learners. The publisher also warns that changes in test difficulty can make percent-correct scores invalid for trend descriptions. Cross-year comparisons therefore require test-form comparability evidence, consistent population scope, and separate profiling of each delivery.

## Questions for the publisher or mentor

- How were the 5,752 schools and five regions selected for the public file, and what population does the extract represent?
- Is a complete SY 2023-24 school-level file or selection-weight file available?
- What raw point totals, item counts, or weights produce each component MPS and `overall_mps`?
- What rounding precision and decimal-boundary rules apply when assigning proficiency levels?
- What do the compound language labels represent, and is there an official controlled vocabulary?
- Which dated school master should be used to validate `school_id`, region, and division?
- What minimum test-taker threshold and disclosure-control rules apply to school-level publication?
- Are the 98 Numeracy values below 1 valid 0-to-100 scores, decimal proportions requiring rescaling, or missing/error values, and should the affected records be corrected?
- What license, reuse, refresh, correction, and versioning terms govern the machine-ready assessment files?
