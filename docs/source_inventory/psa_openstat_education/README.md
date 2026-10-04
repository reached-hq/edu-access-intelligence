# psa_openstat_education: PSA OpenSTAT education and literacy tables

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | PSA OpenSTAT, Education and Literacy (database `3S`, folder `C10`): 13 regional tables |
| Publisher / agency | Philippine Statistics Authority (PSA) |
| Source system (as stated by the publisher) | PSA OpenSTAT (PXWeb). The tables name no underlying source. The school counts match DepEd's enrollment file exactly (X-1); the literacy years (2013, 2019, 2024) are the PSA FLEMMS survey years, but that link is not stated in the files |
| Source URL or acquisition method | [OpenSTAT API directory](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10); each table saved as the CSV returned by an empty-selection query to `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10/<TABLE_ID>.px`, plus its metadata JSON |
| Licensing or access restrictions | Public API. No license or reuse terms appear in the CSVs or the metadata; reuse terms remain **UNVERIFIED** |
| Owner (team member) | @hyenalouise |
| Date acquired | 2026-10-04 (Philippine time) |

## Files

Raw files are kept in raw storage, never in git. Row count excludes the header row. All 13 CSVs are ASCII with CRLF line endings and no title row.

| File | OpenSTAT table | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|
| `table_10_2a_net_enrolment_kindergarten.csv` | `0031C2BNRP0` | 1,901 | 18 | `b4aad032549a08dfa58338eb67b2cf082c6e98a1d64f5d96617eed059b8dc1c1` | Databricks volume `/Volumes/edu_access/00-source/raw/psa/openstat/` |
| `table_10_2b_net_enrolment_elementary.csv` | `0043E2BNRP1` | 1,905 | 18 | `a96f004d7eee34af19290ac0304d9aafe0913115ff832e4931e6fc53a7bad7e4` | same |
| `table_10_3a_net_enrolment_jhs.csv` | `0051C2BNRP2` | 2,280 | 18 | `d69560d001420e0a0b5b25b009c14adf97c53d690d1b0a64f66ab5e190e34806` | same |
| `table_10_3b_net_enrolment_shs.csv` | `0061C2BRPS3` | 2,275 | 18 | `d3354bab1fb541913b1c727e45896d6a13b68f37b40b6124e44f46d414fc353b` | same |
| `table_10_4_cohort_survival_elementary.csv` | `0073E2BCSR0` | 2,330 | 18 | `ce71f4f566fec1c9006562ae21fc3cf740104441924641be64e48e8319e5f7c2` | same |
| `table_10_5_cohort_survival_jhs.csv` | `0083I2BCSR1` | 2,333 | 18 | `2b62d5f9d24432fc9fc43e13483e7281464b34003fa3e40d643b6c8d85c97c8f` | same |
| `table_10_8_nat_grade_6.csv` | `0091C2BNAT0` | 2,108 | 20 | `a80431364aea2f41dd966943b59c241e2f02384e99c3aba7729ecf7ffa276c90` | same |
| `table_10_9a_nat_grade_10.csv` | `0101C2BNAT0` | 2,217 | 20 | `c04995653f7b4a759c0b27040ff7c2f354e15c86068d9c96287734a767b22704` | same |
| `table_10_9b_nat_grade_12.csv` | `0111C2BNAT2` | 1,994 | 18 | `c79edda63077eff67f7bafc21d94fc936553fa98e31ab2a092db73eb8e059693` | same |
| `table_10_10_public_private_schools.csv` | `0151C2BSCH1` | 10,911 | 162 | `489eb18ed7f9c120fbc51a6151c515e5f599900ad0298b98a2340216f70ef813` | same |
| `table_10_11_public_school_teachers.csv` | `0131C2BNTP1` | 7,440 | 54 | `b9fe82ed7e3dd72535be158c52281eb2f22310f7536fe30e5f653e66040ad826` | same |
| `table_10_13_basic_literacy.csv` | `0153E2BLRP0` | 1,393 | 19 | `6b5acf52c76eb5a4c57cb2f734bca66f5779678fe87c75b34d1b9120ac36fb2e` | same |
| `table_10_14_functional_literacy.csv` | `0163E2BFLR0` | 1,387 | 19 | `a4966f5321616dc916246327f7cabf4ad9846b1945bf3302dd3cc414c442070e` | same |

`RETRIEVED.txt` and `SHA256SUMS.txt` sit in the same folder.

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| Metadata JSON for each table (13 files, `<file>_metadata.json`, 851 to 1,119 bytes) | `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10/<TABLE_ID>.px` (GET) | Listed per file in `SHA256SUMS.txt`, and checked by the profiling script | Table title, dimension names, category codes and labels. The metadata has no notes, units, sources, footnotes, or definitions |
| OpenSTAT API directory | https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3S/C10 | Live web resource; checksum not captured | Table IDs in this folder |

No methodology, definition, footnote, or release note is delivered with the tables. The `a` marker in the literacy tables (O-3) is not explained anywhere in what was downloaded.

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines and its regions: 17 regions in the school tables; 18 (with the Negros Island Region) in the literacy tables; NAT Grades 6 and 10 add empty `NIR` and `Unknown` rows |
| Geographic level | Country and region only |
| Time coverage | Varies by table: school counts SY 2019-20 to 2023-24; teachers SY 2004-05 to 2022-23; net enrolment and cohort survival SY 2018-19 or 2019-20 to 2022-23; NAT three non-consecutive school years each, latest SY 2021-22 (Grade 6) or 2022-23 (Grades 10 and 12); literacy 2013, 2019, and 2024 |
| Time basis | School year, except literacy (survey year) |
| Update frequency | **UNVERIFIED** |
| Population covered | Schools: public and private (public includes SUC/LUC, overseas schools excluded; see X-1). Teachers: public schools only. Net enrolment, cohort survival, and NAT: as titled, public and private. Literacy: population 10 and over (basic) or 10 to 64 (functional) |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One row per geography and category (level, type, or none), with one column per sex or subject and year. Long form: one value per table, geography, category, group, and year |
| Candidate primary key | Table plus geography label plus the table's category columns; unique in every table (O-1) |
| Candidate join keys | Region, through an explicit map from each of the 35 geography labels to one region key (O-2); school year |
| PSGC available? Which version? | No codes. Region names only, in two naming styles |
| Personally identifiable or sensitive fields | None. Published regional aggregates. Classification: **Public** |
| Provenance fields in the source | Table title and dimension codes in the metadata JSON; none in the CSV rows |

Column-by-column descriptions, fill rates, and ranges: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column or structure | Expected type | Actual type | Notes |
|---|---|---|---|
| Geography | Region code or name | Text with a `..` prefix for regions | 35 distinct labels for 20 keys; `NIR` and `Unknown` have no prefix |
| Category columns (level, type) | Category | Text | Match the metadata categories |
| Value columns | Number | Text; numbers or `..`, `...`, `a` | Header combines group and year (e.g. `Male 2019-2020`) |
| Missing values | One documented marker | Three undocumented markers | `..` (teachers), `...` (NAT, literacy), `a` (literacy) |

## Lineage and dependencies

Unstated originating systems (DepEd for the school counts, shown by X-1; not stated for the rest) -> PSA OpenSTAT PXWeb tables -> API CSV and metadata JSON, saved 2026-10-04 -> checksum-verified raw storage -> long-form normalization with an explicit region map -> regional benchmark next to DepEd school-level data.

## Known quality problems

Evidence lives in [profile.md](profile.md).

- **Observed:** geography labels are inconsistent across tables (`..Ilocos Region` and `..I - Ilocos Region`; three spellings of CALABARZON, one with a double space). A region map is required before any join.
- **Observed:** three undocumented missing markers: `..` for Senior High School teachers before SY 2016-17, `...` for empty NIR, Unknown, and NCR NAT cells and for NIR literacy before 2024, and `a` for Eastern Visayas literacy in 2013.
- **Observed:** four elementary net enrolment rates are above 100% (Region III and Region X, SY 2019-20).
- **Observed:** the school and teacher tables have 17 regions and no Negros Island Region; Negros is inside Regions VI and VII.
- **Observed:** national functional literacy falls from 91.6% (2019) to 70.8% (2024). The tables give no note on whether the 2024 survey measured it the same way.

## Limitations for analysis

- Regional and national only: these tables cannot support province, school, or barangay analysis.
- Most tables end at SY 2022-23, so only the school counts (Table 10.10) share a year with the DepEd SY 2023-24 anchor.
- Table 10.10 repeats DepEd's own SY 2023-24 school counts exactly (X-1), so it confirms the enrollment file but adds no independent evidence.
- NAT years are not consecutive and differ by grade, and only three of the five learning areas plus the overall score are published.
- Literacy 2024 must not be compared with 2019 as a trend until the FLEMMS 2024 method is checked (S-1).

## Recommended controls and monitoring

- Fail ingestion if any checksum, header, or geography label changes; the profiling script already stops on an unknown label.
- Keep the raw label and the mapped region key side by side.
- Load `..`, `...`, and `a` as null with the raw marker kept in a separate column.
- Record each table's own year range; never assume all tables cover the same years.
