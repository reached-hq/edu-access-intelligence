"""The comment that @mentions a pull request's reviewers, with a meme.

The opener and meme rotate by PR number, so a PR always gets the same pair.
Images live in .github/memes/ and are linked from main, so they render once
this file is merged.

    NUMBER=24 AUTHOR=hyenalouise REVIEWERS=maeveylain,saraevcldn ISSUE=23 \\
    MILESTONE="01 · Discover" python .github/scripts/reviewer_comment.py
"""

import os

MARKER = "<!-- triage:reviewers -->"
MEME_BASE = "https://raw.githubusercontent.com/reached-hq/edu-access-intelligence/main/.github/memes/"

# (opener, meme file, alt text). {a} and {b} are the two reviewers.
PAIRS = [
    ("Hey {a} and {b} 👋 you've been summoned to review this PR!",
     "summoned.png", "A doodle reaching a hand out towards you"),
    ("Calling {a} and {b}, a fresh PR just landed on your desk.",
     "reading.png", "A dog with glasses pushed up, reading a sheet of paper"),
    ("{a} and {b}, everything is going according to plan. All it needs now is your review.",
     "scheming.png", "A doodle smirking with its hands folded"),
    ("Detectives {a} and {b}, a new case has arrived. Please investigate 🕵️",
     "detective-hamster.png", "A hamster in a detective hat and coat holding a magnifying glass"),
    ("{a} and {b}, grab your magnifying glass 🔍 there's a PR to inspect.",
     "detective-blob.png", "A doodle in a detective hat with a pipe and a magnifying glass"),
]


def build(number, author, reviewers, issue=None, milestone=None):
    """Return the comment body in Markdown."""
    if len(reviewers) < 2:
        return (
            f"{MARKER}\n"
            f"Hmm, @{author} isn't in `.github/reviewers.json` yet, so nobody was summoned automatically. "
            "Please request a reviewer by hand."
        )

    opener, meme, alt = PAIRS[number % len(PAIRS)]
    a, b = (f"@{r}" for r in reviewers[:2])
    closes = f"closes #{issue}" if issue else "isn't linked to an issue yet"
    belongs = f"belongs to {milestone}" if milestone else "has no milestone yet"

    return f"""{MARKER}
{opener.format(a=a, b=b)}

<img src="{MEME_BASE}{meme}" alt="{alt}" width="250">

This one is from @{author}, {closes}, and {belongs}. Only one approval is needed, so whoever gets to it first takes it, and the other is off the hook.

Before you approve, read the Reviewer notes to see what the author wants you to look at closely, check the AI help section (if AI helped, the author should be able to explain every part without it), and make sure CI is green.

<sub>Reviewers come from `.github/reviewers.json`. Think a pairing is off? Open a PR to change it.</sub>"""


if __name__ == "__main__":
    reviewers = [r for r in os.environ.get("REVIEWERS", "").split(",") if r]
    print(build(
        int(os.environ["NUMBER"]),
        os.environ["AUTHOR"],
        reviewers,
        os.environ.get("ISSUE") or None,
        os.environ.get("MILESTONE") or None,
    ))
