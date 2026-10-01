# ched_student_faculty_ratio: profile

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

Usable for regional students per faculty member, AY 2020-2021 to 2024-2025. The CSV reproduces the bulletin's Table 39 exactly (every column adds up to the printed Grand Total), and the printed ratio can be recomputed from the two counts. BARMM and Negros Island Region are missing for some years, as in the bulletin.

## Observed findings

| ID | Finding | Evidence | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | CSV matches the bulletin | 10 of 10 Student and Faculty columns add up to Table 39's Grand Total row | The hand extraction can be trusted | Keep the check when the CSV is re-extracted |
| O-2 | `Region` is unique | 18 rows, 0 duplicate keys | Safe primary key | Assert uniqueness in Bronze validation |
| O-3 | Region labels | 18 labels, the same in all four CHED CSVs; `15 - Bangsamoro Autonomous Region in Muslim Mindanao` contains a line break. BARMM's updated PSGC region code is 19 | Joins within CHED work on the label; no PSGC code | Replace the line break with a space in Silver; map labels to PSGC in integration |
| O-4 | Blank cells | 12 blank count cells: Negros Island Region 8, BARMM 4 | Blank is not zero | Keep as null |
| O-5 | Number format | 166 filled count cells, all whole numbers with thousands commas; no `-` | Must remove commas before typing | Strip commas and cast in Silver |
| O-6 | Regions missing in some years | BARMM has values in 2020-2021 to 2022-2023; Negros Island Region in 2024-2025 only | Regional trends break for these two regions | Report these region-years as not available |
| O-7 | How Ratio is computed | 84 of 84 filled ratios equal 1 : Student ÷ Faculty rounded up; only 45 match normal rounding | Ratio can be recomputed from the counts | Store Student and Faculty as numbers; recompute the ratio rather than parse the text |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | A blank BARMM or Negros Island Region year means "not reported", not zero | Ask CHED OPRKM; the bulletin gives no note | open |

## Changes across files or years

- One file. Negros Island Region first appears in 2024-2025; BARMM last appears in 2022-2023 (O-6).
- The Retrieval Rate beside Table 39 differs by year: 89%, 87%, 84%, 93%, 97%.

## Questions for the publisher or mentor

- What are the bulletin's reuse terms?
- Why is BARMM blank from 2023-2024?
