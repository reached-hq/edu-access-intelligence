# Coverage matrix

One row per source: how it identifies places, its geographic level, years, time basis, grain, and join keys, with the PSGC match rate where the source has names only. Part of #8.

Only the DepEd sources are filled in so far; rows for the other sources are added as their cross-source checks are run. Evidence for the DepEd rows: [deped-dataset-research.md](deped-dataset-research.md).

| Source | PSGC codes or names only | Geographic level | Years | Time basis | Grain | Join keys | PSGC match (2Q 2026) |
|---|---|---|---|---|---|---|---|
| [deped_enrollment](../source-inventory/deped_enrollment/) | Names only (region, division, province, city or municipality, barangay) | School | SY 2023-24 tested; SY 2024-25 and 2025-26 acquired | School year | One row per school per school year | `school_id`; place names to PSGC by name | SY 2023-24: 96.9% of schools to barangay (58,289 of 60,134); 1,845 unmatched or ambiguous, [listed](generated/deped_psgc_unmatched.md) |
| [deped_facilities](../source-inventory/deped_facilities/) | None; location comes from enrollment | School | SY 2023-24 | School year | One row per school | `school_id` (60,167 of 60,167 in enrollment) | Through enrollment |
| deped_personnel ([#40](https://github.com/reached-hq/edu-access-intelligence/pull/40)) | None; location comes from enrollment | School | SY 2023-24 | School year | One row per school | `school_id` (60,167 of 60,167 in enrollment) | Through enrollment |
| deped_ellna ([#49](https://github.com/reached-hq/edu-access-intelligence/pull/49)) | Region and division names only | School | SY 2023-24 | School year | One row per assessed school | `school_id` (5,752 of 5,752 in enrollment) | Through enrollment |
| [deped_nat_gr6](../source-inventory/deped_nat_gr6/) | Region and division names only | School | SY 2023-24 | School year | One row per assessed school | `school_id` (6,636 of 6,636 in enrollment) | Through enrollment |
