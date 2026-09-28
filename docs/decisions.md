# Decision log

Each entry records **problem → decision → reason → consequence**. A **provisional** decision names the point at which it will be revisited.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-001 | 2026-09-29 | Stakeholder needs come from published documents plus mentor validation | Accepted |
| D-002 | 2026-09-29 | Use the course deliverables as the baseline until a rubric exists | Provisional |
| D-003 | 2026-09-29 | Keep higher education in scope during discovery | Provisional |
| D-004 | 2026-09-29 | Follow the NYC Mobility repository conventions | Accepted |
| D-005 | 2026-09-29 | Branch from `main` with short-lived feature branches; no `dev` branch | Provisional |

---

## D-001: Where stakeholder needs come from

- **Problem:** The team has no direct access to DepEd or CHED planners. They are the audience for the presentation, not a source of interviews.
- **Decision:** Needs are drawn from published planning documents and checked with the program mentor. Every need is tagged **documented** (cited source), **mentor-validated**, or **assumed**.
- **Reason:** Planners in the audience will know their own policies, so unsupported needs are the easiest thing for them to challenge.
- **Consequence:** A candidate business question that rests mostly on **assumed** needs cannot be approved.

## D-002: No capstone rubric yet

- **Problem:** No official rubric or deadline has been published.
- **Decision:** Build to the course's deliverables: pipeline, model, validation, documentation, Git, a business dashboard, a DQ dashboard, and the Day 9 production practices.
- **Reason:** These are the most complete statement of expectations available today.
- **Consequence:** Scope may shift. **Revisit when the rubric is released.**

## D-003: Higher education stays in scope for now

- **Problem:** The theme mentions higher-education capacity. Higher education is CHED's mandate, not DepEd's.
- **Decision:** Keep it in scope during source discovery and profiling. The stakeholders are framed as education planners (DepEd and CHED).
- **Reason:** The theme's general question includes it.
- **Consequence:** More sources to profile, and a different grain (one row per institution rather than per school). **Revisit at the end of Phase 3:** keep it only if the profiled data supports it.

## D-004: Follow the NYC Mobility conventions

- **Problem:** The repository needs a structure the team can work in immediately.
- **Decision:** Reuse the NYC Mobility conventions: `etl/NN_layer/` with `90_validate_*` files, `config/` for non-secret settings, the same documentation set, the same PR and issue templates, and the same CI/CD approach.
- **Reason:** The team has already built and defended this structure. A familiar convention is lower risk than a new one.
- **Consequence:** Folders are created only when their phase starts. The capstone adds `docs/source_inventory/`, `docs/profiling/`, `docs/stakeholder/`, and `docs/limitations.md`.

## D-005: Branching model

- **Problem:** NYC Mobility used `main` plus a `dev` branch.
- **Decision:** Use `main` plus short-lived feature branches. `dev` and `prod` exist as Databricks deploy targets, not as branches.
- **Reason:** Separate deploy targets already isolate environments, so a long-lived `dev` branch mostly adds merge overhead.
- **Consequence:** CI runs on PRs into `main`. **Provisional:** the team has not yet confirmed this.
