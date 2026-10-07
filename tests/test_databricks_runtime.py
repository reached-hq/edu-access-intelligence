"""Databricks runs the job differently from a laptop; these tests imitate the differences.

- A spark_python_task's file is run with exec(compile(source, path, "exec")),
  so `__file__` is not defined, and it runs inside IPython, which reports even
  SystemExit(0) as a failed task.
- spark.sql() runs commands (CREATE, INSERT, MERGE) at once, but a SELECT only
  when its result is collected. The Bronze gate ends with a SELECT that raises
  on FAIL, so a store that never collects would make the gate a silent no-op.

No Spark is needed: a fake session records what was executed.
"""

import sys

import pytest

from src.ingestion.store import SparkStore

CLI = "src/ingestion/cli.py"

# Every job file, with a command that succeeds without a store and what it prints.
JOB_FILES = [
    (CLI, "ddl", "CREATE TABLE IF NOT EXISTS"),
]


def run_like_databricks(repo_root, argv, monkeypatch, cli=CLI):
    path = repo_root / cli
    monkeypatch.setattr(sys, "argv", [str(path), *argv])
    namespace = {"__name__": "__main__"}  # no __file__, no __package__
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("cli, command, prints", JOB_FILES)
def test_the_job_file_runs_without___file__(repo_root, monkeypatch, capsys, cli, command, prints):
    run_like_databricks(repo_root, [command, "--source", "deped_enrollment"], monkeypatch, cli)
    assert prints in capsys.readouterr().out


@pytest.mark.parametrize("cli, command, prints", JOB_FILES)
def test_success_does_not_raise_systemexit(repo_root, monkeypatch, capsys, cli, command, prints):
    """IPython on Databricks marks SystemExit(0) as a failed task."""
    run_like_databricks(repo_root, [command, "--source", "deped_enrollment"], monkeypatch, cli)  # must not raise


@pytest.mark.parametrize("cli, command, prints", JOB_FILES)
def test_failure_still_exits_nonzero(repo_root, monkeypatch, capsys, cli, command, prints):
    with pytest.raises(SystemExit) as e:
        run_like_databricks(repo_root, [command, "--source", "no_such_source"], monkeypatch, cli)
    assert e.value.code == 2


def test_every_job_file_is_imitated(repo_root):
    import yaml
    bundle = yaml.safe_load((repo_root / "databricks.yml").read_text(encoding="utf-8"))
    files = {t["spark_python_task"]["python_file"] for job in bundle["resources"]["jobs"].values()
             for t in job["tasks"] if "spark_python_task" in t}
    assert files == {cli for cli, _, _ in JOB_FILES}


class FakeFrame:
    def __init__(self, session, statement):
        self.session, self.statement = session, statement

    def collect(self):
        self.session.executed.append(self.statement)
        if "raise_error" in self.statement:
            raise RuntimeError("Bronze gate failed")
        return []


class FakeSpark:
    """Executes a statement only when collected, like a SELECT in real Spark."""

    def __init__(self):
        self.executed = []
        self.conf = type("Conf", (), {"set": lambda *a: None})()

    def sql(self, statement, args=None):
        return FakeFrame(self, statement)


def test_spark_store_executes_every_statement_it_is_given(tmp_path):
    gate = tmp_path / "90_validate_x.sql"
    gate.write_text("INSERT INTO t (a) SELECT 1;\nSELECT CASE WHEN 1 > 0 THEN raise_error('FAIL') END;\n")
    store = SparkStore(FakeSpark())
    with pytest.raises(RuntimeError, match="Bronze gate failed"):
        store.run_file(gate)
    assert len(store.spark.executed) == 2


def test_spark_store_query_runs_once(tmp_path):
    store = SparkStore(FakeSpark())
    store.query("SELECT 1")
    assert store.spark.executed == ["SELECT 1"]
