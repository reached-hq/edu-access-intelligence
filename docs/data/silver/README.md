# Silver tables

One data dictionary per Silver table, generated from the source's Bronze contract and reviewed Silver mapping (`python -m src.silver.cli dictionary`). How the tables are built, checked, and rerun: [docs/operations/silver.md](../../operations/silver.md).

| Source | Clean table | Quarantine | Dictionary |
|---|---|---|---|
| `deped_enrollment` | `deped_enrollment_clean` | `deped_enrollment_quarantine` | [deped-enrollment-clean.md](deped-enrollment-clean.md) |
| `hdx_boundaries` | `hdx_adm3_clean` | `hdx_adm3_quarantine` | [hdx-adm3-clean.md](hdx-adm3-clean.md) |
