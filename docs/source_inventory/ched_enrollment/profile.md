# ched_enrollment: profile

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

Usable for regional higher-education enrollment by sector and sex, AY 2020-2021 to 2024-2025. The CSV reproduces the bulletin's Table 6 exactly (every column adds up to the printed Grand Total). BARMM and Negros Island Region are missing for some years, as in the bulletin.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | CSV matches the bulletin | 10 of 10 count columns add up to Table 6's Grand Total row | The hand extraction can be trusted | Keep the check when the CSV is re-extracted |
| O-2 | `Region` + `Sector` is unique | 36 rows, 0 duplicate keys | Safe primary key | Assert uniqueness in Bronze validation |
| O-3 | Region labels | 18 labels, the same in all four CHED CSVs; `15 - Bangsamoro Autonomous Region in Muslim Mindanao` contains a line break | Joins within CHED work on the label; no PSGC code | Replace the line break with a space in Silver; map labels to PSGC in integration |
| O-4 | Blank cells | 28 blank cells: BARMM 12, Negros Island Region 16 | Blank is not zero | Keep as null |
| O-5 | Number format | 332 filled cells, all whole numbers with thousands commas; no `-` | Must remove commas before typing | Strip commas and cast in Silver |
| O-6 | Regions missing in some years | BARMM has values in 2020-2021 to 2022-2023; Negros Island Region in 2024-2025 only | Regional trends break for these two regions | Report these region-years as not available |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | A blank BARMM or Negros Island Region year means "not reported", not zero | Ask CHED OPRKM; the bulletin gives no note | open |

## Changes across files or years

- One file. Negros Island Region first appears in 2024-2025; BARMM last appears in 2022-2023 (O-6).

## Questions for the publisher or mentor

- What are the bulletin's reuse terms?
- Why is BARMM blank from 2023-2024?
