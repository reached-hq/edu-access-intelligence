# Coverage matrix

**Updated:** 2026-10-06 · Part of #8

One row per source: how it identifies places, its geographic level, years, time basis, grain, join keys, and how it reaches PSGC 2Q 2026, the master geography ([D-012](../decisions.md#d-012-which-psgc-version-to-use)). Sources still in open pull requests are included and marked.

Every number carries one evidence label:

- **Re-run:** computed from checksum-verified raw files by a script in this repository. Checks new to this matrix print under C-n from [`cross_source_coverage.py`](../../notebooks/profiling/cross_source_coverage.py).
- **Card:** taken from the source's card or profile (merged or in an open pull request), not re-run here.
- **Review:** a reviewer's check on a local copy, posted on a pull request but not yet in any card.
- **Not run:** nobody has computed it yet.

## Summary

1. **PSGC 2Q 2026 is the hub.** Every source reaches it at one of five levels: school (`school_id` through DepEd enrollment), barangay, city or municipality, province or HUC, and region. OSM reaches it only spatially, through the HDX boundaries.
2. **DepEd joins cleanly inside itself and mostly to PSGC.** All four DepEd school files join to enrollment on `school_id` with no loss, and 96.9% of SY 2023-24 schools reach a PSGC barangay by name. Later school years are not matched yet.
3. **Poverty joins entirely, and 96 HDX ADM3 units partly, through PSGC's old 9-digit `Correspondence Code`.** The PSGC card still says not to join on that code, so the rule needs updating (see [Conflicts](#conflicts-between-documents)).
4. **Name-only sources still missing a match rate:** PSA barangay population, PSA age-group population (its codes are in the API, not the CSV), and CMCI (only a partial check). FLEMMS cannot be tested until the microdata is accessed.
5. **Two gaps change school-level results:** 5,476 located schools (9.3%) sit in the 44 cities and municipalities with no poverty estimate, and the 112 Special Geographic Area schools match Region XII municipalities, so any city- or municipality-level value attached to them is wrong (see [Limits](#what-limits-the-joins)).
6. **CHED is profiled but out of scope** ([D-003](../decisions.md#d-003-higher-education-is-out-of-scope)), so its rows are for the record only.

## What each source is

| Source | Owner | Status | Place identifier | Geographic level | Years | Time basis | Grain |
|---|---|---|---|---|---|---|---|
| **DepEd** | | | | | | | |
| [deped_enrollment](../source_inventory/deped_enrollment/) | @hyenalouise | profiled | Names only: region, division, province, city or municipality, barangay | School | SY 2023-24, 2024-25, 2025-26 acquired | School year (BOSY count) | One row per school per school year |
| [deped_facilities](../source_inventory/deped_facilities/) | @hyenalouise | profiled | None; location comes from enrollment | School | SY 2023-24 only | School year | One row per school; facility measures for public schools only |
| [deped_personnel](../source_inventory/deped_personnel/) | @mafelisilda | profiled | None; location comes from enrollment | School | SY 2023-24 only | School year | One row per school |
| [deped_ellna](../source_inventory/deped_ellna/) | @mafelisilda | profiled | Region and division labels | School (selected schools) | SY 2023-24 (given May 2024) | School year | One row per assessed school |
| [deped_nat_gr6](../source_inventory/deped_nat_gr6/) | @mafelisilda | profiled | Region and division labels | School (selected schools) | SY 2023-24 (given April 2024) | School year | One row per assessed school |
| **PSA** | | | | | | | |
| [psa_psgc](../source_inventory/psa_psgc/) | @maeveylain | profiled | 10-digit PSGC; old 9-digit `Correspondence Code` | Region to barangay | 2Q 2026 (`Q4_2023` for comparison only) | Reference date 30 June 2026; population from the 2024 census | One row per geographic unit |
| [psa_poverty_stat](../source_inventory/psa_poverty_stat/) | @maeveylain | profiled | 5- or 6-digit ID: the first 6 digits of the old 9-digit PSGC | City or municipality; no HUCs | 2018, 2021, 2023 | Estimate year; 2023 uses the 2023 FIES and January 2024 LFS | One row per city or municipality, wide by year |
| [psa_population_per_barangay](../source_inventory/psa_population_per_barangay/) | @mafelisilda | profiled | Names only | Barangay | 2024 census | Census reference date, 1 July 2024 | One row per barangay; total population |
| [psa_population_per_age_group](../source_inventory/psa_population_per_age_group/) | @mafelisilda | profiled | Names in the CSV; 10-digit codes only in the OpenSTAT API metadata | Country, region, and a mixed lower level (province, HUC, Pateros, Isabela City, Special Geographic Area) | 2024 census | Census; exact date not stated in the file | One row per age group and place; household population |
| psa_openstat_education ([#58](https://github.com/reached-hq/edu-access-intelligence/pull/58)) | @hyenalouise | profiled, open PR | Region names: 35 labels for 20 keys | Country and region | Varies by table; most end SY 2022-23; literacy 2013, 2019, 2024 | School year; survey year for literacy | One row per place and category, per table |
| [FLEMMS 2024 public-use file](https://psada.psa.gov.ph/catalog/334) | @hyenalouise | candidate, not acquired | Province or HUC code `prv`; region codes `reg` (without NIR) and `reg2` (with NIR) | Person and household, weighted to province or HUC | 2024; attendance asked for SY 2024-25 | Survey (fieldwork 30 September to 22 October 2024) | One row per person or household |
| **BPDA** | | | | | | | |
| [bpda_barmm_education](../source_inventory/bpda_barmm_education/) | @hyenalouise | profiled | Division labels | Historical school division (10) | SY 2018-19 to 2020-21 | School year | One row per division |
| [bpda_barmm_social_infrastructure](../source_inventory/bpda_barmm_social_infrastructure/) | @hyenalouise | profiled | Area labels | Province, city, or Special Geographic Area (9) | Mostly undated; some 2019-2022 headers | Mostly unstated | One row per area |
| [bpda_barmm_roads](../source_inventory/bpda_barmm_roads/) | @hyenalouise | profiled | Area labels | Province, city, or Special Geographic Area (9) | Undated | Unstated | One row per area |
| [bpda_mbhte_infrastructure_projects](../source_inventory/bpda_mbhte_infrastructure_projects/) | @hyenalouise | profiled | Province and municipality names; barangay blank | Project (Basilan only) | Funded 2020-2022; monitored April 2024 | Monitoring date | One row per project record (16) |
| **Other publishers** | | | | | | | |
| dti_cmci ([#35](https://github.com/reached-hq/edu-access-intelligence/pull/35)) | @saraevcldn | profiled, open PR | Names only; 362 carry a two-letter suffix such as `Alaminos (LA)` | City or municipality (1,634) | 2023, 2024 | CMCI reference year | One row per LGU per year, one file per indicator |
| hdx_boundaries ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)) | @saraevcldn | profiled, open PR | `adm3_pcode`, `adm4_pcode`, and polygons | ADM3 city or municipality (1,642); ADM4 barangay (42,048) | `valid_on` 2025-02-13, version v03; 17 regions, before the Negros Island Region | Boundary validity date | One feature per unit |
| osm_philippines ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) | @saraevcldn | profiled, open PR | Coordinates only | Point, line, and area features | Snapshot of 2026-09-28T20:23:05Z | Extract time | One row per mapped feature |
| **CHED (out of scope, D-003)** | | | | | | | |
| [ched_enrollment](../source_inventory/ched_enrollment/) | @catweyine | profiled | Region labels | Region | AY 2020-21 to 2024-25 | Academic year, first semester | One row per region and sector |
| [ched_graduates](../source_inventory/ched_graduates/) | @catweyine | profiled | Region labels | Region | AY 2020-21 to 2024-25 | Academic year | One row per region and program level |
| [ched_school_count](../source_inventory/ched_school_count/) | @catweyine | profiled | Region labels | Region (17; no NIR row) | AY 2023-24 only | As of 10 October 2024 | One row per region |
| [ched_student_faculty_ratio](../source_inventory/ched_student_faculty_ratio/) | @catweyine | profiled | Region labels | Region | AY 2020-21 to 2024-25 | Academic year | One row per region |

## How each source joins

| Source | Join keys | Route to PSGC 2Q 2026 | Result | Not matched, and where it is listed | Evidence |
|---|---|---|---|---|---|
| **DepEd** | | | | | |
| deped_enrollment | `school_id` to the other DepEd files; place names to PSGC | Names inside their parent: province, then city or municipality, then barangay ([rules](deped_dataset_research.md#rules)) | SY 2023-24: 58,289 of 60,134 schools (96.9%) to barangay; 46,614 (77.5%) on the strict rule. SY 2024-25 and 2025-26: **not run** | 1,845 schools, [listed](deped_psgc_unmatched.md). 33 Philippine Schools Overseas excluded by rule | Re-run (A-5, A-12) |
| deped_facilities | `school_id` | Through enrollment | 60,167 of 60,167 enrollment schools, one-to-one | None | Re-run (B-2) |
| deped_personnel | `school_id` | Through enrollment | 60,167 of 60,167, one-to-one | None | Re-run (B-3) |
| deped_ellna | `school_id` | Through enrollment | 5,752 of 5,752 are in enrollment, same region | None, but only CAR and Regions I, III, VIII, IX, at 25.3% to 43.9% of their schools | Re-run (B-4, B-6) |
| deped_nat_gr6 | `school_id` | Through enrollment | 6,636 of 6,636 are in enrollment, same region | None, but the same five regions, at 27.7% to 45.4% of their schools | Re-run (B-5, B-6) |
| **PSA** | | | | | |
| psa_psgc | 10-digit PSGC | Is the reference | Not applicable | 50 rows have no `Correspondence Code`; 2 rows have no geographic level | Card (O-2, O-3) |
| psa_poverty_stat | `PSGC ID` padded to 6 digits plus `000` equals PSGC `Correspondence Code` | Code to `Correspondence Code`, then to the 10-digit PSGC | 1,612 of 1,612 rows (100%), one-to-one | 44 PSGC cities and municipalities have no estimate: 33 HUCs, Isabela City, Cotabato City, Pateros, and 8 Special Geographic Area municipalities. Kalayaan's row has no values. Named in profile X-1 and O-5 | Card (X-1); schools affected re-run (C-1) |
| psa_population_per_barangay | Names inside region, province or HUC, and city or municipality | Name match, **or** PSGC's own `2024 Population` column, which appears to hold the same census counts (see [Population](#population-can-attach-by-code)) | **Not run** | **Not run.** The source has 42,011 barangays against PSGC's 42,010 | Card (O-13); population comparison re-run (C-3) |
| psa_population_per_age_group | 10-digit codes from the OpenSTAT API, or names | Codes checked against PSGC | **Not run** (profile S-3 open) | 38 `Both Sexes` cells and 19 all-age totals are quarantined (Regions V, X, XI, ages 80 and over) | Card (O-7, O-8, O-11) |
| psa_openstat_education | Region map from 35 labels to 20 keys | Region | All 35 labels map; the script stops on an unknown label. School tables use 17 regions | `Unknown` NAT rows have no region | Card (O-2, O-8) |
| FLEMMS 2024 public-use file | `prv`; `reg` or `reg2` | Unknown whether `prv` is a PSGC code or PSA's own numbering | **Cannot be tested** until the microdata is accessed | The Special Geographic Area is not a FLEMMS domain | Documentation only |
| **BPDA** | | | | | |
| bpda_barmm_education | Division labels | Names with documented aliases ([BARMM memo](barmm_dataset_research.md#bpda-label-matches-to-psgc-2q-2026)) | 6 of 10 labels (60.0%) | `Lanao del Sur I`, `Lanao del Sur II`, `Maguindanao I`, `Maguindanao II`: school divisions, not PSGC units | Re-run (BARMM memo) |
| bpda_barmm_social_infrastructure | Area labels | Same | 8 of 9 labels (88.9%) | `Maguindanao` (not split) | Re-run (BARMM memo) |
| bpda_barmm_roads | Area labels | Same | 8 of 9 labels (88.9%) | `Maguindanao` (not split) | Re-run (BARMM memo) |
| bpda_mbhte_infrastructure_projects | Province and municipality names | Same | 4 of 4 place pairs (100%), covering all 16 records | None | Re-run (BARMM memo) |
| **Other publishers** | | | | | |
| dti_cmci | `lgu` plus `year` | Name after removing the suffix, inside the province the suffix stands for. The suffix-to-province lookup is **not built** | 1,472 of 1,634 names equal a PSGC city or municipality name once the suffix is removed. This is not yet a unique match: 122 base names belong to more than one LGU | 162 names, **not listed**. The 8 Special Geographic Area municipalities are not in CMCI | Card (reviewer's check quoted in the card) |
| hdx_boundaries | ADM3 `adm3_pcode`; ADM4 `adm4_pcode` | P-code converted to 10 digits, then PSGC; the rest through `Correspondence Code` or name | ADM3: 1,500 of 1,642 exact (91.35%). Of the other 142: 96 through `Correspondence Code`, 19 Sulu (region `19` to `09`), 18 Maguindanao del Norte and del Sur (16 by name, 2 spelled differently), 1 City of Manila by name, 8 Special Geographic Area. ADM4: 36,762 of 42,048 exact and 3,719 through `Correspondence Code` | ADM3: 10 left (8 Special Geographic Area units need a spatial check; 2 Maguindanao spellings need an alias). ADM4: 1,567 left. **Neither list is in the card yet** | ADM3 total: card (O-11). Breakdown and ADM4: review |
| osm_philippines | None; spatial only | Point or polygon inside an HDX polygon, then HDX to PSGC | **Not run** | 770 school features have blank names (124 points, 646 areas) | Card (O-3, O-4) |
| **CHED (out of scope)** | | | | | |
| ched_* (all four) | Region label | Region map | **Not run**; not needed while out of scope | BARMM has no values from AY 2023-24; the Negros Island Region has values only in AY 2024-25; school count has no NIR row | Card |

## Join paths

| Level | Sources | Key | Notes |
|---|---|---|---|
| School | DepEd enrollment, facilities, personnel, ELLNA, NAT Grade 6 | `school_id` | Enrollment is the anchor and the only DepEd file with place names |
| Barangay | DepEd (through the name match), barangay population, HDX ADM4 | 10-digit PSGC | Barangay is the level the sponsor tests ([D-013](../decisions.md#d-013-who-the-stakeholders-are)) |
| City or municipality | Poverty, CMCI, HDX ADM3, and DepEd aggregated | First 7 digits of the barangay PSGC, plus `000` | Poverty and HDX through `Correspondence Code`; CMCI by name |
| Province or HUC | Age-group population, FLEMMS, and DepEd aggregated | First 5 digits of the PSGC | HUCs have province-level codes, so totals by PSGC province already keep them separate. DepEd files independent cities under their province; the name match sends them to their own codes |
| Region | OpenSTAT, CHED, BPDA context | Explicit region map | Use DepEd's own region for SY 2023-24 (D-012) |
| Spatial | OSM, HDX geometry | Point or polygon in polygon | Needs school coordinates, which no acquired source has |

The intended path for every area source is `school_id → PSGC barangay → aggregate by PSGC code → area source`. No area source is joined directly to DepEd names.

### Population can attach by code

PSGC 2Q 2026 has a `2024 Population` column keyed by the 10-digit code. Re-run against the PSGC workbook (C-3), it matches the barangay population source on every figure that can be compared without the barangay file:

- **Total:** PSGC barangays sum to 112,727,776, the same as the barangay workbooks' geographic total (profile O-7).
- **Zero-population barangays:** 12 in both, with the same regional split: NCR 1, CAR 1, Region II 2, Region III 2, CALABARZON 3, Region VI 1, Region VIII 2 (profile O-10).

So PSGC's column is very likely the same 2024 census count, already coded. If a barangay-by-barangay comparison confirms it, barangay population attaches by code with no name crosswalk, and the name match becomes a check rather than the join. The one-barangay difference (42,011 against 42,010) still needs explaining.

## What limits the joins

| Limit | Size | Handling |
|---|---|---|
| DepEd schools not matched to a PSGC barangay | 1,845 of 60,134 (SY 2023-24) | Listed, never forced. They still count at province level where the province matched |
| Schools in a city or municipality with no poverty estimate | 5,476 of 59,110 schools with a matched city or municipality (9.3%): HUCs 5,301, Cotabato City 83, Isabela City 74, Pateros 18. Public schools: 2,607 of 47,818. Re-run (C-1) | Keep blank with reason `not_in_source`; never impute. HUC, Isabela, and Cotabato estimates exist in PSA's 2023 Official Poverty Statistics, a different method (direct estimation) |
| Special Geographic Area schools at city or municipality level | All 112 SY 2023-24 schools under `BARMM` / `NORTH COTABATO` match a Cotabato municipality in Region XII: Pikit 46, Midsayap 20, Pigkawayan 17, Kabacan 14, Carmen 12, Aleosan 3. Re-run (C-2) | A city- or municipality-level join (poverty, CMCI, ADM3) would give them those Region XII municipalities' values. Exclude them from such joins, or mark them, until their barangays are matched to the eight Special Geographic Area municipalities |
| Region changes since SY 2023-24 | 3,306 matched schools: Negros to NIR (2,725), Sulu to Region IX (469), and the 112 above | Take region from DepEd for SY 2023-24 (D-012) |
| Assessments are samples | ELLNA and NAT Grade 6 cover five regions only; none in BARMM | Report as selected schools, never as regional coverage |
| Population concepts differ | Barangay file: total population. Age-group file: household population, province or HUC and up | Never mix the two in one ratio. School-age measures stay at province or HUC level |
| Quarantined age-group cells | 38 `Both Sexes` cells and 19 all-age totals | Do not recalculate; keep out of joins |
| CMCI LGUs not in PSGC by name | 162 of 1,634, and the suffix lookup is not built | Build and review the lookup before any join |
| No school coordinates | No acquired source has them | Spatial work (OSM, distance) waits for an official coordinate list |

## Time alignment with the SY 2023-24 anchor

| Source | Time | Relation to SY 2023-24 | Label to use |
|---|---|---|---|
| DepEd enrollment, facilities, personnel, ELLNA, NAT Grade 6 | SY 2023-24 | Same | SY 2023-24 |
| PSGC | 30 June 2026 | Later geography; names still match | "PSGC 2Q 2026" |
| Poverty | 2023 estimate | Same calendar year as the start of the school year; inputs are the 2023 FIES and January 2024 LFS | "Poverty 2023" next to "SY 2023-24"; not called the same period (open question 1) |
| Barangay and age-group population | 2024 census, 1 July 2024 | Just after SY 2023-24 ends | "2024 census" |
| FLEMMS | Fieldwork October 2024; attendance SY 2024-25 | One year later | Compare with DepEd SY 2024-25, or label the years apart |
| OpenSTAT | Most tables end SY 2022-23; school counts reach SY 2023-24 | Mostly earlier | Each table's own years |
| CMCI | 2023 and 2024 | Overlaps; meaning of the year not documented | "CMCI 2023" or "CMCI 2024"; never joined on `year` against school year |
| HDX boundaries | Valid 2025-02-13, before NIR | Geography between SY 2023-24 and PSGC 2Q 2026 | "COD-AB v03" |
| OSM | 2026-09-28 | Much later | "OSM 2026-09-28" |
| BPDA | SY 2018-19 to 2020-21, or undated | Earlier | Historical context only |

## Conflicts between documents

Statements that disagree across cards, memos, and the #8 thread, with the evidence that settles each one.

| # | Where | Says | Evidence | Fix |
|---|---|---|---|---|
| 1 | [psa_psgc profile](../source_inventory/psa_psgc/profile.md) O-3 | "Do not join on" `Correspondence Code` | The poverty join (X-1, 1,612 of 1,612) and 96 HDX ADM3 units depend on it. PSGC S-2 calls it "supported, not confirmed". D-012 says to revisit when a source arrives with codes from another PSGC version, which poverty and HDX both do | Revisit D-012 to allow joins through `Correspondence Code` where a source carries old codes, and update O-3 (open question 4) |
| 2 | [BARMM memo](barmm_dataset_research.md), summary 5 | OSM has 3,572 school points | OSM also stores schools as areas: 3,572 points and 47,068 areas, 50,640 school IDs with no overlap (#39 card O-3) | Corrected in this pull request |
| 3 | #8 thread (CMCI) | 1,634 of 1,634 CMCI LGUs match non-SGA PSGC units | #35 records only 1,472 of 1,634 names found after removing the suffix. No full match or lookup is in any card. 1,634 equals 1,642 minus the 8 Special Geographic Area municipalities, which is a count, not a match | Treat CMCI as **not yet matched** until the suffix lookup and full match are in #35 |
| 4 | #8 thread (CMCI and OSM summary table) | CMCI columns `lgu_name`, `capacity_of_school`, `educational`; join to Gold on `psgc_code + year` | The files have `lgu`, `capacity_of_school_services`, `education` (#35 profile O-7). `year` is the CMCI reference year, not a school year | Use the real column names. Join on PSGC code and record the CMCI year as an attribute |
| 5 | #8 thread (OSM summary table) | 49,245 area features (`school`, `kindergarten`, `college`, `university`), "all have names" | 49,245 is right for areas only (47,068 + 217 + 1,273 + 687). 646 area schools have blank names (#39 O-4). The point layer adds 3,572 schools. Colleges and universities are higher education, out of scope under D-003 | Count both layers, `school` only (plus kindergarten if the team keeps it), and count blank names |
| 6 | #8 thread (HDX and PSGC comments) | "Only the 8 SGA units need a spatial check" | The 142 break down as 96 + 19 + 18 + 1 + 8. Two of the 18 Maguindanao units are spelled differently, so 10 are left, not 8 | Record all 10. The full breakdown and the ADM4 check should go into #38's profile |
| 7 | #8 thread (OSM comment) | The "DepEd EBEIS masterlist" lacks usable coordinates | No EBEIS masterlist is in the inventory. The DepEd files acquired have no coordinate columns at all | Name the file, or drop the reference |
| 8 | #8 thread (PSGC comment) | `Q4_2023` could bridge BPDA's pre-2024 geography | `Q4_2023` already has the Maguindanao split: the two provinces have no `Correspondence Code`, yet they are not among the 12 new codes without one (11 barangays and the NIR row, PSGC X-1), so their codes are in both files. It would not resolve BPDA's unsplit `Maguindanao`. It only keeps Sulu in BARMM, which the BARMM memo already handles by keeping the source region | No `Q4_2023` bridge needed; BPDA stays matched to 2Q 2026 as in the memo |
| 9 | [deped_dataset_research.md](deped_dataset_research.md) | Personnel and ELLNA come from open pull requests #40 and #49 | Both merged. Their card checksums equal the ones the script verifies, so the numbers stand | Point the memo at the merged cards (in #57) |
| 10 | #35 | Two folders, `cmci/` and `dti_cmci/`, with identical `profile.md` | One source should have one folder named after its `source_id` (D-006) | Remove `cmci/` in #35 |

## Open questions

1. **Poverty year:** label poverty 2023 next to SY 2023-24 (proposed), or treat them as one period?
2. **Missing poverty areas:** keep the 44 blank with reason `not_in_source` (proposed, and what the poverty card says), or acquire the 2023 Official Poverty Statistics for HUCs, Isabela, and Cotabato and accept a mixed method?
3. **Shared match columns:** one set for every place-name crosswalk (DepEd, barangay population, CMCI, BPDA) before Silver. Proposed:
   - `source_id`, `source_row_ref`, and the raw place fields, unchanged
   - `source_reference_date`
   - `psgc_version` (`2Q 2026`)
   - `psgc_code` (10 digits, blank when not matched)
   - `geographic_level` (`reg`, `prov`, `city_mun`, `bgy`)
   - `match_method` (`exact`, `old_name`, `folded`, `brackets_dropped`, `correspondence_code`, ...)
   - `match_status` (`matched`, `unmatched`, `ambiguous`, `not_in_source`, `excluded`)
   - `population_concept`, for population sources only (`total`, `household`)
4. **D-012 and `Correspondence Code`:** amend D-012 to allow joins through `Correspondence Code` for sources that carry old codes (poverty, HDX), and update PSGC O-3 (conflict 1).
5. **Special Geographic Area schools:** exclude the 112 from city- and municipality-level joins, or mark them, until their barangays are matched?
6. **OSM scope:** `school` only, or also `kindergarten`? Colleges and universities are out under D-003.
7. **Barangay population:** use PSGC's `2024 Population` column as the join, with the barangay workbooks as a check, if a barangay-by-barangay comparison agrees?

## Status against #8

| Done when | Status |
|---|---|
| One row per source: codes or names, level, years, time basis | Done for every acquired source, plus FLEMMS as a candidate |
| Grain statement and join keys per source | Done |
| Names-only sources matched to PSGC, match rate recorded | Done for DepEd and BPDA. Partial for CMCI (no unique match) and HDX ADM4 (review only). **Not run** for barangay population and age-group population. FLEMMS cannot be tested. CHED not needed (D-003) |
| Unmatched records counted and listed | Listed for DepEd and BPDA; poverty gaps named. **Not listed** for CMCI (162) or HDX (ADM3 10, ADM4 1,567) |
| Enrollment compared across SY 2023-24 to 2025-26 | Partly, in the [deped_enrollment profile](../source_inventory/deped_enrollment/profile.md): relabeled categories (O-8), school ID churn counted (O-12), NIR and province changes (O-10, O-11). **Not done:** lists of dropped and new school IDs, and the PSGC match for SY 2024-25 and 2025-26 |
