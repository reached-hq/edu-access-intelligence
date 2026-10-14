# Metric and dashboard specification

**Status:** Draft analytical contract. No metric in this document is an official DepEd indicator or adequacy standard unless its row explicitly says so. Team approval, source validation, and implemented tests are still required before publication.

## Purpose and document boundary

This document translates the approved [business and analytical questions](business-analytics-problem.md) into candidate measures and dashboard fields. It owns formulas, grains, filters, comparison rules, display fields, and validation status. It does not redefine the approved questions, assign datasets to scope, or describe stakeholder authority; those belong to the business-question document, [dataset use map](dataset-use-map.md), and [stakeholder document](stakeholders.md).

## Current validation conclusion

The proposed ratio structures are reasonable analytical candidates, but they are **not yet fully validated production metrics**.

| Area | What is supported now | What prevents final approval |
|---|---|---|
| **AP1 · Schools** | Public-school and enrollment counts can be aggregated by matched LGU and school year | Active-school rule, education-level counting rule, and treatment of schools with zero enrollment still require an explicit contract |
| **AP2 · Classrooms** | SY 2023-24 enrollment and facilities match one-to-one by `school_id`; classroom counts are typed | The facilities field uses the NSBI “instructional classroom” definition, which includes rooms beyond Kindergarten-to-Grade-12 classrooms. It is not DepEd's published classroom–learner ratio and has ambiguous missing values and extreme observations |
| **AP3 · Teachers** | SY 2023-24 enrollment and personnel match one-to-one by `school_id`; personnel counts are typed | The included teaching positions are not approved, people may be counted across roles or levels, blanks are ambiguous, outliers remain under review, and DepEd's method requires annex-to-mother-school consolidation |
| **AP4 · Population and enrollment** | Public-school enrollment is available across three acquired school years | No profiled nationwide city/municipality school-age-population time series exists, and the age range and period-alignment rule are not approved |
| **Resource-gap estimates** | The arithmetic form can be documented as a candidate | No applicable classroom or teacher benchmark has been approved, and the operational assumptions behind converting a ratio into rooms or teachers have not been validated |

The DepEd evidence for these limitations is recorded in the source cards for [enrollment](../data/source-inventory/deped_enrollment/README.md#limitations-for-analysis), [facilities](../data/source-inventory/deped_facilities/README.md#limitations-for-analysis), and [personnel](../data/source-inventory/deped_personnel/README.md#limitations-for-analysis), with observed tests in their linked profiles.

## Contract conventions

Every published measure must declare:

1. **grain** — LGU, school year, and education level where supported;
2. **scope** — public schools only, excluding Philippine Schools Overseas from LGU results;
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
```

Use `COUNT(DISTINCT school_id)` and sum enrollment at the same LGU, education-level, and school-year grain. Total population must retain its own reference year. This measure describes provision and school size; it does not measure travel access or prove that construction is required.

**Validation status:** candidate. Approve the active-school, zero-enrollment, multi-level-school, and level-specific counting rules before implementation.

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

The dashboard label must say **learners per NSBI instructional room**, not “DepEd classroom–learner ratio.” DepEd's source documentation says `*_classrooms_instructional` includes ALS, audio-visual, computer, industrial-arts, home-economics, and laboratory rooms, while its published classroom–learner indicator uses Kindergarten-to-Grade-12 classrooms. The available data therefore tend to produce a lower ratio than the official indicator.

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

### AP4 · School-age-population and enrollment difference

```text
population_enrollment_difference =
    school_age_population - aligned_public_school_enrollment
```

The population age range, geographic coverage, and reference period must be approved before calculation. The output is an arithmetic difference, not an out-of-school count or enrollment rate. Public-school enrollment excludes private-school learners, and school location may differ from learner residence.

**Validation status:** blocked by the nationwide LGU-level school-age-population source and the age/period decisions documented in the [dataset use map](dataset-use-map.md#known-gap-school-age-population).

## Comparison and prioritization methods

The dashboard may show four distinct evidence types without treating them as interchangeable:

| Evidence | Permitted use |
|---|---|
| **LGU observed value** | Primary local measure, with coverage and quality status |
| **Validated official benchmark** | Benchmark comparison only when authority, formula, scope, education level, and effective period match the observed metric |
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
| **AP1 context** | public-school count, public-school enrollment, learners per public school, total population, schools per 10,000 residents | population reference year, zero-enrollment school count, school-count rule | Candidate |
| **Classroom priority** | learners per NSBI instructional room, matched enrollment, reported room count | school and learner coverage, missing-room schools, zero-room schools, outlier/quality flags | Candidate for SY 2023-24 |
| **Teacher priority** | learners per approved teacher count, matched enrollment, approved teacher count | school and learner coverage, included-position version, funding-source split, annex status, outlier/quality flags | Blocked pending definition and annex handling |
| **AP4 context** | school-age population, aligned public-school enrollment, arithmetic difference | age range, population source/year, alignment flag, geographic coverage | Blocked pending source and decisions |
| **Comparisons** | applicable benchmark and status, peer percentile, peer median, national same-type median | benchmark citation/version, peer ID/count/fallback, IQR, national distribution, comparison status | Blocked until method approval |
| **Priority label** | relative-pressure band or benchmark status, affected enrollment | sort rule/version, missingness and quality warnings | Blocked until ranking rule approval |

## Decisions required before implementation

1. AP1 active-school, zero-enrollment, and education-level counting rules.
2. Whether and how elementary, JHS, and SHS NSBI room counts can be combined.
3. Exact teacher positions and funding sources included in AP3, plus duplicate-person handling.
4. Annex-to-mother-school crosswalk and aggregation behavior.
5. Official classroom and teacher benchmarks, if any, with authority, formula, scope, level, and effective period.
6. AP4 age range, official LGU source, comparable periods, and whether modelled values are allowed.
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
