# Dataset use map for Question v1

**Status:** Draft for team approval with Question v1 (#9, D-042).

This map assigns every profiled source in `config/sources.json` to a defined role. A dataset being available does not mean it should enter an analytical metric. The map separates sources that calculate the four APs from sources used only for comparison, context, validation, deferred analysis, or the project record.

## Role definitions

| Role | Meaning | May change an AP value or ranking? |
|---|---|---|
| **Core** | Directly supplies a numerator, denominator, trend, or LGU assignment used by AP1 to AP4 | Yes |
| **Method support** | Defines geography, peers, or a proposed density input | It may change comparison membership, but not the underlying education measure |
| **Context or cross-check** | Helps a planner interpret a result or verifies another source | No; it is displayed or documented separately and is never folded into a need score |
| **Deferred** | Reserved for a later physical-access, candidate-location, outcome, or response-specific analysis | No in Question v1 |
| **Out of scope** | Retained in the inventory for traceability but excluded from the basic-education question | No |

## End-to-end map

```mermaid
flowchart LR
    subgraph CORE["Core education measures"]
        ENR["DepEd enrollment"]
        FAC["DepEd facilities"]
        PER["DepEd personnel"]
    end

    subgraph METHOD["Geography and peer method"]
        PSGC["PSGC<br/>codes · type · income class · population"]
        AREA["Land area<br/>PSA recommended · HDX fallback"]
    end

    ENR --> AP1["AP1 · Schools"]
    PSGC --> AP1
    ENR --> AP2["AP2 · Students per classroom"]
    FAC --> AP2
    ENR --> AP3["AP3 · Students per teacher"]
    PER --> AP3
    ENR --> AP4["AP4 · Enrollment trend"]

    PSGC --> PEERS["Peer groups<br/>type + income class + density band"]
    AREA --> PEERS
    AP1 --> RESULT["LGU results"]
    AP2 --> RESULT
    AP3 --> RESULT
    AP4 --> RESULT
    PEERS --> RESULT

    CONTEXT["Context shown separately<br/>poverty · city class · data coverage"] --> DASH["Planner review"]
    RESULT --> DASH
    DEFER["Deferred sources<br/>OSM · roads · assessments · projects"] -.-> LATER["Later analyses"]
    EXCLUDED["CHED sources"] -.-> RECORD["Inventory only"]
```

The solid path is Question v1. Dotted paths are intentionally outside the current calculations.

## Question-to-dataset mapping

| Question or method | Required datasets | How each dataset is used | Output |
|---|---|---|---|
| **AP1: schools relative to students and population** | `deped_enrollment`; `psa_psgc` | Enrollment supplies public-school learners, the school roster, and level-offering flags. PSGC supplies the city/municipality assignment, total 2024 population, and barangay hierarchy. | Learners per public school; public schools per 10,000 total residents; barangays with no public school offering the level |
| **AP2: students per classroom** | `deped_enrollment`; `deped_facilities`; `psa_psgc` | Enrollment supplies learners; facilities supplies instructional classrooms; PSGC supplies the LGU assignment. Learners enter the ratio only for schools with usable classroom data. | Learners per instructional classroom and coverage of schools and learners |
| **AP3: students per teacher** | `deped_enrollment`; `deped_personnel`; `psa_psgc` | Enrollment supplies learners; personnel supplies teacher counts and funding source; PSGC supplies the LGU assignment. Learners enter the ratio only for schools with usable personnel data. | Learners per teacher and coverage of schools and learners |
| **AP4: enrollment change** | `deped_enrollment`; `psa_psgc` | Enrollment supplies comparable public learner counts for SY 2023-24 to 2025-26; PSGC supplies the documented current LGU reference. | Learner count, absolute change, and percentage change |
| **Peer comparison method** | `psa_psgc`; official land area source still to be approved | PSGC supplies LGU type, income class, population, codes, and hierarchy. Density is population divided by approved land area. `hdx_boundaries.area_sqkm` is only the documented fallback unless the team selects it. | Peer-group ID, peer count, peer median, percentile rank, fallback level, and national same-type median |
| **Context beside results** | `psa_poverty_stat`; `psa_psgc` | Poverty 2023 is displayed under its own year label and never used to group or flag. PSGC city class is visible as governance context but is not a peer criterion. | Context fields with their own source, year, and missingness labels |

### Scope rules

- “Students” in AP1 to AP3 means learners enrolled in public schools in the DepEd files. It does not mean every school-age resident.
- Total population comes from PSGC's `2024 Population` field. `psa_population_per_barangay` remains its cross-check under D-033 and is not a second denominator.
- Context fields never change an AP value, percentile, ranking, or future flag unless the team revises Question v1 and records that decision.
- An available dataset with a different grain is not silently aggregated into an LGU result. Regional, provincial, historical-division, and sample assessment sources keep their published grain.
- Every displayed value keeps its source period. Poverty 2023, population 2024, SY 2023-24 capacity, and later enrollment years are not presented as one common date.

## All registered sources

This table accounts for all 21 profiled sources in `config/sources.json`.

| Dataset | Role in Question v1 | Destination or use | Why it does or does not enter the calculation |
|---|---|---|---|
| [`deped_enrollment`](../data/source-inventory/deped_enrollment/) | **Core: AP1–AP4** | School roster, level offerings, enrolled learners, trend, and school location used for LGU assignment | Only source that supplies school-level enrollment for all four APs; public-school scope is applied with the other DepEd measures |
| [`deped_facilities`](../data/source-inventory/deped_facilities/) | **Core: AP2** | Instructional-classroom denominator and classroom-data coverage | Direct capacity source; available for SY 2023-24 only |
| [`deped_personnel`](../data/source-inventory/deped_personnel/) | **Core: AP3** | Teacher denominator, personnel coverage, and funding-source detail | Direct staffing source; the exact teacher positions remain a team decision |
| [`psa_psgc`](../data/source-inventory/psa_psgc/) | **Core + method support** | Master geography, LGU type, income class, 2024 total population, hierarchy, and city-class context | Common reference for LGU assignment, AP1 population, and peer construction |
| [`psa_poverty_stat`](../data/source-inventory/psa_poverty_stat/) | **Context** | Poverty 2023 beside the education measures, with missing LGUs left blank | Useful for interpretation but not a peer criterion, denominator, or gap flag under D-042 |
| [`psa_population_per_barangay`](../data/source-inventory/psa_population_per_barangay/) | **Cross-check** | Verifies PSGC's coded 2024 population values | D-033 selects PSGC population for downstream use, so this source is not separately ingested into Question v1 |
| [`psa_population_per_age_group`](../data/source-inventory/psa_population_per_age_group/) | **Context / limitation evidence** | Shows age structure only where its published geography permits | Does not cover every municipality, so it cannot supply a common school-age-population denominator for AP1 |
| [`psa_openstat_education`](../data/source-inventory/psa_openstat_education/) | **Context / validation only** | Regional or national education and literacy reference | Its regional grain cannot answer the city/municipality APs and must not be joined as though it were LGU data |
| [`hdx_boundaries`](../data/source-inventory/hdx_boundaries/) | **Method-support candidate + deferred** | Map geometry; possible `area_sqkm` fallback for density; later spatial analysis | Land-area use still needs a team decision; boundaries do not measure education need |
| [`dti_cmci`](../data/source-inventory/dti_cmci/) | **Available context, not approved for Question v1** | Optional LGU socioeconomic or service-capacity context after reviewed PSGC matching | CMCI is not part of the agreed questions or peer definition; adding it to a score or group would require a new decision |
| [`deped_ellna`](../data/source-inventory/deped_ellna/) | **Deferred outcome context** | Possible later learning-outcome view | Selected schools and regions only, with no BARMM coverage; it cannot be treated as a national LGU outcome |
| [`deped_nat_gr6`](../data/source-inventory/deped_nat_gr6/) | **Deferred outcome context** | Possible later Grade 6 learning-outcome view | Selected schools and regions only, with no BARMM coverage; outside the current provision-and-capacity questions |
| [`bpda_barmm_education`](../data/source-inventory/bpda_barmm_education/) | **BARMM historical context** | Descriptive comparison and interpretation of older BARMM division-level indicators | Historical school-division grain does not match the current city/municipality AP grain |
| [`bpda_barmm_social_infrastructure`](../data/source-inventory/bpda_barmm_social_infrastructure/) | **BARMM context / deferred** | Background on published education infrastructure in BARMM | Mixed, partly unstated periods and mixed geographic levels prevent direct use in current ratios |
| [`bpda_barmm_roads`](../data/source-inventory/bpda_barmm_roads/) | **Deferred physical-access context** | Possible later interpretation of transport constraints | Undated historical-area road totals cannot measure present travel time to a school |
| [`bpda_mbhte_infrastructure_projects`](../data/source-inventory/bpda_mbhte_infrastructure_projects/) | **Deferred response context** | Example of monitored education-infrastructure projects after an intervention is selected for investigation | Sixteen Basilan project records are not a national measure of current provision or capacity |
| [`osm_philippines`](../data/source-inventory/osm_philippines/) | **Deferred physical access and candidate locations** | Possible roads, settlements, school-location validation, routing, and service-area analysis | OSM completeness and school identity must be verified before distance or travel-time analysis; it does not enter AP1's provision count |
| [`ched_enrollment`](../data/source-inventory/ched_enrollment/) | **Out of scope** | Inventory only | Higher education is excluded by D-003, and the regional grain does not answer Question v1 |
| [`ched_graduates`](../data/source-inventory/ched_graduates/) | **Out of scope** | Inventory only | Higher education is excluded by D-003 |
| [`ched_school_count`](../data/source-inventory/ched_school_count/) | **Out of scope** | Inventory only | Higher education is excluded by D-003, and HEI counts are not basic-education school counts |
| [`ched_student_faculty_ratio`](../data/source-inventory/ched_student_faculty_ratio/) | **Out of scope** | Inventory only | Higher education is excluded by D-003; the regional student-faculty ratio cannot substitute for AP3 |

## Context-panel recommendation

For Question v1, keep the main result and its context visually separate:

```mermaid
flowchart LR
    R["Main result<br/>school · classroom · teacher · trend"] --> P["Planner review"]
    C["Context panel<br/>poverty 2023 · city class<br/>coverage · source periods"] -.-> P
    N["Not used in current result<br/>CMCI · assessments · BPDA · CHED"] -.-> X["Clearly labelled future, contextual,<br/>or out-of-scope work"]
```

This prevents a contextual variable from being mistaken for part of the need calculation while keeping potentially useful evidence discoverable.

## Decisions connected to this map

The dataset routes depend on four unresolved choices already listed in Question v1:

1. **Land area:** PSA OpenSTAT is recommended; HDX is the fallback.
2. **BARMM:** inclusion is recommended with the documented coverage and geography limits. BPDA sources remain context, not replacements for the DepEd indicators.
3. **Teacher count:** the selected personnel positions determine the AP3 denominator; funding source remains visible.
4. **Time and geography:** one documented current peer definition is recommended across the three enrollment years, with boundary-change flags.

Any future decision to use CMCI, assessment results, age-group population, BPDA data, or another context source inside a peer group, score, threshold, or flag changes the analytical definition and must be recorded before implementation.
