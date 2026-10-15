# Metric and dashboard specification

**Status:** Draft analytical contract. No metric in this document is an official DepEd indicator or adequacy standard unless its row explicitly says so. Team approval, source validation, and implemented tests are still required before publication.

## Purpose and document boundary

This document translates the approved [business and analytical questions](business-analytics-problem.md) into candidate measures and dashboard fields. It owns formulas, grains, filters, comparison rules, display fields, and validation status. It does not redefine the approved questions, assign datasets to scope, describe stakeholder authority, or establish external standards; those belong to the business-question document, [dataset use map](dataset-use-map.md), [stakeholder document](stakeholders.md), and [national benchmark register](national-benchmarks-and-indicators.md).

## Current validation conclusion

The proposed ratio structures are reasonable analytical candidates, but they are **not yet fully validated production metrics**.

| Area | What is supported now | What prevents final approval |
|---|---|---|
| **AP1 · Schools** | Public-school and enrollment counts can be aggregated by matched LGU and school year; 97.9% of SY 2023-24 schools (58,876 of 60,134) reach a PSGC barangay by name | Active-school rule, education-level counting rule, and treatment of schools with zero enrollment still require an explicit contract; the barangay roll-up needs a rule for the 1,258 schools without a unique barangay match |
| **AP2 · Classrooms** | SY 2023-24 enrollment and facilities match one-to-one by `school_id`; classroom counts are typed | The facilities field uses the NSBI “instructional classroom” definition, which includes rooms beyond Kindergarten-to-Grade-12 classrooms. It is not DepEd's published classroom–learner ratio and has ambiguous missing values and extreme observations |
| **AP3 · Teachers** | SY 2023-24 enrollment and personnel match one-to-one by `school_id`; personnel counts are typed | The included teaching positions are not approved, people may be counted across roles or levels, blanks are ambiguous, outliers remain under review, and DepEd's method requires annex-to-mother-school consolidation |
| **AP4 · Population and enrollment** | Ages 5–17, the two matched periods (2020 and 2024), and all-sector enrollment are defined; PSA single-year-age workbooks for every city and municipality were found for 2020 and 2024; SY 2024-25 enrollment is acquired | The PSA workbooks are not yet profiled or ingested and carry names only, with no PSGC codes; SY 2020-21 enrollment is not yet acquired |
| **Resource-gap estimates** | RA No. 7880 supplies a 45:1 statutory classroom-shortage reference; the arithmetic form can be documented as a candidate | The current NSBI room field includes spaces excluded by the law, no current general teacher threshold has been validated, and the operational assumptions behind converting a ratio into rooms or teachers have not been approved |

The DepEd evidence for these limitations is recorded in the source cards for [enrollment](../data/source-inventory/deped_enrollment/README.md#limitations-for-analysis), [facilities](../data/source-inventory/deped_facilities/README.md#limitations-for-analysis), and [personnel](../data/source-inventory/deped_personnel/README.md#limitations-for-analysis), with observed tests in their linked profiles.

## Contract conventions

Every published measure must declare:

1. **grain** — LGU, school year, and education level where supported;
2. **scope** — public schools only for AP1 to AP3; all sectors for AP4; Philippine Schools Overseas excluded from every LGU result;
3. **numerator and denominator** — exact approved fields and filters;
4. **aggregation** — calculate ratios from aggregated sums, not the unweighted average of school ratios;
5. **missingness** — NULL remains missing and is never converted to zero without publisher evidence;
6. **coverage** — both school and enrolled-learner coverage accompany AP2 and AP3;
7. **geography** — the school-to-PSGC match version and unmatched/excluded counts;
8. **period** — school year or population reference year shown on every result; and
9. **quality status** — unresolved outliers, annex handling, and definition mismatches remain visible.

## Candidate analytical metrics

These formulas define what must be validated; they do not by themselves authorize publication.

### AP1 · School-provision context

```text
learners_per_public_school = public_school_enrollment / public_school_count
public_schools_per_10k_residents = public_school_count / total_population * 10,000

barangays_without_public_es =
    PSGC barangays in the LGU with no matched public school offering elementary
barangays_without_public_es_pct =
    barangays_without_public_es / PSGC barangays in the LGU * 100
```

Use `COUNT(DISTINCT school_id)` and sum enrollment at the same LGU, education-level, and school-year grain. Total population must retain its own reference year. This measure describes provision and school size; it does not measure travel access or prove that construction is required.

The barangay measures follow DepEd Order No. 40, s. 2014, which expects at least one Kindergarten-to-Grade-6 school for every barangay (see the [national benchmark register](national-benchmarks-and-indicators.md#ap1--school-provision-references)). They are calculated per city or municipality and school year from the full PSGC 2Q 2026 barangay list and are never ranked by barangay. A school that does not reach a unique barangay can make a served barangay look unserved, so each LGU also shows its count of public schools without a barangay match, and a result with any such school is labelled an upper bound. A barangay without its own school may still be served by a nearby school, so the count is a screen for review, not evidence that a school is needed.

**Validation status:** candidate. Approve the active-school, zero-enrollment, multi-level-school, and level-specific counting rules, and the handling of schools without a unique barangay match, before implementation.

### AP2 · Classroom pressure

```text
learners_per_nsbi_instructional_room =
    matched_public_school_enrollment / reported_nsbi_instructional_rooms

school_coverage_pct =
    public_schools_with_usable_room_count / public_schools_in_scope * 100

learner_coverage_pct =
    enrollment_in_schools_with_usable_room_count / public_school_enrollment * 100
```

The ratio of sums is computed only from schools with a usable denominator. Schools with a recorded zero room count are not silently dropped: they receive a separate zero-denominator flag and count. Missing room counts remain NULL and are reported separately.

The dashboard label must say **learners per reported instructional room**, with the source shown separately as **DepEd School Facilities (NSBI)**. It must not be labelled “DepEd classroom–learner ratio.” NSBI is the source system behind the DepEd School Facilities data; it is not a different facilities dataset. DepEd's source documentation says `*_classrooms_instructional` includes ALS, audio-visual, computer, industrial-arts, home-economics, and laboratory rooms, while its published classroom–learner indicator uses Kindergarten-to-Grade-12 classrooms. The available data therefore tend to produce a lower ratio than the official indicator.

**Validation status:** candidate for a project-defined descriptive measure, limited to SY 2023-24. Review the extreme upper tail and decide whether elementary, JHS, and SHS fields may be combined before publication.

### AP3 · Teacher pressure

```text
learners_per_teacher =
    matched_public_school_enrollment / approved_teacher_count

school_coverage_pct =
    public_schools_with_usable_teacher_count / public_schools_in_scope * 100

learner_coverage_pct =
    enrollment_in_schools_with_usable_teacher_count / public_school_enrollment * 100
```

`approved_teacher_count` is intentionally unresolved. It must be a reviewed list of personnel columns and funding sources, with a rule for possible duplication across levels and roles. The source measures personnel actually working in public schools; they are not authorized plantilla positions, vacancies, or approved new items.

DepEd's documented teacher–learner method adds annex enrollment and teachers to the mother school before division. A DepEd-aligned result is blocked until an annex-to-mother-school crosswalk and the teacher-column list are validated. A provisional ratio that leaves annexes separate must be labelled as project-defined and must not claim to reproduce DepEd's indicator.

**Validation status:** blocked for publication as a DepEd-aligned ratio. Also resolve the reviewed personnel outliers and ambiguous blanks.

### AP4 · School-age population and enrollment gap

```text
school_age_population =
    PSA Total Population, ages 5–17, both sexes
enrollment_all_sectors =
    enrollment in public, private, and SUC/LUC schools,
    excluding Philippine Schools Overseas

population_enrollment_gap = school_age_population - enrollment_all_sectors
gap_share = population_enrollment_gap / school_age_population
gap_change_2020_2024 = population_enrollment_gap (2024) - population_enrollment_gap (2020)

public_school_share = public_school_enrollment / enrollment_all_sectors
```

**Matched periods.** "Over time" means two points. Each pairs a census with the school year that starts in the same year:

| AP4 period | Population | Enrollment |
|---|---|---|
| **2020** | 2020 Census of Population and Housing (CPH), reference date May 1, 2020 | SY 2020-21 |
| **2024** | 2024 Census of Population (POPCEN), reference date July 1, 2024 | SY 2024-25, which opened on July 29, 2024 (DepEd Order No. 9, s. 2024) |

SY 2023-24 and SY 2025-26 have no census in the same year, so their AP4 value is **not available**. Their enrollment can still appear in a separate enrollment trend. Version 1 does not interpolate or extrapolate population between or beyond the two census years.

**Age range.** Ages 5–17 match Kindergarten to Grade 12 at official school age. PSA's broader 5–24 "school-age population" is not used. Population comes from the Total Population sheet (not Household Population), both sexes combined.

**Enrollment scope.** Unlike AP1 to AP3, AP4 counts learners in every sector, because the population side counts every resident child wherever they study. Philippine Schools Overseas are excluded because their learners are abroad and belong to no city or municipality. The public-school share is shown beside the gap. Using public-school enrollment alone would count private-school learners as part of the gap. For 2024 nationally:

| | Enrollment, SY 2024-25 | Gap from 27,569,038 residents aged 5–17 | Gap share |
|---|---:|---:|---:|
| All sectors except Philippine Schools Overseas | 26,375,327 | 1,193,711 | 4.3% |
| Public schools only | 22,543,711 | 5,025,327 | 18.2% |

About 3.83 million of the public-only gap is private and SUC/LUC learners.

**Reading the gap.**

- Population is counted where people live; enrollment is counted where the school is. The gap is not an out-of-school count or an enrollment rate and must never be labelled as either.
- A negative gap is kept, not set to zero. It usually means the city or municipality is a school hub that enrolls learners from neighboring areas. Learners outside ages 5–17 can also add to enrollment.
- The gap shows scale and the gap share allows comparison between cities and municipalities of different size; both are shown.

**Geography comparability, for the 2020-to-2024 change only.** Each single-year gap is internally consistent, because each school year's enrollment file records the school's location for that year. The change between the two points is flagged where boundaries or assignments moved in between:

- **Makati and Taguig:** 10 EMBO barangays moved from Makati to Taguig (Supreme Court, GR 235316);
- **Negros Island Region:** re-established under RA No. 12000, taking Negros Occidental, Negros Oriental, and Siquijor from Regions VI and VII;
- **Sulu:** reassigned from BARMM to Region IX by Executive Order No. 91, s. 2025, following the Supreme Court ruling of September 9, 2024;
- **Maguindanao:** split into Maguindanao del Norte and Maguindanao del Sur (RA No. 11550);
- **Special Geographic Area:** eight new municipalities that did not exist in 2020, already excluded from city and municipality joins under D-031.

For Negros, Sulu, and Maguindanao the cities and municipalities themselves did not change; only their province or region did. The flag matters for name matching and for any province or region grouping.

**Validation status:** method defined; calculation blocked pending ingestion and profiling of the PSA 2020 and 2024 single-year-age workbooks, a name match of their cities and municipalities to PSGC, and acquisition of SY 2020-21 enrollment. Source details are in the [dataset use map](dataset-use-map.md#school-age-population-source).

## Comparison and prioritization methods

The dashboard may show four distinct evidence types without treating them as interchangeable:

| Evidence | Permitted use |
|---|---|
| **LGU observed value** | Primary local measure, with coverage and quality status |
| **Validated official benchmark** | Benchmark comparison only when authority, formula, scope, education level, effective period, and denominator compatibility match the observed metric; see the [research register](national-benchmarks-and-indicators.md) |
| **Peer distribution** | Relative context using an approved peer definition; not proof of shortage |
| **National same-type distribution** | Descriptive context for cities and municipalities separately; not an official standard |

### Proposed peer method

The current proposal groups LGUs by type, income class, and a type-specific population-density band. If a group does not meet the approved minimum size, density is dropped; if the broader group is still too small, only national same-type context is shown. The minimum group size, density bands, and fallback labels remain team decisions.

For an approved peer group, show the median, interquartile range, percentile, and group count. Median is not the only statistic: the IQR shows spread, the percentile locates the LGU, and the national same-type distribution reveals whether pressure is widespread beyond one peer group.

### Priority output

Maintain separate classroom and teacher views. Until an official benchmark and the underlying metric are validated, sort only as **relative capacity pressure** using the observed ratio, affected enrollment, comparison position, coverage, and quality flags. Do not label the result a shortage, deficit, or number of resources needed. Do not create a combined classroom-teacher score without approved weights and interpretation.

## Candidate resource-gap calculations — blocked

The following equations are arithmetically coherent but **not validated for dashboard use**:

```text
candidate_required_classrooms = ceiling(aligned_enrollment / approved_class_size_norm)
candidate_classroom_gap = max(candidate_required_classrooms - approved_existing_classrooms, 0)

candidate_required_teachers = ceiling(aligned_enrollment / approved_student_teacher_norm)
candidate_teacher_gap = max(candidate_required_teachers - approved_existing_teacher_count, 0)
```

They may be activated only if the cited norm is intended for this conversion and matches the observed denominator. Validation must also address education level, shifts, room utilization and condition, temporary spaces, multi-grade classes, annexes, teacher roles, funding source, and whether reallocation is feasible. Even after validation, the result is a planning estimate—not a construction order, staffing item, or budget request.

## Dashboard output contract

The dashboard should expose concise decision fields while keeping audit fields available in a drill-down or download.

| View | Main fields | Coverage and drill-down fields | Current status |
|---|---|---|---|
| **Common identity** | LGU PSGC code, LGU name, LGU type, province/region, education level, school year | geography-match version, unmatched/excluded school counts, source versions | Required |
| **AP1 context** | public-school count, public-school enrollment, learners per public school, total population, schools per 10,000 residents, barangays without a public elementary school (count and share) | population reference year, zero-enrollment school count, school-count rule, schools without a barangay match, upper-bound label, barangay drill-down | Candidate |
| **Classroom priority** | learners per reported instructional room, matched enrollment, reported room count | school and learner coverage, missing-room schools, zero-room schools, outlier/quality flags; source displayed as DepEd School Facilities (NSBI) | Candidate for SY 2023-24 |
| **Teacher priority** | learners per approved teacher count, matched enrollment, approved teacher count | school and learner coverage, included-position version, funding-source split, annex status, outlier/quality flags | Blocked pending definition and annex handling |
| **AP4 context** | population aged 5–17, enrollment in all sectors, gap, gap share, change from 2020 to 2024, public-school share | census and school year for each point, population source, "not available" label for unmatched school years, negative-gap note, geography-comparability flag, name-match coverage | Blocked pending ingestion and profiling |
| **Comparisons** | applicable benchmark and status, peer percentile, peer median, national same-type median | benchmark citation/version, peer ID/count/fallback, IQR, national distribution, comparison status | Blocked until method approval |
| **Priority label** | relative-pressure band or benchmark status, affected enrollment | sort rule/version, missingness and quality warnings | Blocked until ranking rule approval |

## Decisions required before implementation

1. AP1 active-school, zero-enrollment, and education-level counting rules, and the handling of schools without a unique barangay match in the barangay roll-up.
2. Whether and how elementary, JHS, and SHS NSBI room counts can be combined.
3. Exact teacher positions and funding sources included in AP3, plus duplicate-person handling.
4. Annex-to-mother-school crosswalk and aggregation behavior.
5. Which researched classroom and teacher references, if any, are approved for the intended use after the compatibility conditions in the [national benchmark register](national-benchmarks-and-indicators.md) are met.
6. AP4 name-match rule from the PSA census workbooks to PSGC, and how the dashboard shows cities and municipalities flagged for the 2020-to-2024 change. The age range, matched periods, enrollment scope, and the no-modelling rule are set in the AP4 section above.
7. Peer criteria, density source and bands, minimum group size, fallback, and percentile convention.
8. Relative-priority sorting or banding rule; a combined score remains out of scope unless separately approved.
9. BARMM coverage and geography treatment.

## Validation gate

A metric becomes dashboard-ready only when all of the following are present in a reviewed pull request:

- approved business definition and exact source columns;
- executable calculation at the declared grain;
- reconciliation to source totals and matched-school coverage;
- tests for NULL, zero, duplicate, outlier, and zero-denominator behavior;
- comparison with any publisher-defined indicator it claims to reproduce;
- approved labels, thresholds, sorting, and missing-data display; and
- traceable source, period, geography-match, and metric-version fields.
