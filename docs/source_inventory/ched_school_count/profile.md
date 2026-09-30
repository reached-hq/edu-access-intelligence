# ched_school_count: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-09-30 |
| Profiled by | @Catweyine |
| Tool | DuckDB 1.4.5 (Python), run locally: [`notebooks/profiling/profile_ched.py`](../../../notebooks/profiling/profile_ched.py) |
| Files profiled (SHA-256) | See [README.md](README.md#files). The script stops if the CSV's or the bulletin's checksum differs |
| How files were read | All columns as text (`all_varchar`), strict CSV parsing |

## How to rerun

Download the four CSVs and `StatBull2025.pdf` from `/Volumes/edu_access/00-source/raw/` into `<RAW_DATA_DIR>/ched/original/`, then:

```bash
RAW_DATA_DIR=/path/to/raw-data python notebooks/profiling/profile_ched.py
```

The same script profiles all four CHED sources.

## Summary

Usable for counting higher education institutions (including satellite campuses) per region in AY 2023-2024. The CSV reproduces the bulletin table exactly, and its totals add up when blanks count as 0.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | CSV matches the bulletin | 7 of 7 count columns add up to the table's Total row (113, 437, 143, 13, 706, 1,704, 2,410) | The hand extraction can be trusted | Keep the check when the CSV is re-extracted |
| O-2 | `Region` is unique | 17 rows, 0 duplicate keys | Safe primary key | Assert uniqueness in Bronze validation |
| O-3 | Region labels | 17 labels, the same as the other CHED CSVs except no `18 - Negros Island`; the BARMM label contains a line break | Joins within CHED work on the label; no PSGC code | Replace the line break with a space in Silver; map labels to PSGC in integration |
| O-4 | Blank cells | 16 blank cells, all in `Public LUCs` (3) or `Public Other` (13) | See O-6 | See O-6 |
| O-5 | Number format | Whole numbers without commas; no `-` | Casts directly | Cast in Silver |
| O-6 | Totals add up | In 17 of 17 rows, Main + SUCs + LUCs + Other (blank as 0) = Public Total, and Public Total + Private HEIs = Total | A blank component means none | Treat blank components as 0 in Silver |

## Suspected findings

None.

## Changes across files or years

One file, one year. The bulletin prints the same table for AY 2020-2021 to 2024-2025 (pp. 9-13); only AY 2023-2024 was extracted.

## Questions for the publisher or mentor

- What is the bulletin's download URL and reuse terms?
- Do we need the other four years' tables?
