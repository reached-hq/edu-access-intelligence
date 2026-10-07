# 03 Silver

Typed, standardized, and deduplicated data at the source's own grain, with a quarantine for rejected rows.

Empty until milestone 03 (Refine). The source-aligned table and file names are
already finalized in the [ETL table registry](../../docs/standards/tables.md).
Files follow `NN_<verb>_<object>.sql`, with checks in
`90_validate_<object>.sql` (see [File naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
