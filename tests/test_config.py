"""config/sources.json is the source registry; keep it valid as it grows."""

import json
import re

import pytest

REQUIRED_FIELDS = {"source_id", "name", "publisher", "status"}
STATUSES = {"candidate", "acquired", "inventoried", "profiled", "accepted", "rejected"}
SOURCE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@pytest.fixture(scope="module")
def registry(repo_root):
    return json.loads((repo_root / "config" / "sources.json").read_text())


def test_registry_shape(registry):
    assert isinstance(registry.get("registry_status"), str)
    assert isinstance(registry.get("sources"), list)


def test_sources_have_required_fields(registry):
    problems = []
    for i, source in enumerate(registry["sources"]):
        missing = REQUIRED_FIELDS - source.keys()
        if missing:
            problems.append(f"sources[{i}] is missing {sorted(missing)}")
        if source.get("status") not in STATUSES:
            problems.append(
                f"sources[{i}] status {source.get('status')!r} is not one of {sorted(STATUSES)}"
            )
    assert not problems, problems


def test_source_ids_are_unique_snake_case(registry):
    ids = [s.get("source_id", "") for s in registry["sources"]]
    bad = [i for i in ids if not SOURCE_ID.match(i)]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not bad, f"source_id must be snake_case: {bad}"
    assert not dupes, f"duplicate source_id: {dupes}"


def test_sources_past_candidate_have_an_inventory_card(repo_root, registry):
    inventory = repo_root / "docs" / "data" / "source-inventory"
    missing = [
        s["source_id"] for s in registry["sources"]
        if s.get("status") not in (None, "candidate")
        and not (inventory / s.get("source_id", "") / "README.md").is_file()
    ]
    assert not missing, (
        f"Sources beyond 'candidate' need docs/data/source-inventory/<source_id>/README.md: {missing}"
    )


def test_profiled_sources_have_a_profile(repo_root, registry):
    inventory = repo_root / "docs" / "data" / "source-inventory"
    missing = [
        s["source_id"] for s in registry["sources"]
        if s.get("status") in ("profiled", "accepted")
        and not (inventory / s.get("source_id", "") / "profile.md").is_file()
    ]
    assert not missing, (
        f"Profiled or accepted sources need docs/data/source-inventory/<source_id>/profile.md: {missing}"
    )


def test_profiled_sources_have_a_data_dictionary(repo_root, registry):
    inventory = repo_root / "docs" / "data" / "source-inventory"
    missing = [
        s["source_id"] for s in registry["sources"]
        if s.get("status") in ("profiled", "accepted")
        and not (inventory / s.get("source_id", "") / "data_dictionary.md").is_file()
    ]
    assert not missing, (
        f"Profiled or accepted sources need docs/data/source-inventory/<source_id>/data_dictionary.md: {missing}"
    )
