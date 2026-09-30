# Education Access Intelligence

A data engineering capstone by **ReachED** for the FTW Data Engineering program.

**Working theme:** Where are the largest gaps in education access and capacity in the Philippines, and which provinces or municipalities should be prioritized for additional schools, classrooms, teachers, or higher-education capacity?

**Stakeholders:** education planners (DepEd for basic education, CHED for higher education).

> **Status: Phase 1: repository and environment discovery.**
> There is no approved business question yet. No dataset has been inspected yet.
> Nothing in this repository should be read as a finding.

## How this project works

The business question comes from two kinds of evidence, collected before any modeling:

1. What education planners need to decide (`docs/stakeholder/`)
2. What the available datasets can validly support (`docs/source_inventory/`, `docs/cross_source/`)

Data then moves through the course's layered architecture:

```
SOURCE → BRONZE → SILVER → INTEGRATION → GOLD → ANALYTICS → DASHBOARD
```

See [docs/architecture.md](docs/architecture.md) and [docs/decisions.md](docs/decisions.md).

## Repository layout

Folders are added when their phase starts, not before.

| Path | Purpose | Added in |
|---|---|---|
| `config/` | Non-secret configuration and the source registry | Phase 1 |
| `docs/` | Architecture, decisions, source inventory, and the rest of the engineering docs | Phase 1 |
| `tests/` | Repository policy and configuration tests, run by CI | Phase 1 |
| `.github/` | PR and issue templates, CI workflow | Phase 1 |
| `src/ingestion/`, `src/profiling/` | Download, land, and profile sources | Phases 2–3 |
| `notebooks/` | Profiling and exploration (`.py` source format only) | Phase 3 |
| `etl/01_control` … `etl/06_analytics` | SQL per pipeline stage, each with `90_validate_*` checks | Phase 6 onward |
| `dashboards/` | Exported Databricks dashboards | Phase 9 onward |
| `databricks.yml` | Databricks Asset Bundle: job and dashboards | Phase 6 |

## Setup

Follow [docs/terminal_setup.md](docs/terminal_setup.md) once per laptop, then [docs/workflow.md](docs/workflow.md) for day-to-day work, including where code runs to save Databricks compute.

## Running the checks locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

CI runs the same checks on every pull request.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
