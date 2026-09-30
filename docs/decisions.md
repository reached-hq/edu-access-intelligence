# Decision log

Each entry records **problem → decision → reason → consequence**. A **provisional** decision names the point at which it will be revisited.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-001 | 2026-09-29 | Stakeholder needs come from published documents plus mentor validation | Accepted |
| D-002 | 2026-09-29 | Use the course deliverables as the baseline until a rubric exists | Provisional |
| D-003 | 2026-09-29 | Keep higher education in scope during discovery | Provisional |
| D-004 | 2026-09-29 | Follow the NYC Mobility repository conventions | Accepted |
| D-005 | 2026-09-29 | Branch from `main` with short-lived feature branches; no `dev` branch | Provisional |
| D-006 | 2026-09-29 | One documentation folder per source; publisher documents stay with raw data | Accepted |
| D-007 | 2026-09-29 | Profile sources locally with DuckDB, in scripts saved under `notebooks/profiling/` | Accepted |
| D-008 | 2026-09-29 | Develop locally; use Databricks compute only for planned runs | Accepted |
| D-009 | 2026-09-29 | Catalog `edu_access` owned by the team group; raw files in a managed volume | Provisional |
| D-010 | 2026-09-30 | AI help is allowed but disclosed on every PR, and must pass four gates | Provisional |
| D-011 | 2026-09-30 | Data dictionaries keep the publisher's words and the team's labeled interpretation in separate columns | Accepted |

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

## D-006: Where source documentation lives

- **Problem:** Each source produces an inventory card, profiling findings, and publisher documents (for example DepEd's README files and Technical Notes). These need one predictable home.
- **Decision:** Each source gets a folder, `docs/source_inventory/<source_id>/`, with `README.md` (the inventory card) and `profile.md` (findings with evidence). Publisher documents stay with the raw files in raw storage; the card records their URL, size, and SHA-256. Cross-source work stays in `docs/cross_source/`.
- **Reason:** Keeping everything about one source together makes review easier. Publisher documents arrive with the data, so they are part of the raw delivery, and recording their checksum proves which version the team relied on.
- **Consequence:** `tests/test_config.py` requires `README.md` for any source past `candidate`, and `profile.md` for any source that is `profiled` or `accepted`.

## D-007: How sources are profiled

- **Problem:** Profiling findings must be reproducible by another engineer, without spending Databricks Free Edition compute on small files.
- **Decision:** Profile locally with DuckDB (pinned in `requirements-dev.txt`), in a `.py` script per source under `notebooks/profiling/` with `# %%` cells. Each check prints under the finding ID used in that source's `profile.md`. Scripts read raw data from `RAW_DATA_DIR` and verify file checksums before profiling.
- **Reason:** The DepEd files are about 60,000 rows each, so DuckDB profiles them in seconds on a laptop. DuckDB is in the course's Day 9 tool list and was used in NYC Mobility. Keeping the code next to the findings lets a reviewer rerun every number.
- **Consequence:** CI cannot run profiling scripts because raw data is not in git. Each PR that changes a profile states that the script was run and the numbers matched. Checks that repeat across sources move into `src/profiling/` once a second source repeats them.

## D-008: Develop locally, run on Databricks deliberately

- **Problem:** The team shares one Databricks Free Edition workspace with limited compute. Repeated debugging runs, forgotten sessions, and overlapping full runs could exhaust it before the deadline.
- **Decision:** Profile and develop SQL or PySpark logic on laptops (DuckDB by default; local PySpark optional), then confirm on Databricks once. Full pipeline runs are announced, dashboards get no scheduled refresh during development, and every full run is recorded in `pipeline_runs`. The rules are in `docs/workflow.md`, Part 5.
- **Reason:** The data is small (about 60,000 rows per file), so laptops handle development easily, and each Databricks run is then a deliberate confirmation rather than trial and error.
- **Consequence:** Local and Databricks behavior can differ (SQL dialect, no Unity Catalog locally), so logic is not trusted until it has run on Databricks. Setup is longer: every teammate needs a local Python environment (`docs/terminal_setup.md`).

## D-009: Workspace, catalog, and raw storage

- **Problem:** The team needs one shared place for data in Databricks Free Edition, usable by all five teammates, before ingestion starts.
- **Decision:** One workspace (`dbc-76bcfddb-1669`) with CLI profile `reached-hq`. Catalog `edu_access`, created through the UI (Free Edition requires Default Storage, which the CLI could not use). The catalog, schemas, and raw volume are owned by the `reached-hq` group, not a person. Raw files go to the managed volume `` edu_access.`00-source`.raw ``. All five teammates are workspace admins.
- **Reason:** Group ownership means nobody is blocked when one teammate is unavailable. A managed volume needs no credentials, and the data is small (the DepEd downloads are about 3 MB each). Making everyone an admin keeps setup fast for a student team.
- **Consequence:** Every teammate can change or delete anything in the workspace and the catalog, which is the opposite of least privilege (Day 9); the team accepts that for the capstone. **Provisional:** if the mentor approves the course R2 bucket, an R2-backed volume is added and this entry is updated.

## D-010: Using AI

- **Problem:** Teammates use AI tools for code, SQL, and documentation. Nothing records when AI helped, so a reviewer cannot tell which statements were checked by a person. AI can produce a column description, a number, or a platform limit that looks right and is wrong, and it can be given data or credentials that should never leave the team.
- **Decision:** AI help is allowed for all work. Every pull request states whether AI helped and what it did. If it helped, the work must pass four gates (data, AI claims, output, accountability) before the pull request is opened. The rules are in `CONTRIBUTING.md` under **Using AI**, and the pull request template carries an **AI help** block. Issue templates do not: the pull request is where work is reviewed, so that is where AI help is declared.
- **Reason:** Banning AI would be ignored and unverifiable. Disclosure plus checkable gates keeps the author accountable and tells the reviewer where to look. Stating the gates once in `CONTRIBUTING.md` means a change is made in one place, not in the template.
- **Consequence:** CI (the **PR declares AI help** check) fails a pull request whose AI help section is not filled in, but it only sees the ticks: disclosure is still an honor system, and a false "No AI help" cannot be detected. The **Accountability** gate carries the weight: work its author cannot explain in review is sent back. Open pull requests from before this decision add the block when next edited. **Provisional:** revisit once the whole team has agreed to it, and if the course publishes its own AI policy.

## D-011: Interpreting undocumented columns

- **Problem:** Publishers often leave columns undocumented (in PSA's PSGC workbook, 6 of 11 columns). The rule "never write a description from guesswork" keeps the dictionary honest, but it leaves those columns blank even when their meaning is well supported by a law, by the data, or by an obvious header. Teammates then either guess silently in later work or are tempted to write a guess into the publisher's column.
- **Decision:** Add an **Our interpretation** column to every data dictionary. **Description (publisher)** stays the publisher's words only, including documentation given as an image. **Our interpretation** holds the team's reading, and every entry starts with a label, **[other source]**, **[observed]**, or **[assumed]**, followed by its evidence. An [assumed] entry the pipeline relies on needs a suspected finding in `profile.md`. The rules are in `docs/source_inventory/_template/data_dictionary.md`.
- **Reason:** Separate columns let a reader tell at a glance who said what, which is what planners will question. The labels follow the documented / mentor-validated / assumed tagging from D-001, so the team uses one way of stating how sure it is. Keeping the text in the script keeps the dictionary generated and reproducible (D-007).
- **Consequence:** Existing dictionaries (`deped_enrollment`, `deped_facilities`) gain the column when their script is next changed; DepEd documents almost every column, so they need few entries. Sources in review, starting with `psa_psgc` (#19), add it before approval. Interpretations can be wrong: the label and evidence make that visible, and they are reviewed like any other claim.
