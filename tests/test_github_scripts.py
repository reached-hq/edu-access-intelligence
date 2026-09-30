"""Tests for the scripts the GitHub workflows run (.github/scripts/)."""

import importlib.util

import pytest

from conftest import REPO_ROOT


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / ".github/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


title_labels = _load("title_labels")
pr_ai_help = _load("pr_ai_help")


# --- title_labels ---------------------------------------------------------

@pytest.mark.parametrize("title, expected", [
    ("[BRONZE] Load sources into Bronze tables", ["infra"]),
    ("[SOURCE] Find, download, and first look: PSGC", ["source-candidate"]),
    ("[DECISION] Pick the business question", ["decision"]),
    ("[docs] lowercase tag", ["docs"]),
    ("[DASHBOARD] [AI/BI] Build the dashboard", ["dashboard"]),
    ("[SETUP] [DOCS] Two tags", ["infra", "docs"]),
    ("[FRAME] No clear label", []),
    ("No tag at all", []),
    ("Tag later [DOCS] is ignored", []),
])
def test_labels_for(title, expected):
    assert title_labels.labels_for(title) == expected


def test_every_mapped_label_is_a_known_repo_label():
    # Labels created in the repository (gh label list). Adding a mapping to a
    # label that does not exist would make the workflow fail.
    known = {"infra", "decision", "source-candidate", "research", "dashboard", "docs", "data-issue"}
    assert set(title_labels.TAG_LABELS.values()) <= known


# --- pr_ai_help -----------------------------------------------------------

GATES_TICKED = """
  - [x] **Data:** only public or made-up data
  - [x] **AI claims:** every fact checked
  - [x] **Output:** I checked the result myself
  - [x] **Accountability:** I can explain every part
"""


def _body(section):
    return f"## Summary\n\nText.\n\n## AI help\n\n{section}\n\n## Reviewer notes\n\nCheck X.\n"


def test_template_itself_fails():
    template = (REPO_ROOT / ".github/pull_request_template.md").read_text()
    assert pr_ai_help.problems(template) == ["Tick exactly one: 'No AI help' or 'AI helped'."]


def test_template_has_every_gate_the_check_requires():
    template = (REPO_ROOT / ".github/pull_request_template.md").read_text()
    for gate in pr_ai_help.GATES:
        assert f"**{gate}:**" in template


def test_missing_section_fails():
    assert "no '## AI help' section" in pr_ai_help.problems("## Summary\n\nCloses #1\n")[0]


def test_no_ai_help_passes():
    assert pr_ai_help.problems(_body("- [x] No AI help\n- [ ] AI helped")) == []


def test_both_ticked_fails():
    assert pr_ai_help.problems(_body("- [x] No AI help\n- [x] AI helped")) == ["Tick exactly one: 'No AI help' or 'AI helped'."]


def test_ai_helped_with_everything_passes():
    section = "- [ ] No AI help\n- [x] AI helped, and it passed all four gates:" + GATES_TICKED
    section += "\n**What the AI did** (leave blank if no AI help): Claude drafted the wording."
    assert pr_ai_help.problems(_body(section)) == []


def test_note_written_in_bold_label_style_passes():
    section = "- [x] AI helped" + GATES_TICKED + "\n**What the AI did:** Claude drafted the wording."
    assert pr_ai_help.problems(_body(section)) == []


def test_missing_gate_fails():
    section = "- [x] AI helped" + GATES_TICKED.replace("[x] **Output:**", "[ ] **Output:**") + "\n**What the AI did:** X."
    assert pr_ai_help.problems(_body(section)) == ["The Output gate is not ticked. Fix the work until you can tick it."]


def test_empty_note_fails():
    section = "- [x] AI helped" + GATES_TICKED + "\n**What the AI did** (leave blank if no AI help):\n"
    assert pr_ai_help.problems(_body(section)) == ["Say what the AI did: which tool, and which parts of the work."]


def test_ticks_in_html_comments_are_ignored():
    assert pr_ai_help.problems(_body("<!-- - [x] No AI help -->\n- [ ] No AI help\n- [ ] AI helped"))


# --- pr_reviewers ---------------------------------------------------------

pr_reviewers = _load("pr_reviewers")
REVIEWERS = pr_reviewers.load_table()


def test_reviewers_known_author():
    assert pr_reviewers.reviewers_for("hyenalouise", REVIEWERS) == ["maeveylain", "saraevcldn"]


def test_reviewers_unknown_author_gets_none():
    assert pr_reviewers.reviewers_for("someone-else", REVIEWERS) == []


def test_every_author_has_two_other_teammates_as_reviewers():
    team = set(REVIEWERS)
    for author, reviewers in REVIEWERS.items():
        assert len(reviewers) == 2 and len(set(reviewers)) == 2, author
        assert author not in reviewers, f"{author} reviews their own PRs"
        assert set(reviewers) <= team, f"{author} has a reviewer outside the team"


def test_review_load_is_balanced():
    load = {person: 0 for person in REVIEWERS}
    for reviewers in REVIEWERS.values():
        for r in reviewers:
            load[r] += 1
    assert set(load.values()) == {2}, load
