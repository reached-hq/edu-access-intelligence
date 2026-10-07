"""Check which issues a pull request will close when it merges.

An issue closes on merge when the description says Closes, Fixes, or Resolves
#N, and also when it is linked in the PR sidebar (Development). A PR closes at
most one issue: the leaf issue it finishes. A parent is closed by hand once its
sub-issues and parent-level acceptance evidence are done
(docs/operations/workflow.md, "Linking the issue").

Reads the PR's closingIssuesReferences nodes, each with subIssuesSummary, as
JSON from CLOSING, lists what merging will close, and prints each problem as a
GitHub error.
"""

import json
import os
import sys


def problems(closing):
    """Return a list of problems; an empty list means the PR may close these issues."""
    found = []
    if len(closing) > 1:
        numbers = ", ".join(f"#{issue['number']}" for issue in closing)
        found.append(
            f"Merging would close {len(closing)} issues ({numbers}). A PR may close at most one "
            "leaf issue. Split the work, or use 'Part of #N' for issues this PR does not finish."
        )
    for issue in closing:
        subs = (issue.get("subIssuesSummary") or {}).get("total", 0)
        if subs:
            n = issue["number"]
            found.append(
                f"Merging would close #{n}, a parent issue with {subs} sub-issues. "
                f"Write 'Part of #{n}', close the sub-issue this PR finishes instead, and remove "
                f"#{n} from the sidebar (Development) if it is linked there."
            )
    return found


if __name__ == "__main__":
    closing = json.loads(os.environ.get("CLOSING") or "[]")
    for issue in closing:
        print(f"Merging closes #{issue['number']}: {issue['title']}")
    if not closing:
        print("Merging closes no issue.")
    found = problems(closing)
    for p in found:
        print(f"::error::{p}")
    sys.exit(1 if found else 0)
