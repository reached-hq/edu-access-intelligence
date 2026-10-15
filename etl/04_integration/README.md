# 04 Integration

Matching across sources: DepEd place names to PSGC codes, and other sources to the shared geography.

Built so far: `03_map_hdx_adm3_psgc.sql` and `90_validate_hdx_adm3_psgc_map.sql` (#93, D-042),
generated from `config/integration/hdx_adm3_psgc.json` by `python -m src.integration.hdx_adm3_psgc sql|gate`;
`tests/test_integration_hdx.py` fails if they differ. The other files are placeholders until milestone 03 (Refine). Candidate mapping names are documented as
drafts in the [ETL table registry](../../docs/standards/tables.md); they are not
reserved until keys, grains, and review rules are approved. Files follow
`NN_<verb>_<object>.sql`, with checks in `90_validate_<object>.sql` (see
[File naming and layout](../../docs/architecture/overview.md#file-naming-and-layout)).
