# Business and analytics problem: Question v1

**Status:** Draft for team approval (#9). Recorded as D-042; BARMM and head-teacher treatment as D-043 and D-044.

| | |
|---|---|
| **Primary users** | LGU education planners (D-013) |
| **Focus** | Students, measured as enrolled learners (observed demand) |
| **Education scope** | Basic education: elementary, junior high, and senior high (D-003) |
| **Unit of analysis** | City or municipality |
| **Decision boundary** | The analysis organizes evidence for local review. Planners remain responsible for prioritization and intervention decisions. |

## Business problem

LGU education planners need to know whether their city or municipality has enough schools, classrooms, and teachers for its students. National totals do not answer this. A raw ranking of all 1,642 cities and municipalities does not answer it either, because a 1st class city and a 5th class municipality differ in budget and size, so their numbers will always look different.

Planners need a fair reference point: how their LGU compares with LGUs like it. If an LGU has far more students per classroom than LGUs with the same income class and population density, its gap is not explained by being poorer or smaller, and it should be looked at more closely.

Enrollment is **observed demand** only. It does not include children who are not enrolled. The analysis therefore cannot measure total unmet need or prescribe an intervention.

## Business questions

### Main business question

> **Which cities and municipalities need more schools, classrooms, and teachers based on their student population and enrollment demand?**

### Sub-business question

> **Among cities and municipalities with the same income class and population density, which show greater need for additional schools, classrooms, or teachers?**

### Decision supported

The analysis helps planners decide which cities and municipalities to look at more closely, and whether the gap is in schools, classrooms, or teachers. It does not decide where to build a school, hire teachers, or construct classrooms.

## How the questions fit together

**AP1 finds each LGU's peers → AP2 to AP5 compare the LGU with its peers on each measure → Sub-BP: which LGUs show greater need than their peers → Main BP: which LGUs need more schools, classrooms, and teachers → planners decide what to prioritize**

Peer comparison is not the only basis for need. Each LGU's own values show *whether* it has a gap; the peer comparison shows *how unusual* that gap is for an LGU like it. Both are shown together, because a whole peer group can be behind: if every LGU in a group has crowded classrooms, none stands out from its peers, but all of them still need attention.

## Peer groups

A **peer group** is the set of LGUs that a city or municipality is compared with. It exists so that comparisons are fair, not to rank LGUs into fixed tiers.

### Default criteria

| Criterion | Rule | Source |
|---|---|---|
| LGU type | Same type: city or municipality | PSGC 2Q 2026 `Geographic Level` (`City`, `Mun`) |
| Income class | Same class | PSGC 2Q 2026 `Income Classification (DOF DO No. 074.2024)` |
| Population density | Same density band | 2024 population (PSGC) ÷ land area (`area_sqkm`, HDX ADM3, matched through `Correspondence Code` under D-030) |

The 14 Manila sub-municipalities (`SubMun`) are not LGUs and are not peers; Manila is compared as one city. The density bands are not yet set (see Follow-up work).

### Why city class (HUC, ICC, CC) is not a criterion

City class is set largely by income and population, so it repeats what income class and density already measure. PSGC 2Q 2026 shows the overlap:

| City class | 1st | 2nd | 3rd | 4th | Total |
|---|---|---|---|---|---|
| HUC | 33 | | | | 33 |
| ICC | 4 | 1 | | | 5 |
| CC | 48 | 24 | 30 | 9 | 111 |
| **All cities** | **85** | **25** | **30** | **9** | **149** |

Every HUC is 1st class, and only component cities vary. Adding city class would split the 149 cities into smaller groups without adding much information.

### Why city vs. municipality is kept

Income class uses separate brackets for cities and for municipalities (RA 11964, DOF DO No. 074.2024), so a 1st class city and a 1st class municipality are not the same income level. Grouping them by income class alone would put unlike LGUs together. LGU type is therefore the split inside which income class is compared, not a separate factor.

City status is also a legal status set by a charter law, and it does not change when income or population changes later. Becoming a city requires meeting income and population or land-area thresholds (Local Government Code Sec. 450, as amended), so the two overlap, but one does not define the other.

### Group sizes

| Municipalities | 1st | 2nd | 3rd | 4th | 5th | No class | Total |
|---|---|---|---|---|---|---|---|
| Count | 696 | 247 | 242 | 236 | 64 | 8 | 1,493 |

- 696 of 1,493 municipalities (47%) are 1st class, so density does most of the work in separating them.
- The smallest city group, 4th class, has 9 cities, so splitting it by density may leave fewer than 5 peers.
- The 8 municipalities with no income class (`-`) are the 8 Special Geographic Area municipalities (Kapalawan, Old Kaabakan, Kadayangan, Nabalawag, Pahamuddin, Malidegao, Ligawasan, Tugunan). They have no peer group, and their schools are already excluded from city- and municipality-level results (D-031).

**Minimum size (proposal):** a peer group with fewer than 5 LGUs falls back to all LGUs of the same type nationwide, and the fallback is shown on the result.

**Dashboard option:** users may narrow the comparison (for example to the same region or province). The default above is what Question v1 answers.

## Analytical questions

| # | Analytical question | Metric or output | Approximate formula | Grain | Primary sources | Main limitation |
|---|---|---|---|---|---|---|
| AP1 | Which LGUs are similar to each city or municipality in income class and population density, so their schools, classrooms, and teachers can be fairly compared? | Peer set per LGU; peer count; whether the fallback was used | Same type + same income class + same density band; density = `2024 population / area_sqkm` | City/municipality | PSGC 2Q 2026; HDX ADM3 boundaries | Density bands not yet set; `area_sqkm` is undocumented by the publisher (observed only); some groups are small |
| AP2 | Compared with similar LGUs, which cities and municipalities have fewer schools relative to their number of students and population? | Learners per school offering the level; schools offering the level per 10,000 residents | `learners at level / schools offering level`; `schools offering level / 2024 population * 10,000` | City/municipality × education level × school year | DepEd enrollment (school roster and `offers_*` flags); PSGC 2024 population | Total population, not school-age population; a school count does not measure distance or physical access |
| AP3 | Compared with similar LGUs, which have the most students per classroom? | Learners per instructional classroom; classroom-data coverage | `public-school learners at level / instructional classrooms` | City/municipality × education level × school year | DepEd enrollment and facilities, public schools, SY 2023-24 | One school year only; classroom counts missing for some schools, more often in BARMM (D-043) |
| AP4 | Compared with similar LGUs, which have the most students per teacher? | Learners per teacher (primary and sensitivity); personnel-data coverage | `public-school learners at level / teaching personnel` (D-044) | City/municipality × education level × school year | DepEd enrollment and personnel, public schools, SY 2023-24 | Working-personnel counts, not plantilla (personnel profile O-13); head-teacher treatment unconfirmed (D-044) |
| AP5 | Compared with similar LGUs, which have student enrollment increasing or decreasing over time? | Learner count; absolute and percentage change | `current - prior`; `(current - prior) / prior * 100` | City/municipality × education level × school year | DepEd enrollment, SY 2023-24, 2024-25, 2025-26 | **Provisional** until cross-year comparability is validated (#8) |

For AP2 to AP5, each LGU's result shows:

- its own value;
- the median of its peers and its rank among them;
- the number of peers, and whether the fallback was used;
- the national value for the same LGU type, so a group that is behind as a whole is still visible;
- how much of the LGU's learners the measure covers.

No hard flags or composite score are applied in Question v1. Rankings and values come first; thresholds come later, once they can be defended (follow-up work).

### Interpretation controls

- **AP2 measures provision, not access.** An LGU with few schools for its population may still have schools close by in a neighbouring LGU.
- **Schools per 10,000 residents uses total population,** because school-age population is not available at city or municipality level. The denominator is labelled as total population.
- **AP2 counts every school offering the level, public and private,** since private schools also serve learners. AP3 and AP4 cover public schools only, because facilities and personnel data are public-school data (personnel profile O-3).
- **Annex schools:** AP3 and AP4 add annex enrollment and capacity to the mother school where a verified annex crosswalk exists, following DepEd's ratio method (personnel profile O-14). Results without that step are labelled provisional.
- **No ratio from a zero or missing denominator.** Missing classroom or personnel values stay NULL, never 0 (D-023), and every result reports its coverage.
- **AP5 reports both absolute and percentage change.** Percentage change is undefined when the prior value is 0. Rising enrollment alone does not prove a shortage, and falling enrollment does not prove a surplus.
- **The analysis does not decide.** Planners, not the query, decide whether an LGU is a priority and what response to investigate.

## Scope decisions

### Basic education only

Higher education is out of scope (D-003, D-013). CHED sources stay profiled but are not inputs to any AP.

### BARMM is included, with its limits stated (D-043)

Excluding BARMM would remove a material part of the public-school system and hide known coverage gaps. BARMM results carry these limits:

- All 2,603 BARMM public schools are in the SY 2023-24 enrollment, facilities, and personnel files.
- About 93% of BARMM public schools have classroom counts, against about 99% elsewhere. AP3 shows this coverage and never treats a missing count as 0.
- School-level NAT Grade 6 and ELLNA extracts do not cover BARMM. They are not inputs to AP1 to AP5 and must not be used to infer BARMM learning outcomes.
- DepEd's SY 2023-24 files place Sulu in BARMM; PSGC 2Q 2026 places it in Region IX. Regional results for SY 2023-24 use DepEd's region column (D-012).
- The 112 Special Geographic Area schools are excluded from city- and municipality-level results until their barangays are matched (D-031), and the 8 Special Geographic Area municipalities have no income class, so they have no peer group.

### Head teachers are excluded from the primary teacher count (D-044)

The personnel file lists head teachers as separate positions, and the reviewed documentation does not say how much teaching each one does. Counting each as a full classroom teacher could overstate teacher capacity unevenly.

- **Primary ratio:** learners ÷ teaching personnel (Teacher, Master Teacher, SPED/SNED Teacher, Special Science Teacher, and documented locally funded teacher fields), excluding principals, assistant principals, head teachers, and non-teaching staff.
- **Sensitivity ratio:** learners ÷ teaching personnel plus head teachers.
- **Review control:** report how much the ranking changes between the two, and confirm with DepEd or the mentor before counting head teachers as classroom teachers.

## Deferred analysis

### Physical access (stretch)

> **Where is physical access to schools most limited?**

Distance or travel time to the nearest school offering each level is deferred until school locations are complete and verified. Until then, AP2 measures provision only and is not a proxy for distance.

### Candidate locations (second stage)

> **If an additional school or service point is selected for investigation, where could candidate locations improve coverage?**

Center of gravity, clustering (K-means), or network accessibility belong to this stage. Its results would be candidate locations for local assessment, not recommendations to build. It starts only after planners decide that a new service point is the response worth investigating.

## Planner needs

Under D-001, a question resting mostly on **assumed** needs cannot be approved. The needs behind AP1 to AP5 are documented and tagged in #7 (`docs/business/needs.md`). Until #7 lands, the comparison-with-peers framing is **mentor-validated** (program mentor review, 2026-10-12), and the remaining needs are **assumed**.

## Revision history

| Version | Date | Change |
|---|---|---|
| Draft (#9 thread) | 2026-10-05 | Consolidated by @mafelisilda: provision, classroom, teacher, enrollment-trend, and overlap questions at barangay and city/municipality level |
| Question v1 (this draft) | 2026-10-12 | Reframed after mentor review around city and municipality need compared with similar LGUs. City class (HUC/ICC/CC) dropped as a criterion; city vs. municipality kept as the split for income class; AP1 rephrased as finding each LGU's peers; the overlap question folded into the peer comparison shown by AP2 to AP5 |

## Follow-up work

- **Planner needs:** cite and tag the needs behind each AP (#7).
- **Cross-year comparability:** validate SY 2023-24 to 2025-26 enrollment at the same geography and level before AP5 leaves provisional (#8).
- **Density bands:** choose the bands (for example quantiles within each type and income class) and check that groups reach the minimum size.
- **Metric contracts:** exact filters, source columns, grade-to-level mapping, missing-data rules, and final formulas.
- **Gold model:** fact-table names, grain statements, and keys (milestone 03).
- **Prioritization method:** thresholds or composite rules, only once they can be defended with a cited standard or an agreed analytical rule.
- **Head teachers:** confirm the treatment with DepEd or the mentor (D-044).
