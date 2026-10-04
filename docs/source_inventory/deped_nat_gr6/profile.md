# deped_nat_gr6: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-03 |
| Profiled by | @mafelisilda |
| Tool | Python standard library: [`notebooks/profiling/profile_deped_nat_gr6.py`](../../../notebooks/profiling/profile_deped_nat_gr6.py) |
| Files profiled (SHA-256) | `nat_2023-24_selected.csv`: `ddd3e019b0ad952cecce95566aff2ecb7b2b4ff4ce1135a2a1575b14f5f939bf` |
| How files were read | CSV parsed as UTF-8 text; all fields initially retained as text; exact schema and checksum validated before integer and score conversion |

## How to rerun

```powershell
$env:DEPED_NAT_GR6_FILE = "C:\path\to\nat_2023-24_selected.csv"
python notebooks\profiling\profile_deped_nat_gr6.py
```

## Summary

Usable as a descriptive school-level profile of the selected SY 2023-24 NAT Grade 6 release when small-n and sampling limitations are enforced. All 6,636 rows have unique school identifiers, complete values, valid numeric types, and scores within 0 to 100. The main risks are undocumented school selection, learner sampling without weights, coverage of only five regions, and 5,320 schools, or 80.2% of the file, with 10 or fewer test takers.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | File identity and publisher lineage are reproducible | CSV SHA-256 `ddd3e019...f939bf`; official ZIP SHA-256 `370eacc1...f2950f0`; publisher README and Technical Notes checksums are recorded in the source card | Supports immutable raw lineage | Stop on checksum mismatch and re-inventory publisher revisions |
| O-2 | The apparent school grain is unique | 6,636 rows, 6,636 distinct six-digit `school_id` values, 0 duplicate candidate keys, and 0 duplicate full rows | Supports one row per selected school | Enforce uniqueness before loading |
| O-3 | The selected extract is geographically incomplete | 5 regions: CAR, I, III, VIII, and IX; 44 divisions. School counts are 778, 1,250, 1,786, 2,027, and 795 respectively | Results cannot be generalized nationally from this file | Publish a coverage matrix and block national claims |
| O-4 | The underlying administration and public extract have distinct selection stages | Technical Notes page 7 describes SY 2023-24 as census of schools and sampling of learners; the archive README says the public file contains selected schools only | Unstated school selection and learner sampling prevent population inference | Obtain both selection designs, inclusion probabilities, and weights |
| O-5 | All source cells are complete | 0 blanks across 66,360 data cells; every division label maps to one region in this file | No null imputation is required | Fail ingestion on any blank or division-region ambiguity |
| O-6 | Numeric values pass domain checks | 0 invalid numeric values; all six MPS fields are within 0 to 100; `n_test_takers` ranges from 1 to 117 with no zero or negative values | Supports numeric typing | Make type and range checks blocking controls |
| O-7 | The extract represents 52,761 reported test takers | Sum of `n_test_takers` across 6,636 selected schools is 52,761; median is 6 | Provides only a selected-extract denominator | Label all aggregates as selected-school, sampled-learner results |
| O-8 | Small denominators dominate the file | The median school has 6 test takers. A total of 333 schools report 1 test taker, 1,375 report 2 or fewer, 3,153 report 5 or fewer, and 5,320, or 80.2%, report 10 or fewer | School MPS is highly unstable and may expose individual results | Apply minimum-n suppression and prohibit unsupported school rankings |
| O-9 | Scores use excessive display precision | MPS text contains as many as 16 decimal places | Raw computational precision can imply false measurement certainty | Preserve raw values; derive rounded presentation fields under an explicit rule |
| O-10 | Overall MPS differs slightly from the simple subject average | `overall_mps` differs from the unweighted mean of the five subject MPS values in 6,633 of 6,636 rows, but the median absolute gap is only 0.05 points and the maximum is 0.34 points. The README defines it as total points correct over total possible points | The numerical effect is small in this delivery, but replacing the published measure would still change its definition | Use the published value and obtain raw point totals and weighting rules |
| O-11 | Score distributions differ materially by subject | Medians: Filipino 66.67, Mathematics 55.77, English 65.43, Science 54.07, Araling Panlipunan 64.81, overall 61.57 | Subject comparisons may reflect different item counts or difficulty | Avoid causal or difficulty claims without test specifications and scaling evidence |
| O-12 | The file lacks sampling and release provenance | School year and selected status occur in the filename or README; grade, assessment date, sampling weight, release version, and extraction timestamp are absent from the 10 columns | Combining deliveries can lose lineage and invite unweighted inference | Add derived lineage fields and preserve archive metadata |
| O-13 | No direct personal identifiers are published, but small cells are sensitive | Rows contain institutional identifiers and aggregate scores; 333 rows have one test taker | Public availability does not eliminate re-identification or reputational risk | Classify as Public with strict small-cell safeguards |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The five-region public-school selection may be purposive rather than probabilistic | Obtain the publisher's selection documentation and compare the 6,636 IDs with the full SY 2023-24 NATG6 school universe | open |
| S-2 | Unweighted school or learner summaries from this file may be biased | Obtain learner sampling strata, probabilities, nonresponse adjustments, and final weights; reproduce official estimates | open |
| S-3 | Some `school_id` values may refer to schools whose current region, division, or operational status has changed | Join to a school master effective at the April 2024 assessment date and compare with current master data | open |
| S-4 | Decimal proficiency boundaries may require rules not stated in the Technical Notes | Ask BEA how values between integer labels, such as 89.5, are categorized and whether MPS is rounded before classification | open |
| S-5 | Public reporting of rows with one test taker may require suppression despite the archive being publicly downloadable | Confirm applicable DepEd assessment-data sharing and disclosure-control rules | open |

## Changes across files or years

Only the selected SY 2023-24 CSV was profiled. The Technical Notes document material changes in NATG6 administration: census schools and learners in SY 2016-17; sampled schools with census learners in SY 2017-18 and 2018-19; pandemic postponement; sampled schools and learners using a computer-based modality in SY 2020-21; sampled schools with census learners and older test materials in SY 2021-22; no assessment in SY 2022-23; and census schools with sampled learners in SY 2023-24. The publisher explicitly identifies changing test design and modality as cross-year comparability challenges. Trend analysis requires aligned constructs, modes, population definitions, and weights, plus separate profiling of every delivery.

## Questions for the publisher or mentor

- How were the 6,636 schools and five regions selected for the public file?
- What learner sampling strata, probabilities, nonresponse adjustments, and final weights apply?
- Is a complete school file, learner-weight file, or official weighted estimate available?
- What raw point totals, item counts, or weights produce each subject MPS and `overall_mps`?
- How do subject-labeled MPS values relate to the Technical Notes statement that NATG6 measures 21st-century skills using learning areas as content?
- What rounding precision and decimal-boundary rules apply when assigning proficiency levels?
- Which dated school master should validate `school_id`, region, and division?
- What minimum test-taker threshold and disclosure-control rules apply to school-level publication?
- What license, reuse, refresh, correction, and versioning terms govern the machine-ready assessment files?
