# cmci: CMCI education-related indicators

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Cities and Municipalities Competitiveness Index (CMCI) Data Portal |
| Publisher / agency | Department of Trade and Industry (DTI) |
| Source system (as stated by the publisher) | Cities and Municipalities Competitiveness Index (CMCI) |
| Source URL or acquisition method | Extracted from the public CMCI Data Portal ([https://cmci.dti.gov.ph/data-portal.php](https://cmci.dti.gov.ph/data-portal.php)) using the portal's processing endpoint |
| Licensing or access restrictions | Public web portal. Specific license or reuse terms were not verified. UNVERIFIED |
| Owner (team member) | @YOUR_GITHUB_USERNAME |
| Date acquired | 2026-09-29 |

## Files

The project extraction contains two education-related CMCI indicators for 2023 and 2024, plus an LGU reference list.

| File | Format | Row count | Geographic coverage | Raw storage location |
|---|---|---:|---|---|
| `cmci_capacity_of_school_services_2023_2024.csv` | CSV | 3,268 | 1,634 LGUs × 2 years | `/Volumes/edu_access/00-source/raw/cmci/` |
| `cmci_education_2023_2024.csv` | CSV | 3,268 | 1,634 LGUs × 2 years | `/Volumes/edu_access/00-source/raw/cmci/` |
| `cmci_lgu_list.csv` | CSV | 1,634 | 1,634 LGUs | `/Volumes/edu_access/00-source/raw/cmci/` |

## Publisher documentation

| Document | URL | Sections relied on |
|---|---|---|
| CMCI Data Portal | [https://cmci.dti.gov.ph/data-portal.php](https://cmci.dti.gov.ph/data-portal.php) | Indicator selection, LGU selection, reference years, published CMCI indicators |

The extraction was limited to:

- `css` — Capacity of School Services
- `edu` — Education

Other CMCI indicators were not extracted because they are outside the scope of the Education Access Intelligence project.

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippine cities and municipalities available in the CMCI portal |
| Geographic level | City / municipality (LGU) |
| Time coverage | 2023–2024 |
| Time basis | CMCI reference year |
| Update frequency | Annual CMCI publication |
| LGUs covered | 1,634 |
| Expected records per indicator | 3,268 |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One indicator value per LGU per year |
| Candidate join keys | LGU name + year |
| PSGC available? | **No.** LGUs are represented by names from the CMCI portal |
| Geographic standardization | LGU names should be mapped to official PSGC identifiers before joining with other project datasets |
| Personally identifiable or sensitive fields | None found |
| Provenance fields in the source | None. Year is represented in the extracted data |

Column-by-column descriptions, fill rates, and data types: [data_dictionary.md](data_dictionary.md).

## Known quality problems

See [profile.md](profile.md) for detailed evidence.

- **Observed:** CSS contains 3,264 valid records and 4 records with `cmci_server_error`.
- **Observed:** Education contains 3,262 valid records, 4 records with `cmci_server_error`, and 2 records with `cmci_missing`.
- **Observed:** The CMCI portal returned HTTP 200 for some failed requests, but the response body contained a server-side PHP/database error. HTTP status alone was therefore not used to determine validity.
- **Observed:** The Education indicator returned `-` for some records; these were treated as missing rather than converted to zero.
- **Observed:** LGU names are portal names rather than PSGC codes and require geographic standardization before cross-source joins.
- **Observed:** The extraction output does not expose the underlying calculation formula for the two selected indicators.

## Limitations for analysis

- `Capacity of School Services` and `Education` are CMCI indicator values and should not be interpreted as direct counts of schools, classrooms, teachers, learners, or other education resources.
- The underlying calculation methodology for the extracted indicator values was not independently verified from the extraction output.
- CMCI LGU names should be standardized to PSGC identifiers before joining with DepEd, PSA, CHED, or other geographic datasets.
- Missing and server-error records should remain missing and should not be treated as zero.
- `Capacity of School Services` and `Education` are kept as separate indicators. No project-specific combined CMCI education score is created.