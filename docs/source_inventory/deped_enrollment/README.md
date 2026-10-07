# deped_enrollment: DepEd school-level enrollment

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Enrollment (School Characteristics, machine-ready files) |
| Publisher / agency | Department of Education (DepEd), Policy and Planning Service |
| Source system (as stated by the publisher) | Learner Information System (LIS), Beginning of School Year (BOSY) collection. Technical Notes p. 1, 3 |
| Source URL or acquisition method | Download from https://www.deped.gov.ph/machine-ready-files/ (School Characteristics section), one zip per school year |
| Licensing or access restrictions | Public download. No license terms stated on the page. UNVERIFIED |
| Owner (team member) | @hyenalouise |
| Date acquired | 2026-09-28 22:55 UTC |

## Files

Published years: SY 2017-18 to SY 2025-26. Acquired so far: the three years below.

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Enrollment-in-SY-2023-2024.zip` | zip | n/a | 2,969,709 | n/a | `a10f4d0f9082919c13b3a091774c8231c99c95b1b1872310714107013b77dbbb` | Local (`raw-data/deped/original/`), pending storage decision (#1) |
| ↳ `enrollment_2023-24.csv` | CSV | UTF-8, LF | 19,010,469 | 60,167 | `cb9457d1dd12cccde880e0d8065212f16a4a5970ac525d5e2f8c90069f1c3657` | extracted from the zip |
| `Enrollment-in-SY-2024-2025.zip` | zip | n/a | 2,962,042 | n/a | `fd5dd74a62b828608c62335b7c324ddf05be58e3f05465fee68854795f5b1a92` | Local, pending #1 |
| ↳ `enrollment_2024-25.csv` | CSV | UTF-8, LF | 19,223,401 | 60,129 | `dd14e211bb32d8b80450c1e061397f6d7d3c819cef2070f204ddf33395ff5dac` | extracted from the zip |
| `Enrollment-in-SY-2025-2026.zip` | zip | n/a | 2,981,421 | n/a | `ab4d7e24b3a46a99db2c76dee5279a976e4c3a76062e79f7217e70dc6dd1b450` | Local, pending #1 |
| ↳ `enrollment_2025-26.csv` | CSV | **Windows-1252, CRLF** | 18,840,355 | 60,204 | `8c80173a7fc29eb3dd7b9e018d603022c731713d794945a8c9c2a2f0f190ee9e` | extracted from the zip |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `README.md` in the SY 2023-24 and 2024-25 zips (identical) | inside the zips above | `5eb05f7dc0bb7ecc7f9b531eca109af0b86b9379957d9c2261640500ba492a80` | Variable documentation, notes on school ID and region changes |
| `README.md` in the SY 2025-26 zip | inside the zip above | `f2aa7710a2448a69e6276672ad15ebb46abd6666e6b923a5639bd4e9541cb0b6` | Adds the four `g11_sshs_*` columns |
| School Characteristics Technical Notes (PDF, 12 pages, effective 2024-09-10) | https://www.deped.gov.ph/wp-content/uploads/School-Characteristics-Technical-Notes.pdf | `a0cb8728a4b175e6eba493fa0d06146c10db9064bc3c71807162fd9266f39cbc` | Data sources (p. 1-2), collection timing (p. 3), indicator formulas (p. 4-9), data limitations (p. 11-12) |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, plus Philippine Schools Overseas (PSO) |
| Geographic level | School, with names of region, division, province, municipality, and barangay |
| Time coverage | SY 2023-24 to SY 2025-26 acquired (SY 2017-18 onward published) |
| Time basis | School year. Enrollment is the official BOSY count (Technical Notes p. 3) |
| Update frequency | Annual. Files re-uploaded 2025-10-15; SY 2025-26 added 2026-07-23 |
| Population covered | All sectors: public, private, SUC/LUC, PSO |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per school per school year |
| Candidate primary key | `school_id` (6 digits; unique within each file) |
| Candidate join keys | `school_id` to other DepEd school datasets. Location names to PSGC (by name matching only) |
| PSGC available? | **No.** Location is names only |
| Personally identifiable or sensitive fields | None found. Counts are aggregated per school |
| Provenance fields in the source | None. School year comes from the file name |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column group | Expected (README) | Actual | Notes |
|---|---|---|---|
| School information (17 columns) | as documented | matches in 2023-24 and 2024-25 | 2025-26 adds undocumented `Modified Curricular Offering Classification` |
| Enrollment counts | nullable integers | 62 columns (2023-24, 2024-25), 66 (2025-26) | All values are whole numbers; none negative |
| `offers_es/jhs/shs` | boolean | `True`/`False` (2023-24, 2024-25); `Yes`/`No` (2025-26) | Label change |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** no PSGC codes; place names need standardizing before matching (suffixes like "(Capital)", mixed capitalization, extra spaces in 2025-26).
- **Observed:** about 173 place names per year contain mangled characters (`Ã‘` for `Ñ`), and barangay names appear to be capped at 40 characters.
- **Observed:** SY 2025-26 differs in encoding, columns, and category labels.
- **Observed:** Negros Island Region (NIR) appears from SY 2024-25; 2,704 schools moved into it from Regions VI and VII.
- **Observed:** about 1% of school IDs appear or disappear between consecutive years.
- **Suspected:** schools with zero enrollment (115 in SY 2023-24, mostly private) may be closed or non-reporting.

## Limitations for analysis

- Enrollment rates (GER, NER) require PSA projected population. DepEd itself reports them no lower than the school division (Technical Notes p. 11-12).
- A below-100% NER must not be read as the share of children not enrolled (Technical Notes p. 9).
- Year-over-year school comparisons are affected by school ID changes; DepEd has not yet published an ID mapping (README).
