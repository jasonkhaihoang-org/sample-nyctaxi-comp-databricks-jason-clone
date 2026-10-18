# Fabric Lakehouse port (VD-6997) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace this repo's August-era Fabric Git tree with the DuckDB model-answer repo's agent-context layer, rewritten for a Fabric Lakehouse Domain in the vibedata-data-engineering plugin's `fabric_lakehouse` layout.

**Architecture:** Three-phase history on one branch. First, delete the Fabric-era tree. Then import `accelerate-data/sample-nyctaxi-comp` `main` byte-for-byte, so its own tests are green. Then rewrite its prose (AGENTS, skills, docs, ADRs, repo-map notes) for Fabric. Code-coupled entries (pipelines, profile, orchestration, CI, `.sqlfluff` dialect, the `sql-style` skill) stay DuckDB until VD-6998 and VD-6999, on the same branch, swap the code and its repo-map entries together. One PR closes all three tickets.

**Tech Stack:** Markdown, JSON, pytest (`tests/test_maps.py`, `tests/test_adr_links.py`), ruff.

**Spec:** Linear VD-6997 (parent VD-6996). Plugin conventions: `vibedata-data-engineering/_shared/platforms/fabric_lakehouse/{dbt,dlt,pipeline-notebook,orchestration,destination-staging}.md` and `_family/fabric/{orchestration-authoring,dbt-job-notebook}.md`.

## Global Constraints

- Source of the import: `accelerate-data/sample-nyctaxi-comp` `main` at `b2be6db`.
- Layout the prose describes: `transformation/` (dbt, fabricspark), `ingestion/<name>_pipeline.Notebook/` (dlt pipeline notebook, `vibedata.dlt.fabric`, Delta via the `filesystem` destination), `orchestration/<Name>.DataPipeline/` plus `orchestration/<job>_dbt.Notebook/`.
- Names fixed for VD-6998: pipeline notebooks `tlc_pipeline`, `ops_pipeline` and `mdm_pipeline`; Data Pipeline `nyc_taxi_refresh`; dbt job notebook `nyc_taxi_build_dbt`.
- Sandbox dbt target: `ephemeral_dev`, rendered by Studio. A sandbox command carries `--defer --state /cache/prod-target`. `transformation/profiles.yml` holds a `prod` target with the Domain's fixed coordinates.
- Committed ids: Domain coordinates only (the `prod` profile and `[destination.filesystem]`). Never an Ephemeral or workspace-item id.
- Data window: Q1 2024 (`report_start` 2024-01-01, `report_end` 2024-04-01). The Domain seed loads January.
- Domain slug: `nyc-taxi-fabric-demo`.
- `docs/setup/` is repo maintenance and build agents never read it.

## Review Focus

- An instruction left pointing at a DuckDB-only path (`domain.duckdb`, `VD_EPHM_DUCKDB_LOCAL_PATH`, `relations.sql`, `run_ingest.py`) in prose an agent reads. Task 5 greps for it, and the allow-list covers only code VD-6998 replaces.
- A doc names a file that does not exist after the deletions. `tests/test_adr_links.py` and a relative-link check over every `.md` cover this.
- An ADR or design record whose decision depends on DuckDB behaviour (catalog-free views, float reproducibility) states it as if it held on Spark. Task 4 rewrites or qualifies each one.
- A skill still tells the agent to run dbt with `--target dev`. Task 5 greps for `--target dev`.
- A committed GUID. Task 1 and Task 5 grep for the GUID pattern outside `.github/`.

---

### Task 1: Remove the Fabric-era tree

**Files:**
- Delete: `src/`, `tools/`, `scripts/`, `docs/functional/`, `docs/design/`, `docs/superpowers/`, `docs/adr/`, `docs/future-requests/` (its requests are DuckDB's `docs/proposal/pending-requests.md`), `docs/data-provenance.md`, `README.md`, `CONTEXT.md`, `.gitignore`

- [ ] **Step 1:** `git rm -r` the paths above.
- [ ] **Step 2: Verify.** Run `git ls-files`. Expected: empty.
- [ ] **Step 3: Commit.** `chore: remove the Fabric Git tree ahead of the port from sample-nyctaxi-comp (VD-6997)`

### Task 2: Import the DuckDB repo unchanged

- [ ] **Step 1:** `git -C ~/src/sample-nyctaxi-comp archive b2be6db | tar -x -C .`, then `git add -A`.
- [ ] **Step 2: Verify.** In a venv with `requirements-dev.txt`, run `python3 -m pytest tests -q`. Expected: the same pass count as the source repo at `b2be6db` (record both).
- [ ] **Step 3: Commit.** `chore: import sample-nyctaxi-comp main@b2be6db unchanged (VD-6997)`

### Task 3: Repo-maintenance docs for this repo

**Files:**
- Delete: `docs/setup/{work-plan,requirements,conventions-inventory,rules-docs-draft,repo-map-design,skill-change-notes,skill-changes,seeding-the-domain}.md`, `docs/setup/seed_domain_duckdb.py`, `tests/setup/`. VD-6999 rewrites seeding for Fabric.
- Keep: `docs/setup/onboarding-skill-design.md` (the onboarding skill's design), `data-provenance.md`, `domain-terms.md`.
- Create: `docs/setup/requirements.md` (this port: the VD-6996 decisions and R-NN lines for VD-6997/6998/6999, the DuckDB origin commit, and a pointer to the DuckDB repo's `docs/setup/` for the history), `docs/setup/skill-changes.md` (same table format as the DuckDB file, starting empty), and this plan.
- Modify: `docs/setup/data-provenance.md` (Lakehouse schemas, not `domain.duckdb`), `README.md`, `CONTRIBUTING.md` (Fabric prerequisites: a Fabric workspace, a schema-enabled Lakehouse and `az login`; no local warehouse file; the local loop is pytest and `dbt parse`).
- Modify: `docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md`. Leave its history intact and add one line saying the platform is Fabric Lakehouse in this repo.

- [ ] **Step 1:** Make the edits above.
- [ ] **Step 2: Verify.** Run `python3 -m pytest tests -q` (expected: pass) and the Task 5 relative-link check over `docs/setup/`, `README.md` and `CONTRIBUTING.md` (expected: no broken links).
- [ ] **Step 3: Commit.** `docs: repo-maintenance docs for the Fabric port (VD-6997)`

### Task 4: Context, ADRs and design records

**Files:**
- Modify: `CONTEXT.md` (expected platform-neutral; change only lines naming DuckDB).
- Modify: `docs/adr/0005-…`, `0008-…`. Keep the decision and restate the platform as Fabric Lakehouse (Delta via the `filesystem` destination). No new ADR: the platform is a Domain fact, not a design decision.
- Modify: `docs/design/pipelines/{tlc,ops,mdm}.md`. Each artifact is `ingestion/<name>_pipeline.Notebook/`. The schema-contract decision follows the Lakehouse: tables persist across runs, so `tables: freeze` after the first load.
- Modify: `docs/review/2026-10-14-{onboarding,performance}-nyctaxi.md`. Each finding is a historical record: add one note per DuckDB-specific finding saying whether it holds on Fabric. Do not rewrite the finding.
- Modify: every design record or ADR that cites `relations.sql` or the renamed-copy reason. On Fabric the reason is defer: `source_defer.sql` resolves a source against the Domain.

- [ ] **Step 1:** Make the edits above.
- [ ] **Step 2: Verify.** Run `python3 -m pytest tests/test_adr_links.py -q`. Expected: pass.
- [ ] **Step 3: Commit.** `docs: context, ADRs and design records state the Fabric Lakehouse platform (VD-6997)`

### Task 5: AGENTS.md, repo-map prose and skills

**Files:**
- Modify: `AGENTS.md`. Fabric Lakehouse platform; startup unchanged. Commands run in the sandbox through the plugin's `vd-intent-context-run.sh`. Safety: no warehouse file; the Domain Lakehouse is written only by a release; never commit Ephemeral ids. `.workflow/ci-config.yml` slug `nyc-taxi-fabric-demo` is left for VD-6999.
- Modify: `repo-map.json` prose-only keys: `repo_root` → `sample-nyctaxi-comp-fabric`; `applications` (name `nyc-taxi-fabric-demo`, Fabric Lakehouse); `notes_for_agents.{warehouse,dlt_environment,dbt_sources,new_source}`; `modules.macros.description`; `build_systems[].notes`. Location keys (`entrypoints`, `sources.*.pipeline`, `artifact_paths.pipeline`, `commands`, `build_systems[].config_files`) stay until VD-6998 changes the files they point at.
- Modify: `.agents/skills/workarounds/SKILL.md`. "Run dbt in the sandbox" becomes the `ephemeral_dev` target with `--defer --state /cache/prod-target`, async launch, and the `remove when` pointing at `fabric_lakehouse/dbt.md`. "Sample load lands whole pages" points at `fabric_lakehouse/dlt.md`. "Tier-1 tests after a safety run": the plugin defers a Tier 2/3 suite on Fabric (`fabric_lakehouse/dlt.md` § Bronze tests), so the rule names that.
- Modify: `.agents/skills/dlt/SKILL.md`. The pipeline is `ingestion/<name>_pipeline.Notebook/` from the plugin's generator. Register a new pipeline as an activity in `orchestration/nyc_taxi_refresh.DataPipeline/`, not in `run_ingest.py`. Delta `merge` does not deduplicate. The D7 contract: tables persist, so `freeze` after the first load.
- Modify: `.agents/skills/dbt-testing/SKILL.md`. Generalise the float note from "DuckDB" to "the engine": Spark aggregation is not reproducible bit for bit either.
- Modify: `.agents/skills/onboarding/` for a `fabric_lakehouse` Domain:
  - `references/base-setup.md`: the `profiles.yml` row becomes a `prod` target with the Domain coordinates. The `relations.sql` row is replaced by rows for `source_defer.sql` and `generate_schema_name.sql`, copied from the plugin's `fabric_lakehouse/templates/`.
  - `references/greenfield.md`: the pipeline notebook comes from the plugin generator. Orchestration is a Data Pipeline plus a dbt job notebook from the plugin materializers. No `run_*.py`.
  - Templates: delete `templates/dbt/relations.sql`, `templates/orchestration/` and `templates/tests/test_run.py`. Rewrite `templates/dbt/profiles.yml` as the `prod` shape. Set `templates/dlt/requirements.txt` to `vibedata-dlt-fabric-studio`. Make the same Fabric changes to `templates/repo/{AGENTS.md,repo-map.json,requirements-dev.txt,repo-checks.yml}` and `templates/skills/{workarounds,dlt,dbt-testing,dbt-models}.md` as in the repo's own copies.
- Modify: `docs/setup/skill-changes.md`. One row per plugin gap found while rewriting.

- [ ] **Step 1: Write the guard test first.** Add `tests/test_platform_prose.py` with two tests:
  - `test_agent_read_prose_names_no_duckdb_runtime`: for every `.md` under `.agents/`, `AGENTS.md`, `CONTEXT.md` and `docs/{adr,design}/`, plus `repo-map.json` `notes_for_agents` and `applications`, assert none of `domain.duckdb`, `VD_EPHM_DUCKDB_LOCAL_PATH`, `relations.sql`, `run_ingest.py`, `run_transform.py`, `run_all.py`, `duckdb_local` or `--target dev` appears.
  - `test_no_committed_guid`: no file outside `.github/` matches `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`.
- [ ] **Step 2:** Run `python3 -m pytest tests/test_platform_prose.py -q`. Expected: FAIL, listing the files to rewrite.
- [ ] **Step 3:** Make the edits above.
- [ ] **Step 4:** Run `python3 -m pytest tests -q` and `ruff check .`. Expected: pass. Also run a relative-link check over every `.md` (a short one-off script, not committed). Expected: no broken links.
- [ ] **Step 5: Commit.** `docs: AGENTS, repo-map notes and skills for a Fabric Lakehouse Domain (VD-6997)`

## Handoff to VD-6998 (same branch)

Code-coupled leftovers VD-6998 replaces, together with their repo-map and test-map entries:
- `ingestion/*_pipeline.py` → the notebooks.
- `transformation/profiles.yml` and `relations.sql` → `prod` profile, `source_defer.sql` and `generate_schema_name.sql`.
- `orchestration/run_*.py` and `tests/orchestration/` → `nyc_taxi_refresh` and `nyc_taxi_build_dbt`.
- `.sqlfluff` dialect and the `sql-style` skill → `sparksql`.
- `tools/dq.py` → removed (it reads a local DuckDB file).
- The `test_maps.py` dbt env.

VD-6999 replaces `.github/` and `.workflow/` with the `fabric_lakehouse` bundle.
