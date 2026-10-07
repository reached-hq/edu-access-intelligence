"""Repository rules from CONTRIBUTING.md that a test can enforce."""

import re
from pathlib import Path

# Data belongs in the agreed storage, never in git. Small static, made-up
# samples under tests/data/ are the only exception. Test factories are code and
# create their files in pytest-provided temporary directories.
DATA_EXTENSIONS = {
    ".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".avro", ".orc",
    ".duckdb", ".db", ".sqlite", ".zip", ".gz",
    ".shp", ".shx", ".dbf", ".geojson", ".gpkg",
}
TEST_DATA_DIR = Path("tests/data")

MAX_FILE_BYTES = 1_000_000

SECRET_PATTERNS = {
    "Databricks personal access token": re.compile(r"dapi[0-9a-f]{32}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "AWS access key id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def _is_test_data(path):
    return TEST_DATA_DIR in path.parents


def test_no_data_files_outside_test_data(repo_files):
    offenders = [
        str(p) for p in repo_files
        if p.suffix.lower() in DATA_EXTENSIONS and not _is_test_data(p)
    ]
    assert not offenders, (
        "Data files must not be committed; keep them in the agreed storage "
        f"(or use a small made-up sample under {TEST_DATA_DIR}/): {offenders}"
    )


def test_no_committed_notebooks(repo_files):
    offenders = [str(p) for p in repo_files if p.suffix == ".ipynb"]
    assert not offenders, (
        f"Keep reproducible analysis in analysis/ as .py files, not .ipynb: {offenders}"
    )


def test_no_env_files(repo_files):
    offenders = [
        str(p) for p in repo_files
        if (p.name == ".env" or p.name.startswith(".env.")) and p.name != ".env.example"
    ]
    assert not offenders, f"Local .env files must not be committed: {offenders}"


def test_no_oversized_files(repo_root, repo_files):
    offenders = [
        f"{p} ({(repo_root / p).stat().st_size:,} bytes)"
        for p in repo_files
        if (repo_root / p).is_file() and (repo_root / p).stat().st_size > MAX_FILE_BYTES
    ]
    assert not offenders, (
        f"Files over {MAX_FILE_BYTES:,} bytes usually mean data slipped in: {offenders}"
    )


def test_no_secrets(repo_root, repo_files):
    findings = []
    for p in repo_files:
        path = repo_root / p
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{p}: looks like a {label}")
    assert not findings, (
        "Possible secrets found. Remove them and rotate the credential: "
        f"{findings}"
    )
