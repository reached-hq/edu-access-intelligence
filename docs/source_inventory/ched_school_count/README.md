# ched_school_count: CHED higher education institutions by region and type

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | "Higher Education Institutions by Region, Sector and Institutional Type: Academic Year 2023-2024", Higher Education Statistical Bulletin 2020-2025 |
| Publisher / agency | Commission on Higher Education (CHED), Office of Planning, Research, and Knowledge Management (OPRKM) |
| Source system (as stated by the publisher) | Not named. "Based on the submission of higher education institutions, as compiled by OPRKM-Knowledge Management Division" (table note) |
| Source URL or acquisition method | Bulletin PDF (download URL UNVERIFIED); table extracted by hand into CSV |
| Licensing or access restrictions | Not stated in the bulletin. UNVERIFIED |
| Owner (team member) | @Catweyine |
| Date acquired | Bulletin 2026-09-29; CSV extracted 2026-09-30 |

## Files

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `School Count - CHED.csv` | CSV | UTF-8, CRLF | 791 | 17 | `27aea7e1c552d7c0adb88a521cc73233a643eb337be67b2fa667df673023b2de` | Databricks volume `/Volumes/edu_access/00-source/raw/` |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| `StatBull2025.pdf`, Higher Education Statistical Bulletin 2020-2025 | UNVERIFIED | `41e5ed465c713cc23dca7e14c24134d96cd72ae2252ce336c85f8432195f3bf2` | AY 2023-2024 institutions table and its notes (p. 12) |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines, 17 regions (no Negros Island Region) |
| Geographic level | Region only |
| Time coverage | **AY 2023-2024 only** (table title; the CSV has no year column) |
| Time basis | Academic year, "as of October 10, 2024" (table note) |
| Update frequency | The bulletin has one such table per year, 2020-2021 to 2024-2025; only 2023-2024 was extracted |
| Population covered | Higher education institutions, public and private; SUC counts include satellite, extension campuses and external study centers (table note) |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per region |
| Candidate primary key | `Region` |
| Candidate join keys | `Region` + AY 2023-2024; labels are identical to the other CHED CSVs |
| PSGC available? | No; region label text only |
| Personally identifiable or sensitive fields | None; regional totals |
| Provenance fields in the source | None |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column group | Expected (bulletin) | Actual | Notes |
|---|---|---|---|
| `Region` | text | matches | |
| 7 count columns | counts | whole numbers | `Public LUCs` and `Public Other` have blanks, as in the bulletin; the bulletin's two "Excluding Satellite Campus" totals were not extracted |

## Known quality problems

See [profile.md](profile.md) for evidence.

- **Observed:** 16 blank cells, all in `Public LUCs` or `Public Other`; the totals add up only when they count as 0.
- **Observed:** no Negros Island Region row.
- **Observed:** the BARMM region label contains a line break.

## Limitations for analysis

- One year only (AY 2023-2024).
- Counts include satellite campuses, so they count campuses, not separate institutions.
- Region level only.
