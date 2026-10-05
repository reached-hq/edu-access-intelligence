# psa_population_per_age_group: 2024 household population by age group

**Status:** profiled

## Identity

| Field | Value |
|---|---|
| Source name | Household Population by Age-Group Region, Province, and Highly Urbanized City: Philippines, 2024 Census of Population |
| Publisher / agency | Philippine Statistics Authority (PSA) |
| Source system (as stated by the publisher) | PSA OpenSTAT, 2024 Census of Population |
| Source URL or acquisition method | Manual CSV export from the [PSA OpenSTAT 2024 population tables](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1A__PO_2024/?tablelist=true); exact table ID `0201A6DPAG0.px` |
| Licensing or access restrictions | Public download. License and reuse terms were not present in the CSV or API metadata and remain **UNVERIFIED** |
| Owner (team member) | @mafelisilda |
| Date acquired | 2026-09-29 11:13 UTC |

## Files

Raw files are kept outside git. Row count excludes the title and header records.

| File | Format | Encoding | Size (bytes) | Row count | SHA-256 | Raw storage location |
|---|---|---|---|---|---|---|
| `Household Population by Age-Group Region, Province, and Highly Urbanized City- Philippines, 2024 Census of Population.csv` | CSV | UTF-8, CRLF; 38 encoded `U+FFFD` replacement characters | 131,051 | 2,603 | `ce797046a055f870c30f5a2ce6d42b4bdc8f14f4dd8145269f450372c6c93ad6` | Governed raw storage; uploaded |

## Publisher documentation

| Document | URL | SHA-256 | Sections relied on |
|---|---|---|---|
| PSA OpenSTAT 2024 population table listing | https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1A__PO_2024/?tablelist=true | Live web resource; checksum not captured | Publisher, table title, table selection, and source system |
| OpenSTAT API metadata for table `0201A6DPAG0.px` | https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1A/PO_2024/0201A6DPAG0.px | Live JSON resource; checksum not captured | Exact table title; age-group, geography, and sex dimensions; category labels; 10-digit geographic codes |
| PSA OpenSTAT table `0221A6DLPD0.px`, "Population, Land Area, Population Density, and Percent Change in Population Density by Region, Province/Highly Urbanized City, and City/Municipality: 2015, 2020, and 2024" | https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1A__PO_2024/0221A6DLPD0.px/ | Live web resource; checksum not captured | Publisher footnote defining `*` as province population excluding HUC counts |
| CSV title and header | Inside the inventoried file | File checksum above | Delivered title, column names, and exported layout |

## Coverage

| Field | Value |
|---|---|
| Geographic coverage | Philippines: 1 national total, 18 region totals, and 118 province, HUC, or special-area labels |
| Geographic level | Country, region, and a mixed lower level containing provinces, highly urbanized cities, Pateros, Isabela City, and the Special Geographic Area |
| Time coverage | One census reference year: 2024 |
| Time basis | 2024 Census of Population; the exact census reference date is not stated in the CSV or table metadata inspected |
| Update frequency | Census-based release; refresh schedule **UNVERIFIED** |
| Population covered | Household population by sex and 19 age categories, including `All Ages`; institutional population is not represented by the table title |

## Structure

| Field | Value |
|---|---|
| Apparent grain | One household-population value set per `(Age Group, Geographic Location)` |
| Candidate primary key | `(Age Group, Geographic Location)`; 2,603 rows and 0 duplicate keys |
| Candidate join keys | The OpenSTAT API provides 10-digit geographic codes, but the CSV omits them. The raw geographic label can support a controlled, reference-date-aware crosswalk to `psa_psgc` |
| PSGC available? Which version? | Codes are available in the live API metadata but absent from the CSV. Their PSGC edition or effective date is not stated and remains **UNVERIFIED** |
| Personally identifiable or sensitive fields | None. Public aggregate population counts only. Classification: **Public** |
| Provenance fields in the source | Title row, dimension labels, display-label hierarchy markers, and footnote markers. The CSV has no download timestamp, table ID, API category codes, source URL, release version, or correction flag |

Column-by-column descriptions, fill rates, and sample values: [data_dictionary.md](data_dictionary.md).

### Expected vs actual schema

| Column | Expected type | Actual type | Notes |
|---|---|---|---|
| `Age Group` | Category | Text | 19 categories: `All Ages` plus 18 exhaustive age bands |
| `Geographic Location` | Geographic category | Text | 137 labels; hierarchy encoded by 0, 2, or 4 leading periods; codes omitted from CSV |
| `Both Sexes` | Nonnegative whole number | Integer-form text | Complete, but 38 lower-level values fail sex-total reconciliation |
| `Male` | Nonnegative whole number | Integer-form text | Complete and nonnegative |
| `Female` | Nonnegative whole number | Integer-form text | Complete and nonnegative |

## Lineage and dependencies

PSA 2024 Census of Population collection and processing -> PSA OpenSTAT table `0201A6DPAG0.px` -> manual CSV export -> checksum-verified raw storage -> title and schema validation -> population typing and reconciliation -> reference-date-aware geographic crosswalk -> downstream demographic denominators and access indicators.

The source depends on the live OpenSTAT API metadata to recover geographic codes discarded by the CSV export. Downstream use depends on a governed PSGC crosswalk, explicit handling of the 38 reconciliation failures, and retention of raw age and geography labels.

## Known quality problems

Summary only; evidence lives in [profile.md](profile.md).

- **Observed:** 38 province or HUC rows in the `80 - 84` and `85 and over` groups fail `Both Sexes = Male + Female`. They occur only in Regions V, X, and XI.
- **Observed:** 19 geographic labels fail the `All Ages = sum(age bands)` check for `Both Sexes`; the discrepancy equals the corresponding `85 and over` value. Male and female totals reconcile for all 137 geographies.
- **Observed:** the six affected region-by-age child sums do not reconcile to published region totals, while all national totals reconcile to the 18 region totals.
- **Observed:** 38 rows across `City of Las Piñas` and `City of Parañaque` contain `U+FFFD` in place of `ñ`; the original characters cannot be reconstructed from this file alone.
- **Observed:** the CSV omits the 10-digit geographic codes available in the table API, making names and footnote-bearing labels the only delivered join material.
- **Observed:** 25 geographic labels include asterisks, slash-number footnote markers, or both. PSA OpenSTAT table `0221A6DLPD0.px`, titled "Population, Land Area, Population Density, and Percent Change in Population Density by Region, Province/Highly Urbanized City, and City/Municipality: 2015, 2020, and 2024," defines `*` as province population excluding separately reported HUC counts. The marker is absent from Agusan del Norte in this file even though Butuan is listed separately.
- **Observed:** leading periods encode geographic display hierarchy rather than being part of the place name.
- **Suspected:** the affected `Both Sexes` values may reflect a table-generation or export alignment defect. No correction is applied without publisher confirmation.

## Limitations for analysis

- Do not use the affected lower-level `Both Sexes` counts for the two oldest age groups until corrected or verified. Male and female columns may be aggregated separately only if the limitation is disclosed.
- This is one census snapshot and does not support trend analysis without comparable releases.
- The table does not include barangays, cities other than listed HUCs and special cases, household identifiers, institutional population, or uncertainty measures.
- Geographic codes, footnote definitions, and release-version details are absent from the downloaded CSV. The related official table supplies the general asterisk definition, but not why its application differs for Agusan del Norte.
- Household population must not be described as total population without reconciling the definitional difference.

## Recommended controls and monitoring

- Fail ingestion if the checksum, title, five-column schema, 2,603-row count, 19-age-group roster, or 137-geography roster changes without re-inventory.
- Enforce uniqueness of `(Age Group, Geographic Location)` and reject blanks, non-integers, negatives, or unexpected hierarchy-prefix lengths.
- Run sex-total, all-age, region-child, and national-region reconciliations on every delivery. Quarantine failing cells rather than modifying them.
- Retrieve and retain API geographic codes and category codes with the raw export; record retrieval timestamp and API table ID.
- Preserve raw labels, including footnote markers and replacement characters, alongside separately cleaned matching fields.
- Alert when replacement-character counts, footnote-bearing labels, mismatch counts, or mismatch locations change.
- Seek PSA confirmation or a corrected export for the 38 inconsistent rows and confirmation of the omitted Agusan del Norte asterisk.
