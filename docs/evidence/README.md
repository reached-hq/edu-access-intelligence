# Evidence

Records of runs that prove a claim about the pipeline, one file per claim, named `YYYY-MM-DD-<topic>.md` (date in Manila time). Each states the claim, what was run (run IDs, commit), the queries and their results, why the claim holds, what it does not prove, and how to reproduce it. Results are counts and identifiers only, never source records.

| Evidence | Claim | Issue |
|---|---|---|
| [2026-10-06-deped-enrollment-idempotency.md](2026-10-06-deped-enrollment-idempotency.md) | Loading DepEd enrollment into Bronze twice on Databricks inserts nothing the second time | #11 |
