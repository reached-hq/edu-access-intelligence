# Philippine administrative boundaries data dictionary

## Purpose

This data dictionary documents the fields observed in the Philippine administrative boundary datasets used by the Education Access Intelligence project.

The dictionary covers:

1. City/municipality boundaries (ADM3)
2. Barangay boundaries (ADM4)

The field names and data types are generated from the observed GeoParquet schemas. Field descriptions are based on the source structure and observed administrative hierarchy.

## ADM3 — City/Municipality

Source file: `/Volumes/edu_access/00-source/raw/admin_boundaries/phl_admin3.parquet`

Rows profiled: **1,642**

| Column | Data type | Description |
| --- | --- | --- |
| `adm3_name` | `object` | Name of the city or municipality. |
| `adm3_name1` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_name2` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_name3` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_pcode` | `object` | Administrative code assigned to the city or municipality in the source. |
| `adm2_name` | `object` | Name of the parent province. |
| `adm2_name1` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_name2` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_name3` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_pcode` | `object` | Administrative code of the parent province. |
| `adm1_name` | `object` | Name of the parent region. |
| `adm1_name1` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_name2` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_name3` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_pcode` | `object` | Administrative code of the parent region. |
| `adm0_name` | `object` | Name of the country. |
| `adm0_name1` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_name2` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_name3` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_pcode` | `object` | Administrative code of the country. |
| `valid_on` | `datetime64[ms]` | Date from which the administrative boundary record or version is valid. |
| `valid_to` | `object` | End date of validity when provided by the source. |
| `area_sqkm` | `float64` | Area of the administrative boundary in square kilometers. |
| `version` | `object` | Source dataset version. |
| `lang` | `object` | Primary language or name-language indicator provided by the source. |
| `lang1` | `object` | Source-provided language or name-language indicator. |
| `lang2` | `object` | Source-provided language or name-language indicator. |
| `lang3` | `object` | Source-provided language or name-language indicator. |
| `adm3_ref_name` | `object` | Reference name for the city or municipality. |
| `center_lat` | `float64` | Latitude of the administrative area's representative center. |
| `center_lon` | `float64` | Longitude of the administrative area's representative center. |
| `geometry` | `geometry` | Polygon or MultiPolygon geometry representing the administrative boundary. |

## ADM4 — Barangay

Source file: `/Volumes/edu_access/00-source/raw/admin_boundaries/phl_admin4.parquet`

Rows profiled: **42,048**

| Column | Data type | Description |
| --- | --- | --- |
| `adm4_name` | `object` | Name of the barangay. |
| `adm4_name1` | `object` | Source-provided alternate or language-specific name for the barangay. |
| `adm4_name2` | `object` | Source-provided alternate or language-specific name for the barangay. |
| `adm4_name3` | `object` | Source-provided alternate or language-specific name for the barangay. |
| `adm4_pcode` | `object` | Administrative code assigned to the barangay in the source. |
| `adm3_name` | `object` | Name of the city or municipality. |
| `adm3_name1` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_name2` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_name3` | `object` | Source-provided alternate or language-specific name for the city or municipality. |
| `adm3_pcode` | `object` | Administrative code assigned to the city or municipality in the source. |
| `adm2_name` | `object` | Name of the parent province. |
| `adm2_name1` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_name2` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_name3` | `object` | Source-provided alternate or language-specific name for the parent province. |
| `adm2_pcode` | `object` | Administrative code of the parent province. |
| `adm1_name` | `object` | Name of the parent region. |
| `adm1_name1` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_name2` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_name3` | `object` | Source-provided alternate or language-specific name for the parent region. |
| `adm1_pcode` | `object` | Administrative code of the parent region. |
| `adm0_name` | `object` | Name of the country. |
| `adm0_name1` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_name2` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_name3` | `object` | Source-provided alternate or language-specific country name. |
| `adm0_pcode` | `object` | Administrative code of the country. |
| `valid_on` | `datetime64[ms]` | Date from which the administrative boundary record or version is valid. |
| `valid_to` | `object` | End date of validity when provided by the source. |
| `area_sqkm` | `float64` | Area of the administrative boundary in square kilometers. |
| `version` | `object` | Source dataset version. |
| `lang` | `object` | Primary language or name-language indicator provided by the source. |
| `lang1` | `object` | Source-provided language or name-language indicator. |
| `lang2` | `object` | Source-provided language or name-language indicator. |
| `lang3` | `object` | Source-provided language or name-language indicator. |
| `adm4_ref_name` | `object` | Reference name for the barangay. |
| `center_lat` | `float64` | Latitude of the administrative area's representative center. |
| `center_lon` | `float64` | Longitude of the administrative area's representative center. |
| `geometry` | `geometry` | Polygon or MultiPolygon geometry representing the administrative boundary. |

## Notes

- `adm3_*` fields describe city/municipality-level information.
- `adm4_*` fields describe barangay-level information.
- `adm2_*` fields identify the parent province.
- `adm1_*` fields identify the parent region.
- `geometry` contains the administrative boundary geometry.
- Source administrative codes are preserved as provided and are not modified in the source layer.
- PSGC compatibility is documented separately in the source profile.

## Reproducibility

Generated by: `notebooks/profiling/data_dictionary_admin_boundaries.py`

Generated from source files under: `/Volumes/edu_access/00-source/raw/admin_boundaries/`

Generated on: **2026-10-02**