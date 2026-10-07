"""databricks.yml and the Bronze gates must keep every output traceable to its commit.

The chain is: the deploy resolves ${bundle.git.commit} into both the job's
git_source (the code that runs) and its code_revision parameter (the value
recorded); each task passes the parameter on; each gate stamps it on its rows.
A break anywhere leaves rows that name the wrong commit, or none, and nobody
notices until a number is questioned. These tests fail at the pull request
instead.
"""

import json
import re

import pytest
import yaml

from src.ingestion.store import split_statements

COMMIT = "${bundle.git.commit}"
PARAMETER = "{{job.parameters.code_revision}}"


@pytest.fixture(scope="module")
def bundle(repo_root):
    return yaml.safe_load((repo_root / "databricks.yml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def jobs(bundle):
    return bundle["resources"]["jobs"]


@pytest.fixture(scope="module")
def project(repo_root):
    return json.loads((repo_root / "config" / "project.json").read_text(encoding="utf-8"))


def python_tasks(jobs):
    for job_name, job in jobs.items():
        for task in job["tasks"]:
            if "spark_python_task" in task:
                yield job_name, task


def argument(task, flag):
    args = task["spark_python_task"]["parameters"]
    return args[args.index(flag) + 1] if flag in args else None


def gates(repo_root):
    return sorted(repo_root.glob("etl/*/90_validate_*.sql"))


def test_the_job_and_gates_were_found(jobs, repo_root):
    """Guards the lookups: empty lists would make every test below vacuous."""
    assert list(python_tasks(jobs))
    assert gates(repo_root)


def test_each_job_records_the_deployed_commit(jobs):
    for name, job in jobs.items():
        parameters = {p["name"]: p["default"] for p in job.get("parameters", [])}
        assert parameters.get("code_revision") == COMMIT, (
            f"{name}: job parameter code_revision must default to {COMMIT}, or runs record the wrong commit")


def test_each_job_runs_the_commit_it_records(jobs):
    for name, job in jobs.items():
        source = job.get("git_source", {})
        assert "git_branch" not in source, (
            f"{name}: git_branch is resolved at run time, so the job could run newer code than it records")
        assert source.get("git_commit") == COMMIT, f"{name}: git_source.git_commit must be {COMMIT}"


def test_each_task_passes_the_revision_and_target_on(jobs):
    for name, task in python_tasks(jobs):
        assert argument(task, "--code-revision") == PARAMETER, f"{name}/{task['task_key']} does not pass code_revision"
        assert argument(task, "--environment") == "${bundle.target}", (
            f"{name}/{task['task_key']} must record the deploy target as its environment")


def test_python_tasks_read_their_file_from_git(jobs):
    """Without source: GIT the jobs API rejects a repository-relative python_file (seen on deploy, 2026-10-06)."""
    for name, task in python_tasks(jobs):
        assert task["spark_python_task"].get("source") == "GIT", f"{name}/{task['task_key']} needs source: GIT"


def test_tasks_load_sources_that_have_a_contract(jobs, repo_root, project):
    for name, task in python_tasks(jobs):
        if task["spark_python_task"]["python_file"] != "src/ingestion/cli.py":
            continue
        source = argument(task, "--source")
        assert (repo_root / "config" / "ingestion" / f"{source}.json").is_file(), f"{source} has no contract"
        assert argument(task, "--landing") == project["raw_volume_path"]
        assert argument(task, "--backend") == "spark"


def test_source_tasks_run_one_after_another(jobs):
    """Parallel tasks would compete for Free Edition's serverless capacity, and one
    source's failure must not stop the next (run_if: ALL_DONE)."""
    for name, job in jobs.items():
        tasks = [t for _, t in python_tasks({name: job})]
        for previous, task in zip(tasks, tasks[1:]):
            assert [d["task_key"] for d in task.get("depends_on", [])] == [previous["task_key"]], (
                f"{name}/{task['task_key']} must depend on {previous['task_key']} only")
            assert task.get("run_if") == "ALL_DONE", f"{name}/{task['task_key']} must run even if the previous source failed"


def test_every_contract_has_a_task(jobs, repo_root):
    sources = {argument(t, "--source") for _, t in python_tasks(jobs)}
    contracts = {p.stem for p in (repo_root / "config" / "ingestion").glob("*.json")}
    assert contracts <= sources, f"contracts with no job task: {sorted(contracts - sources)}"


def test_no_schedules_during_development(jobs):
    for name, job in jobs.items():
        assert "schedule" not in job and "trigger" not in job and "continuous" not in job, (
            f"{name}: no schedules during development (docs/workflow.md, Part 5)")


def test_one_run_at_a_time(jobs):
    for name, job in jobs.items():
        assert job.get("max_concurrent_runs") == 1, f"{name}: two concurrent runs could both load one batch"


def test_dev_target_names_the_project_workspace(bundle, project):
    dev = bundle["targets"]["dev"]
    assert dev["mode"] == "development"
    assert dev["workspace"]["host"] == project["workspace_host"]


def test_every_gate_result_stamps_the_revision_from_the_parameter(repo_root):
    """Checked per INSERT: one check out of several with a literal revision is enough to break lineage."""
    inserts = 0
    for path in gates(repo_root):
        for statement in split_statements(path.read_text(encoding="utf-8")):
            if not re.match(r"INSERT\s+INTO\s+\S*data_quality_results\b", statement, re.IGNORECASE):
                continue
            inserts += 1
            values = statement[statement.index(")") + 1:]  # after the column list
            assert ":code_revision" in values, f"{path.name}: a result does not read :code_revision"
            assert ":run_id" in values, f"{path.name}: a result does not read :run_id"
            assert "'UNSET'" not in values, f"{path.name} writes the sentinel instead of the parameter"
    assert inserts, "no gate writes to data_quality_results"


def test_gate_inserts_name_their_columns(repo_root):
    """A positional INSERT would put values in the wrong columns if a table's columns are ever reordered."""
    for path in sorted(repo_root.glob("etl/*/*.sql")):
        for statement in split_statements(path.read_text(encoding="utf-8")):
            match = re.match(r"INSERT\s+INTO\s+\S+\s*(\()?", statement, re.IGNORECASE)
            if match:
                assert match.group(1), f"{path.name}: INSERT must list its columns"
                head = statement[match.end():statement.index(")", match.end())]
                names = [c.strip() for c in head.split(",")]
                assert all(re.fullmatch(r"`?\w+`?", c) for c in names), f"{path.name}: column list holds {names}"


CREATES = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?(TABLE|VIEW|SCHEMA)\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)", re.IGNORECASE)
OWNS = re.compile(r"ALTER\s+(TABLE|VIEW|SCHEMA)\s+(\S+)\s+OWNER\s+TO\s+`([^`]+)`", re.IGNORECASE)


def test_every_created_object_is_owned_by_the_team_group(repo_root, project):
    """Unity Catalog makes the creator the owner, and a dev job runs as its deployer: without
    these statements only one person could read or load the tables (found on the first
    Databricks run, 2026-10-06). D-009: objects belong to the group."""
    created = 0
    for path in sorted(repo_root.glob("etl/*/*.sql")):
        statements = split_statements(path.read_text(encoding="utf-8"))
        owned = {(kind.upper(), name): group for s in statements for kind, name, group in OWNS.findall(s)}
        for s in statements:
            match = CREATES.match(s)
            if not match:
                continue
            created += 1
            key = (match.group(1).upper(), match.group(2))
            assert owned.get(key) == project["owner_group"], f"{path.name}: {key} is not handed to {project['owner_group']}"
    assert created, "no CREATE statements found"


def test_bronze_ddl_uses_the_project_group(project):
    from src.ingestion.bronze import OWNER_GROUP
    assert OWNER_GROUP == project["owner_group"]
