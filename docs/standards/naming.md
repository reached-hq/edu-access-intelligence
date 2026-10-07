# Naming conventions

The machine-readable pattern authority is [`config/naming.yml`](../../config/naming.yml).
Final source table and SQL file names are registered in
[`config/tables.yml`](../../config/tables.yml) and summarized in
[`tables.md`](tables.md).

- Use lowercase `snake_case` for source IDs, Python modules, task keys, tables,
  and columns.
- Use lowercase `kebab-case` for documentation folders and ordinary Markdown
  filenames.
- Source-inventory folders match their `source_id` and therefore use
  `snake_case`.
- Name ETL files `NN_<verb>_<object>.sql`; validation files use
  `90_validate_<object>.sql`.
- Bronze tables end in `_raw`; Silver tables end in `_clean`; rejected Silver
  rows go to `_quarantine`; reviewed Integration mappings end in `_map`.
- Gold dimensions start with `dim_`; Gold facts start with `fact_`.
- Do not reserve Gold or Analytics object names until their question, metric,
  and grain are approved.
- Use fully qualified `catalog.schema.table` references for persisted objects.
  The numbered, hyphenated schema names require backticks in SQL.
