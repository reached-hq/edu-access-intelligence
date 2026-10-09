# Limitations

What the data and methods can and cannot support, with evidence. Filled in as findings are confirmed.

## Data coverage

- **DepEd enrollment SY 2025-26 publishes blanks where earlier years publish 0.** All 47,232 schools that do not offer senior high have blank senior-high counts, 1,403 schools have blank kindergarten-to-grade-10 counts, and 46 schools publish no count at all. Silver keeps these NULL (D-023), so totals are unaffected, but a school-level comparison across years must not read NULL as zero. Evidence: [Silver](../operations/silver.md#what-the-bronze-data-showed-beyond-the-profile).
- **DepEd enrollment SY 2023-24 publishes no unique-strand enrollment.** The four `g11_unique_*` and `g12_unique_*` columns exist that year but are blank in all 60,167 rows, so Silver keeps them NULL. Gold must not read them as zero learners, and a unique-strand trend can start only in SY 2024-25.
- **Schools with no learners are kept, flagged.** 115 / 24 / 0 schools publish only zeros and 0 / 0 / 46 publish no count (SY 2023-24 / 2024-25 / 2025-26); whether they are closed or non-reporting is unknown (profile S-1). Gold decides per measure whether they count (`enrollment_status`).
- **Suspected: three private schools in Maguindanao report implausible Grade 11 growth.** Schools 410978, 410977, and 410472 report a Grade 11 strand (HUMSS or Arts) that grows 5 to 23 times in one year, to 4,000 to 7,900 learners, and Grade 12 counts that do not follow the previous year's Grade 11 (profile S-4). Silver keeps the counts as published (D-023): they are below the plausible maximum, and Silver does not compare years. Gold must decide whether strand- and school-level results include these schools, and say so.

## Measurement

## Geography

- **Overseas schools (33 / 35 / 36) carry placeholder places.** In SY 2025-26 they are published in CITY OF PASIG, "Lone District". Silver flags them (`is_overseas`); Gold excludes them from every geographic result.
- **About 25 schools a year have a barangay name that may be cut at 40 characters**, and 70 / 65 / 7 have none. Silver flags the first and keeps the second NULL; barangay-level results for these schools depend on Integration's matching (profile O-15, O-18).

## Methods
