# deped_psgc_coordinates: data dictionary

The 88 columns, their header cells and their publisher meanings are those of [deped_enrollment_psgc: data dictionary](../deped_enrollment_psgc/data_dictionary.md): the header in row 8 is identical (schema `v1`), and Bronze gives them the same names in `deped_psgc_coordinates_raw`.

Fill rates differ from that file. These counts are from [`profile_deped_psgc_coordinates.py`](../../../../analysis/profiling/profile_deped_psgc_coordinates.py) over the 47,818 rows:

| Column | Fill in this file |
|---|---|
| `sector` | `Public` on every row |
| `school_id` | 6 digits on every row, all distinct |
| `psgc_region`, `psgc_province`, `psgc_city_municipality`, `psgc_barangay` | numeric on 47,614 (28,811 with 9 digits, the leading zero lost); `#N/A` on 204; never blank |
| `longitude`, `latitude` | numeric on 47,139; `#N/A` on 679; never blank |
| `barangay` | blank on 14 |
| `urp` | never blank |
| 58 enrollment counts | identical to deped_enrollment_psgc for every school (profile X-1) |
