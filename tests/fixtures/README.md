# Test fixtures

Small, made-up sample files for tests. This is the only folder where data files may be committed (`tests/test_repo_policy.py`).

| Fixture | What it is |
|---|---|
| `deped.py` | Builds DepEd-shaped zips (one CSV and a README) for any source listed in its `NAMES`, in a temporary folder, from the source's real column contract, with invented schools (IDs from 900001). No data file is committed; zip timestamps are fixed so checksums are repeatable |
