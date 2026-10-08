"""Check that the issues a pull request description links to exist and are open.

Reads ISSUES as JSON: one entry per issue the description links to, either
{"number", "state", "is_pull_request"} from the issues API, or {"number",
"missing": true} when GitHub returned no issue. A link to a missing issue or to a
pull request fails, since it is almost always a typo. A link to a closed issue
only warns: 'Related to' a finished issue is fine, but 'Closes' or 'Part of' one
usually means the wrong number.
"""

import json
import os
import sys


def problems(issues):
    """Return (errors, warnings); errors fail the check, warnings only show on the PR."""
    errors, warnings = [], []
    for issue in issues:
        n = issue["number"]
        if issue.get("missing"):
            errors.append(f"#{n} is not an issue in this repository. Check the number in the description.")
        elif issue.get("is_pull_request"):
            errors.append(f"#{n} is a pull request, not an issue. Link the issue the work belongs to.")
        elif issue.get("state", "").lower() == "closed":
            warnings.append(
                f"#{n} is already closed. If this PR still works on it, reopen it or link the "
                "issue that tracks the remaining work."
            )
    return errors, warnings


if __name__ == "__main__":
    errors, warnings = problems(json.loads(os.environ.get("ISSUES") or "[]"))
    for w in warnings:
        print(f"::warning::{w}")
    for e in errors:
        print(f"::error::{e}")
    if not errors and not warnings:
        print("Every linked issue exists and is open.")
    sys.exit(1 if errors else 0)
