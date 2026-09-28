# Source inventory

One folder per source, created by copying [`_template/`](_template/) to `<source_id>/`:

| File | Contents |
|---|---|
| `README.md` | The inventory card: identity, files, publisher documentation, coverage, structure, limitations |
| `profile.md` | First-look and profiling findings, with evidence |

Cross-source work (PSGC match rates, coverage matrix) lives in [`docs/profiling/`](../profiling/).

## Rules

- A source is not described as useful until it has been inspected.
- Any field not yet confirmed is written as `UNVERIFIED`, not guessed.
- Each folder name matches the source's `source_id` in [`config/sources.json`](../../config/sources.json).
- Raw data files and publisher documents stay in raw storage. The card records their URL, size, and SHA-256 instead.
- Every finding is labeled **observed** (with evidence) or **suspected** (still to test).

## Sources

| source_id | Name | Publisher | Status | Owner |
|---|---|---|---|---|
| | | | | |
