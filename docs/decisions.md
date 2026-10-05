# Decision log

Each entry records **problem → decision → reason → consequence**. A **provisional** decision names the point at which it will be revisited.

| ID | Date | Decision | Status | Primary consequence |
|---|---|---|---|---|
| D-001 | 2026-09-29 | Stakeholder needs come from published documents plus mentor validation | Accepted | A question that rests mostly on assumed needs cannot be approved |
| D-002 | 2026-09-29 | Use the course deliverables as the baseline until a rubric exists | Provisional | Scope may shift once the rubric is released |
| D-003 | 2026-09-29 | Higher education is out of scope (decided 2026-10-05) | Accepted | CHED sources stay profiled, but none moves on to ingestion |
| D-004 | 2026-09-29 | Data and secrets stay out of Git, enforced by CI | Accepted | CI fails pull requests that add data files, files over 1 MB, `.env` files, or secrets |
| D-005 | 2026-09-29 | Branch from `main` with short-lived feature branches; no `dev` branch | Provisional | `dev` and `prod` are Databricks deploy targets, not branches |
| D-006 | 2026-09-29 | One documentation folder per source; publisher documents stay with raw data | Accepted | Each source past `candidate` needs a `README.md`, and each profiled source a `profile.md` |
| D-007 | 2026-09-29 | Profile sources locally with DuckDB, in scripts saved under `notebooks/profiling/` | Accepted | CI cannot rerun profiling, so each pull request states the script was run and the numbers matched |
| D-008 | 2026-09-29 | Develop locally; use Databricks compute only for planned runs | Accepted | Logic is trusted only after it has run once on Databricks |
| D-009 | 2026-09-29 | Catalog `edu_access` owned by the team group; raw files in a managed volume | Provisional | Every teammate can change or delete anything in the workspace |
| D-010 | 2026-09-30 | AI help is allowed but disclosed on every PR, and must pass four gates | Provisional | CI blocks a pull request whose AI help section is empty; disclosure is otherwise on trust |
| D-011 | 2026-09-30 | Data dictionaries keep the publisher's words and the team's labeled interpretation in separate columns | Accepted | Every interpretation carries a label and evidence, and is reviewed like any other claim |
| D-012 | 2026-09-30 | PSGC 2Q 2026 is the master geographic reference, including for SY 2023-24; no crosswalk | Accepted | Region from PSGC is not used for Negros or Sulu in SY 2023-24 results |
| D-013 | 2026-10-05 | The stakeholders are LGU planners, with students as the focus | Accepted | Results must be trustworthy at barangay level, and higher education leaves scope |
| D-014 | 2026-10-06 | A raw delivery is identified by its SHA-256 and approved in the source contract | Provisional | A file the contract does not list, or whose checksum differs, is blocked rather than loaded |
| D-015 | 2026-10-06 | Bronze keeps every delivery; a revised file is a new version, never an overwrite | Provisional | Downstream reads only succeeded batches, and by default the latest version of each school year |
| D-016 | 2026-10-06 | First downloads stay in the publisher folder; any later download goes into a dated subfolder | Provisional | A raw file is never overwritten, so a re-download sits beside the earlier one |
| D-017 | 2026-10-06 | Local ingestion runs use DuckDB as a stand-in for Delta tables | Provisional | Four Databricks behaviors are proven only by the Databricks confirmation run |

---

## D-001: Where stakeholder needs come from

- **Problem:** The team has no direct access to the planners it serves (LGU planners since D-013). They are the audience for the presentation, not a source of interviews.
- **Decision:** Needs are drawn from published planning documents and checked with the program mentor. Every need is tagged **documented** (cited source), **mentor-validated**, or **assumed**.
- **Reason:** Planners in the audience will know their own policies, so unsupported needs are the easiest thing for them to challenge.
- **Consequence:** A candidate business question that rests mostly on **assumed** needs cannot be approved.

## D-002: No capstone rubric yet

- **Problem:** No official rubric or deadline has been published.
- **Decision:** Build to the course's deliverables: pipeline, model, validation, documentation, Git, a business dashboard, a DQ dashboard, and the Day 9 production practices.
- **Reason:** These are the most complete statement of expectations available today.
- **Consequence:** Scope may shift. **Revisit when the rubric is released.**

## D-003: Higher education is out of scope

- **Problem:** The theme mentions higher-education capacity. Higher education is CHED's mandate, not DepEd's.
- **Decision:** Keep it in scope during source discovery and profiling. The stakeholders are framed as education planners (DepEd and CHED).
- **Reason:** The theme's general question includes it.
- **Consequence:** More sources to profile, and a different grain (one row per institution rather than per school). **Revisit at the end of Phase 3:** keep it only if the profiled data supports it.
- **Revisited 2026-10-05:** higher education is out of scope. Sponsors pointed out that foundational learning gaps in basic education are more urgent, CHED data is available only by region or province, and the stakeholders are now LGU planners (D-013). The CHED source cards stay in the inventory as profiled, but no CHED source moves on to ingestion.

## D-004: Data and secrets stay out of Git

- **Problem:** Raw files, credentials, and large outputs can end up committed by accident, and once pushed they stay in the repository's history.
- **Decision:** No data and no secrets go into Git. Raw, interim, and processed datasets live in the agreed storage; the only exception is small, made-up samples under `tests/fixtures/`. Credentials stay in a local, git-ignored `.env`, and only `.env.example` (names, no values) is committed. CI enforces this in `tests/test_repo_policy.py`.
- **Reason:** The repository is shared by the whole team and reviewed in public pull requests. Checking it automatically on every pull request is more reliable than relying on each person to remember.
- **Consequence:** CI fails a pull request that adds a data file (for example `.csv`, `.xlsx`, or `.zip`), a file over 1 MB, a `.env` file, or text that looks like a token or private key. Generated outputs that are lists of records are written as Markdown, and profiling reads raw files from `RAW_DATA_DIR` outside the repository (D-007).

## D-005: Branching model

- **Problem:** A long-lived `dev` branch alongside `main` is a common pattern, but it adds merge overhead for a small team.
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
- **Reason:** The DepEd files are about 60,000 rows each, so DuckDB profiles them in seconds on a laptop. DuckDB is in the course's Day 9 tool list. Keeping the code next to the findings lets a reviewer rerun every number.
- **Consequence:** CI cannot run profiling scripts because raw data is not in git. Each PR that changes a profile states that the script was run and the numbers matched. Checks that repeat across sources move into `src/profiling/` once a second source repeats them. The xlsx reader was the first (`src/profiling/xlsx.py`, #33, added 2026-10-01).

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

## D-012: Which PSGC version to use

- **Problem:** The anchor data is DepEd SY 2023-24, but the PSGC we profiled is 2Q 2026. Between them the Negros Island Region (NIR) was created and Sulu moved from BARMM to Region IX, so region labels and codes differ. The PSA API returns no records for `Q3_2023`; the nearest version it serves, `Q4_2023`, was pulled and compared.
- **Decision:** Use the PSGC 2Q 2026 workbook as the one master reference for all school years. No crosswalk to older versions is built. DepEd files carry place names only, so joins use province, municipality, and barangay names inside their parent, never region. For SY 2023-24 results by region, use DepEd's own region column or report at province level.
- **Reason:** About 1,855 of about 43,760 codes differ from `Q4_2023`, almost all from NIR and Sulu, and name joins are not affected by a code change. `Q4_2023` has 457 names with broken accents and no 2024 population for about 1,780 barangays. 2Q 2026 has neither problem, is PSA's published file, and is already profiled.
- **Consequence:** Region from PSGC must not be used for Negros or Sulu in SY 2023-24 results. Barangays split or renamed since 2023 (for example Barangay 176 in Caloocan) are flagged as unmatched or ambiguous, not forced. **Revisit** if a source arrives with codes from another PSGC version, or if the team needs code-level history; then build a crosswalk from `Correspondence Code`. Evidence and matching rules: [psa_psgc README](source_inventory/psa_psgc/README.md#version-used-and-sy-2023-24).

## D-013: Who the stakeholders are

- **Problem:** The project was framed for DepEd and CHED planners. Sponsors asked what a mayor or local planner would actually need, for example whether a mayor can zoom into a barangay and trust what they see.
- **Decision:** The stakeholders are LGU planners, with students as the focus. The analysis is basic education at city/municipality and barangay level.
- **Reason:** LGUs take part in local school planning and funding (for example through local school boards), and they need area-level evidence that a national total cannot give; the cited needs are collected under D-001. Keeping students as the focus keeps every measure tied to learners.
- **Consequence:** Planner needs are drawn from LGU-facing documents (D-001). Results must be trustworthy at barangay level, so place-name matching to PSGC is reported with its match rate. Higher education leaves scope (D-003).

## D-014: How a raw delivery is identified and approved

- **Problem:** DepEd publishes each school year as a new zip, and re-uploads years it has already published (the enrollment files were re-uploaded on 2025-10-15). The files have no `updated_at` or other change field. A pipeline that trusts file names would load a changed file as if it were the old one, or load the same file twice under different names.
- **Decision:** A delivery is identified by the SHA-256 of the archive, and its rows by the SHA-256 of the data file inside it. Each source has a contract, `config/ingestion/<source_id>.json`, listing the schema versions (exact, ordered column lists) and every approved delivery with its checksums, encoding, schema version, and row count. A delivery is approved by merging its entry in a reviewed pull request; the pipeline never approves anything. A header that matches no schema version stops the load; a new version is added to the contract in a pull request, and Bronze gains the new columns from the contract, never from a file.
- **Reason:** A checksum is the only change signal these files carry, and it cannot be faked by a rename. Approval in a pull request puts a reviewer between a new file and the tables, which is where the encoding and schema changes of SY 2025-26 were caught (enrollment profile O-6 to O-8).
- **Consequence:** A file the contract does not list is recorded as `blocked`; a file with an approved name but a different checksum is `blocked` as a possible revision; a re-zipped copy of an approved data file is `skipped`. Each new school year needs a profile update and a contract entry before it loads. `tests/test_ingestion_validate.py` fails if the contract's checksums and row counts are not also on the source card. **Provisional:** the team has not yet reviewed it (#11).

## D-015: Bronze keeps every delivery and every version

- **Problem:** When a publisher revises a school year it has already published, the team must choose between replacing the earlier rows and keeping both. There is no evidence yet of what DepEd's re-uploads change. The pipeline also needs a way to load the same file again without duplicating rows, while keeping rows the publisher itself repeated.
- **Decision:** Bronze is append-only, one table per source covering all school years. A revised file for a school year is approved as the next `delivery_version` with `supersedes` naming the earlier one, and both stay in Bronze. A Bronze row is identified by `(source_sha256, source_row_number)` and loaded with an insert-only MERGE, so a rerun inserts nothing and publisher duplicates (different row numbers) are all kept and flagged as WARN. Because Delta commits one table at a time, the batch's `succeeded` status in `01-control`.ingestion_batches is written last and acts as the commit marker. Downstream reads `01-control`.current_batches: for each school year, the latest succeeded version.
- **Reason:** Keeping both versions is reversible and choosing one is not; the history is what lets the team answer "what changed?" when a number moves. The data-file checksum, rather than the archive's, makes a re-zipped copy load nothing; a hash of row content would wrongly merge publisher duplicates.
- **Consequence:** A revised file that changes one value reloads every row of that school year as a new version (about 60,000 rows), which is acceptable at this size. A load that dies after its MERGE leaves rows that downstream cannot see until a retry reconciles them. **Open:** whether the latest version should always be current, or whether some revisions need review first (decide when the first real revision arrives). **Provisional:** the team has not yet reviewed it (#11).

## D-016: Raw storage layout

- **Problem:** Raw files are stored flat, one folder per publisher with original file names; the DepEd files were uploaded that way to `/Volumes/edu_access/00-source/raw/deped/` on 2026-09-30 and 2026-10-03. A later download with the same name, such as a DepEd re-upload, would overwrite the earlier file, and the earlier bytes would be gone.
- **Decision:** Files already in `raw/<publisher>/` stay where they are. No raw file is ever overwritten: any later download, whether a new school year or a re-download of a published one, goes into `raw/<publisher>/<download date, YYYY-MM-DD>/` under its original file name. Every folder has a `SHA256SUMS.txt` covering all of its files, updated in the same upload.
- **Reason:** Moving the uploaded files would change paths teammates already use, for no gain: ingestion searches the publisher folder at any depth and identifies files by checksum (D-014), not by path. What protects history is the no-overwrite rule, and a dated subfolder is enough to keep it.
- **Consequence:** The folder mixes the first downloads with dated later ones; a dated folder also records when its files were retrieved. Before an upload, list the target folder to check that no file of that name is there. The flat uploads do not meet #10's "one folder per source"; whether per-publisher folders are enough is open. `SHA256SUMS.txt` in `raw/deped/` does not yet cover the files added on 2026-10-03 (#10). Local copies may keep the `raw-data/<publisher>/original/` layout used for profiling. **Revised 2026-10-06:** first proposed one folder per source and download date for every file; changed after finding the files already uploaded flat. **Provisional:** the team has not yet reviewed it.

## D-017: DuckDB stands in for Delta in local ingestion runs

- **Problem:** Ingestion logic must be tested on every pull request without Databricks credentials (D-008), but local tests can only prove what the local engine can show.
- **Decision:** Local runs and CI use DuckDB through a thin store (`src/ingestion/store.py`) that runs the same `etl/` SQL files as Databricks, translating backticks, `STRING`, and Delta table properties. Writes are single statements, never a multi-table transaction, to match Delta. Spark/Delta is the store on Databricks.
- **Reason:** DuckDB is already pinned and used by the team (D-007), supports MERGE, and loads all three enrollment years (about 180,000 rows) in about seven seconds. Local PySpark with Delta needs Java on every laptop and still has no Unity Catalog.
- **Consequence:** Three Databricks runtime differences are imitated in `tests/test_databricks_runtime.py` (no `__file__` under `exec`, `SystemExit(0)` reported as failure, lazy `SELECT`). Four behaviors are not proven locally and must be confirmed on Databricks: Delta column mapping for the column name with spaces, single-table commit semantics under a real failure, Unity Catalog permissions, and reading raw files from `/Volumes/` paths. Found on the first Databricks run (2026-10-06): a task needs `source: GIT` to read its file from the repository; tables are owned by whoever ran the job unless handed to the group (now done in every `CREATE` file); and each statement costs seconds on serverless, so a load that takes 7 seconds locally took 39 minutes. **Provisional:** revisit if the Databricks confirmation run finds a behavior that differs.
