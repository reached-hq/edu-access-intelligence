# Cross-source analysis

Work that compares or joins sources, with evidence: for example the DepEd to PSGC match rate (#8) and the coverage matrix. Findings for a single source stay in `docs/source_inventory/<source_id>/`.

Not to be confused with `notebooks/profiling/`, which holds the scripts.

## Contents

- [Coverage matrix](coverage.md): one row per source with geographic key, level, years, grain, join keys, and PSGC match rate, plus join paths, limits, time alignment, conflicts between documents, and open questions (part of #8).
- [DepEd SY 2023-24: PSGC match and school ID joins](deped_dataset_research.md): how the DepEd anchor joins to PSGC 2Q 2026 and to the other DepEd school files. Unmatched names: [deped_psgc_unmatched.md](deped_psgc_unmatched.md).
- [DepEd enrollment across SY 2023-24 to 2025-26](deped_year_comparison.md): label mappings, blank counts, school ID churn, place changes, and the PSGC match for each year. Lists: [deped_year_changes.md](deped_year_changes.md).
- [BARMM sources: what they support and how they join](barmm_dataset_research.md): status, join keys, timing, and distance design for the BPDA, PSA, and teammates' sources covering BARMM (part of #8).
