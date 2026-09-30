"""Reviewers to request for a pull request, from .github/reviewers.json.

    python .github/scripts/pr_reviewers.py hyenalouise   ->  maeveylain,saraevcldn

Prints nothing when the author is not in the table.
"""

import json
import sys
from pathlib import Path

TABLE = Path(__file__).resolve().parent.parent / "reviewers.json"


def load_table(path=TABLE):
    """Return {author: [reviewer, ...]}, skipping keys that start with '_'."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {author: reviewers for author, reviewers in data.items() if not author.startswith("_")}


def reviewers_for(author, table):
    return table.get(author, [])


if __name__ == "__main__":
    print(",".join(reviewers_for(sys.argv[1] if len(sys.argv) > 1 else "", load_table())))
