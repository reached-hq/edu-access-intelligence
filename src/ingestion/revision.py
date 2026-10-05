"""Which commit produced a row: the `code_revision` stamped on every output.

A Bronze row is traced to its source file by its provenance columns, and to
the code that loaded it by `code_revision`. That second link is what you need
when a number turns out wrong.

- On Databricks the job passes it in: the bundle sets the job parameter
  `code_revision` to `${bundle.git.commit}`, the same substitution that pins
  the code the job runs, so the two cannot disagree. A job run must supply a
  full commit SHA; `require_commit=True` refuses anything else.
- Locally it is read from git. Uncommitted or untracked changes add `-dirty`,
  because the bare SHA would claim code that did not actually run.
- When neither is available the value is `UNSET`, spelled one way only, so
  "not recorded" is one value in every table.
"""

import re
import subprocess

from src.ingestion.errors import IngestionError

UNSET = "UNSET"
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _git(repo_root, *args):
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def resolve_code_revision(repo_root, explicit=None, require_commit=False):
    if explicit is not None and explicit.strip():
        revision = explicit.strip()
    else:
        sha = _git(repo_root, "rev-parse", "HEAD")
        if sha:
            # Untracked files count: a new module that is not committed yet
            # still changes what runs.
            dirty = _git(repo_root, "status", "--porcelain")
            revision = f"{sha}-dirty" if dirty else sha
        else:
            revision = UNSET
    if require_commit and not COMMIT.match(revision):
        raise IngestionError("config", "code_revision_required",
                             f"code_revision {revision!r} is not a full commit SHA. A job run must receive "
                             "--code-revision from the job parameter (default ${bundle.git.commit}); "
                             "deploy from a clean checkout.")
    return revision
