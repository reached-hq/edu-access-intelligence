# CHED sources as one table

The four CHED CSVs can be combined into one long table, because they share the same region labels and academic years (O-3 in each profile). Each row holds one number from one CSV cell.

## Target table: `ched_region_stats`

| Column | Type | Values | Comes from |
|---|---|---|---|
| `source_id` | string | `ched_enrollment`, `ched_graduates`, `ched_school_count`, `ched_student_faculty_ratio` | the CSV |
| `region` | string | 18 labels, e.g. `01 - Ilocos Region` (line break in the BARMM label replaced by a space) | `Region` |
| `academic_year` | string | `2020-2021` … `2024-2025` | column name; School Count: `2023-2024` from the table title |
| `sector` | string | `Public`, `Private`, `All` | Enrollment `Sector`; School Count column name |
| `institution_type` | string | `SUC main`, `SUC satellite`, `LUC`, `Other government`, `Private HEI`, `All` | School Count column name |
| `program_level` | string | `Pre-baccalaureate`, `Baccalaureate`, `Post-baccalaureate`, `Master`, `Doctorate`, `All` | Graduates `Program Level` |
| `sex` | string | `Male`, `Female`, `All` | column name |
| `measure` | string | `enrolled_students`, `graduates`, `institutions`, `students`, `faculty` | the CSV and column name |
| `value` | bigint, nullable | count, thousands commas removed | the cell |
| `value_note` | string, nullable | `-` where the bulletin prints `-` | the cell |

**Key:** every column except `value` and `value_note`. `All` means the source has no breakdown for that dimension, so the key never contains nulls.

## Example rows

| source_id | region | academic_year | sector | institution_type | program_level | sex | measure | value |
|---|---|---|---|---|---|---|---|---|
| ched_enrollment | 01 - Ilocos Region | 2023-2024 | Private | All | All | Male | enrolled_students | 67917 |
| ched_graduates | 01 - Ilocos Region | 2023-2024 | All | All | Master | Female | graduates | 1849 |
| ched_school_count | 01 - Ilocos Region | 2023-2024 | Public | SUC satellite | All | All | institutions | 22 |
| ched_student_faculty_ratio | 01 - Ilocos Region | 2023-2024 | All | All | All | All | faculty | 8154 |

## What goes in, and what stays out

| Source | Cells loaded | Left out, and why |
|---|---|---|
| `ched_enrollment` | 332 | 28 blank cells (region not reported that year) |
| `ched_graduates` | 832, including 9 `-` cells (`value` null, `value_note` `-`) | 68 blank cells |
| `ched_school_count` | 85 (17 regions × 5 components; blank components loaded as 0, per O-6) | `Public Total` and `Total`: sums of the components (O-6) |
| `ched_student_faculty_ratio` | 168 | 12 blank cells; `Ratio`: recomputed from `students` and `faculty` (O-7) |
| **Total** | **1,417 rows** | |

## Rules for using it

- Filter on one `measure` before summing; the measures count different things.
- `enrolled_students` (Table 6, first semester) and `students` (Table 39) are kept separate because they come from different bulletin tables.
- `institutions` exists for `2023-2024` only.
- BARMM has no rows after 2022-2023, and Negros Island Region has rows for 2024-2025 only (O-6), so region trends for those two break.
