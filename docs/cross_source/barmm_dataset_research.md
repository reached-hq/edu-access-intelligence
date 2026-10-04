# BARMM dataset research and recommendation

**Research date:** 2026-10-04  
**Scope:** sources that can add BARMM-specific evidence for education access, infrastructure, teacher load, learning outcomes, and distance. Official government sources were prioritized. A link was not treated as a usable dataset until the file or metadata was inspected.

## Recommendation

Use the two profiled BPDA workbooks as **historical BARMM context**, not as the core fact tables:

1. [`bpda_barmm_education`](../source_inventory/bpda_barmm_education/) adds division-level net-enrolment, completion, and cohort-survival rates for SY 2018-2021. Cotabato City has no completion or cohort-survival values, Lamitan City's elementary net enrolment is above 100% in all three years, and Marawi City's SY 2019-20 cohort survival is exactly 100% at both levels; these stay flagged until BPDA explains them.
2. [`bpda_barmm_social_infrastructure`](../source_inventory/bpda_barmm_social_infrastructure/) adds broad school, madrasah, classroom-building, and facility counts. Two parts are not usable yet: the private elementary and private secondary school counts are identical in 5 of 9 rows and look copied, and four classroom-building counts are far out of line with school counts.

For the analytical model, keep the existing school-level DepEd enrollment/facilities data as the anchor and acquire the missing pieces in this order:

1. **School coordinates and identifiers** from MBHTE BEMIS or a formal DepEd/MBHTE data request.
2. **Teacher/personnel counts** at school level and matching school year.
3. **Learning outcomes** from DepEd NAT/ELLNA, with PSA FLEMMS as a population-level outcome/context source.
4. **Routable roads or travel-time data**, not aggregate road-length totals.

The project should not claim that distance, crowding, or teacher load *caused* poor learning performance until predictors and outcomes are joined at a defensible common grain and time.

## Sources inspected

| Priority | Source | What it contains | Grain and time | Fit for this project | Decision / next action |
|---|---|---|---|---|---|
| A | [BPDA BARMM Education](https://knowledge.bpda.bangsamoro.gov.ph/open-data/bangsamoro-ecological-profile/population-and-social-services) | Net-enrolment, completion, and cohort-survival rates | 10 historical province/school-division labels; SY 2018-2019 to 2020-2021 | Adds BARMM-specific access and progression context below the region level | **Profiled.** Normalize to long form, but use only as contextual evidence until definitions and denominators are obtained. Keep the Cotabato City blanks, Lamitan City rates above 100%, and Marawi City 100% values flagged |
| A | [BPDA BARMM Social Infrastructure](https://knowledge.bpda.bangsamoro.gov.ph/open-data/bangsamoro-ecological-profile/infrastructure) | Counts of public/private schools, madaris, classroom buildings, selected facilities, SUCs, and ministry-supervised HEIs | 9 mixed province/city/SGA rows; mostly undated, with some 2019-2022 headers | Adds infrastructure context not present in the BARMM outcome workbook | **Profiled.** Use public school and madrasah counts descriptively; do not derive crowding or capacity. Exclude private elementary and private secondary school counts until BPDA confirms which is correct, and do not rank areas on classroom-building counts |
| A | [PSA OpenSTAT FLEMMS Table 10.13](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__3S__C10/0153E2BLRP0.px/) and [Table 10.14](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__3S__C10/0163E2BFLR0.px/) | Basic and functional literacy by region and sex | Region; 2013, 2019, 2024 | Strong official outcome context and national comparison. In 2024, BARMM basic literacy is 81.0% and functional literacy is 64.7% | **Acquire/profile with the PSA workstream.** Preserve the 2024 methodology break; do not present 2019-to-2024 changes as a like-for-like trend |
| A | [PSA 2024 FLEMMS public-use file](https://psada.psa.gov.ph/catalog/334) | Household and individual education/literacy microdata, including region, province/HUC, urbanity, weights, and literacy measures | Household/individual; 2024; province/HUC sample domains | Could support weighted BARMM province comparisons and richer equity analysis | **Candidate with restrictions.** Requires PSA access agreement, secure handling, survey weights, and disclosure controls. Prefer published aggregates if microdata is not essential |
| A | [PSA OpenSTAT Education tables](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10) | Regional NER, cohort survival, NAT Grades 6/10/12, teacher counts, and school counts | Mostly region by school year; table-specific | Best official national benchmark for the narrative and regional gap | **Coordinate with Angela's DepEd/PSA profiling** to avoid duplicate work. Relevant table IDs: `0091C2BNAT0`, `0101C2BNAT0`, `0111C2BNAT2`, `0131C2BNTP1`, `0151C2BSCH1` |
| A | [MBHTE BEMIS](https://bemis-mbhte.bangsamoro.gov.ph/pbi/report/landing) | Site advertises education performance, resources, directories, and downloadable datasets for basic, madaris, higher, and technical education | Potentially school/institution level; exact files not yet inspected | Highest-value candidate for current BARMM operational data and school identifiers | **Manual acquisition required.** The public page timed out/redirected during reproducible retrieval. Open in a browser or request an export/codebook from MBHTE; inventory before use |
| B | [BPDA Monitoring and Evaluation of MBHTE Infrastructure Projects](../source_inventory/bpda_mbhte_infrastructure_projects/) ([publisher page](https://knowledge.bpda.bangsamoro.gov.ph/open-data/bpda-monitoring-and-evaluation/mbhte-m-and-e)) | 16 monitored project records in the downloaded file, with province, municipality, project name, program, funding year, monitored date, status, type, and monitor. Two Tipo-Tipo ES repair rows may be one project, and 6 of the 16 are repairs rather than new construction | Project; 2020-2022 funding for 13 records; all delivered records are in Basilan | Useful for a limited implementation example, but not a regional infrastructure inventory; barangay is blank and coordinates are absent. Classroom counts in project names cannot be totalled because repairs add no new classrooms | **Profiled, low coverage.** Request the complete dataset, selection rules, identifiers, and version history before integration |
| B | [DepEd National Inventory Dashboard](https://www.nid.deped.gov.ph/public-dashboard/region/BARMM/division/Special%20Geographic%20Area%20Division?page=1) | Public school IDs and project-submission status; indexed page showed 116 SGA schools | School; current dashboard state | Can validate school IDs and infrastructure-project status, but is not a stable bulk source and does not solve coordinates | **Candidate for validation only.** Seek a documented bulk export/API |
| B | [DepEd geospatial-school FOI example](https://www.foi.gov.ph/agencies/deped/schools-in-the-philippines-geospatial-database/) | Demonstrates that DepEd can release a geospatial school list through a formal request | School; request-specific | A formal request could supply the coordinates needed for distance | **Prepare an MBHTE/DepEd request** specifying school ID, name, level, status, barangay/PSGC, latitude, longitude, coordinate method/date, and permission to reuse |
| C | [BPDA BARMM Roads](../source_inventory/bpda_barmm_roads/) ([publisher page](https://knowledge.bpda.bangsamoro.gov.ph/open-data/bangsamoro-ecological-profile/infrastructure)) | Road length by surface and administrative road type | 9 broad reporting areas; date not stated in workbook | Describes road conditions but contains no geometry, endpoints, routes, or travel speeds. Four province totals differ from their components by the separate Lamitan City or Marawi City values, and Cotabato City's road-opening component (43.04 km) exceeds its total (42.04 km) | **Profiled. Reject for distance computation.** May be used only as aggregate regional context |

## What is still missing for the proposed story

| Story claim or analytical need | Minimum defensible data | Current state |
|---|---|---|
| A child lives far from school | School coordinates plus child/community origin or barangay centroid, matched geography, and a routable network | Missing school coordinates and a governed routing network; straight-line distance alone is insufficient for islands and disconnected roads |
| A classroom is crowded | Learners and usable classrooms/seats at the same school, level, and school year | Existing sources have enrollment and facilities, but the BPDA file counts classroom **buildings**, not rooms or seats |
| A teacher serves too many learners | Learner and teacher counts at the same school, level, position scope, and school year | School-level personnel source still needs to be integrated and date-aligned |
| Access conditions relate to poor learning | School-level NAT/ELLNA or another outcome joined to the same school/year predictors, with appropriate controls | Candidate outcome sources exist; causal language is not yet supported |
| BARMM differs from the national picture | Comparable region-level official indicators and method notes | PSA OpenSTAT NAT, teacher/school counts, and FLEMMS can supply the benchmark |

## Distance-specific acquisition design

A usable distance model needs three linked layers:

1. **Origins:** barangay centroids, populated places, or anonymized learner communities with a dated PSGC code.
2. **Destinations:** active school ID, school level, latitude/longitude, and coordinate provenance/date.
3. **Network:** routable road/ferry/walking graph with surface or impedance attributes and a clear license.

Calculate both straight-line distance (quality-control baseline) and network travel distance/time. In BARMM, water crossings, islands, seasonal accessibility, and missing road links can make straight-line distance materially misleading. Every result should retain routing status (`routed`, `no route`, `off-network`, or `coordinate missing`) rather than silently dropping unreachable places.

## Immediate follow-up requests

- Ask MBHTE/BEMIS for a current school master list and codebook with school ID, name, sector, level, status, division, province, municipality, barangay/PSGC, latitude, longitude, coordinate method/date, enrollment, usable classrooms/seats, and teachers by school year.
- Ask BPDA for the definitions, dates, originating ministry/system, and license for all four profiled workbooks, and specifically:
  - what `-`, blank cells, and zeroes mean in the social infrastructure and roads tables;
  - why Lamitan City's net enrolment is above 100% and Marawi City's SY 2019-20 cohort survival is exactly 100%;
  - which of the private elementary and private secondary school columns is correct;
  - whether Cotabato City road opening is 42.04 km or 43.04 km, and whether province road totals include Lamitan City and Marawi City;
  - whether the two Tipo-Tipo ES repair rows are one project, and the complete MBHTE project register with IDs and selection rules.
- Coordinate with the DepEd/PSA owner before profiling OpenSTAT tables already in her assignment.
- Decide whether PSA FLEMMS microdata adds enough value to justify restricted-data handling; otherwise use its published regional/provincial aggregates.
