# Limitations

What the data and methods can and cannot support, with evidence. Filled in as findings are confirmed.

## Data coverage

- **DepEd enrollment SY 2025-26 publishes blanks where earlier years publish 0.** All 47,232 schools that do not offer senior high have blank senior-high counts, 1,403 schools have blank kindergarten-to-grade-10 counts, and 46 schools publish no count at all. Silver keeps these NULL (D-020), so totals are unaffected, but a school-level comparison across years must not read NULL as zero. Evidence: [Silver](../operations/silver.md#what-the-bronze-data-showed-beyond-the-profile).
- **Schools with no learners are kept, flagged.** 115 / 24 / 0 schools publish only zeros and 0 / 0 / 46 publish no count (SY 2023-24 / 2024-25 / 2025-26); whether they are closed or non-reporting is unknown (profile S-1). Gold decides per measure whether they count (`enrollment_status`).

## Measurement

## Geography

- **Overseas schools (33 / 35 / 36) carry placeholder places.** In SY 2025-26 they are published in CITY OF PASIG, "Lone District". Silver flags them (`is_overseas`); Gold excludes them from every geographic result.
- **About 25 schools a year have a barangay name that may be cut at 40 characters**, and 70 / 65 / 7 have none. Silver flags the first and keeps the second NULL; barangay-level results for these schools depend on Integration's matching (profile O-15, O-18).

## Methods
