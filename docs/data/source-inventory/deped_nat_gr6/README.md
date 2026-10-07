# deped_nat_gr6: selected school-level NAT Grade 6 results

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | National Achievement Test Grade 6, selected school-level results, SY 2023-24 |
| Publisher / agency | Department of Education (DepEd), Bureau of Education Assessment (BEA) |
| Source system (as stated by the publisher) | National Achievement Test Grade 6 (NATG6) |
| Source URL or acquisition method | Manual download from the Assessment Data section of [DepEd Machine Ready Files](https://www.deped.gov.ph/machine-ready-files/); official archive: [NAT Grade 6 ZIP](https://www.deped.gov.ph/wp-content/uploads/National-Achievement-Test-NAT-Grade-6-2023-2024.zip) |
| Licensing or access restrictions | Public download. No explicit license or reuse terms were found in the archive or Technical Notes. The Technical Notes identify restrictive assessment-data sharing as a challenge; applicable terms remain **UNVERIFIED** |
| Owner (team member) | @mafelisilda |
| Date acquired | 2026-09-26 11:36 UTC |

## Files

Raw files are kept outside git. Row count excludes the CSV header.

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `National-Achievement-Test-NAT-Grade-6-2023-2024.zip` | Official publisher ZIP | n/a | 171,391 | n/a | `370eacc1b6ab5f8b8c36c7671a7300c4928255c9a98da4e752f61ba84f2950f0` | Databricks volume `/Volumes/edu_access/00-source/raw/deped/`; checksum verified 2026-10-06 |
| ↳ `nat_2023-24_selected.csv` | CSV | UTF-8-compatible ASCII, LF | 920,894 | 6,636 | `ddd3e019b0ad952cecce95566aff2ecb7b2b4ff4ce1135a2a1575b14f5f939bf` | Member of the ZIP in Databricks volume `/Volumes/edu_access/00-source/raw/deped/` |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Official NAT Grade 6 ZIP archive | https://www.deped.gov.ph/wp-content/uploads/National-Achievement-Test-NAT-Grade-6-2023-2024.zip | `370eacc1b6ab5f8b8c36c7671a7300c4928255c9a98da4e752f61ba84f2950f0` | File packaging, selected-school scope, CSV, and included README |
| README inside the official ZIP | Inside the archive above | `ab5b20350255d125ff96ab8903b732d8abaec4aa0d5fdd01345acafafe0060fc` | Column names, publisher data types, descriptions, and score ranges |
| Learning Assessment Technical Notes (ELLNA and NATG6), as of 31 March 2025 | https://www.deped.gov.ph/wp-content/uploads/Learning-Assessment-Technical-Notes-ELLNA-and-NATG6.pdf | `828f7e8526b1a5e031abf11ebe38746ae0f14a2d2726b8cd21c42b72b0dd3a95` | NATG6 background, test design, SY 2023-24 modality and administration, scoring, proficiency, limitations, and planned enhancements, pages 6-10. Raw copy: Databricks volume `/Volumes/edu_access/00-source/raw/deped/`; checksum verified 2026-10-06 |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Selected schools in CAR and Regions I, III, VIII, and IX only; 5 regions and 44 divisions |
| Geographic level | School, with region and schools division labels |
| Time coverage | School Year 2023-24 |
| Time basis | SY 2023-24 NATG6, administered in April 2024 from FY 2023 procurement according to the Technical Notes |
| Update frequency | Assessment schedule and modality vary across school years; public-file refresh cadence is **UNVERIFIED** |
| Population covered | 6,636 selected schools and 52,761 reported test takers. The Technical Notes describe the underlying SY 2023-24 administration as a census of schools with sampled learners, while the public archive contains selected schools only and does not state the school-selection method |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One school-level NAT Grade 6 result row per `school_id` for SY 2023-24 |
| Candidate primary key | `school_id`; 6,636 populated values and 0 duplicates in this delivery |
| Candidate join keys | `school_id` to other DepEd school-level sources; region and division are supporting validation fields, not stable identifiers |
| PSGC available? Which version? | No PSGC codes are present. Region and division are labels only; PSGC version is not stated |
| Personally identifiable or sensitive fields | No learner names or direct personal identifiers. Public aggregate school results. Classification: **Public**, with high disclosure, stability, and reputational risk because 333 schools report one test taker and 5,320 report 10 or fewer |
| Provenance fields in the source | School identifier, region, and division. School year, grade, and selected-school status occur only in the filename and archive README; no row-level assessment date, sampling weight, release version, or extraction timestamp is present |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected type | Actual type | Notes |
|---|---|---|---|
| `school_id` | 6-digit integer identifier | Six-digit integer-form text | Complete and unique; ingest as text to preserve identifier formatting |
| `region` | String | Text | Complete; 5 labels |
| `division` | String | Text | Complete; 44 labels |
| `n_test_takers` | Integer | Positive integer-form text | Complete; range 1 to 117 |
| `filipino_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `math_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `english_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `science_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `araling_panlipunan_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `overall_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range; documented as total points correct divided by total possible points |

## Lineage and dependencies

DepEd BEA Grade 6 exit-assessment design -> NATG6 administration in April 2024 -> census of schools and sampling of learners -> percentage-score calculation and school aggregation -> selected-school public CSV -> official ZIP on DepEd Machine Ready Files -> checksum-verified raw storage -> schema and quality validation -> school-ID integration -> downstream learning-outcome and education-access analysis.

The source depends on a stable DepEd school master for school names, type, operational status, location, and geographic codes. Valid population inference also depends on learner sampling documentation and weights that are not included in the public archive.

## Known quality problems

Summary only; evidence lives in [profile.md](profile.md).

- **Observed:** the published file covers only 5 of the 18 current DepEd regional groupings and is explicitly labeled `selected`; no school-selection method or inclusion probability is documented.
- **Observed:** all 10 columns are complete, all score values fall within 0 to 100, all test-taker counts are positive, and there are no duplicate school IDs or full rows.
- **Observed:** the median school has six test takers; 333 schools report one and 5,320, or 80.2%, report 10 or fewer, creating severe instability and disclosure risk for school-level comparisons.
- **Observed:** MPS fields retain up to 16 decimal places, which implies computational precision beyond an appropriate reporting precision.
- **Observed:** `overall_mps` differs slightly from the simple mean of the five subject MPS values in 6,633 rows. The median absolute gap is 0.05 points and the maximum is 0.34 points. This is consistent with its points-based definition, but raw numerator, denominator, and subject weights are unavailable for independent recalculation.
- **Observed:** only the filename identifies the school year and selected status. Grade, assessment date, sampling weight, release version, and extraction timestamp are absent from the rows.
- **Suspected:** the school and learner selection represented by the public extract may not support unbiased division or region estimates without sampling weights.

## Limitations for analysis

- The selected public extract is not demonstrably representative of all Philippine schools, regions, divisions, or Grade 6 learners.
- Results cannot support national totals, national rankings, or estimates for the 13 regional groupings absent from the file.
- The Technical Notes describe sampled learners for SY 2023-24, but the CSV provides no sampling strata, probabilities, or weights.
- The Technical Notes warn that test-design and modality differences create comparability challenges across years.
- The assessment measures 21st-century skills using learning areas as content; subject-labeled MPS fields should not be interpreted beyond the publisher's definitions.
- Mathematics and English scores are not aligned with SDG 4.1.1 indicators according to the Technical Notes.
- School-level MPS values do not provide learner distributions, standard errors, confidence intervals, item counts, or score numerators and denominators.
- Small test-taker counts can make school comparisons unstable and can expose an individual result when combined with local knowledge.
- Proficiency labels should not be assigned until decimal-boundary and aggregation rules are confirmed.
- Region and division names cannot replace a dated school master or PSGC crosswalk.

## Recommended controls and monitoring

- Fail ingestion on checksum or schema changes, duplicate or malformed school IDs, blanks, nonpositive test-taker counts, or scores outside 0 to 100.
- Preserve raw score strings and full precision, but round only presentation fields according to an approved reporting rule.
- Add derived `school_year`, `grade_level`, `source_file`, `source_sha256`, `source_row`, and ingestion timestamp fields without overwriting source columns.
- Join to a versioned DepEd school master by `school_id`; monitor unmatched IDs and region or division disagreements.
- Suppress or aggregate school-level reporting below an approved minimum test-taker threshold, while retaining source rows in access-controlled analytical storage.
- Do not calculate population estimates, rankings, or confidence intervals without documented sampling design and weights.
- Monitor row counts, regional and division coverage, small-n counts, score ranges, decimal precision, and duplicate keys on every refresh.
- Obtain school-selection criteria, learner sampling design and weights, score calculation inputs, rounding rules, and applicable data-use terms before broader analytical use.
