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
4. **Open a pull request.** Fill in the template and link the issue (`Closes #14` or `Part of #14`). CI fails if no issue is linked, if the PR has no milestone (it is copied from the linked issue when the issue has one), or if the **AI help** section is not filled in (see [Using AI](#using-ai)).
5. **Review.** At least one teammate who is not the author approves the PR.
6. **Merge.** Merge with a merge commit (the only method turned on, D-013), then delete the branch.

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

## Using AI

AI tools are allowed for any work in this project: code, SQL, documentation, issues, pull requests, and review comments. The person who submits the work is its author and answers for it, whether or not AI helped.

**What counts as AI help:** any tool that writes or rewrites content for you, including chat assistants, code completion, and AI rewriting of text. Spell-check alone does not count.

Every pull request states whether AI helped with the work in it. If it did, the work must pass four gates before you open the pull request:

| Gate | The rule |
|---|---|
| **Data** | Give AI tools only public or made-up data. Never share keys, tokens, passwords, workspace credentials, or personal information. |
| **AI claims** | Anything the AI states as fact must be checked against a source you can link: official documentation, the publisher, the lectures, or our own output. Nothing enters the project on the AI's word alone. |
| **Output** | You checked the result yourself. Where there is something to run, it works, it is safe to rerun, and every result can be traced to its source. |
| **Accountability** | You can explain every part of the work without the AI, and you answer for it. |

State what the AI did: which tool, and which parts of the work. CI fails a pull request that does not tick exactly one option, or that ticks **AI helped** without all four gates and a note on what the AI did. CI can only see the ticks, so reviewers still send back work that does not really pass the gates.

This applies to pull requests opened after this rule was merged. Open pull requests add the block the next time they are edited. See D-010 in [docs/decisions.md](docs/decisions.md).

## Running the checks locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```
