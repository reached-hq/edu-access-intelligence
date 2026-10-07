# Education Access Intelligence

A data engineering capstone by **ReachED** for the FTW Data Engineering program.

**Working theme:** Where are the largest gaps in education access and capacity in the Philippines, and which provinces or municipalities should be prioritized for additional schools, classrooms, teachers, or higher-education capacity?

**Stakeholders:** education planners (DepEd for basic education, CHED for higher education).

> **Status: milestone 01 (Discover), moving into 02 (Land).**
> DepEd enrollment and facilities are profiled; PSGC, CHED, and PSA poverty are in review.
> There is no approved business question yet, so nothing in this repository should be read as a finding.

## How this project works

The business question comes from two kinds of evidence, collected before any modeling:

1. What education planners need to decide (`docs/business/`)
2. What the available datasets can validly support (`docs/data/source-inventory/`, `docs/data/cross-source/`)

Data then moves through the course's layered architecture:

```
SOURCE → BRONZE → SILVER → INTEGRATION → GOLD → ANALYTICS → DASHBOARD
```

See [docs/architecture/overview.md](docs/architecture/overview.md) and [docs/governance/decisions.md](docs/governance/decisions.md).

## Repository layout

Every folder exists from the start (see [File naming and layout](docs/architecture/overview.md#file-naming-and-layout)). Until its phase begins, a folder holds only a short `README.md` saying what will go there.

| Path | Purpose | Filled in |
|---|---|---|
| `config/` | Non-secret configuration, source registry, naming rules, and ETL table registry | Phase 1 |
| `docs/` | Architecture, decisions, source inventory, and the rest of the engineering docs | Phase 1 |
| `tests/` | Repository policy and configuration tests, run by CI | Phase 1 |
| `tests/factories/` | Python builders for deterministic, made-up test deliveries | Phase 2 |
| `tests/data/` | Small, static, made-up test files; the only place data files may be committed | When a test needs one |
| `.github/` | PR and issue templates, CI and triage workflows | Phase 1 |
| `docs/data/source-inventory/`, `docs/data/cross-source/`, `docs/business/` | One folder per source; work that compares sources; planner needs and the business question | Phase 1 |
| `analysis/profiling/`, `analysis/cross_source/` | Reproducible source profiling, dictionary generation, and cross-source research | Phases 1–3 |
| `src/ingestion/`, `src/profiling/` | Production ingestion code and reusable profiling helpers | Phases 2–3 |
| `etl/01_control` … `etl/06_analytics` | SQL per pipeline stage, each with `90_validate_*` checks | Phase 6 onward |
| `evidence/` | Pipeline runs, source validation, and reconciliation evidence | As stages are verified |
| `dashboards/` | Exported Databricks dashboards | Phase 9 onward |
| `databricks.yml` | Databricks Asset Bundle: job and dashboards | Phase 6 |

## Setup

Follow [docs/getting-started/terminal-setup.md](docs/getting-started/terminal-setup.md) once per laptop, then [docs/operations/workflow.md](docs/operations/workflow.md) for day-to-day work, including where code runs to save Databricks compute.

## Running the checks locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

CI runs the same checks on every pull request.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [documentation index](docs/README.md).
Final Bronze and Silver names are in the [ETL table registry](docs/standards/tables.md).
