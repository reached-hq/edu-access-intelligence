"""Check the AI help section of a pull request description (D-010).

Passes when "No AI help" is ticked, or when "AI helped" is ticked together with
all four gates and a note on what the AI did. Reads the description from the
PR_BODY environment variable and prints each problem as a GitHub error.
"""

import os
import re
import sys

GATES = ("Data", "AI claims", "Output", "Accountability")


def _ticked(text, label):
    return re.search(rf"^\s*[-*] \[[xX]\] {re.escape(label)}", text, re.M) is not None


def problems(body):
    """Return a list of problems; an empty list means the section is valid."""
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S).replace("\r\n", "\n")
    section = re.search(r"^## AI help[ \t]*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not section:
        return ["The description has no '## AI help' section. Copy it from the pull request template."]
    text = section.group(1)

    no_help, helped = _ticked(text, "No AI help"), _ticked(text, "AI helped")
    if no_help == helped:
        return ["Tick exactly one: 'No AI help' or 'AI helped'."]
    if no_help:
        return []

    found = [f"The {g} gate is not ticked. Fix the work until you can tick it." for g in GATES if not _ticked(text, f"**{g}:**")]
    note = re.search(r"\*\*What the AI did:?\*\*(?:\s*\(leave blank if no AI help\))?:?(.*)", text, re.S)
    if not note or not note.group(1).strip():
        found.append("Say what the AI did: which tool, and which parts of the work.")
    return found


if __name__ == "__main__":
    found = problems(os.environ.get("PR_BODY", ""))
    for p in found:
        print(f"::error::{p}")
    if not found:
        print("AI help is declared.")
    sys.exit(1 if found else 0)
