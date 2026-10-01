# ched_enrollment: CHED enrollment by region, sector and sex

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Table 6, "Enrollment by Region, Sector, Sex and Academic Year", Higher Education Statistical Bulletin 2020-2025 |
| Publisher / agency | Commission on Higher Education (CHED), Office of Planning, Research, and Knowledge Management (OPRKM) |
| Source system (as stated by the publisher) | Not named. "Consolidated by CHED-OPRKM Knowledge Management Division" from HEI submissions (Table 2 note) |
| Source URL or acquisition method | Bulletin PDF downloaded from https://ched.gov.ph/statistics; Table 6 extracted by hand into CSV |
| Licensing or access restrictions | Not stated in the bulletin. UNVERIFIED |
| Owner (team member) | @Catweyine |
| Date acquired | Bulletin 2026-09-29; CSV extracted 2026-09-30 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Enrollment - CHED.csv` | CSV | UTF-8, CRLF | 4,342 | 36 | `6aabc9e14b2abee0dd09c7607815abcd9b75edaf972fd93819610071f4f28c3e` | Databricks volume `/Volumes/edu_access/00-source/raw/` |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `StatBull2025.pdf`, Higher Education Statistical Bulletin 2020-2025 | https://ched.gov.ph/statistics | `41e5ed465c713cc23dca7e14c24134d96cd72ae2252ce336c85f8432195f3bf2` | Table 6 (pp. 18-19); Table 2 note on coverage (p. 14) |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, 18 regions |
| Geographic level | Region only |
| Time coverage | AY 2020-2021 to 2024-2025 |
| Time basis | Academic year, **first semester only** (Table 2 note) |
| Update frequency | Not stated |
| Population covered | Students of CHED-recognized higher education institutions, public and private |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per region and sector; academic year and sex are in the column names |
| Candidate primary key | `Region`, `Sector` |
| Candidate join keys | `Region` (+ academic year once unpivoted); labels are identical across the four CHED CSVs |
| PSGC available? | No; region label text only |
| Personally identifiable or sensitive fields | None; regional totals |
| Provenance fields in the source | None |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column group | Expected (bulletin) | Actual | Notes |
|---|---|---|---|
| `Region`, `Sector` | text | matches | `Sector` is `Public` or `Private` |
| `<year> Male`, `<year> Female` | counts | 10 columns, whole numbers written with thousands commas | Blank where the bulletin is blank |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** Bangsamoro (BARMM) has no values from 2023-2024, and only public values in 2021-2022 and 2022-2023; Negros Island Region has values in 2024-2025 only. The bulletin has the same blanks.
- **Observed:** the BARMM region label (`15 - …`, as printed in the bulletin) contains a line break. BARMM's updated PSGC region code is 19.
- **Observed (bulletin note):** 11 Region VII students with unspecified sex are excluded in 2023-2024.

## Limitations for analysis

- Region level only; no province, city, or institution detail.
- First-semester enrollment only.
- Region totals are not comparable across years for BARMM and Negros Island Region (see above).
