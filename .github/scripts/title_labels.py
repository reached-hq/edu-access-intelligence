"""Labels for an issue, read from the tag at the start of its title.

The mapping follows how the team has labeled issues so far. Every tag in
docs/workflow.md (Issue titles) has a label.

    python .github/scripts/title_labels.py "[BRONZE] Load sources"   ->  infra
"""

import re
import sys

TAG_LABELS = {
    "SETUP": "infra",
    "DECISION": "decision",
    "FRAME": "framing",
    "SOURCE": "source-candidate",
    "PROFILE": "research",
    "BRONZE": "infra",
    "SILVER": "infra",
    "INTEGRATE": "infra",
    "GOLD": "infra",
    "DQ": "data-quality",
    "DEPLOY": "infra",
    "MONITOR": "infra",
    "OPS": "infra",
    "DASHBOARD": "dashboard",
    "AI/BI": "dashboard",
    "DOCS": "docs",
    "PROOF": "evidence",
    "PRESENT": "presentation",
}


def labels_for(title):
    """Return the labels for a title, in tag order, without duplicates."""
    leading = re.match(r"\s*((?:\[[^\]]+\]\s*)+)", title)
    tags = re.findall(r"\[([^\]]+)\]", leading.group(1)) if leading else []
    labels = []
    for tag in tags:
        label = TAG_LABELS.get(tag.strip().upper())
        if label and label not in labels:
            labels.append(label)
    return labels


if __name__ == "__main__":
    print(",".join(labels_for(sys.argv[1] if len(sys.argv) > 1 else "")))
