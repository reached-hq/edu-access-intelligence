# BARMM sources: what they support and how they join

**Research date:** 2026-10-04 · Part of #8

## Purpose and method

This memo compares the sources that can add BARMM-specific evidence on education access, infrastructure, teacher load, learning outcomes, and distance, and states what each can and cannot support. Official government sources were prioritized.

- The four BPDA sources were profiled from checksum-verified files; their findings and evidence are in each source card, not repeated in full here.
- The BARMM literacy figures and OpenSTAT table IDs were checked against the downloaded OpenSTAT files.
- Teammates' sources are described from their open pull requests and were not re-profiled.
- Claims taken from web pages without inspecting the data are listed under [Not verified](#not-verified).

Each source has one status:

- **Profiled:** file inspected, source card and profile written.
- **Downloaded:** file saved with a checksum, but not yet profiled.
- **Candidate:** file or metadata partly seen; not yet acquired.
- **Not inspected:** only a landing page was seen.

## Summary

1. **The four BPDA workbooks are historical context, not fact tables.** None has a geographic code, all use pre-2024 geography, and each has flagged values that BPDA has to explain before use.
2. **Two BPDA sources are narrower than their titles suggest.** Roads has no geometry, so it cannot measure distance. The MBHTE projects file holds 16 Basilan records, so it cannot describe BARMM.
3. **DepEd school-level data stays the anchor.** Enrollment, facilities, and personnel join one-to-one on `school_id`. No BPDA source has a school ID.
4. **BARMM learning outcomes exist only at region level.** OpenSTAT NAT and FLEMMS literacy tables give regional figures. The school-level ELLNA ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49)) and NAT Grade 6 ([#50](https://github.com/reached-hq/edu-access-intelligence/pull/50)) files cover only CAR and Regions I, III, VIII, and IX.
5. **Distance analysis needs official school coordinates.** OSM ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) has 3,572 school points nationwide, far from a complete school list.

None of these sources supports a claim that distance, crowding, or teacher load *caused* poor learning outcomes. That would need predictors and outcomes joined at the same school and year.

## Source status

| Source | Status | Grain | Time | Geographic key | Use in this project |
|---|---|---|---|---|---|
| [BPDA BARMM Education](../source_inventory/bpda_barmm_education/) | Profiled | One row per historical school division (10) | SY 2018-19 to 2020-21 | Division labels; no codes | Division-level enrolment and progression context. Cotabato City blanks, Lamitan City rates above 100%, and Marawi City 100% values stay flagged |
| [BPDA BARMM Social Infrastructure](../source_inventory/bpda_barmm_social_infrastructure/) | Profiled | One row per province, city, or SGA (9) | Mostly undated; some 2019-2022 headers | Area labels; no codes | Public school and madrasah counts only. Private school counts look copied, and classroom-building counts are buildings with four outliers |
| [BPDA BARMM Roads](../source_inventory/bpda_barmm_roads/) | Profiled | One row per province, city, or SGA (9) | Undated | Area labels; no codes | Regional road-length context only. No geometry, so not usable for distance |
| [BPDA MBHTE Infrastructure Projects](../source_inventory/bpda_mbhte_infrastructure_projects/) | Profiled | One row per project record (16) | Funded 2020-2022; monitored April 2024 | Province and municipality names; barangay blank | A small Basilan example only. Possibly 15 projects; 6 are repairs |
| [PSA OpenSTAT FLEMMS Tables 10.13 and 10.14](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__3S__C10/0153E2BLRP0.px/) | Downloaded | Region by sex | 2013, 2019, 2024 | Region names | Regional literacy benchmark. BARMM 2024: basic 81.0%, functional 64.7%. The 2024 method change means 2019 to 2024 is not a like-for-like trend |
| [PSA OpenSTAT education tables](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10) | Downloaded | Region by school year | Varies by table | Region names | Regional benchmark for enrolment, cohort survival, NAT Grades 6/10/12, teachers, and schools (`0091C2BNAT0`, `0101C2BNAT0`, `0111C2BNAT2`, `0131C2BNTP1`, `0151C2BSCH1`) |
| [PSA 2024 FLEMMS public-use file](https://psada.psa.gov.ph/catalog/334) | Candidate | Household and individual | 2024 | Region, province/HUC | Weighted province comparisons, only if PSA approves access; needs secure handling, survey weights, and disclosure controls |
| [MBHTE BEMIS](https://bemis-mbhte.bangsamoro.gov.ph/pbi/report/landing) | Not inspected | Possibly school or institution | Unknown | Unknown | Strongest candidate for current BARMM school IDs and coordinates; needs a manual export or a request to MBHTE |
| [DepEd National Inventory Dashboard](https://www.nid.deped.gov.ph/public-dashboard/region/BARMM/division/Special%20Geographic%20Area%20Division?page=1) | Not inspected | School | Current dashboard state | School ID | Possible check on school IDs and project status; not a bulk source |

Thirteen OpenSTAT tables, including the FLEMMS tables, were downloaded from the API on 2026-10-04 with SHA-256 checksums. They are kept locally outside git and are not yet in the raw volume or given a source card.

## How the sources join

### Keys

- **School ID.** DepEd enrollment (SY 2023-24 to 2025-26), facilities (SY 2023-24), personnel ([#40](https://github.com/reached-hq/edu-access-intelligence/pull/40), SY 2023-24), and the school-level ELLNA and NAT Grade 6 files ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49), [#50](https://github.com/reached-hq/edu-access-intelligence/pull/50), SY 2023-24) all carry `school_id`. Facilities and personnel each match all 60,167 SY 2023-24 enrollment IDs one-to-one. No BPDA source has a school ID, and MBHTE project names cannot be matched to schools without manual review.
- **PSGC code.** PSGC 2Q 2026 is the master geography ([D-012](../decisions.md#d-012-which-psgc-version-to-use)). The COD-AB boundaries ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)) carry administrative codes: 1,500 of 1,642 municipality codes (91.35%) match PSGC 2Q 2026 exactly, and the rest need a crosswalk before use.
- **Names only.** DepEd location fields, all four BPDA workbooks, the PSA barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)), and the OpenSTAT tables have place names but no codes. They join to PSGC only by name matching.
- **Coordinates.** OSM school points and roads ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) join to the boundaries spatially, not by key.

### Geography versions

The sources describe BARMM at different dates, so the same name can mean a different area:

- **BPDA workbooks:** pre-2024 geography. Sulu is inside BARMM, Maguindanao is either one province or two school divisions (I and II), and the Special Geographic Area is one row. The Education workbook uses school divisions, which are not local government units.
- **PSA barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)):** 1 July 2024 geography, still with Sulu under BARMM.
- **COD-AB boundaries ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)):** valid 2025-02-13.
- **PSGC 2Q 2026:** Sulu is under Region IX, and Maguindanao is split into del Norte and del Sur.

A direct name match from the BPDA labels to PSGC 2Q 2026 is therefore expected to fail for Sulu, Maguindanao, the numbered divisions, and SGA. The match rates that #8 asks for have not been computed for the BARMM sources yet.

### Timing

The DepEd anchor is SY 2023-24. The BPDA Education rates cover SY 2018-19 to 2020-21, two of which overlap COVID-19 disruption; Social Infrastructure and Roads are mostly undated; MBHTE projects were monitored in April 2024. BPDA values therefore cannot be joined to DepEd records as same-year predictors. They can sit beside the school-level results as historical regional context.

## Distance design

A usable distance model needs three linked layers:

1. **Origins:** barangay centroids, populated places, or anonymized learner communities with a dated PSGC code. Candidate: centroids of the COD-AB barangay polygons ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38), valid 2025-02-13), weighted by 2024 barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)).
2. **Destinations:** active school ID, school level, latitude/longitude, and coordinate provenance/date. OSM school points ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) are partial and need matching to DepEd school IDs; an official coordinate list is still needed. DepEd has released a [geospatial school list through FOI](https://www.foi.gov.ph/agencies/deped/schools-in-the-philippines-geospatial-database/) before, so a formal request to DepEd or MBHTE is a realistic route.
3. **Network:** routable road/ferry/walking graph with surface or impedance attributes and a clear license. Candidate: OSM roads ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)), with assumed speeds by road class because most records have no speed limit.

Calculate both straight-line distance (quality-control baseline) and network travel distance/time. In BARMM, water crossings, islands, seasonal accessibility, and missing road links can make straight-line distance materially misleading. Every result should retain routing status (`routed`, `no route`, `off-network`, or `coordinate missing`) rather than silently dropping unreachable places.

The candidate layers are dated differently: the OSM extract is from 2026-09-28, the COD-AB boundaries are valid 2025-02-13, barangay population is as of 1 July 2024, the PSGC master is 2Q 2026, and the DepEd anchor is SY 2023-24. Each distance result should record the date of every layer it used, and barangays that changed between those dates should be flagged rather than forced to match.

## Not verified

These statements come from landing pages, catalogs, or teammates' cards and were not checked against data for this memo:

- **DepEd National Inventory Dashboard:** a search-indexed page showed 116 schools in the Special Geographic Area division. The dashboard itself was not opened or counted.
- **MBHTE BEMIS:** the public page timed out or redirected during retrieval, so its datasets and downloads are unconfirmed.
- **PSA 2024 FLEMMS public-use file:** the variables, province/HUC domains, and weights are taken from the PSA catalog page; the file was not accessed.
- **DepEd FOI geospatial school list:** the FOI request page was seen; the released file was not inspected.
- **Teammates' sources:** the OSM school count ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)), the COD-AB code match rate ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)), the ELLNA and NAT Grade 6 region coverage ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49), [#50](https://github.com/reached-hq/edu-access-intelligence/pull/50)), and the 60,167 school-ID matches ([#40](https://github.com/reached-hq/edu-access-intelligence/pull/40)) come from their source cards and were not re-run here.
