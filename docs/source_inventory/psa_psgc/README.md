# psa_psgc: Philippine Standard Geographic Code (PSGC), 2Q 2026

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Philippine Standard Geographic Code (PSGC), 2Q 2026 Publication Datafile |
| Publisher / agency | Philippine Statistics Authority (PSA), Statistical Classifications Division (SCD), Standards Service |
| Source system (as stated by the publisher) | PSGC, a systematic classification and coding of geographic areas. Updated from Republic Acts and local ordinances ratified by plebiscite (COMELEC). `Metadata` sheet |
| Source URL or acquisition method | Manual download from https://psa.gov.ph/classification/psgc |
| Licensing or access restrictions | Access constraints: none. Use constraints: acknowledge the PSA as the source. Distributed without warranty; interpretation and use are the user's responsibility (`Metadata` sheet) |
| Owner (team member) | @maeveylain |
| Date acquired | 2026-09-28 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `PSGC-2Q-2026-Publication-Datafile.xlsx` | xlsx (6 sheets) | n/a (binary workbook; text is Unicode, e.g. "Tañong") | 3,250,889 | 43,768 data rows on sheet `PSGC` (range A1:K43769, 1 header row) | `31892bc2bdde3ea0682562d9412b5bab4d45a0be5e5a5b4f6c9d7714b94bca5d` | Local |

Sheets: `Metadata`, `National Summary`, `Prov Sum`, `PSGC` (the data), `Notes`, `Coding Structure` (images only, no cells).

## Publisher documentation

The documentation is inside the workbook. No separate document was downloaded.

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `Metadata` sheet | inside the workbook above | same as the file | Abstract, process, progress, access and use constraints, disclaimer |
| `Notes` sheet | inside the workbook above | same as the file | A. General notes; B. Income classification; C. Urban / Rural; D. 2024 Population; E. Geographic Level codes |
| `National Summary` sheet | inside the workbook above | same as the file | Counts of provinces, cities, municipalities, barangays and population by region, used to cross-check the `PSGC` sheet |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines (18 regions) |
| Geographic level | All levels in one table: region, province, city, municipality, barangay, plus 14 sub-municipalities of Manila and 2 special rows (see quality problems) |
| Time coverage | Administrative structure as of 30 June 2026. Population from the 2024 Census of Population |
| Time basis | Reference date (30 June 2026). Population: 2024 census. Urban / Rural: 2020 census (CPH) |
| Update frequency | Quarterly (`Metadata`: "Ongoing (updated quarterly)") |
| Population covered | All geographic units. Regional populations do not sum to the national total (`Notes` D.2) |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per geographic unit (region, province, city, municipality, sub-municipality or barangay) |
| Candidate primary key | `10-digit PSGC` (43,768 rows, 43,768 unique, always 10 digits) |
| Candidate join keys | `10-digit PSGC`. `Name` is not usable: 27,391 distinct in 43,768 rows, and 4,041 barangay names repeat |
| PSGC available? | This is the PSGC, 2Q 2026. The code appears to be region (2) + province (3) + city or municipality (2) + barangay (3) digits, consistent with sample rows. The `Coding Structure` sheet is only an image. UNVERIFIED against the PSA page |
| Personally identifiable or sensitive fields | None. Place names only |
| Provenance fields in the source | `Old names` (former names), `Status` (`Pob.`, `Capital`), publication date on the `Metadata` sheet |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected | Actual | Notes |
|---|---|---|---|
| `10-digit PSGC` | identifier | text of 10 digits | Leading zeros must be kept (e.g. `0900000000`) |
| `Name` | text | text | 2,855 values have trailing spaces |
| `Correspondence Code` | identifier | text of 9 digits | 50 blank. Not explained in the `Notes` sheet |
| `Geographic Level` | category | text, 6 values | 2 blank |
| `Old names` | text | text | Filled for 1,699 rows |
| `City Class` | category | text | Cities only (149 rows) |
| `Income Classification` | category | text | Contains `-` and starred values such as `2nd*` |
| `Urban / Rural` | category | text | Barangays only. Contains `-` |
| `2024 Population` | whole number | text | 1 cell is `#N/A` |
| (no header, column J) | none | text | Footnote text and markers, 19 rows |
| `Status` | category | text | `Pob.` or `Capital` |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** 2 rows have a blank `Geographic Level`: "City of Isabela (Not a Province)" (`0990100000`, population `#N/A`) and "Special Geographic Area" (`1999900000`).
- **Observed:** 50 rows have no `Correspondence Code` (38 barangays, 8 municipalities, 2 provinces, 1 region, 1 blank-level row).
- **Observed:** 1 population cell is the text `#N/A`.
- **Observed:** column J has no header and holds footnote text such as "(excluding CITY OF BAGUIO)" and markers `1/`, `2/`, `3/` (19 rows).
- **Observed:** `Income Classification` mixes classes with `-` (8 municipalities in the Special Geographic Area) and starred classes (6 rows). `Notes` B explains the asterisk as a class retained after downgrade.
- **Observed:** `Urban / Rural` is `-` for 38 barangays, and they are exactly the 38 barangays with no `Correspondence Code`.
- **Observed:** 12 barangays have a population of 0.
- **Observed:** the `Notes` legend for `Geographic Level` lists `Dist`, but no row uses it. The data uses `City`, which the legend omits.
- **Observed:** names are not unique, and 2,855 names have trailing spaces.
- **Observed:** regional populations sum to 112,727,776, and the national figure is 112,729,484. The 1,708 difference matches the `Notes` D.2 explanation (Filipinos in embassies and consulates abroad).
- **Observed:** unit counts on the `PSGC` sheet match the `National Summary` sheet (82 provinces, 149 cities, 1,493 municipalities, 42,010 barangays).
- **Observed:** the hierarchy is complete: every barangay has its city or municipality in the file, and every province, city, and municipality has its region.
- **Suspected:** the 38 barangays without a code or urban/rural class are new or split barangays created after the 2020 census. To test against the previous PSGC quarter.

## Limitations for analysis

- One snapshot in time. The only history is the `Old names` column.
- Population is 2024 only and urban/rural is based on 2020, so the two bases differ.
- No coordinates or boundaries.
- Sub-municipalities of Manila are not officially municipalities (`Notes` A.1). City of Isabela is geographically in Basilan but belongs to Region IX with a special code (`Notes` A.2).
- Population counts do not add up to the national total (`Notes` D.2).
- Codes change when local government units are created, merged, or renamed. Joining to sources built on another PSGC version needs a version check first.
