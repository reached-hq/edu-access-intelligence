# Verification

Local checks of a built layer on the real, checksum-verified data. Each program runs the job's real tasks on a fresh DuckDB file under `local_state/` (git-ignored) and prints counts and hashes, never row values, for an evidence record under `evidence/`. They are not job tasks.

| Program | What it checks |
|---|---|
| `psa_poverty_stat_silver.py` | The PSA Poverty Stat lane twice: Bronze rows by kind, candidates, clean and quarantined per estimate year, missing estimates, warning flags, the Silver gate, lineage, task timings, and the business-content hash of each rebuild ([Silver, PSA Poverty Stat](../../docs/operations/silver.md#running-locally-psa)) |
