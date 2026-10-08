"""databricks.yml and the Bronze gates must keep every output traceable to its commit.

The lineage path is: the deploy resolves ${bundle.git.commit} into both the job's
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


def test_each_load_records_the_job_run_its_gate_uses(jobs):
    """The Bronze gate task writes data_quality_results under :run_id; the load stores the same
    value as job_run_id, or the two cannot be joined (D-020)."""
    for name, job in jobs.items():
        parameters = {p["name"]: p["default"] for p in job.get("parameters", [])}
        assert parameters.get("run_id") == "{{job.run_id}}"
        for task in job["tasks"]:
            if task.get("spark_python_task", {}).get("python_file") == "src/ingestion/cli.py":
                assert argument(task, "--job-run-id") == "{{job.parameters.run_id}}", (
                    f"{name}/{task['task_key']} does not record the job run its gate uses")


def test_python_tasks_read_their_file_from_git(jobs):
    """Without source: GIT the jobs API rejects a repository-relative python_file (seen on deploy, 2026-10-06)."""
    for name, task in python_tasks(jobs):
        assert task["spark_python_task"].get("source") == "GIT", f"{name}/{task['task_key']} needs source: GIT"


def test_tasks_load_sources_that_have_a_contract(jobs, repo_root, project):
    for name, task in python_tasks(jobs):
        if task["spark_python_task"]["python_file"] != "src/ingestion/cli.py":
            continue
        source = argument(task, "--source")
        contract = repo_root / "config" / "ingestion" / f"{source}.json"
        assert contract.is_file() or task.get("disabled") is True, f"{source} has no contract and must be disabled"
        assert argument(task, "--landing") == project["raw_volume_path"]
        assert argument(task, "--backend") == "spark"


def sql_tasks(jobs):
    for job_name, job in jobs.items():
        for task in job["tasks"]:
            if "sql_task" in task:
                yield job_name, task


def test_control_bootstrap_is_the_only_root(jobs):
    """Control objects are initialized once before the source lanes fan out."""
    for name, job in jobs.items():
        roots = [task["task_key"] for task in job["tasks"] if not task.get("depends_on")]
        assert roots == ["01_create_pipeline_runs"], f"{name}: unexpected roots {roots}"


def test_source_lanes_fan_out_after_control_bootstrap(jobs, repo_root):
    """Each load depends on its own raw DDL, never on another source lane."""
    registry = yaml.safe_load((repo_root / "config" / "tables.yml").read_text(encoding="utf-8"))
    tables = {entry["source_id"]: entry["bronze"]["table"] for entry in registry["source_tables"]}
    for name, job in jobs.items():
        tasks = {task["task_key"]: task for task in job["tasks"]}
        loads = [task for task in job["tasks"] if "spark_python_task" in task]
        assert loads, f"{name} has no source loads"
        for load in loads:
            source = argument(load, "--source")
            ddl_path = f"etl/02_bronze/{next(p.name for p in (repo_root / 'etl' / '02_bronze').glob('*_create_*.sql') if p.name.endswith(f'_create_{tables[source]}.sql'))}"
            ddl = next(task for task in job["tasks"] if task.get("sql_task", {}).get("file", {}).get("path") == ddl_path)
            assert load.get("depends_on") == [{"task_key": ddl["task_key"]}]
            assert ddl.get("depends_on") == [{"task_key": "05_create_current_batches"}]
            assert load.get("run_if") == "ALL_SUCCESS"
            assert ddl.get("run_if") == "ALL_SUCCESS"


def test_non_source_tasks_declare_dependencies(jobs):
    """After the control root, every setup, load, transform, and check names its upstream task."""
    for name, job in jobs.items():
        for task in job["tasks"]:
            if task["task_key"] != "01_create_pipeline_runs":
                assert task.get("depends_on"), f"{name}/{task['task_key']} has no dependency"


def test_parallel_stages_fan_in_only_at_the_next_stage(jobs):
    tasks = {task["task_key"]: task for task in jobs["edu_access_pipeline"]["tasks"]}

    expected_maps = {
        "01_map_deped_school_psgc": {
            "90_validate_control", "90_validate_deped_enrollment_clean", "90_validate_deped_facilities_clean",
            "90_validate_deped_personnel_clean", "90_validate_psa_psgc_clean",
        },
        "02_map_psa_poverty_psgc": {
            "90_validate_control", "90_validate_psa_poverty_stat_clean", "90_validate_psa_psgc_clean",
        },
        "03_map_hdx_adm3_psgc": {
            "90_validate_control", "90_validate_hdx_adm3_clean", "90_validate_psa_psgc_clean",
        },
    }
    for key, expected in expected_maps.items():
        assert {d["task_key"] for d in tasks[key]["depends_on"]} == expected

    integration_gate = {"90_validate_education_geography_integrated"}
    for key in ("01_placeholder_dim_geography", "02_placeholder_dim_school"):
        assert {d["task_key"] for d in tasks[key]["depends_on"]} == integration_gate

    dimension_gates = {"90_placeholder_validate_dim_geography", "90_placeholder_validate_dim_school"}
    for key in ("10_placeholder_fact_school_year", "20_placeholder_fact_poverty_estimate"):
        assert {d["task_key"] for d in tasks[key]["depends_on"]} == dimension_gates

    fact_gates = {"90_placeholder_validate_fact_school_year", "90_placeholder_validate_fact_poverty_estimate"}
    for key in ("01_answer_ap1", "02_answer_ap2", "03_answer_ap3", "04_answer_ap4"):
        assert {d["task_key"] for d in tasks[key]["depends_on"]} == fact_gates


def test_a_load_that_skips_its_gate_is_followed_by_it(jobs, repo_root):
    """`ingest --no-gate` leaves the Bronze gate to the next task; that task must be the gate
    of the same source, and run only if the load succeeded. No source loads unchecked."""
    for name, job in jobs.items():
        tasks = job["tasks"]
        for i, task in enumerate(tasks):
            if "spark_python_task" not in task or "--no-gate" not in task["spark_python_task"]["parameters"]:
                continue
            source = argument(task, "--source")
            registry = yaml.safe_load((repo_root / "config" / "tables.yml").read_text(encoding="utf-8"))
            table = next(entry["bronze"]["table"] for entry in registry["source_tables"]
                         if entry["source_id"] == source)
            gate = tasks[i + 1] if i + 1 < len(tasks) else {}
            assert gate.get("sql_task", {}).get("file", {}).get("path") == f"etl/02_bronze/90_validate_{table}.sql", (
                f"{name}/{task['task_key']} skips its gate, so the next task must run 90_validate_{table}.sql")
            assert gate.get("run_if") == "ALL_SUCCESS"


def test_job_loads_leave_table_setup_to_explicit_sql_tasks(jobs):
    for name, task in python_tasks(jobs):
        assert "--no-setup" in task["spark_python_task"]["parameters"], (
            f"{name}/{task['task_key']} would repeat shared DDL inside a parallel source load")


def test_placeholder_tasks_are_disabled(jobs, repo_root):
    for name, task in sql_tasks(jobs):
        path = repo_root / task["sql_task"]["file"]["path"]
        if path.read_text(encoding="utf-8").lstrip().startswith("-- PLACEHOLDER:"):
            assert task.get("disabled") is True, f"{name}/{task['task_key']} runs placeholder SQL"


def test_sql_tasks_run_committed_files_on_the_warehouse(jobs, repo_root):
    tasks = list(sql_tasks(jobs))
    assert tasks, "no SQL task found"
    for name, task in tasks:
        sql = task["sql_task"]
        assert sql["file"]["source"] == "GIT", f"{name}/{task['task_key']} must read its file from the commit"
        assert (repo_root / sql["file"]["path"]).is_file(), f"{name}/{task['task_key']}: {sql['file']['path']} missing"
        assert sql["warehouse_id"] == "${var.warehouse_id}", f"{name}/{task['task_key']} must use the warehouse variable"


def test_sql_tasks_share_the_run_id(jobs):
    """A gate's results carry :run_id, and its last statement fails on a FAIL recorded under it."""
    for name, job in jobs.items():
        parameters = {p["name"]: p["default"] for p in job.get("parameters", [])}
        assert parameters.get("run_id") == "{{job.run_id}}", f"{name}: job parameter run_id must be {{{{job.run_id}}}}"


def test_every_contract_has_a_task(jobs, repo_root):
    sources = {argument(t, "--source") for _, t in python_tasks(jobs)
               if t["spark_python_task"]["python_file"] == "src/ingestion/cli.py"}
    contracts = {p.stem for p in (repo_root / "config" / "ingestion").glob("*.json")}
    assert contracts <= sources, f"contracts with no job task: {sorted(contracts - sources)}"


def test_no_schedules_during_development(jobs):
    for name, job in jobs.items():
        assert "schedule" not in job and "trigger" not in job and "continuous" not in job, (
            f"{name}: no schedules during development (docs/operations/workflow.md, Part 5)")


def test_one_run_at_a_time(jobs):
    for name, job in jobs.items():
        assert job.get("max_concurrent_runs") == 1, f"{name}: two concurrent runs could both load one batch"


def test_the_job_is_named_for_the_whole_pipeline(jobs):
    assert list(jobs) == ["edu_access_pipeline"]
    assert jobs["edu_access_pipeline"]["name"] == "edu_access_pipeline"


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


def test_delivered_sources_are_not_disabled(jobs, repo_root):
    """A source with a contract and real Bronze SQL already runs on main; disabling its
    create, load or gate task would quietly stop a delivered source."""
    registry = yaml.safe_load((repo_root / "config" / "tables.yml").read_text(encoding="utf-8"))
    for entry in registry["source_tables"]:
        source, bronze = entry["source_id"], entry["bronze"]
        ddl = repo_root / "etl" / "02_bronze" / bronze["create_file"]
        if not (repo_root / "config" / "ingestion" / f"{source}.json").is_file():
            continue
        if ddl.read_text(encoding="utf-8").lstrip().startswith("-- PLACEHOLDER:"):
            continue
        for name, job in jobs.items():
            lane = [task for task in job["tasks"]
                    if task.get("sql_task", {}).get("file", {}).get("path") in (
                        f"etl/02_bronze/{bronze['create_file']}", f"etl/02_bronze/90_validate_{bronze['table']}.sql")
                    or ("spark_python_task" in task and argument(task, "--source") == source)]
            assert len(lane) == 3, f"{name}: {source} should have a create, load and gate task, found {len(lane)}"
            for task in lane:
                assert task.get("disabled") is not True, f"{name}/{task['task_key']} disables delivered source {source}"
