# deped_ellna: selected school-level ELLNA results

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Early Language, Literacy and Numeracy Assessment (ELLNA), selected school-level results, SY 2023-24 |
| Publisher / agency | Department of Education (DepEd), Bureau of Education Assessment (BEA) |
| Source system (as stated by the publisher) | Early Language, Literacy and Numeracy Assessment (ELLNA) |
| Source URL or acquisition method | Manual download from the Assessment Data section of [DepEd Machine Ready Files](https://www.deped.gov.ph/machine-ready-files/); official archive: [ELLNA ZIP](https://www.deped.gov.ph/wp-content/uploads/Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip) |
| Licensing or access restrictions | Public download. No explicit license or reuse terms were found in the archive or Technical Notes. Reuse terms remain **UNVERIFIED** |
| Owner (team member) | @mafelisilda |
| Date acquired | 2026-09-29 11:36 UTC |

## Files

Raw files are kept outside git. Row count excludes the CSV header.

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip` | Official publisher ZIP | n/a | 181,924 | n/a | `d998d5c1af37c29a3247ae3e7f5d4d9aa3b0f34f94db391f55c1a8f587b7f124` | Direct download from the official DepEd URL on 2026-10-03 |
| `Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip` | Repackaged shared-storage ZIP | n/a | 183,613 | n/a | `5d293e40da87491528388ed87a618212cb2544071328670b680cad346f9edecb` | Team-managed shared raw storage |
| `ellna_2023-24_selected.csv` | CSV | UTF-8-compatible ASCII, LF | 728,685 | 5,752 | `a379ccd0cf48bf3ff1174fc76374627bd92f71d31f49fa73e59c9f57b1390dc2` | Member of both ZIP packages; shared package retained in team-managed raw storage |

The profiled CSV and included README are byte-for-byte identical to the corresponding members of the official DepEd ZIP downloaded on 2026-10-03. The shared-storage ZIP was repackaged and therefore has a different size and outer checksum. Both package hashes are retained so the packaging-lineage difference remains reproducible after the shared file is replaced. Verify the member hashes before using either package, and replace the shared copy with the untouched publisher archive when practical.

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Official ELLNA ZIP archive | https://www.deped.gov.ph/wp-content/uploads/Early-Language-Literacy-and-Numeracy-Assessment-ELLNA.zip | `d998d5c1af37c29a3247ae3e7f5d4d9aa3b0f34f94db391f55c1a8f587b7f124` | File packaging, selected-school scope, CSV, and included README |
| README inside the official ELLNA ZIP | Inside the archive above | `ab5b20350255d125ff96ab8903b732d8abaec4aa0d5fdd01345acafafe0060fc` | Column names, publisher data types, descriptions, score ranges, and documented non-applicable components |
| Learning Assessment Technical Notes (ELLNA and NATG6), as of 31 March 2025 | https://www.deped.gov.ph/wp-content/uploads/Learning-Assessment-Technical-Notes-ELLNA-and-NATG6.pdf | `828f7e8526b1a5e031abf11ebe38746ae0f14a2d2726b8cd21c42b72b0dd3a95` | ELLNA background, Grade 3 scope, test design, languages, SY 2023-24 modality and administration, scoring, proficiency levels, and limitations, pages 1-6 |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Selected schools in CAR and Regions I, III, VIII, and IX only; 5 regions and 44 divisions |
| Geographic level | School, with region and schools division labels |
| Time coverage | School Year 2023-24 |
| Time basis | SY 2023-24 ELLNA, administered in May 2024 from FY 2023 procurement according to the Technical Notes |
| Update frequency | Assessment schedule varies across school years; public-file refresh cadence is **UNVERIFIED** |
| Population covered | 5,752 selected schools and 218,296 reported test takers. The Technical Notes describe the underlying SY 2023-24 administration as a census of schools and learners, but the public archive explicitly contains selected schools only and does not state the selection method |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One school-level ELLNA result row per `school_id` for SY 2023-24 |
| Candidate primary key | `school_id`; 5,752 populated values and 0 duplicates in this delivery |
| Candidate join keys | `school_id` to other DepEd school-level sources; region and division are supporting validation fields, not stable identifiers |
| PSGC available? Which version? | No PSGC codes are present. Region and division are labels only; PSGC version is not stated |
| Personally identifiable or sensitive fields | No learner names or direct personal identifiers. Public aggregate school results. Classification: **Public**, with elevated disclosure and reputational risk for 26 schools reporting one test taker and 1,016 schools reporting 10 or fewer |
| Provenance fields in the source | School identifier, region, division, and declared language. School year and selected-school status appear only in the filename and archive README; no row-level source file, assessment date, release version, or extraction timestamp is present |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected type | Actual type | Notes |
|---|---|---|---|
| `school_id` | 6-digit integer identifier | Six-digit integer-form text | Complete and unique; ingest as text to preserve identifier formatting |
| `region` | String | Text | Complete; 5 labels |
| `division` | String | Text | Complete; 44 labels |
| `language` | String | Text | Complete; 9 labels, including two compound labels |
| `n_test_takers` | Integer | Positive integer-form text | Complete; range 1 to 674 |
| `english_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `filipino_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range |
| `numeracy_mps` | Float, 0 to 100 | Decimal-form text or blank | 154 documented non-applicable blanks for `English/Filipino` schools |
| `mother_tongue_mps` | Float, 0 to 100 | Decimal-form text or blank | 1,925 documented non-applicable blanks for `English/Filipino` and `Tagalog` schools |
| `overall_mps` | Float, 0 to 100 | Decimal-form text | Complete and in range; documented as total points correct divided by total possible points |

## Lineage and dependencies

DepEd BEA Grade 3 ELLNA administration in May 2024 -> language, literacy, and numeracy scoring -> school-level aggregation -> selected-school public CSV -> official ZIP on DepEd Machine Ready Files -> checksum-verified raw storage -> schema and quality validation -> school-ID integration with other DepEd sources -> downstream learning-outcome and education-access analysis.

The source depends on a stable DepEd school master for school names, type, operational status, location, and geographic codes. Downstream use also depends on preserving documented non-applicable blanks, controlling small test-taker counts, and avoiding unsupported comparisons across years.

## Known quality problems

Summary only; evidence lives in [profile.md](profile.md).

- **Observed:** the published file covers only 5 of the 18 current DepEd regional groupings and is explicitly labeled `selected`; no selection method or inclusion probability is documented.
- **Observed:** `numeracy_mps` has 154 blanks and `mother_tongue_mps` has 1,925 blanks. Every blank follows the archive README's language-based non-applicability rules; they are not ordinary nulls.
- **Observed:** 26 schools report one test taker and 1,016 report 10 or fewer, producing unstable school estimates and heightened disclosure risk.
- **Observed:** MPS fields retain up to 16 decimal places, which implies computational precision beyond an appropriate reporting precision.
- **Observed:** `overall_mps` differs from the simple mean of the available component MPS values in 5,595 rows. This is consistent with its points-based definition, but the raw numerator, denominator, and component weights are not supplied for independent recalculation.
- **Observed:** no score is outside 0 to 100, no test-taker count is zero or negative, and there are no duplicate school IDs or full rows.
- **Observed:** 98 schools covering 3,157 test takers have Numeracy below 1 while English and Filipino are at least 30. The affected schools are concentrated in several divisions; 27 values are exact zero and 71 are nonzero values below 1.
- **Suspected:** the near-zero Numeracy pattern may be valid performance, inconsistent 0-to-1 versus 0-to-100 scaling, or another encoding issue. The file does not support treating the values as confirmed zeros or missing data.
- **Observed:** only the filename identifies the school year. The rows contain no assessment date, release version, selection flag, or extraction timestamp.
- **Suspected:** the compound language labels `Ilokano/Iloko-Pangasinense` and `English/Filipino` may encode different concepts and should not be split or normalized without publisher guidance.

## Limitations for analysis

- The selected public extract is not demonstrably representative of all Philippine schools, regions, divisions, or Grade 3 learners.
- Results cannot support national totals, national rankings, or estimates for the 13 regional groupings absent from the file.
- The Technical Notes warn that percent-correct results may not be comparable across years because test difficulty can vary despite a common specification.
- School-level MPS values do not provide learner distributions, standard errors, confidence intervals, item counts, or score numerators and denominators.
- Small test-taker counts can make school comparisons unstable and can expose individual performance when combined with local knowledge.
- Blank component scores must not be converted to zero or included as failed assessments.
- Proficiency labels should not be assigned until decimal-boundary rules and the intended aggregation measure are confirmed.
- Region and division names cannot replace a dated school master or PSGC crosswalk.

## Recommended controls and monitoring

- Fail ingestion on checksum or schema changes, duplicate or malformed school IDs, nonpositive test-taker counts, or populated scores outside 0 to 100.
- Assert that numeracy blanks occur only for `English/Filipino` and mother-tongue blanks only for `English/Filipino` or `Tagalog`; quarantine unexpected null patterns.
- Preserve raw score strings and full precision, but round only presentation fields according to an approved reporting rule.
- Add derived `school_year`, `source_file`, `source_sha256`, `source_row`, and ingestion timestamp fields without overwriting original columns.
- Join to a versioned DepEd school master by `school_id`; monitor unmatched IDs and region or division disagreements.
- Suppress or aggregate school-level reporting below an approved minimum test-taker threshold, while retaining source rows in access-controlled analytical storage.
- Monitor row counts, region and division coverage, language categories, small-n counts, null patterns, score ranges, and duplicate keys on every refresh.
- Flag the 98 near-zero Numeracy records and exclude them from comparative reporting until DepEd confirms their units and meaning; never convert them to null or rescale them without publisher evidence.
- Obtain the publisher's school-selection method, release cadence, score calculation inputs, decimal reporting rules, and applicable data-use terms before broader analytical use.
