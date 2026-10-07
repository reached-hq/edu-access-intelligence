# bpda_mbhte_infrastructure_projects: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-04 |
| Profiled by | @hyenalouise |
| Tool | `analysis/profiling/profile_bpda_mbhte_infrastructure_projects.py`, standard-library XLSX reader |
| Files profiled (SHA-256) | `BARMM_MBHTE_Infrastructure_Projects.xlsx` — `9a21113c97a773bdbeba66d23cb7855b563ff91bfa8f320268b6c0b687fee734` |
| How files were read | All cells read as stored text from XLSX XML; checksum, worksheet names, workbook date system, and exact shape checked first |

## Summary

Usable only as a small descriptive list of the 16 delivered Basilan monitoring records. It is not a BARMM-wide project inventory and lacks the identifiers, locations, budgets, progress measures, and outcome fields required for project coverage or impact analysis. Published statuses and dates can be reported as source facts, but they should not be interpreted as proof that facilities became usable.

## Observed findings

| ID | Finding | Evidence (query or check, counts) | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | Project names are unique within the delivered file | 16 rows, 16 distinct exact project names, 0 exact duplicate names, and 0 fully duplicated rows | Supports file-local record tracking but not a persistent project key | Preserve source row and name; request a governed project ID |
| O-2 | Every delivered record is in Basilan | Province: `BASILAN` for 16 of 16. Municipality/city counts: Sumisip 6, Lamitan City 5, Tipo Tipo 4, Al Barka 1 | The file cannot represent or compare all BARMM provinces | Label coverage as delivered Basilan records only; do not extrapolate |
| O-3 | Barangay is completely missing | `BARANGAY` filled for 0 of 16 records | Prevents precise geographic joins and local mapping | Keep null; request barangay and PSGC rather than inferring from school names |
| O-4 | Program and funding year are incomplete | Program: GAAB 4, SDF 4, TDIF 3, QRF 2, blank 3. Funding year: 2020 4, 2021 5, 2022 4, blank 3 | Three projects cannot be grouped reliably by program or funding cohort | Preserve nulls and raw acronyms; obtain program definitions and missing values |
| O-5 | Monitoring occurred on two dates in April 2024 | 13 records decode to 2024-04-22 and 3 to 2024-04-26; all date cells are filled | Dates support monitoring-event timing only | Store raw serial and decoded date; do not treat as completion date |
| O-6 | Published status distribution is complete | `COMPLETED` 9, `ON GOING` 6, `ABANDONED` 1 | Supports a descriptive status count for these 16 records | Retain exact source wording and monitoring date; do not infer percentage progress |
| O-7 | Most records concern buildings | `BUILDING` 15 and `COVERED COURT` 1; `MONITORED BY` is `BPDA` for all 16 | Project type is coarse and does not describe capacity or usability | Use only the two published categories; retain full project name for context |
| O-8 | Core identifiers and analytical fields are absent | No project ID, school ID, PSGC, coordinates, cost, physical-progress value, start date, completion date, beneficiary count, source-system ID, or release date | Reliable joins, cost analysis, distance analysis, and impact analysis are unsupported | Request a complete project register and codebook before integration |
| O-9 | Two rows may be the same project | `Repair of Tipo-Tipo ES 6CL` and `REPAIR OF TIPO-TIPO ES3CL` name the same school and share program `TDIF`, funding year 2020, status `COMPLETED`, and monitoring date 2024-04-22. Names are unique only letter for letter (O-1) | The file may hold 15 distinct projects rather than 16, or two separate repairs at one school | Keep both rows; count them as 16 records, not 16 confirmed projects, until BPDA confirms |
| O-10 | Project names mix new construction and repairs | 10 names start with `Construction` and 6 with `Repair`. Of the 9 `COMPLETED` records, 6 are construction and 3 are repairs; 14 of 16 names carry a classroom token such as `2CL` | A completed repair fixes existing classrooms and adds no new capacity, so classroom tokens cannot be summed as new classrooms | Derive an action field (construction or repair) from the name with the raw name kept; never total classroom tokens across both actions |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The workbook may be a filtered or partial monitoring extract rather than the full MBHTE project inventory | Compare with the source Google Sheet's version history or obtain the official project register and stated selection criteria | open |
| S-2 | Tokens such as `2CL`, `3CL`, and `10CL` in project names may mean classroom quantities; for repairs they would be classrooms repaired, not added (O-10) | Obtain the project naming convention and structured scope-of-work fields from MBHTE; do not parse until confirmed | open |
| S-3 | The final three blank program and funding-year values may share a missing batch or source record | Request the original monitoring forms or project IDs and reconcile against the complete register | open |
| S-4 | The two Tipo-Tipo ES repair rows may be one project entered twice, or two separate repairs (6 and 3 classrooms) | Ask BPDA for the project IDs and contracts behind both rows | open |

## Changes across files or years

- Only one workbook delivery was acquired, so revision history and cross-delivery schema changes cannot be assessed.
- Funding year is present for 2020-2022 but missing for three records; date monitored is in April 2024 for every record.
- The data sheet contains 983 empty formatted rows after the 16 populated records. These are not counted as projects.
- `Dashboard` and `Copy of Dashboard` contain a title but no additional tabular records.

## Questions for the publisher or mentor

- Is this the complete MBHTE monitoring dataset or a Basilan-only extract? What selection rule produced these 16 rows?
- What stable project ID and school ID belong to each record?
- What are the barangay, PSGC, and coordinates for each project?
- What do GAAB, QRF, SDF, and TDIF mean, and what program and funding year apply to the three blank records?
- Does `CL` in project names mean classrooms, and is it a planned or delivered quantity?
- Are `Repair of Tipo-Tipo ES 6CL` and `REPAIR OF TIPO-TIPO ES3CL` one project or two?
- How are `COMPLETED`, `ON GOING`, and `ABANDONED` defined and validated?
- Can BPDA provide budget, physical progress, start/completion dates, beneficiary counts, source-system fields, revision history, and reuse license?

