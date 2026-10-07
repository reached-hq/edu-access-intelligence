# Evidence

Records that prove a claim about pipeline behavior. Results contain counts and
identifiers only, never source records or bulk outputs.

| Folder | Contents |
|---|---|
| `pipeline-runs/` | Run-specific, human-readable execution and rerun evidence |
| `source-validation/` | Compact machine-readable source-gate results when implemented |
| `reconciliation/` | Source-to-layer count and measure reconciliation when implemented |

| Evidence | Claim | Issue |
|---|---|---|
| [2026-10-06-deped-enrollment-idempotency.md](pipeline-runs/2026-10-06-deped-enrollment-idempotency.md) | Loading DepEd enrollment into Bronze twice on Databricks inserts nothing the second time | #11 |
| [2026-10-06-deped-facilities-idempotency.md](pipeline-runs/2026-10-06-deped-facilities-idempotency.md) | DepEd facilities loads once from its own contract, a second run inserts nothing, and enrollment is untouched | #11 |
| [2026-10-07-psa-poverty-stat-local-idempotency.md](pipeline-runs/2026-10-07-psa-poverty-stat-local-idempotency.md) | PSA Poverty Stat loads once, skips on rerun, loads new and older estimate years incrementally, blocks a changed file, and recovers from a crash (local, made-up workbooks; real file and Databricks pending) | #109 |
