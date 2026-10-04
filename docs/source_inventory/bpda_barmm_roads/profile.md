# bpda_barmm_roads: profile

## Run details

| Field | Value |
|---|---|
| Date profiled | 2026-10-04 |
| Profiled by | @hyenalouise with AI-assisted checks; human review required before PR |
| Tool | `notebooks/profiling/profile_bpda_barmm_roads.py`, standard-library XLSX reader |
| Files profiled (SHA-256) | `BARMM_Roads.xlsx` — `5e36f1c36db08617d511d900a9052bc58b73f521d00e9b1712a4ab841cf63cc9` |
| How files were read | All cells read as stored text from XLSX XML; checksum, worksheet names, and exact shape checked first |

## Summary

Conditionally usable for an undated, descriptive summary of published road length by surface and administrative road class. It is not a spatial road network and cannot calculate distance or travel time. Geography, missing markers, explicit zeroes, reference date, and the relationship between province totals and separately listed cities require publisher clarification.

## Observed findings

| ID | Finding | Evidence (query or check, counts) | Impact | Proposed handling |
|---|---|---|---|---|
| O-1 | The data table has one unique row per published area label | 9 data rows, 9 distinct `Province/City` values, 0 duplicate keys, and 0 fully duplicated rows | Supports a file-local row key | Preserve the raw label; do not treat it as a current province code |
| O-2 | Measure cells mix numeric values, blanks, and `-` markers | 180 measure cells: 132 numeric, 41 blank, and 7 `-`; numeric range 0.00 to 1,401.18 km; median 47.325 km; 28 explicit zeroes | Missingness and zero semantics are ambiguous | Keep numeric zero, blank, and `-` as three separate raw states |
| O-3 | The seven `-` markers are concentrated in four reporting areas | Basilan municipal gravel; Sulu provincial gravel; Cotabato City barangay road opening; SGA provincial road opening, municipal earth, municipal road opening, and barangay road opening | Treating `-` as zero could understate road length | Retain as null with raw marker `-` until BPDA defines it |
| O-4 | Most complete total/component checks reconcile, but four do not | 20 combinations have numeric overall, provincial, municipal, barangay, and city values. 16 differ by no more than 0.02 km. Larger overall-minus-component differences: Lanao del Sur concrete 70.56 km, Lanao del Sur earth 4.91 km, Basilan concrete 2.65 km, and Basilan earth 1.10 km | Province and city records may overlap; naive aggregation can double count | Preserve published values and flag the four differences; do not repair or sum across rows |
| O-5 | Larger component gaps align numerically with separate city rows, but not on every surface | Basilan gaps equal Lamitan City concrete 2.65 km and earth 1.10 km. Lanao del Sur earth gap equals Marawi City earth 4.91 km; its concrete gap 70.56 km is 0.02 km above Marawi City's 70.54 km. However, Marawi City has 0.08 km of road opening while Lanao del Sur's road-opening total equals its components exactly (gap 0.00) | Suggests, but does not prove, that some province totals include separately listed city roads | Record as a suspected scope relationship and request confirmation |
| O-6 | The source has no usable fields for routing | No segment ID, road name, geometry, endpoint, coordinate, connectivity, speed, travel-time, ferry, or seasonal-access field appears in the 21-column data sheet | Cannot measure a learner's or community's distance to school | Reject for distance calculation; retain only as regional context |
| O-7 | Time and provenance are absent from the workbook | No reference date, year, source note, methodology, PSGC, boundary vintage, release date, or missing-marker definition appears in the data sheet or headers | Values cannot be aligned reliably with education school years or current boundaries | Treat as undated historical context until BPDA provides documentation |
| O-8 | One component is larger than its total | Cotabato City `City Roads ... Road Opening` is 43.04 km, but its `Local Road ... Road Opening` total is 42.04 km, exactly 1.00 km less. The barangay component is `-`, so the O-4 reconciliation skips this row, but no reading of `-` can make a 43.04 km component fit in a 42.04 km total | At least one of the two values is wrong, possibly a one-digit entry error | Retain both values and flag; do not use Cotabato City road-opening length until BPDA confirms it |

## Suspected findings

| ID | Suspicion | How to test | Status |
|---|---|---|---|
| S-1 | The Basilan total may include Lamitan City, and the Lanao del Sur total may include Marawi City, while the road-class components place those city roads in separate rows. Evidence against: Marawi City's 0.08 km of road opening is not in Lanao del Sur's road-opening gap (0.00), so the pattern does not hold for every surface (O-5) | Obtain BPDA's geographic and aggregation rules, then reconcile source-level totals before and after adding the city rows | open |
| S-2 | `-` may mean unavailable or not applicable rather than measured zero. Evidence for zero in some cells: in all 3 rows where a total can be checked against components that include `-` (Basilan gravel, Sulu gravel, SGA earth), the total balances exactly if `-` is read as zero. Cotabato City road opening cannot balance under any reading (O-8) | Obtain the workbook codebook or a written definition from BPDA | open |
| S-3 | Some explicit zeroes may represent structural non-applicability for road classes rather than surveyed zero length. 24 of the 28 zeroes are `City Roads` columns in province or SGA rows | Request the collection form and validation rules; compare with the originating roads inventory | open |

## Changes across files or years

- Only one undated workbook was acquired, so cross-delivery or cross-year schema changes cannot be assessed.
- The `BARMM Roads` sheet contains the data table. `Charts BARMM Roads` contains a chart title and no additional tabular data.
- Several numeric cells store long binary-decimal representations such as `270.59000000000003`; these are storage artefacts, not evidence of greater measurement precision.

## Questions for the publisher or mentor

- What is the reference date and originating agency or system for the road inventory?
- Which geographic boundaries and PSGC version apply to `Maguindanao`, `SGA`, and the city rows?
- Do Basilan and Lanao del Sur totals include Lamitan City and Marawi City respectively?
- Is Cotabato City road-opening length 42.04 km (total) or 43.04 km (city roads)?
- What do physical blanks, `-`, and explicit zeroes mean?
- Are columns B:E authoritative totals, calculated totals, or independently reported values?
- What are the exact definitions of provincial, municipal, barangay, city, and `Road Opening`?
- What is the dataset's publication/revision date and reuse license?

