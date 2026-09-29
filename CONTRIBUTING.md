# Contributing

The rules in short. For the full walkthrough see [docs/workflow.md](docs/workflow.md); for laptop setup see [docs/terminal_setup.md](docs/terminal_setup.md).

## Workflow

```
ISSUE → BRANCH → CHANGE → VALIDATE → COMMIT → PUSH → PULL REQUEST → REVIEW → MERGE
```

1. **Start from an issue.** Every change has a reason, and the issue records it.
2. **Branch off `main`.** Name the branch `<type>/<issue-number>-<short-description>`:
   - `feat/14-ingest-psgc`
   - `fix/22-duplicate-school-ids`
   - `docs/9-source-card-deped-enrollment`
   - `chore/3-ci-setup`
3. **Validate before you commit.** Run `python -m pytest tests -q`. For data changes, also check row counts, duplicates, and rerun safety.
4. **Open a pull request.** Fill in the template and link the issue (`Closes #14` or `Part of #14`). CI fails if no issue is linked.
5. **Review.** At least one teammate who is not the author approves the PR.
6. **Merge.** Squash-merge, then delete the branch.

## Commit messages

- Use the imperative mood: "Add PSGC source card", not "added stuff".
- Make one meaningful checkpoint per commit.

## Repository rules

These are enforced by `tests/test_repo_policy.py` where possible.

- **Never commit data.** Raw, interim, and processed datasets live in the agreed storage, not in git. The only exception is small, made-up samples under `tests/fixtures/`.
- **Never commit secrets.** Use `.env` locally; it is git-ignored. Only `.env.example`, with variable names and no values, is committed.
- **Save notebooks in `.py` source format,** not `.ipynb`.
- **Never modify raw files.** Every transformation writes a new layer.
- **Don't hard-code paths or dates.** Put them in `config/` or pass them as parameters.
- **Use fully qualified table names** (`catalog.schema.table`) in all SQL.
- **Don't clean data silently.** Every cleaning rule is documented, with the number of records it affects.

## Running the checks locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```
