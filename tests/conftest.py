import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def repo_files():
    """Files git would commit: tracked plus untracked-but-not-ignored.

    Checking this set (rather than only tracked files) catches a data file or
    secret before it is committed, not after.
    """
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"git ls-files failed; run the tests inside the git repo.\n{result.stderr}")
    return [Path(line) for line in result.stdout.splitlines() if line]
