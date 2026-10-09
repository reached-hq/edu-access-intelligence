# BARMM sources: what they support and how they join

**Research date:** 2026-10-04 · Part of #8

## Purpose and method

This memo compares the sources that can add BARMM-specific evidence on education access, infrastructure, teacher load, learning outcomes, and distance, and states what each can and cannot support. Official government sources were prioritized.

- The four BPDA sources were profiled from checksum-verified files; their findings and evidence are in each source card, not repeated in full here.
- The OpenSTAT tables were profiled from checksum-verified files in [#58](https://github.com/reached-hq/edu-access-intelligence/pull/58); the BARMM literacy figures and table IDs here come from that profile.
- Teammates' sources are described from their open pull requests and were not re-profiled.
- Claims taken from web pages without inspecting the data are listed under [Not verified](#not-verified).

Each source has one status:

- **Profiled:** file inspected, source card and profile written.
- **Downloaded:** file saved with a checksum, but not yet profiled.
- **Candidate:** file or metadata partly seen; not yet acquired.
- **Not inspected:** only a landing page was seen.

## Summary

1. **The four BPDA workbooks are historical context, not fact tables.** None of the four profiled BPDA workbooks supplies a governed geographic code, the three region-wide workbooks use pre-2024 geography, and each has documented data-quality limitations that should be considered before use.
2. **Two BPDA sources are narrower than their titles suggest.** Roads has no geometry, so it cannot measure distance. The MBHTE projects file holds 16 Basilan records, so it cannot describe BARMM.
3. **DepEd school-level data stays the anchor.** Enrollment, facilities, and personnel join one-to-one on `school_id`. No BPDA source has a school ID.
4. **BARMM learning outcomes exist only at region level.** OpenSTAT NAT and FLEMMS literacy tables give regional figures. The school-level ELLNA ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49)) and NAT Grade 6 ([`deped_nat_gr6`](../source-inventory/deped_nat_gr6/)) files cover only CAR and Regions I, III, VIII, and IX.
5. **Distance analysis needs official school coordinates.** OSM ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) maps 50,640 schools nationwide (3,572 as points and 47,068 as areas), against about 60,000 in DepEd, and none carries a DepEd school ID.
6. **The DepEd anchor covers BARMM, so BARMM can be included on purpose.** DepEd's SY 2023-24 region field classifies 2,603 public schools as BARMM, including Sulu; all are in enrollment, facilities, and personnel. Of those schools, 93.3% have classroom counts and 99.2% have teachers counted, against 99.0% and 99.6% elsewhere ([#57](https://github.com/reached-hq/edu-access-intelligence/pull/57), B-7).

None of these sources supports a claim that distance, crowding, or teacher load *caused* poor learning outcomes. That would need predictors and outcomes joined at the same school and year.

## Recommendation: include BARMM, with stated limits

This is a recommendation for the team, not yet a decision. If agreed, it should be recorded in `decisions.md`.

BARMM can be analyzed with the same DepEd indicators as the rest of the country: school availability, classroom pressure, and teacher pressure all have near-complete coverage there ([#57](https://github.com/reached-hq/edu-access-intelligence/pull/57), B-7). Excluding it would drop 2,603 public schools classified as BARMM in DepEd's SY 2023-24 region field, including Sulu. We would include it on purpose and state these limits wherever BARMM results appear:

- 174 BARMM public schools (6.7%) have no classroom counts and are left out of the classroom ratio, compared with 1.0% elsewhere.
- BARMM has no school-level NAT or ELLNA results, so learning outcomes stay at region level.
- Sulu is in BARMM for SY 2023-24 but under Region IX in PSGC 2Q 2026, so regional totals must say which map they use.
- Only 7 of the 112 SY 2023-24 DepEd schools filed under `BARMM` / `NORTH COTABATO`, the Special Geographic Area set used in [#57](https://github.com/reached-hq/edu-access-intelligence/pull/57), match a barangay in PSGC 2Q 2026, so barangay results there are incomplete.
- The BPDA workbooks are historical background only; they cannot be joined to DepEd year for year.

## Source status

| Source | Status | Grain | Time | Geographic key | Use in this project |
|---|---|---|---|---|---|
| [BPDA BARMM Education](../source-inventory/bpda_barmm_education/) | Profiled | One row per historical school division (10) | SY 2018-19 to 2020-21 | Division labels; no codes | Division-level enrolment and progression context. Cotabato City blanks, Lamitan City rates above 100%, and Marawi City 100% values stay flagged |
| [BPDA BARMM Social Infrastructure](../source-inventory/bpda_barmm_social_infrastructure/) | Profiled | One row per province, city, or SGA (9) | Mostly undated; some 2019-2022 headers | Area labels; no codes | Public school and madrasah counts only. Private school counts look copied, and classroom-building counts are buildings with four outliers |
| [BPDA BARMM Roads](../source-inventory/bpda_barmm_roads/) | Profiled | One row per province, city, or SGA (9) | Undated | Area labels; no codes | Regional road-length context only. No geometry, so not usable for distance |
| [BPDA MBHTE Infrastructure Projects](../source-inventory/bpda_mbhte_infrastructure_projects/) | Profiled | One row per project record (16) | Funded 2020-2022; monitored April 2024 | Province and municipality names; barangay blank | A small Basilan example only. The file has 16 project records, including 6 repairs. Two Tipo-Tipo records may refer to one project, but this is unconfirmed |
| [PSA OpenSTAT FLEMMS Tables 10.13 and 10.14](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__3S__C10/0153E2BLRP0.px/) | Profiled | Region by sex | 2013, 2019, 2024 | Region names | Regional literacy benchmark. BARMM 2024: basic 81.0%, functional 64.7%. National functional literacy falls from 91.6% to 70.8% between 2019 and 2024, but PSA changed both definitions and the test for 2024 (PSA Board Resolution No. 13, Series of 2024; FLEMMS 2024 Technical Notes, p. 1 and 3). In 2019, finishing high school or junior high school counted as functional literacy; in 2024 it must be shown on a test. So 2024 is not comparable with earlier years as a trend |
| [PSA OpenSTAT education tables](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10) | Profiled | Region by school year | Varies by table; most end at SY 2022-23 | Region names | Regional benchmark for enrolment, cohort survival, NAT Grades 6/10/12, teachers, and schools (`0091C2BNAT0`, `0101C2BNAT0`, `0111C2BNAT2`, `0131C2BNTP1`, `0151C2BSCH1`). The SY 2023-24 school counts equal DepEd's enrollment file in every region, so they confirm the anchor rather than add new evidence |
| [PSA 2024 FLEMMS public-use file](https://psada.psa.gov.ph/catalog/334) | Candidate | Household and individual | 2024 (fieldwork 30 September to 22 October 2024) | Province/HUC code (`PRV`) | Weighted province comparisons: provinces and HUCs are the sampling domains, including Basilan, Lanao del Sur, Maguindanao del Norte (with Cotabato City), Maguindanao del Sur, Sulu, and Tawi-Tawi; the Special Geographic Area is not listed in the coverage. Includes school attendance, how each student travels to school (up to three modes), and the reason for not attending (ages 3 to 30), with region codes both with and without the Negros Island Region. Needs survey weights, design variables, and disclosure controls |
| [MBHTE BEMIS](https://bemis-mbhte.bangsamoro.gov.ph/pbi/report/landing) | Not inspected | Possibly school or institution | Unknown | Unknown | Strongest candidate for current BARMM school IDs and coordinates; needs a manual export or a request to MBHTE |
| [DepEd National Inventory Dashboard](https://nid.deped.gov.ph/public-dashboard/region/BARMM/division/Special%20Geographic%20Area%20Division?page=1) | Candidate | School | Current dashboard state; school list matches SY 2024-25 | School ID | A check on school IDs and inventory-submission status only. No export, download, or API link |

The DepEd National Inventory Dashboard was opened on 2026-10-04. Its Special Geographic Area division page lists 116 schools (47 not started, 41 API imported, 28 submitted; 45 projects), and those 116 school IDs are exactly DepEd's 116 public schools in that division in SY 2024-25; 111 of the dashboard IDs are present in SY 2023-24, and SY 2025-26 adds one (`306532`). This 111-school overlap is different from the 112-school set in [#57](https://github.com/reached-hq/edu-access-intelligence/pull/57): that set contains every SY 2023-24 DepEd school filed under `BARMM` / `NORTH COTABATO`, including one school outside the dashboard's current roster. The `www.` address fails a certificate check; `nid.deped.gov.ph` works.

The thirteen OpenSTAT tables, including the FLEMMS tables, are profiled as `psa_openstat_education` in [#58](https://github.com/reached-hq/edu-access-intelligence/pull/58) and stored in `/Volumes/edu_access/00-source/raw/psa/openstat/`.

## How the sources join

### Keys

- **School ID.** DepEd enrollment (SY 2023-24 to 2025-26), facilities (SY 2023-24), personnel ([#40](https://github.com/reached-hq/edu-access-intelligence/pull/40), SY 2023-24), and the school-level ELLNA and NAT Grade 6 files ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49), [`deped_nat_gr6`](../source-inventory/deped_nat_gr6/), SY 2023-24) all carry `school_id`. Facilities and personnel each match all 60,167 SY 2023-24 enrollment IDs one-to-one. No BPDA source has a school ID, and MBHTE project names cannot be matched to schools without manual review.
- **PSGC code.** PSGC 2Q 2026 is the master geography ([D-012](../../governance/decisions.md#d-012-which-psgc-version-to-use)). The COD-AB boundaries ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)) carry administrative codes: 1,500 of 1,642 municipality codes (91.35%) match PSGC 2Q 2026 exactly, and the rest need a crosswalk before use.
- **Names only.** DepEd location fields, all four BPDA workbooks, the PSA barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)), and the OpenSTAT tables have place names but no codes. They join to PSGC only by name matching.
- **Coordinates.** OSM school points and roads ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) join to the boundaries spatially, not by key.

### Geography versions

The sources describe BARMM at different dates, so the same name can mean a different area:

- **BPDA Education, Social Infrastructure, and Roads:** pre-2024 geography. Sulu is inside BARMM, and Maguindanao is either one province or two school divisions (I and II). Social Infrastructure and Roads list the Special Geographic Area as one `SGA` row. The Education workbook uses school divisions, which are not local government units. The MBHTE projects file names only Basilan places.
- **PSA barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)):** 1 July 2024 geography, still with Sulu under BARMM.
- **COD-AB boundaries ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)):** valid 2025-02-13.
- **PSGC 2Q 2026:** Sulu is under Region IX, and Maguindanao is split into del Norte and del Sur.

### BPDA label matches to PSGC 2Q 2026

All distinct reporting-area labels in the four BPDA workbooks were compared with the team's [PSGC 2Q 2026 reference](../source-inventory/psa_psgc/README.md). Matching normalized case and whitespace, used parent geography, and allowed only unambiguous form aliases: `Lamitan City`, `Marawi City`, and `Cotabato City` to PSGC's `City of ...` form; `SGA` or `Special Geographic Area (SGA)` to `Special Geographic Area` (`1999900000`); and missing hyphens in the MBHTE labels `Tipo Tipo` and `Al Barka`. Historical areas were not forced onto current units.

| BPDA source | Unit tested | Matched | Match rate | Matched labels | Unmatched labels |
|---|---|---:|---:|---|---|
| Education | 10 distinct reporting-area labels | 6 | 60.0% | `Basilan`; `Lamitan City`; `Marawi City`; `Sulu`; `Tawi-Tawi`; `Cotabato City` | `Lanao del Sur I`; `Lanao del Sur II`; `Maguindanao I`; `Maguindanao II` |
| Social Infrastructure | 9 distinct reporting-area labels | 8 | 88.9% | `Lanao del Sur`; `Basilan`; `Sulu`; `Tawi-Tawi`; `Cotabato City`; `Special Geographic Area (SGA)`; `Lamitan City`; `Marawi City` | `Maguindanao` |
| Roads | 9 distinct reporting-area labels | 8 | 88.9% | `Lanao del Sur`; `Basilan`; `Sulu`; `Tawi-Tawi`; `Cotabato City`; `SGA`; `Lamitan City`; `Marawi City` | `Maguindanao` |
| MBHTE Infrastructure Projects | 4 distinct Basilan province-municipality/city pairs across 16 records | 4 (16 records) | 100.0% | `Basilan` with `Lamitan City`, `Sumisip`, `Tipo Tipo`, or `Al Barka` | None |

The four Education division labels are not PSGC units. The unsplit `Maguindanao` label is ambiguous because PSGC 2Q 2026 has `Maguindanao del Norte` and `Maguindanao del Sur`. Sulu matches province code `0906600000`, but that code now sits under Region IX, so the match does not preserve the workbook's historical BARMM region. For DepEd's BARMM schools, [#57](https://github.com/reached-hq/edu-access-intelligence/pull/57) matched SY 2023-24 place names to PSGC 2Q 2026: 463 of 469 Sulu schools reach a barangay, now under Region IX, but only 7 of the 112 `BARMM` / `NORTH COTABATO` schools do, because PSGC now lists the area's barangays under eight new municipalities.

### Timing

The DepEd anchor is SY 2023-24. The BPDA Education rates cover SY 2018-19 to 2020-21, two of which overlap COVID-19 disruption; Social Infrastructure and Roads are mostly undated; MBHTE projects were monitored in April 2024. BPDA values therefore cannot be joined to DepEd records as same-year predictors. They can sit beside the school-level results as historical regional context.

## Distance design

A usable distance model needs three linked layers:

1. **Origins:** barangay centroids, populated places, or anonymized learner communities with a dated PSGC code. Candidate: centroids of the COD-AB barangay polygons ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38), valid 2025-02-13), weighted by 2024 barangay population ([#41](https://github.com/reached-hq/edu-access-intelligence/pull/41)).
2. **Destinations:** active school ID, school level, latitude/longitude, and coordinate provenance/date. OSM school points and areas ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) are partial and need matching to DepEd school IDs; an official coordinate list is still needed. DepEd has released a [geospatial school list through FOI](https://www.foi.gov.ph/agencies/deped/schools-in-the-philippines-geospatial-database/) before, so a formal request to DepEd or MBHTE is a realistic route.
3. **Network:** routable road/ferry/walking graph with surface or impedance attributes and a clear license. Candidate: OSM roads ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)), with assumed speeds by road class because most records have no speed limit.

The FLEMMS 2024 public-use file is a separate, survey-based check: it records how each student travels to school, weighted to provinces and HUCs. It gives reported travel mode, not distance, so it can test a distance model's results but not replace them.

Calculate both straight-line distance (quality-control baseline) and network travel distance/time. In BARMM, water crossings, islands, seasonal accessibility, and missing road links can make straight-line distance materially misleading. Every result should retain routing status (`routed`, `no route`, `off-network`, or `coordinate missing`) rather than silently dropping unreachable places.

The candidate layers are dated differently: the OSM extract is from 2026-09-28, the COD-AB boundaries are valid 2025-02-13, barangay population is as of 1 July 2024, the PSGC master is 2Q 2026, and the DepEd anchor is SY 2023-24. Each distance result should record the date of every layer it used, and barangays that changed between those dates should be flagged rather than forced to match.

## Not verified

These statements come from landing pages, catalogs, or teammates' cards and were not checked against data for this memo:

- **MBHTE BEMIS:** on 2026-10-04 the reports page first returned a Cloudflare timeout (error 524) and then `404 Not Found`, and the site's home page also returned `404 Not Found`. The page may have moved, so its datasets and downloads are unconfirmed.
- **PSA 2024 FLEMMS public-use file:** the variables, domains, and weights come from the catalog's documentation PDF (`ddi-documentation-english-334.pdf`, SHA-256 `0f7f20f7e75302385419521b521b77cbe520294cfa1b0eaf8b45901b00256598`, stored in `/Volumes/edu_access/00-source/raw/psa/flemms/`). The FLEMMS 2024 Technical Notes and PUF User's Guide (same folder) add the definitions and the variable list. None of the three documents states the access conditions, and the microdata was not accessed.
- **DepEd FOI geospatial school list:** the FOI request page was seen; the released file was not inspected.
- **Teammates' sources:** the OSM school count ([#39](https://github.com/reached-hq/edu-access-intelligence/pull/39)) and the COD-AB code match rate ([#38](https://github.com/reached-hq/edu-access-intelligence/pull/38)) come from their source cards and were not re-run. The ELLNA and NAT Grade 6 region coverage and the 60,167 school-ID matches were re-run from the raw files in [#57](https://github.com/reached-hq/edu-access-intelligence/pull/57).
