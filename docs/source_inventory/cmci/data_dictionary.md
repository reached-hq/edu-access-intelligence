# CMCI Data Dictionary

**Source:** Cities and Municipalities Competitiveness Index (CMCI)

**Publisher:** Department of Trade and Industry (DTI)

**Reference years:** 2023–2024

This data dictionary describes the CMCI indicator files extracted from the public CMCI Data Portal.


## 1. Capacity of School Services

**Source file:** `cmci_capacity_of_school_services_2023_2024.csv`

**Grain:** One CMCI Capacity of School Services indicator record per LGU-year.

**Coverage:** 1,634 LGUs for 2023 and 2024.

| Column | Description |
|---|---|
| `lgu` | Name of the city or municipality as provided by the CMCI portal. |
| `year` | CMCI reference year. |
| `capacity_of_school_services` | CMCI Capacity of School Services indicator value. The underlying calculation or formula was not independently verified. |
| `status` | Extraction/data-quality status. Observed values are `valid` and `cmci_server_error`. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
| `lgu` | `VARCHAR` | 100.00% | 1634 |
| `year` | `BIGINT` | 100.00% | 2 |
| `capacity_of_school_services` | `DOUBLE` | 99.88% | 1333 |
| `status` | `VARCHAR` | 100.00% | 2 |


## 2. Education

**Source file:** `cmci_education_2023_2024.csv`

**Grain:** One CMCI Education indicator record per LGU-year.

**Coverage:** 1,634 LGUs for 2023 and 2024.

| Column | Description |
|---|---|
| `lgu` | Name of the city or municipality as provided by the CMCI portal. |
| `year` | CMCI reference year. |
| `education` | CMCI Education indicator value. The underlying calculation or formula was not independently verified. |
| `status` | Extraction/data-quality status. Observed values are `valid`, `cmci_server_error`, and `cmci_missing`. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
| `lgu` | `VARCHAR` | 100.00% | 1634 |
| `year` | `BIGINT` | 100.00% | 2 |
| `education` | `DOUBLE` | 99.82% | 1808 |
| `status` | `VARCHAR` | 100.00% | 3 |


## 3. CMCI LGU Reference List

**Source file:** `cmci_lgu_list.csv`

**Purpose:** Reference list of LGUs available in the CMCI portal. This file is used to validate LGU coverage and support later geographic standardization.

| Column | Description |
|---|---|
| `lgu` | LGU name as provided by the CMCI portal. |

### Column profiling

| Column | Type | Completeness | Distinct values |
|---|---|---:|---:|
| `lgu` | `VARCHAR` | 100.00% | 1634 |


## 4. Data Handling Notes

- The analytical grain is **LGU-year-indicator**.
- `lgu` contains CMCI portal names and should be mapped to official PSGC codes before joining with other datasets.
- `capacity_of_school_services` and `education` are kept as separate indicators.
- Missing values are not converted to zero.
- `cmci_server_error` identifies records where the CMCI portal returned a server-side error during extraction.
- `cmci_missing` identifies records where the portal response did not provide a usable indicator value.
- CMCI indicator values should not be interpreted as direct counts of schools, classrooms, teachers, learners, or other education resources.
- The calculation methodology of the CMCI indicators was not independently verified from the extraction output.