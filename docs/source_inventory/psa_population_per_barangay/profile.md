# psa_population_per_barangay: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-02 |
| Profiled by | @mafelisilda with Codex assistance |
| Tool | Python standard library and shared XLSX reader: [`notebooks/profiling/profile_psa_population_per_barangay.py`](../../../notebooks/profiling/profile_psa_population_per_barangay.py) |
| Files profiled (SHA-256) | All 18 checksums in [README.md](README.md#files); the script stops on a missing file or mismatch |
| How files were read | XLSX XML read as text with `src/profiling/xlsx.py`; only sheets marked visible were parsed; source file, sheet, and Excel row retained; population required to contain digits only |

## How to rerun

```powershell
$env:PSA_POPULATION_DIR = "<folder-containing-the-18-workbooks>"
python notebooks\profiling\profile_psa_population_per_barangay.py
```

## Summary

Usable as a complete barangay-level population snapshot for 01 July 2024 after preserving source lineage and applying reference-date-aware PSGC matching. All 42,011 barangay rows have populated, nonnegative whole-number counts, no candidate-key duplicates, and complete reconciliation to 1,655 parent areas and 118 visible sheet totals. The principal risks are the absence of PSGC codes, repeated and whitespace-affected names, embedded footnote formatting, 12 zero-population barangays, and geographic changes between the source date and PSGC 2Q 2026.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | All regional files were acquired and verified | 18 expected files present; all SHA-256 values match the source card; regions include NCR, CAR, Regions I–XII, CALABARZON, MIMAROPA, NIR, Caraga, and BARMM | Supports nationwide coverage | Fail on missing or changed files |
| O-2 | Complete barangay extraction | 42,011 barangay rows across 118 visible sheets and 1,655 parent areas | Supports national barangay-level analysis | Assert file, sheet, parent, and row counts on refresh |
| O-3 | Six hidden non-publication sheets were excluded | `NCR_2.xlsx`: `Table B`; `CAR_0.xlsx`: `Sheet9`; `BARMM_1.xlsx`: four `Table C_*` sheets. Workbook state is `hidden`; calculation sheets include check columns and `#REF!` values | Reading every sheet would duplicate or contaminate published rows | Exclude only explicit hidden sheets and log them |
| O-4 | Candidate key and rows are unique | 0 duplicate normalized `(region, sheet, parent_area, barangay)` keys and 0 duplicate lineage rows | Safe normalized grain | Enforce uniqueness before loading Silver |
| O-5 | Barangay populations are complete whole numbers | 42,011 of 42,011 populated; 0 non-integers; 0 negatives; min 0, median 1,424, max 215,035 | Safe numeric typing, subject to zero review | Cast only after text validation; retain raw values |
| O-6 | All published totals reconcile | 0 of 1,655 parent totals mismatch their barangay sums; 0 of 118 sheet totals mismatch their child sums | Strong evidence that hierarchy parsing is complete | Make both reconciliations blocking controls |
| O-7 | Geographic totals reconcile to the documented national exception | Sheet totals sum to 112,727,776. PSA's national figure is 112,729,484; the difference is 1,708, matching PSGC Notes D.2 for Filipinos in embassies, consulates, and missions abroad | Regional shares must use a clearly defined denominator | Document whether the national or geographically assigned total is used |
| O-8 | Names require cleaning and parent scoping | 2,775 barangay labels end in whitespace. 4,004 names repeat and cover 20,136 rows, but the scoped candidate key has 0 duplicates | Name-only joins can silently misassign population | Preserve raw names; trim matching fields; match only within parent geography |
| O-9 | No geographic codes are supplied | Neither the hierarchy column nor any other published column contains PSGC | Stable integration requires an external crosswalk | Join to `psa_psgc` with explicit version and match-status fields |
| O-10 | Twelve zero-population barangays are present | NCR 1; CAR 1; Region II 2; Region III 2; CALABARZON 3; Region VI 1; Region VIII 2 | Ratios can divide by zero or misclassify coverage | Retain as valid source values, flag denominator use, seek contextual confirmation |
| O-11 | Largest barangay counts are concentrated in urban areas | Commonwealth, Quezon City: 215,035; Pinagbuhatan, Pasig: 173,576; Batasan Hills, Quezon City: 168,770; San Isidro, Rodriguez: 164,822; San Jose, Rodriguez: 143,031 | Outliers can dominate unweighted summaries but are plausible published counts | Use population-weighted aggregation where appropriate; monitor maxima without arbitrary rejection |
| O-12 | Workbook layout is consistent enough for deterministic parsing | Every visible sheet repeats the title and 01 July 2024 reference date; names are in column B and population in column D; blank-row grouping reconciles without error | The raw source is report-shaped rather than analysis-ready | Keep parser tests and total reconciliation tied to layout assumptions |
| O-13 | Geographic versions differ | Source has 42,011 barangays and places Sulu in BARMM; PSGC 2Q 2026 has 42,010 barangays and places Sulu in Region IX | A current PSGC join can change regional attribution or leave units unmatched | Preserve source region; build a dated, auditable crosswalk and never force matches |
| O-14 | No direct personal information is present | Only aggregate geographic names and population counts are published | Low privacy risk | Classify as Public; continue to verify reuse terms |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | Superscript footnote markers embedded in geographic labels become plain trailing digits during text extraction | Inspect formatted rich-text runs and obtain the publisher's footnote legend; compare affected names with PSGC | open |
| S-2 | The one-row barangay-count difference from PSGC 2Q 2026 is caused by post-reference-date creation, split, merger, or recoding | Build a 01 July 2024 to 2Q 2026 PSGC change crosswalk and compare scoped names | open |
| S-3 | All 12 zero-population rows are legitimate census results rather than suppressed, uninhabited, or encoding-error values | Check PSA census technical notes and request row-level confirmation | open |
| S-4 | Download suffixes `_0`, `_1`, and `_2` are browser collision suffixes rather than PSA release versions | Compare HTTP content disposition and publisher manifest names | open |

## Changes across files or years

Only the 01 July 2024 census snapshot was supplied. The 18 files are regional partitions of one release, not a time series. Their visible-sheet layout is consistent, while the number and names of worksheets vary by region. NCR, CAR, and BARMM contain six explicitly hidden working sheets in total. No cross-year schema or population drift can be assessed.

## Questions for the publisher or mentor

- Is there an official flat file with PSGC codes for these 42,011 barangay counts?
- What do all superscript footnote markers mean, and can they be supplied in a machine-readable notes table?
- Are zero-population barangays confirmed census counts, uninhabited units, or another status?
- What official file names and release-version identifiers should replace browser suffixes such as `_0`, `_1`, and `_2`?
- What license or reuse terms apply beyond public download access?
- Is there a correction or revision log for the regional workbooks?
