# CMCI source profile

## Purpose

This profile documents the structure and observed data-quality characteristics
of the CMCI indicator extracts used by the Education Access Intelligence project.

The profiling covers:

1. Capacity of School Services (`css`)
2. Education (`edu`)

The CMCI LGU list is also used as a reference for LGU coverage validation.

## Source data location

The raw CMCI files are stored in the Databricks source volume:

`/Volumes/edu_access/00-source/raw/cmci/`

## O-1. Extracted file structure

| Source | File | Path | File size (bytes) |
| --- | --- | --- | --- |
| css | cmci_capacity_of_school_services_2023_2024.csv | /Volumes/edu_access/00-source/raw/cmci/cmci_capacity_of_school_services_2023_2024.csv | 93982 |
| edu | cmci_education_2023_2024.csv | /Volumes/edu_access/00-source/raw/cmci/cmci_education_2023_2024.csv | 94530 |
| lgu | cmci_lgu_list.csv | /Volumes/edu_access/00-source/raw/cmci/cmci_lgu_list.csv | 18081 |

## O-2. Expected schema

### Capacity of School Services

| Column | Expected |
| --- | --- |
| lgu | yes |
| year | yes |
| capacity_of_school_services | yes |
| status | yes |

Observed columns:

`lgu, year, capacity_of_school_services, status`

### Education

| Column | Expected |
| --- | --- |
| lgu | yes |
| year | yes |
| education | yes |
| status | yes |

Observed columns:

`lgu, year, education, status`

### LGU reference list

Observed columns:

`lgu`

## O-3. Row count and LGU coverage

### Capacity of School Services

- Row count: **3,268**
- Distinct LGUs: **1,634**
- Expected LGUs: **1,634**

### Education

- Row count: **3,268**
- Distinct LGUs: **1,634**
- Expected LGUs: **1,634**

### CMCI LGU reference list

- Distinct LGUs: **1,634**

Expected LGU-year combinations:

**1,634 LGUs × 2 years = 3,268 records**

## O-4. Records by year

### Capacity of School Services

| Year | Records | Distinct LGUs |
| --- | --- | --- |
| 2023 | 1634 | 1634 |
| 2024 | 1634 | 1634 |

### Education

| Year | Records | Distinct LGUs |
| --- | --- | --- |
| 2023 | 1634 | 1634 |
| 2024 | 1634 | 1634 |

## O-5. Duplicate LGU-year records

The expected grain is one indicator value per LGU per year.

### Capacity of School Services

- Duplicate LGU-year groups: **0**

### Education

- Duplicate LGU-year groups: **0**

## O-6. Status distribution

### Capacity of School Services

| Status | Records |
| --- | --- |
| cmci_server_error | 4 |
| valid | 3264 |

### Education

| Status | Records |
| --- | --- |
| cmci_missing | 2 |
| cmci_server_error | 4 |
| valid | 3262 |

The `status` field distinguishes valid extracted values from
server errors and explicit missing values.

## O-7. Score completeness

### Capacity of School Services

- Missing or blank scores: **4**

### Education

- Missing or blank scores: **6**

Missing values are not converted to zero because a missing response does not
establish that the underlying indicator value is zero.

## O-8. Numeric validation

### Capacity of School Services

- Invalid numeric values among records marked `valid`:
  **0**

### Education

- Invalid numeric values among records marked `valid`:
  **0**

The files were initially loaded as text and numeric conversion was performed
separately during validation.

## O-9. Descriptive score ranges

### Capacity of School Services

min=0.0, max=1.0087, mean=0.08460036764705853

### Education

min=0.0, max=1.393, mean=0.11847670141017791

These are descriptive statistics of the extracted CMCI scores. They should not
be interpreted as direct counts of schools, classrooms, teachers, learners,
or population.

## O-10. Status/value consistency

### Capacity of School Services

- Status/value consistency issues: **0**

### Education

- Status/value consistency issues: **0**

## O-11. Non-valid records

### Capacity of School Services

| LGU | Year | Score | Status |
| --- | --- | --- | --- |
| Brooke's Point | 2023 |  | cmci_server_error |
| Brooke's Point | 2024 |  | cmci_server_error |
| T'boli | 2023 |  | cmci_server_error |
| T'boli | 2024 |  | cmci_server_error |

### Education

| LGU | Year | Score | Status |
| --- | --- | --- | --- |
| Brooke's Point | 2023 |  | cmci_server_error |
| Brooke's Point | 2024 |  | cmci_server_error |
| Concepcion (RN) | 2023 |  | cmci_missing |
| Initao | 2023 |  | cmci_missing |
| T'boli | 2023 |  | cmci_server_error |
| T'boli | 2024 |  | cmci_server_error |

Non-valid records are retained rather than replaced with zero.

## O-12. Cross-indicator coverage

Distinct LGU-year keys:

- Capacity of School Services: **3,268**
- Education: **3,268**

## S-1. LGU-year differences between indicators

### Present in CSS but not Education

Count: **0**

| LGU | Year |
| --- | --- |

### Present in Education but not CSS

Count: **0**

| LGU | Year |
| --- | --- |

## S-2. Expected LGU-year coverage

Expected LGU-year combinations:

**3,268**

### Capacity of School Services

- Missing expected combinations: **0**

### Education

- Missing expected combinations: **0**

## S-3. Comparison with CMCI LGU reference list

### CSS LGUs not found in the reference list

Count: **0**

| LGU |
| --- |

### Education LGUs not found in the reference list

Count: **0**

| LGU |
| --- |

### LGUs in the reference list but not in CSS

Count: **0**

| LGU |
| --- |

## Analytical limitations

### CMCI is an indicator dataset

The CMCI values are indicator/index measures and are not direct counts of:

- schools
- classrooms
- teachers
- learners
- population

CMCI should therefore be used as contextual information alongside the
education supply and population datasets.

### LGU name standardization

The CMCI extracts use LGU names as provided by the portal.

LGU names should be mapped to official PSGC codes before joining with PSA,
DepEd, CHED, or other geographic datasets.

### Missing/server-error records

CMCI server errors and explicit missing values are retained as non-valid
records. They should not be interpreted as zero.

### Indicator separation

`Capacity of School Services` and `Education` are kept as separate indicators.
No combined CMCI education score is created because no verified CMCI formula
for combining the two indicators was established.

## Reproducibility

Profiling script:

`notebooks/profiling/profile_cmci.py`

Raw source location:

`/Volumes/edu_access/00-source/raw/cmci/`

Output:

`docs/source_inventory/cmci/profile.md`
