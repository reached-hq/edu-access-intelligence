# ched_graduates: CHED graduates by region, program level and sex

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Table 27, "Graduate by Region, Program Level, Sex and Academic Year", Higher Education Statistical Bulletin 2020-2025 |
| Publisher / agency | Commission on Higher Education (CHED), Office of Planning, Research, and Knowledge Management (OPRKM) |
| Source system (as stated by the publisher) | Not named |
| Source URL or acquisition method | Bulletin PDF downloaded from https://ched.gov.ph/statistics; Table 27 extracted by hand into CSV |
| Licensing or access restrictions | Not stated in the bulletin. UNVERIFIED |
| Owner (team member) | @Catweyine |
| Date acquired | Bulletin 2026-09-29; CSV extracted 2026-09-30 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Graduate - CHED.csv` | CSV | UTF-8, CRLF | 6,952 | 90 | `36017b30bc792021b742b2f63e52bd64c4f216b351a0f96ddc5dd10dbff14ac6` | Databricks volume `/Volumes/edu_access/00-source/raw/` |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `StatBull2025.pdf`, Higher Education Statistical Bulletin 2020-2025 | https://ched.gov.ph/statistics | `41e5ed465c713cc23dca7e14c24134d96cd72ae2252ce336c85f8432195f3bf2` | Table 27 (pp. 56-57) |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, 18 regions |
| Geographic level | Region only |
| Time coverage | AY 2020-2021 to 2024-2025 |
| Time basis | Academic year |
| Update frequency | Not stated |
| Population covered | Graduates of higher education institutions, five program levels (pre-baccalaureate to doctorate), public and private combined |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per region and program level; academic year and sex are in the column names |
| Candidate primary key | `Region`, `Program Level` |
| Candidate join keys | `Region` (+ academic year once unpivoted); labels are identical across the four CHED CSVs |
| PSGC available? | No; region label text only |
| Personally identifiable or sensitive fields | None; regional totals |
| Provenance fields in the source | None |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column group | Expected (bulletin) | Actual | Notes |
|---|---|---|---|
| `Region`, `Program Level` | text | matches | 5 program levels |
| `<year> Male`, `<year> Female` | counts | 10 columns, whole numbers, 9 cells are `-` | `-` is printed in the bulletin too |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** 9 cells are `-`, all in Post-baccalaureate rows.
- **Observed:** BARMM has no values from 2023-2024; Negros Island Region has values in 2024-2025 only. The bulletin has the same blanks.
- **Observed:** the BARMM region label contains a line break, and the CSV numbers it `19 - …` (BARMM's PSGC region code) where the bulletin prints `15 - …`.
- **Observed (bulletin note):** 1 Region VII graduate with unspecified sex is excluded in 2022-2023.
- **Suspected:** `-` means zero.

## Limitations for analysis

- Region level only; no province, city, or institution detail.
- No public/private split.
- Region totals are not comparable across years for BARMM and Negros Island Region (see above).
