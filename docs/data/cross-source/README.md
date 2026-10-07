# Cross-source analysis

Work that compares or joins sources, with evidence: for example the DepEd to PSGC match rate (#8) and the coverage matrix. Findings for a single source stay in `docs/data/source-inventory/<source_id>/`.

The reproducible join checks live in `analysis/cross_source/`; source-only
profiling stays in `analysis/profiling/`.

## Contents

- [Coverage matrix](coverage.md): one row per source with geographic key, level, years, grain, join keys, and PSGC match rate (part of #8).
- [DepEd SY 2023-24: PSGC match and school ID joins](deped-dataset-research.md): how the DepEd anchor joins to PSGC 2Q 2026 and to the other DepEd school files. Unmatched names: [deped_psgc_unmatched.md](generated/deped_psgc_unmatched.md).
- [BARMM sources: what they support and how they join](barmm-dataset-research.md): status, join keys, timing, and distance design for the BPDA, PSA, and teammates' sources covering BARMM (part of #8).
