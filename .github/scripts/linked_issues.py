"""Issue numbers a pull request description links to, in the order they appear.

Uses the same keywords as the "PR links an issue" check: closes, fixes,
resolves, part of, related to. Reads the description from PR_BODY.

    PR_BODY="Closes #23" python .github/scripts/linked_issues.py   ->  23
"""

import os
import re

LINK = re.compile(r"\b(?:closes|fixes|resolves|part of|related to)\s+#(\d+)", re.I)


def linked_issues(body):
    numbers = []
    for match in LINK.finditer(re.sub(r"<!--.*?-->", "", body or "", flags=re.S)):
        n = int(match.group(1))
        if n not in numbers:
            numbers.append(n)
    return numbers


if __name__ == "__main__":
    print(" ".join(str(n) for n in linked_issues(os.environ.get("PR_BODY", ""))))
