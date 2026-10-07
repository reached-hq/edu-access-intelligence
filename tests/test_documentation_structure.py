"""Keep the reorganized documentation navigable and free of retired paths."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


REQUIRED_READMES = [
    Path("analysis/README.md"),
    Path("analysis/profiling/README.md"),
    Path("analysis/cross_source/README.md"),
    Path("config/README.md"),
    Path("config/ingestion/README.md"),
    Path("config/mappings/README.md"),
    Path("docs/README.md"),
    Path("docs/business/README.md"),
    Path("docs/data/README.md"),
    Path("docs/data/source-inventory/README.md"),
    Path("docs/data/cross-source/README.md"),
    Path("docs/governance/README.md"),
    Path("docs/operations/README.md"),
    Path("evidence/README.md"),
    Path("src/README.md"),
    Path("tests/README.md"),
    Path("tests/data/README.md"),
    Path("tests/factories/README.md"),
]

RETIRED_PREFIXES = (
    "notebooks/",
    "tests/fixtures/",
    "docs/cross_source/",
    "docs/source_inventory/",
    "docs/stakeholder/",
    "docs/evidence/",
)


def markdown_files(repo_root: Path) -> list[Path]:
    return [
        path
        for path in repo_root.rglob("*.md")
        if not any(part in {".git", ".pytest_cache", ".venv", "local_state", "tmp"} for part in path.parts)
    ]


def test_required_readmes_exist(repo_root):
    missing = [str(path) for path in REQUIRED_READMES if not (repo_root / path).is_file()]
    assert not missing, f"missing repository indexes: {missing}"


def test_retired_paths_are_not_committable(repo_files):
    offenders = [
        str(path)
        for path in repo_files
        if any(path.as_posix().startswith(prefix) for prefix in RETIRED_PREFIXES)
    ]
    assert not offenders, f"move files out of retired repository paths: {offenders}"


def test_markdown_local_link_targets_exist(repo_root):
    broken = []
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    for path in markdown_files(repo_root):
        text = path.read_text(encoding="utf-8")
        for raw_target in pattern.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0])
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(repo_root)} -> {raw_target}")

    assert not broken, "broken local Markdown links:\n" + "\n".join(broken)
