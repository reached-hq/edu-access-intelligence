"""Report issues whose open or closed state disagrees with their sub-issues or the board.

Run weekly by .github/workflows/issue-hygiene.yml. Reads the repository's issues
as a JSON list from the file named by ISSUES_FILE: GraphQL nodes with number,
title, url, state, subIssues and, when the board could be read, projectItems.
Prints each finding as a GitHub warning, writes a summary to the run page, and
exits 1 if anything was found. It never changes an issue: whether a parent is
really finished is a person's call (docs/operations/workflow.md, "Linking the
issue").
"""

import json
import os
import sys

CLOSED_PARENT = "Closed issues with open sub-issues"
FINISHED_PARENT = "Open parent issues whose sub-issues are all closed"
OPEN_IN_DONE = "Open issues in Done on the board"
DONE = "Done"


def _subs(issue):
    return (issue.get("subIssues") or {}).get("nodes") or []


def _refs(issues):
    return ", ".join(f"#{i['number']}" for i in issues)


def board_was_read(issues):
    """True when the issues were fetched with their board status (projectItems)."""
    return any("projectItems" in issue for issue in issues)


def findings(issues):
    """Return a list of (heading, message) pairs; an empty list means nothing to fix."""
    found = []
    for issue in issues:
        n, state, subs = issue["number"], issue["state"].upper(), _subs(issue)
        open_subs = [s for s in subs if s["state"].upper() == "OPEN"]

        if state == "CLOSED" and open_subs:
            found.append((CLOSED_PARENT, (
                f"#{n} is closed but its sub-issues {_refs(open_subs)} are still open. "
                f"Reopen #{n}, or finish or move those sub-issues."
            )))
        if state == "OPEN" and subs and not open_subs:
            found.append((FINISHED_PARENT, (
                f"#{n} is open but all {len(subs)} of its sub-issues are closed. Check its own "
                "acceptance evidence and close it by hand, or add a sub-issue for what is left."
            )))
        if state == "OPEN":
            for item in (issue.get("projectItems") or {}).get("nodes") or []:
                status = (item.get("fieldValueByName") or {}).get("name")
                if status == DONE:
                    found.append((OPEN_IN_DONE, (
                        f"#{n} is open but sits in {DONE} on {item['project']['title']}. "
                        "Move the card back, or close the issue if its acceptance evidence is complete."
                    )))
    return found


def summary(issues, found):
    """Markdown for the run page, one section per kind of finding."""
    lines = ["## Issue hygiene", "", f"Checked {len(issues)} issues.", ""]
    headings = [CLOSED_PARENT, FINISHED_PARENT]
    if board_was_read(issues):
        headings.append(OPEN_IN_DONE)
    for heading in headings:
        messages = [m for h, m in found if h == heading]
        lines += [f"### {heading}", ""]
        lines += [f"- {m}" for m in messages] if messages else ["None."]
        lines.append("")
    if not board_was_read(issues):
        lines += [
            f"### {OPEN_IN_DONE}",
            "",
            "Not checked: the workflow's own token cannot read the organization's board. "
            "Add a `PROJECT_READ_TOKEN` secret to turn this on.",
            "",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    with open(os.environ["ISSUES_FILE"], encoding="utf-8") as f:
        issues = json.load(f)
    found = findings(issues)
    for _, message in found:
        print(f"::warning::{message}")
    if not found:
        print(f"Checked {len(issues)} issues: nothing to fix.")
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(summary(issues, found))
    sys.exit(1 if found else 0)
