# ched_student_faculty_ratio: CHED student-faculty ratio by region

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Table 39, "Student-Faculty Ratio by Academic Year", Higher Education Statistical Bulletin 2020-2025 |
| Publisher / agency | Commission on Higher Education (CHED), Office of Planning, Research, and Knowledge Management (OPRKM) |
| Source system (as stated by the publisher) | Not named |
| Source URL or acquisition method | Bulletin PDF (download URL UNVERIFIED); Table 39 extracted by hand into CSV |
| Licensing or access restrictions | Not stated in the bulletin. UNVERIFIED |
| Owner (team member) | @Catweyine |
| Date acquired | Bulletin 2026-09-29; CSV extracted 2026-09-30 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Student Faculty Ratio - CHED.csv` | CSV | UTF-8, CRLF | 2,635 | 18 | `bc132836fc86fe36bf4dfb702a5c546f9df8dd7ab05c64e68dc42d30965b25b9` | Databricks volume `/Volumes/edu_access/00-source/raw/` |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `StatBull2025.pdf`, Higher Education Statistical Bulletin 2020-2025 | UNVERIFIED | `41e5ed465c713cc23dca7e14c24134d96cd72ae2252ce336c85f8432195f3bf2` | Table 39 (p. 80) and the Retrieval Rate table beside it (p. 81) |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, 18 regions |
| Geographic level | Region only |
| Time coverage | AY 2020-2021 to 2024-2025 |
| Time basis | Academic year |
| Update frequency | Not stated |
| Population covered | Students and faculty of higher education institutions, public and private combined. Retrieval rate 84% to 97% per year (p. 81) |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per region; academic year and measure are in the column names |
| Candidate primary key | `Region` |
| Candidate join keys | `Region` (+ academic year once unpivoted); labels are identical across the four CHED CSVs |
| PSGC available? | No; region label text only |
| Personally identifiable or sensitive fields | None; regional totals |
| Provenance fields in the source | None |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column group | Expected (bulletin) | Actual | Notes |
|---|---|---|---|
| `Region` | text | matches | |
| `Student <year>`, `Faculty <year>` | counts | 10 columns, whole numbers written with thousands commas | |
| `Ratio <year>` | ratio | 5 columns, text such as `1:27` | Equals 1 : Student ÷ Faculty rounded up |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** BARMM has no values from 2023-2024; Negros Island Region has values in 2024-2025 only. The bulletin has the same blanks.
- **Observed:** the BARMM region label contains a line break.

## Limitations for analysis

- Region level only; no split by sector, program, or institution.
- The bulletin reports a retrieval rate below 100% for every year, so counts cover only the institutions that submitted.
- Region totals are not comparable across years for BARMM and Negros Island Region (see above).
