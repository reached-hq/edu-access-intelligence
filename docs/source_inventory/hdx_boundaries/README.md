# hdx_boundaries: Philippine administrative boundaries

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Common Operational Dataset – Administrative Boundaries (COD-AB), Philippines |
| Publisher / agency | UN OCHA |
| Source system (as stated by the publisher) | Common Operational Dataset – Administrative Boundaries (COD-AB) |
| Source URL or acquisition method | https://data.humdata.org/dataset/cod-ab-phl |
| Licensing or access restrictions | UN OCHA / Humanitarian Data Exchange access; specific licensing terms UNVERIFIED |
| Owner (team member) | @saraevcldn |
| Date acquired | UNVERIFIED |

## Files

Raw files are kept in raw storage, never in git. Record exactly what arrived.

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---:|---:|---|---|
| `phl_admin3.geojson` | GeoJSON | UTF-8 | 555,585,099 | 1,642 | `f682747fbb26ba773131049ef61603f4b872ba93739f6e2c3320f55dd21eec41` | `/Volumes/edu_access/00-source/raw/admin_boundaries/` |
| `phl_admin4.geojson` | GeoJSON | UTF-8 | 710,191,069 | 42,048 | `4ebb5e3cf7b3245c659ea5886725e6a77ffc2d4bcbe3963d8f704d5adc5523d2` | `/Volumes/edu_access/00-source/raw/admin_boundaries/` |

## Publisher documentation

Documents the publisher provides about this data. Keep them with the raw files; do not commit them.

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| COD-AB Philippines dataset page | https://data.humdata.org/dataset/cod-ab-phl | UNVERIFIED | Source identity and administrative-boundary metadata |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines |
| Geographic level (region / province / city-municipality / barangay / school) | ADM3 city/municipality; ADM4 barangay |
| Time coverage | `valid_on = 2025-02-13` |
| Time basis (school year / calendar year / reference date) | Administrative boundary validity date |
| Update frequency | UNVERIFIED |
| Population covered (e.g. public schools only) | Not applicable; geographic reference data |

## Structure

| Field | Value |
|---|---|
| Apparent grain (what one row represents) | One administrative boundary feature per ADM3 city/municipality or ADM4 barangay |
| Candidate primary key | `adm3_pcode` for ADM3; `adm4_pcode` for ADM4 |
| Candidate join keys | `adm3_pcode`, `adm4_pcode`, parent administrative codes; validated PSGC crosswalk where available |
| PSGC available? Which version? | Source contains administrative PCODEs; current PSA PSGC 2Q 2026 used for compatibility checking |
| Personally identifiable or sensitive fields | None observed |
| Provenance fields in the source | `valid_on`, `valid_to`, `version`, administrative hierarchy fields |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected type | Actual type | Notes |
|---|---|---|---|
| `adm3_pcode` | string | `object` | ADM3 administrative code |
| `adm3_name` | string | `object` | ADM3 city/municipality name |
| `adm2_pcode` | string | `object` | Parent administrative code |
| `adm2_name` | string | `object` | Parent administrative name |
| `adm1_pcode` | string | `object` | Higher-level administrative code |
| `adm1_name` | string | `object` | Higher-level administrative name |
| `adm0_pcode` | string | `object` | Country-level code |
| `adm0_name` | string | `object` | Country name |
| `valid_on` | date/datetime | `datetime64[ms]` | Boundary validity date |
| `valid_to` | date/datetime | `object` | Boundary validity end date |
| `area_sqkm` | numeric | `float64` | Area in square kilometers |
| `version` | string | `object` | Source version |
| `center_lat` | numeric | `float64` | Administrative-area center latitude |
| `center_lon` | numeric | `float64` | Administrative-area center longitude |
| `geometry` | geometry | `geometry` | Polygon or MultiPolygon geometry |
| `adm4_pcode` | string | `object` | ADM4 code; present in ADM4 layer |
| `adm4_name` | string | `object` | ADM4 barangay name; present in ADM4 layer |

## Known quality problems

Summary only; evidence lives in [profile.md](profile.md). Label each one **observed** or **suspected**.

- **Observed:** No missing or duplicate ADM3/ADM4 administrative codes were found.
- **Observed:** No missing, empty, or invalid geometries were found in either layer.
- **Observed:** Both layers use EPSG:4326 (WGS 84).
- **Observed:** The ADM3 structural code comparison with the PSA PSGC 2Q 2026 publication matched 1,500 of 1,642 records (91.35%); 142 did not have an exact structural match.
- **Suspected:** ADM3 boundary codes may require a validated PSGC crosswalk before being treated as official PSGC identifiers.
- **Suspected:** The boundary source version may not represent the same geographic edition as the current PSGC publication.
- **Suspected:** Administrative names should not be used as the primary join key when a geographic or validated code-based join is available.

## Limitations for analysis

What this source cannot support, or supports only with caveats.

- This is geographic reference data and does not contain education enrollment, capacity, population, or education outcomes.
- The boundary source should not be treated as the project's authoritative PSGC reference.
- Current PSGC identifiers should only be assigned through a validated crosswalk.
- Spatial joins should be performed using the boundary geometry rather than relying on administrative names alone.
- Geographic boundaries may not exactly match the geographic editions used by other project datasets.
- ADM4 should only be used for barangay-level analysis where the underlying project data supports that geographic level.