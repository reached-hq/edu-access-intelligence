# dti_cmci: CMCI Capacity of School Services and Education indicators by LGU and year

**Status:** profiled

## Identity

| Field                                      | Value |
| ------------------------------------------ | ----- |
| Source name                                | Cities and Municipalities Competitiveness Index (CMCI) Data Portal: indicators "Capacity of School Services" and "Education" |
| Publisher / agency                         | Department of Trade and Industry (DTI) |
| Source system (as stated by the publisher) | Cities and Municipalities Competitiveness Index (CMCI) |
| Source URL or acquisition method           | Extracted by the project from the public CMCI Data Portal, [https://cmci.dti.gov.ph/data-portal.php](https://cmci.dti.gov.ph/data-portal.php), using HTTP POST requests to its processing endpoint, [https://cmci.dti.gov.ph/data-portal-process.php](https://cmci.dti.gov.ph/data-portal-process.php). **The CSVs are project-generated extractions, not files received directly from the publisher.** Form fields sent: `chk-indicators[]` = `css` or `edu`; `chk-lgu[]` = the LGU name exactly as listed in the portal's LGU dropdown; `chk-year[]` = `2023` or `2024`. One request was made per LGU, year, and indicator, with a 0.2-second pause between requests, a 30-second timeout, and a browser-style User-Agent. The score was extracted from the second cell of the HTML table row whose first cell was `Education` or `Capacity of School Services`. The LGU list was extracted from the `lgu` dropdown options on the portal page. Current extraction scripts (Python, requests + BeautifulSoup), with the `status` rules written in their header comment: [`src/ingestion/dti_cmci/cmci_capacity_of_school_services_2023_2024.py`](../../../src/ingestion/dti_cmci/cmci_capacity_of_school_services_2023_2024.py) and [`src/ingestion/dti_cmci/cmci_education_2023_2024.py`](../../../src/ingestion/dti_cmci/cmci_education_2023_2024.py). The delivered CSVs were produced on 2026-10-01 by earlier versions of these scripts plus retry passes; see "Extraction rules" for the run dates, times and history. |
| Licensing or access restrictions           | Public web portal. Specific license or reuse terms were not verified. **UNVERIFIED** |
| Owner (team member)                        | @saraevcldn |
| Date acquired                              | 2026-10-01 (all passes; Philippine time, with UTC times documented in "Extraction rules") |

### Extraction rules

The portal does not provide a file download for these indicators, so values were requested one LGU, indicator, and year at a time using the endpoint described above. The extraction added a `status` column. Each LGU-year gets exactly one status; these are the rules as coded in the current extraction scripts:

| `status`            | Rule |
| ------------------- | ---- |
| `valid`             | HTTP 200, the indicator row was found, and its score cell is a number. |
| `cmci_missing`      | HTTP 200, the indicator row was found, and the portal showed `-` as the score. This is the only source-side gap. The value is stored as blank; `-` is never converted to 0. |
| `cmci_server_error` | The request failed (network error or timeout), returned a non-200 status, or returned a page without the indicator row, for example the portal's "Please choose a Province and/or a Local Government Unit" message or a PHP error page. This is an extraction failure, not missing data. |
| `unexpected_value`  | The indicator row was found but its score is neither `-` nor a number. Should not occur; review by hand if it does. |

The delivered files contain only `valid`, `cmci_missing` (Education only) and `cmci_server_error`; no `unexpected_value` records.

**Passes.** All extraction was completed on 2026-10-01. The files in the volume represent the most complete result after the initial and retry passes described below. During a retry pass, records whose requests had failed were requested again using the same endpoint and parameters, and the new result replaced the previous row in place.

| Indicator | Pass       | Script                                                  | Start, Philippine time (UTC+8) | Start, UTC       |
| --------- | ---------- | ------------------------------------------------------- | ------------------------------ | ---------------- |
| CSS       | First pass | `cmci_capacity_of_school_services_2023_2024_scraper.py` | 2026-10-01 07:03               | 2026-09-30 23:03 |
| CSS       | Retry      | `cmci_capacity_of_school_services_2023_2024_retry2.py`  | 2026-10-01 09:08               | 2026-10-01 01:08 |
| Education | First pass | `cmci_education_2023_2024_scraper.py`                   | 2026-10-01 09:20               | 2026-10-01 01:20 |
| Education | Retry      | `cmci_education_2023_2024_retry1.py`                    | 2026-10-01 14:33               | 2026-10-01 06:33 |

The CSS retry script is named `retry2`; the script from an earlier CSS retry (`retry1`) was overwritten and is no longer available. The first-pass files and pass logs were also not retained, so the number of records retried and recovered in each pass cannot be reconstructed. The `status` labels in the final files were not all set by the scripts currently retained, so the exact rule used at the time to assign `cmci_server_error` cannot be fully reconstructed.

The current scripts make the rules explicit. In particular, an HTTP 200 response without the indicator row is now always `cmci_server_error`, never `cmci_missing`, so a rerun cannot turn an extraction failure into an apparent source-side gap. The delivered labels are consistent with these rules: when Brooke's Point and T'boli were requested by hand on the portal, it showed the "Please choose a Province and/or a Local Government Unit" message instead of a score (profile S-1). The `-` behind the two `cmci_missing` records (Concepcion (RN) and Initao, 2023) has not been re-checked by hand. The checksums below correspond to the final uploaded files and are the reference files for `profile.md`.

## Files

| File                                             | Format | Encoding             | Size (bytes) | Row count | SHA-256                                                            | Raw storage location                                        |
| ------------------------------------------------ | ------ | -------------------- | ------------ | --------- | ------------------------------------------------------------------ | ----------------------------------------------------------- |
| `cmci_capacity_of_school_services_2023_2024.csv` | CSV    | UTF-8, CRLF          | 93,982       | 3,268     | `a9258fede279e1194e53a0ffeefd596df33505e82558e928f3adaee9791214e4` | Databricks volume `/Volumes/edu_access/00-source/raw/cmci/` |
| `cmci_education_2023_2024.csv`                   | CSV    | UTF-8, CRLF          | 94,530       | 3,268     | `6267b77a1043dbcd63f37957ec7c01cc4eb9fcba1bf88ed9c6247c6a8e7de102` | Databricks volume `/Volumes/edu_access/00-source/raw/cmci/` |
| `cmci_lgu_list.csv`                              | CSV    | UTF-8 with BOM, CRLF | 18,081       | 1,634     | `187931b652b0912a5fa176b9743f107d6bb8c020004b132e42b753a1afabbebb` | Databricks volume `/Volumes/edu_access/00-source/raw/cmci/` |

`cmci_lgu_list.csv` contains the LGU names offered by the portal and is used as the reference for portal coverage. The profiling script verifies these checksums before reading the files. `cmci_lgu_list.csv` begins with a UTF-8 byte order mark (BOM); a reader that does not strip it may read the first column name as `\ufefflgu` instead of `lgu`. The profiling script's column check passes on the file, and DuckDB handles the BOM.

## Publisher documentation

| Document                                                 | URL                                                                                | SHA-256 | Sections relied on                                                             |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------ |
| CMCI Data Portal (web page, not a downloadable document) | [https://cmci.dti.gov.ph/data-portal.php](https://cmci.dti.gov.ph/data-portal.php) | n/a     | Indicator selection, LGU selection, reference years, published CMCI indicators |

No methodology document has been reviewed yet, so the meaning, calculation method, and scale of the scores remain **UNVERIFIED**. Only two indicators were extracted (`css` Capacity of School Services and `edu` Education); other CMCI indicators are outside the scope of the Education Access Intelligence project.

## Coverage

| Field                          | Value                                                             |
| ------------------------------ | ----------------------------------------------------------------- |
| Geographic coverage            | Philippine cities and municipalities available in the CMCI portal |
| Geographic level               | City / municipality (LGU), by name                                |
| Time coverage                  | 2023-2024                                                         |
| Time basis                     | CMCI reference year                                               |
| Update frequency               | Appears to be annual based on the 2023 and 2024 reference years; not independently verified |
| LGU names available in portal  | 1,634                                                             |
| Expected records per indicator | 3,268 (1,634 LGUs x 2 years)                                      |
| Valid CSS records              | 3,264                                                             |
| Valid Education records        | 3,262                                                             |

## Structure

| Field                                       | Value |
| ------------------------------------------- | ----- |
| Apparent grain                              | One indicator value per LGU per year (one file per indicator) |
| Candidate unique key                        | `lgu`, `year` (within each file) |
| Candidate join keys                         | `lgu` + `year` between the two CMCI files; for other sources, the LGU name after suffix handling (see below) |
| PSGC available?                             | **No.** LGUs are represented by names from the CMCI portal |
| Geographic standardization                  | LGU names must be mapped to official PSGC identifiers before joining with other project datasets. This requires a suffix-to-province lookup (see below). |
| Personally identifiable or sensitive fields | None found |
| Provenance fields in the source             | None in the portal data. `status` was added during project extraction (see "Extraction rules"). |

Column-by-column descriptions, fill rates, and data types: [data_dictionary.md](data_dictionary.md).

### LGU name convention

`lgu` + `year` is unique within each CMCI file across the 1,634 distinct LGU names. However, 362 names carry a two-letter suffix in parentheses to distinguish LGUs with the same name, for example `Alaminos (LA)` and `Alaminos (PS)`. A total of 122 base names are shared by more than one LGU. The suffixes appear to be CMCI's own province abbreviations rather than PSGC codes (**UNVERIFIED:** no published list of the abbreviations has been found).

- Mapping to PSGC requires a suffix-to-province lookup that should be built and reviewed before matching LGUs by city or municipality name.
- In a reviewer's check on a local copy against the PSGC 2Q 2026 city and municipality names, 1,472 of 1,634 names matched exactly after removing the suffix. The remaining names differ in other ways, such as dropped accents (`Science City of Munoz`). The project's own match against administrative boundaries is documented in that source's profile, not here.

### Expected vs actual schema

| Column group                                | Expected                                     | Actual  | Notes |
| ------------------------------------------- | -------------------------------------------- | ------- | ----- |
| `lgu`, `year`                               | text                                         | matches | `year` is `2023` or `2024` |
| `capacity_of_school_services` / `education` | numeric score                                | matches | Stored as text; blank when `status` is not `valid` |
| `status`                                    | `valid`, `cmci_missing`, `cmci_server_error`, `unexpected_value` | matches | Added during project extraction; `unexpected_value` does not occur in the delivered files |

## Known quality problems

See [profile.md](profile.md) for supporting evidence.

- **Observed:** CSS contains 3,264 valid records and 4 `cmci_server_error` records (Brooke's Point and T'boli, both years). Education contains 3,262 valid records, 4 `cmci_server_error` records, and 2 `cmci_missing` records (Concepcion (RN) and Initao, 2023).
- **Observed:** The `cmci_server_error` records are the same LGUs in both years and both indicators, so the failure repeats for the same names. Requested by hand on the portal, both returned the "Please choose a Province and/or a Local Government Unit" message instead of a score.
- **Observed:** The Education indicator returned `-` for some records. These were stored as blank rather than 0.
- **Observed:** 127 valid CSS scores and 51 valid Education scores are exactly 0, and 41 LGU-years have a value of 0 in both indicators. Whether 0 represents a valid score or an absence of submitted data is unknown (profile S-2).
- **Observed:** The only LGU names with an apostrophe in the reference list (Brooke's Point and T'boli) are the `cmci_server_error` records. The extraction behavior may therefore be related to how these names were submitted to the portal (profile S-1).
- **Observed:** LGUs are represented by portal names rather than PSGC codes (see "LGU name convention").
- **Observed:** The extracted output does not expose the formulas or component variables behind the two indicators.

## Limitations for analysis

- `Capacity of School Services` and `Education` are CMCI indicator scores, not direct counts of schools, classrooms, teachers, learners, or other education resources. The CMCI `Capacity of School Services` score should therefore **not be interpreted as a direct measure of physical education capacity** without verification of its methodology.
- The calculation method, score scale, and component variables behind the indicators have not been verified. Comparability between 2023 and 2024 has also not been established (profile S-3, S-4).
- LGU names must be mapped to PSGC identifiers using a reviewed suffix-to-province lookup before joining with DepEd, PSA, CHED, or other project datasets.
- Missing and server-error records remain missing and must not be treated as zero.
- The two indicators are kept separate. No combined CMCI education score is created.
- CMCI indicators should be treated as **contextual or exploratory variables** unless their methodology is verified; they should not be used alone to infer education demand, capacity gaps, or planning priorities.
- Check whether the PSA poverty statistics (#5) provide overlapping contextual information or whether CMCI contributes additional information to the analysis.

### Open questions / pending review

- Verify the official methodology, calculation, and scale of the `Capacity of School Services` and `Education` indicators.
- Determine whether the scores are comparable across the 2023 and 2024 reference years.
- Determine whether a value of 0 represents a valid score, missing reporting, or another condition.
- Complete and review the CMCI LGU-to-PSGC mapping before joining this source with other project datasets.
- Assess whether CMCI provides analytical value beyond other socioeconomic or education-related contextual indicators already included in the project.