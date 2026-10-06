# DepEd SY 2023-24: PSGC match and school ID joins

**Research date:** 2026-10-04 · Part of #8

## Purpose and method

This memo tests how the DepEd anchor, school-level enrollment for SY 2023-24, joins to the other sources: by place name to PSGC 2Q 2026, and by `school_id` to the other DepEd school files. Every number below is printed by [`notebooks/profiling/cross_source_deped.py`](../../notebooks/profiling/cross_source_deped.py) under the finding ID shown, from checksum-verified raw files:

- [`deped_enrollment`](../source_inventory/deped_enrollment/) and [`deped_facilities`](../source_inventory/deped_facilities/), SY 2023-24.
- [`deped_nat_gr6`](../source_inventory/deped_nat_gr6/), [`deped_personnel`](../source_inventory/deped_personnel/), and [`deped_ellna`](../source_inventory/deped_ellna/). Their files were re-run here, not quoted from their cards.
- [`psa_psgc`](../source_inventory/psa_psgc/) 2Q 2026, the master geography ([D-012](../decisions.md#d-012-which-psgc-version-to-use)).

The unmatched and ambiguous names are listed in [deped_psgc_unmatched.md](generated/deped_psgc_unmatched.md).

## Summary

1. **96.9% of schools match PSGC 2Q 2026 down to barangay** (58,289 of 60,134). Only 77.5% match on the strict rule (exact or old name at every level); the rest need documented rules for how DepEd writes names. 1,845 schools stay unmatched or ambiguous and are listed, not forced.
2. **Most failures are naming conventions, not missing places.** DepEd adds former names in brackets, leaves out "City" for places that became cities, files independent cities under their geographic province, and groups NCR into four districts that are not PSGC units.
3. **3,306 matched schools change region between SY 2023-24 and 2Q 2026**, all from the Negros Island Region and Sulu moves, plus 112 Special Geographic Area schools. Region must come from DepEd's own column for SY 2023-24 results.
4. **DepEd's own place names have two data problems:** 173 names (260 schools) contain mangled characters, and 13 barangay names (24 schools) are exactly 40 characters long, which looks like truncation.
5. **The school ID joins are clean.** Facilities and personnel cover all 60,167 enrollment schools one-to-one with the same sector. Every ELLNA and NAT Grade 6 school is in enrollment, with the same region, and none is in BARMM.
6. **BARMM is covered by the DepEd anchor.** 93.3% of its public schools have classroom counts and 99.2% have teachers counted, against 99.0% and 99.6% elsewhere (B-7). Its limits are no school-level assessments, the Sulu region change, and the unmatched Special Geographic Area barangays.

## A. Place names to PSGC 2Q 2026

### Rules

The [psa_psgc card](../source_inventory/psa_psgc/README.md#version-used-and-sy-2023-24) sets the rules: match province, then city or municipality inside the province, then barangay inside its city or municipality; never use region as a key; try the current name, then PSGC `Old names`; flag anything left and never force it. DepEd's names needed these extensions. Each one is a separate, counted tier, and every match must be unique among its candidates:

- **Before matching:** names with mangled characters (`PEÃ‘ARANDA` for `PEÑARANDA`) are repaired by reading them back as UTF-8. Names are compared in capitals with spaces collapsed, "City of X" is read as "X City", and a trailing "(Capital)" is dropped.
- **Folded:** accents and the punctuation `.` `-` `'` are ignored (`SANCHEZ-MIRA` matches `Sanchez Mira`).
- **Brackets dropped:** bracketed text is ignored. DepEd often writes a former name in brackets (`DARAGA (LOCSIN)`), where PSGC keeps it in `Old names`.
- **Word City ignored:** the words "City" and "of" are ignored (`BACOOR` matches `City of Bacoor`). Not used for provinces, where it would turn `CITY OF COTABATO` into Cotabato province.
- **NCR district:** DepEd's four NCR districts are matched against every NCR city, municipality, and Manila sub-municipality.
- **Documented split:** DepEd's single `MAGUINDANAO` is matched against Maguindanao del Norte and del Sur.
- **Independent city:** a city not found in its DepEd province is looked up among the 33 independent cities, which PSGC codes at province level (`CEBU CITY` under `CEBU` matches `City of Cebu`). If the province itself is unmatched, every city is searched.
- **Truncated at 40:** a 40-character barangay name may match the one PSGC barangay in its city or municipality that starts with it. No name matched this way in SY 2023-24.

The 33 Philippine Schools Overseas are excluded (A-1).

### Results

| Level | Distinct names | Exact | Old name | Folded | Brackets dropped | Word City ignored | Other documented rule | Unmatched | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Province (A-2) | 87 | 78 | 3 | 0 | 0 | — | 5 | 1 | 0 |
| City or municipality (A-3) | 1,647 | 1,529 | 1 | 4 | 69 | 7 | 18 | 19 | 0 |
| Barangay (A-4) | 34,465 | 30,449 | 13 | 133 | 2,891 | 0 | 0 | 411 | 9 |

- **Provinces:** the 5 under "other documented rule" are the 4 NCR districts and `MAGUINDANAO`. The 3 old-name matches are `COMPOSTELA VALLEY` (Davao de Oro), `WESTERN SAMAR` (Samar), and `NORTH COTABATO` (Cotabato). `CITY OF COTABATO` has no PSGC province; its 83 schools still match through the City of Cotabato in Maguindanao del Norte.
- **Cities and municipalities:** the 18 under "other documented rule" are 17 independent cities and the City of Cotabato. The largest unmatched are spelling differences: `KALOOKAN CITY` (319 schools; PSGC `City of Caloocan`), `OZAMIS CITY` (83; `City of Ozamiz`), `BARAUEN` (69; `Burauen`), and `BALIUAG` (66; `City of Baliwag`). `TONDO` (85) is `Tondo I/II` in PSGC.
- **Barangays:** 529 barangay names (1,022 schools) were not attempted because their city or municipality is unmatched. 30 names (37 schools) are blank.
- **Ambiguous barangays** fit more than one PSGC barangay in the same city. PSGC tells Sorsogon City's duplicates apart by district (`Balogo (Sorsogon East District)` and `Balogo (Bacon District)`), while DepEd writes only `BALOGO`. In Navotas and Valenzuela, one DepEd name is the old name of two PSGC barangays: `TANGOS` (Tangos North and South), `TANZA` (Tanza 1 and 2), and `CANUMAY` (Canumay East and West).

### What it means for joins

- **School share (A-5):** 58,289 of 60,134 schools (96.9%) reach a barangay code; 52,852 (87.9%) have an exact city or municipality match; 46,614 (77.5%) match on the strict rule: exact or old name at every level, with the NCR district and Maguindanao split rules allowed at province level, since those provinces cannot match exactly.
- **Unmatched (A-12):** 1,845 schools are left: 1,022 under an unmatched city or municipality, 726 with an unmatched barangay, 60 with an ambiguous barangay, and 37 with no barangay given. All are listed with their school counts.
- **Regions (A-8, A-9):** 3,306 matched schools have a different region in 2Q 2026: 1,602 from Region VI and 1,123 from Region VII to the Negros Island Region, 469 Sulu schools from BARMM to Region IX, and 112 schools that DepEd lists under BARMM but files in `NORTH COTABATO`, which now match Cotabato municipalities in Region XII. Negros and Siquijor match to barangay for 2,723 of 2,725 schools, and Sulu for 463 of 469.
- **Special Geographic Area (A-11):** those 112 schools sit in the old Cotabato municipalities in DepEd (Aleosan, Carmen, Kabacan, Midsayap, Pigkawayan, Pikit). Only 7 of their barangays are found under those municipalities, which fits PSGC 2Q 2026 listing the area's eight new municipalities separately (codes starting `19999`).

### Data problems in DepEd's place names (A-10)

- **Mangled characters:** 173 place names (260 schools) contain `Ã‘` where `Ñ` belongs, a sign the text was saved in the wrong encoding at some point. They are repaired before matching; the raw values are unchanged.
- **Possible truncation:** 13 barangay names (24 schools) are exactly 40 characters long as published, and some end mid-word or with an open bracket (`AURORA HILL PROPER (MALVAR-SGT. FLORESCA`). DepEd appears to cap the field at 40 characters.

Both are also recorded as O-17 and O-18 in the [deped_enrollment profile](../source_inventory/deped_enrollment/profile.md), for all three acquired school years.

## B. School ID joins

| File | Rows | In enrollment SY 2023-24 | Not in enrollment | Field compared | Differences |
|---|---:|---:|---:|---|---:|
| Facilities (B-2) | 60,167 | 60,167 | 0 | sector | 0 |
| [Personnel](../source_inventory/deped_personnel/) (B-3) | 60,167 | 60,167 | 0 | sector | 0 |
| [ELLNA](../source_inventory/deped_ellna/) (B-4) | 5,752 | 5,752 | 0 | region | 0 |
| NAT Grade 6 (B-5) | 6,636 | 6,636 | 0 | region | 0 |

- **Sectors (B-1):** enrollment has 47,818 public, 12,113 private, 203 SUC/LUC, and 33 overseas schools. Facilities and personnel have a row for every one of them, so a join never drops a school. The facilities card notes that facility measures are filled for public schools only.
- **Duplicates:** no file has a duplicate `school_id`.
- **Assessment coverage (B-6):** ELLNA and NAT Grade 6 cover only CAR and Regions I, III, VIII, and IX, and 5,548 schools are in both. Within those regions they cover 25.3% to 43.9% (ELLNA) and 27.7% to 45.4% (NAT Grade 6) of enrollment schools, so they are samples of schools, not full coverage:

| Region | Enrollment schools | ELLNA | NAT Grade 6 |
|---|---:|---:|---:|
| CAR | 2,080 | 527 (25.3%) | 778 (37.4%) |
| Region I | 3,393 | 1,107 (32.6%) | 1,250 (36.8%) |
| Region III | 5,194 | 1,364 (26.3%) | 1,786 (34.4%) |
| Region VIII | 4,466 | 1,962 (43.9%) | 2,027 (45.4%) |
| Region IX | 2,868 | 792 (27.6%) | 795 (27.7%) |

### BARMM coverage (B-7)

The DepEd anchor covers BARMM's public schools almost as completely as the rest of the country:

- **Schools:** all 2,603 BARMM public schools in SY 2023-24 enrollment are also in facilities and personnel.
- **Classrooms:** 2,429 (93.3%) have instructional classroom counts, against 99.0% elsewhere. The 174 without them are in Lanao del Sur (56), Maguindanao (51), Sulu (42), Tawi-Tawi (14), Basilan (8), and the Special Geographic Area schools that DepEd files under North Cotabato (3).
- **Teachers:** 2,583 (99.2%) have at least one teacher counted across the 51 teacher-position columns, against 99.6% elsewhere.

So the availability, classroom, and teacher indicators can be computed for BARMM, with the 174 schools without classroom counts excluded from the classroom ratio and counted. The limits are elsewhere: no school-level NAT or ELLNA results (B-4, B-5), Sulu under Region IX in PSGC 2Q 2026 (A-8, A-9), and only 7 of 112 Special Geographic Area schools matched to a barangay (A-11).

## Limits

- Only SY 2023-24 is tested. SY 2024-25 and 2025-26 enrollment may name places differently.
- The tiers beyond exact and old name are judgment calls. They are counted separately so a stricter rule can drop them; the strict rule (A-5) reaches 77.5% of schools at all three levels.
- A unique match is not proof that the place is the same, so every brackets-dropped match, the largest non-exact tier, is checked against what DepEd's bracket holds (A-13). All 69 cities and municipalities have a bracket that is the PSGC unit's old name. Of the 2,891 barangays, 1,710 have only "(POB.)", 1,168 have the PSGC barangay's old name, and 10 have a bracket cut off at 40 characters. Three names (7 schools) are left: in Kapalong, `SAMPAO (BIENVENIDA)` matches Sampao, and `SEMONG (SAMPAO)` matches Semong although Sampao is also a barangay there; in Samal, `SAN MIGUEL (MAGAMOMO)` matches San Miguel, whose PSGC old name is spelled Magamono. The smaller tiers were read in full: 7 word-City-ignored, 17 independent-city, 4 folded, and 1 old-name city or municipality, and the 13 old-name barangays, all of which come from PSGC's own `Old names`. The 133 folded barangays differ from PSGC only in accents, punctuation, or spacing.
