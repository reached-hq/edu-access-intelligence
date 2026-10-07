"""Run the Databricks job's tasks locally, in order, on DuckDB.

    python -m src.job.local_run
    RAW_DATA_DIR=~/Projects/reached-hq/raw-data python -m src.job.local_run --db local_state/edu_access.duckdb

databricks.yml is the one definition of the job. This reads it and runs each
task the way Databricks would, on the local store instead (D-008, D-017):

- a spark_python_task runs the same command line, through the module's main(),
  with --backend duckdb, the local database, the local landing folder, and
  environment local;
- a sql_task runs its SQL file through DuckDBStore, with the job parameters
  bound as :name parameters, as Databricks binds them to a SQL file task.

Tasks run one at a time in dependency order, and run_if is honoured:
ALL_SUCCESS runs only when every dependency succeeded, ALL_DONE whatever they
ended as. What this cannot show is listed in docs/operations/ingestion.md
(what only the Databricks run can prove).
"""

import argparse
import importlib
import inspect
import os
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(inspect.currentframe().f_code.co_filename).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from src.ingestion.revision import resolve_code_revision
from src.ingestion.store import DuckDBStore

DEFAULT_DB = REPO_ROOT / "local_state" / "edu_access.duckdb"
LOCAL_VALUES = {"--backend": "duckdb", "--environment": "local"}


@dataclass
class TaskResult:
    task_key: str
    kind: str          # python | sql
    status: str        # succeeded | failed | upstream_failed
    seconds: float = 0.0
    detail: str = ""


def load_job(repo_root, job_key=None):
    bundle = yaml.safe_load((Path(repo_root) / "databricks.yml").read_text(encoding="utf-8"))
    jobs = bundle["resources"]["jobs"]
    if job_key is None:
        if len(jobs) != 1:
            raise SystemExit(f"databricks.yml defines {sorted(jobs)}; choose one with --job.")
        job_key = next(iter(jobs))
    return job_key, jobs[job_key]


def in_order(tasks):
    """Dependencies first, otherwise in the order databricks.yml lists them."""
    done, ordered, pending = set(), [], list(tasks)
    while pending:
        ready = [t for t in pending if all(d["task_key"] in done for d in t.get("depends_on", []))]
        if not ready:
            raise SystemExit(f"tasks with missing or circular dependencies: {[t['task_key'] for t in pending]}")
        task = ready[0]
        ordered.append(task)
        done.add(task["task_key"])
        pending.remove(task)
    return ordered


def job_parameters(job, code_revision, run_id):
    """The job's parameters as the run would resolve them, with local values for the deploy-time ones."""
    values = {}
    for p in job.get("parameters", []):
        default = str(p.get("default", ""))
        if default == "${bundle.git.commit}":
            values[p["name"]] = code_revision
        elif default == "{{job.run_id}}":
            values[p["name"]] = run_id
        elif default == "${bundle.target}":
            values[p["name"]] = "local"
        else:
            values[p["name"]] = default
    return values


def python_argv(task, landing, db, params):
    args = []
    given = list(task["spark_python_task"].get("parameters", []))
    i = 0
    while i < len(given):
        flag = given[i]
        if flag in LOCAL_VALUES or flag in ("--landing", "--code-revision") and i + 1 < len(given):
            value = {"--landing": str(landing), "--code-revision": params.get("code_revision")}.get(flag, LOCAL_VALUES.get(flag))
            args += [flag, value]
            i += 2
            continue
        args.append(flag)
        i += 1
    return args + ["--db", str(db)]


def run_python(task, repo_root, landing, db, params):
    path = task["spark_python_task"]["python_file"]
    module = importlib.import_module(path[:-3].replace("/", "."))
    previous = module.REPO_ROOT
    module.REPO_ROOT = Path(repo_root)  # the repository whose contracts and SQL the task should use
    try:
        code = module.main(python_argv(task, landing, db, params))
    finally:
        module.REPO_ROOT = previous
    return ("succeeded", "") if code == 0 else ("failed", f"exit code {code}")


def run_sql(task, repo_root, db, params):
    path = Path(repo_root) / task["sql_task"]["file"]["path"]
    store = DuckDBStore(db)
    try:
        store.run_file(path, params)
    except Exception as e:  # a gate's raise_error fails the task, as on Databricks
        return "failed", str(e).splitlines()[0][:300]
    finally:
        store.close()
    return "succeeded", ""


def run_job(repo_root, landing, db, code_revision, job_key=None, run_id=None, log=print):
    job_key, job = load_job(repo_root, job_key)
    run_id = run_id or str(uuid.uuid4())
    params = job_parameters(job, code_revision, run_id)
    log(f"job {job_key}  run_id={run_id}  code_revision={code_revision}")
    results = {}
    for task in in_order(job["tasks"]):
        key, kind = task["task_key"], "sql" if "sql_task" in task else "python"
        deps = [results[d["task_key"]].status for d in task.get("depends_on", [])]
        if task.get("run_if", "ALL_SUCCESS") == "ALL_SUCCESS" and any(s != "succeeded" for s in deps):
            results[key] = TaskResult(key, kind, "upstream_failed")
        else:
            started = time.monotonic()
            if kind == "sql":
                status, detail = run_sql(task, repo_root, db, params)
            else:
                status, detail = run_python(task, repo_root, landing, db, params)
            results[key] = TaskResult(key, kind, status, round(time.monotonic() - started, 3), detail)
        r = results[key]
        log(f"  {key:40} {kind:6} {r.status:16} {r.seconds:>7.2f}s  {r.detail}")
    return list(results.values())


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m src.job.local_run", description=__doc__.split("\n\n")[0])
    parser.add_argument("--job", help="job key in databricks.yml (default: the only one)")
    parser.add_argument("--landing", help="raw data root holding the publisher folders (default: RAW_DATA_DIR)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--code-revision", help="default: the local git commit, -dirty if uncommitted")
    args = parser.parse_args(argv)
    landing = args.landing or os.environ.get("RAW_DATA_DIR")
    if not landing:
        print("error: set --landing or RAW_DATA_DIR to the raw data root.", file=sys.stderr)
        return 3
    revision = resolve_code_revision(REPO_ROOT, args.code_revision)
    results = run_job(REPO_ROOT, Path(landing).expanduser(), args.db, revision, args.job)
    failed = [r.task_key for r in results if r.status != "succeeded"]
    print(f"status: {'failed: ' + ', '.join(failed) if failed else 'succeeded'}")
    return 1 if failed else 0


if __name__ == "__main__":
    exit_code = main()
    if exit_code:
        sys.exit(exit_code)
