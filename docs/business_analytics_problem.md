# Business and analytics problem

**Primary users:** LGU education planners  
**Education scope:** Basic education

## Business problem

LGU education planners need to decide which areas warrant closer investigation for possible gaps in education provision or capacity. The available evidence is fragmented across school locations and offerings, enrollment, classrooms, personnel, and population. Viewed separately, these sources do not provide a consistent area-level picture of where provision is limited, where existing schools appear under pressure, or where several pressures overlap.

Enrollment represents **observed learner demand** only. It does not include children who are not enrolled. The analysis therefore cannot measure total unmet educational need or prescribe an intervention. It should organize measurable evidence so planners can prioritize local review and decide which response, if any, should be investigated.

### Business question

> **How can LGU planners identify and prioritize areas where education provision and capacity appear insufficient relative to observed learner demand?**

### Sub-business question

> **How can LGU planners determine which planning response should be investigated in each priority area?**

### Decision supported

The analysis supports a planner's decision about which geographic areas require further assessment and what type of constraint should be investigated. It does not decide where to build a school, assign personnel, or construct classrooms.

## Analytics problem

Create a reproducible area-by-education-level view that integrates DepEd school, enrollment, facilities, and personnel data with PSA population and geographic references. Calculate comparable provision, classroom pressure, teacher pressure, and enrollment-trend measures; rank areas on each measure; and show the measures together so planners can identify areas with several signals of possible pressure.

## Core analytical questions

| # | Analytical question | Metric or output | How it is measured | Grain | Primary sources |
|---|---|---|---|---|---|
| AP1 | Where is education provision limited relative to observed demand and population? | Schools offering each level; areas with no school offering the level; schools per 10,000 residents | `distinct schools offering level`; `school count / total population * 10,000` | Barangay and city/municipality × education level × reference period | DepEd enrollment school roster; PSA 2024 barangay population; PSGC crosswalk |
| AP2 | Where are learners per instructional classroom highest? | Learners per instructional classroom and classroom-data coverage | `enrolled learners / instructional classrooms` | City/municipality × education level × school year | DepEd enrollment and facilities, public schools, SY 2023-24 |
| AP3 | Where are learners per teacher highest? | Learners per teacher and personnel-data coverage | `enrolled learners / teaching personnel` | City/municipality × education level × school year | DepEd enrollment and personnel, public schools, SY 2023-24 |
| AP4 | Where is enrollment increasing or decreasing over time? | Learner count, absolute change, and percentage change | `current learners - prior learners`; `(current learners - prior learners) / prior learners * 100` | City/municipality × education level × school year | DepEd enrollment, SY 2023-24 to SY 2025-26 |
| AP5 | Which areas show multiple provision or capacity pressures, and which indicators are present? | Side-by-side metrics and within-metric rankings from AP1–AP4 | No initial hard flag or unvalidated composite score | City/municipality × education level | Outputs of AP1–AP4 |

### Interpretation controls

- AP1 is a provision and coverage indicator, not direct proof of physical inaccessibility. A barangay with no school may be near a school in another barangay.
- Schools per 10,000 residents uses total population because school-age population is unavailable at barangay and city/municipality level. The denominator must be labeled accordingly. 
- AP2 and AP3 cover public schools because the facilities and personnel measures do not support equivalent non-public comparisons.
- AP2 and AP3 aggregate annex enrollment and capacity to the mother school when a verified annex crosswalk is available, following DepEd's published ratio method. Results without that consolidation must be labeled provisional.
- A zero denominator does not produce a ratio. Missing classroom or personnel values remain null rather than being converted to zero, and every result reports source coverage.
- AP4 reports absolute and percentage change. Percentage change is undefined when the prior-year value is zero. Geographic and education-level definitions must be harmonized before comparison.
- AP5 presents the underlying values and rankings. Planners, not the query, decide whether an area is a priority and which response merits investigation.

## Scope decision: BARMM

BARMM is included as excluding it would remove a material part of the national public-school system and hide known data-coverage differences.

The following limitations must accompany BARMM results:

- All 2,603 BARMM public schools identified during cross-source review occur in the SY 2023-24 enrollment, facilities, and personnel sources.
- Classroom counts are available for about 93% of BARMM public schools, compared with about 99% elsewhere. AP2 must publish this coverage difference and must not treat missing classrooms as zero.
- The available school-level ELLNA and NAT Grade 6 extracts do not cover BARMM. These assessments are not inputs to AP1–AP5 and must not be used to infer BARMM learning outcomes.
- The source geography places Sulu in BARMM for SY 2023-24, while PSGC 2Q 2026 places Sulu in Region IX. Historical results retain the source-period region, and current PSGC region must not silently replace it.
- Most Special Geographic Area schools are not yet matched to a barangay. They remain in supported city/municipality-level results where a valid match exists, but unmatched schools are counted and disclosed rather than dropped or forced into AP1 barangay results.

BARMM comparisons are therefore included but coverage-qualified. Rankings must display denominator coverage so that lower data completeness is not mistaken for lower pressure.

## AP3 decision: treatment of head teachers

Head teachers are excluded from the primary AP3 teacher denominator. The personnel file identifies them as separate positions, and the reviewed documentation does not establish how much classroom teaching load each head teacher carries. Counting every head teacher as one full classroom teacher would therefore overstate instructional capacity in an unknown and potentially uneven way.

The primary `teaching personnel` denominator includes positions explicitly identified as teaching roles for the relevant education level, such as Teacher, Master Teacher, SPED/SNED Teacher, Special Science Teacher, and documented locally funded teacher fields. It excludes principals, assistant principals, head teachers, and non-teaching or teaching-related support positions.

A sensitivity measure will also be produced:

- **Primary ratio:** learners divided by teaching personnel, excluding head teachers.
- **Sensitivity ratio:** learners divided by teaching personnel plus head teachers.
- **Review control:** report the difference between the two rankings and seek DepEd or mentor confirmation before treating head teachers as full-time classroom teachers.

This keeps the primary measure conservative and makes the effect of the unresolved classification visible rather than silently choosing one interpretation.

## Deferred analysis

### Physical access stretch question

> **Where is physical access to schools most limited?**

For the MVP, a barangay with no school offering an education level is only a proxy for possible access limitations. Distance or travel-time analysis remains deferred until school and community coordinates are sufficiently complete and verified.

### Response-specific location analysis

> **If an additional education service point is selected for investigation, where could candidate locations improve geographic coverage?**

Center of gravity, clustering, or network-accessibility methods belong to this second stage. Their results would be candidate locations for local assessment, not recommendations to construct a school.

## Analytical boundary

The intended flow is:

**Observed demand and provision → capacity pressure → overlapping pressures → planner prioritization → response investigation**

The first three stages are analytical outputs. Prioritization and response selection remain accountable planning decisions.
