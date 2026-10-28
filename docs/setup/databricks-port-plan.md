# Databricks port (VD-7384) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Probe Databricks for the decisions this repo depends on, then rewrite the agent-context layer inherited from the Fabric Lakehouse repo so that every platform statement an agent reads is true for a Databricks Domain in the plugin's `databricks` layout.

**Architecture:** One branch and one PR for VD-7384, VD-7385 and VD-7386, as the Warehouse and Redshift ports did. `main` is the Lakehouse repo's `main` at `be4a547`, unchanged. VD-7384 probes first, then rewrites the prose that does not describe this repo's own code. Prose that describes code (the dbt profile, the pipeline notebooks, the orchestration job, `.sqlfluff`, macros, seeding) changes in VD-7385 and VD-7386 with that code. A guard test bans Fabric Lakehouse vocabulary from agent-read prose, with an allow-list naming the files each later ticket owns. The PR is ready only when the allow-list is empty.

**Tech Stack:** Markdown, JSON, pytest (`tests/test_platform_prose.py`, `tests/test_maps.py`, `tests/test_adr_links.py`), ruff; live probes with the Databricks CLI (statement execution API), dbt-databricks, dlt and sqlfluff against the `uk-vd-spike-dbx` workspace.

**Spec:** Linear VD-7384 (parent VD-7383). Plugin on vde `origin/main` (`5ec5dbe5f` or later; Studio's pin `2cde8ea14` predates the Databricks dlt and orchestration work): `_shared/platforms/databricks/{dbt,dlt,dialect,ci,orchestration,audit-surfaces}.md`, `templates/`, `scripts/platforms/databricks.py` and `scripts/platforms/databricks/`. Studio `origin/main`: `databricks.descriptor.ts`, `databricks.provider.ts`, `providers/databricks/*`, `intents/templates/databricks-dbt-{profiles,project}.yml`, `intent-prod-manifest-{cache,publication}.ts`. domain-cicd `domain-ci-databricks-bundle`.

## Global Constraints

- Origin: `accelerate-data/sample-nyctaxi-comp-fabric` `main` at `be4a547`. The Warehouse and Redshift repos are read for anything a later fix added.
- Platform: dbt runs on `dbt-databricks`. Studio's profile is `dbt_databricks`, target `databricks_sandbox`: catalog `VD_EPHM_DATABRICKS_CATALOG`, schema `VD_EPHM_DATABRICKS_MIRROR_SCHEMA`, token minted per dbt process by the shim. A `+schema:` node lands in `<VD_EPHM_SCHEMA_PREFIX><name>` in the Ephemeral catalog; the sandbox guard refuses any other schema.
- dlt: each pipeline is a Databricks notebook `ingestion/<name>_pipeline.ipynb` from the plugin template, destination `databricks_files_api()` from `vibedata-dlt-databricks-notebook`, run on serverless compute by `run_notebook.py`; `ingestion/.dlt/config.toml` holds the production catalog and warehouse, overridden per run through `dlt_env`.
- Cross reads: a source reads through `macros/source_defer.sql` (sandbox prefixed schema first, else the Domain's table); an unbuilt `ref()` defers to the production manifest at `/cache/prod-target` (Studio `deferManifest: 'none'`: the one manifest the CI bundle publishes serves selection and defer).
- Orchestration: a Lakeflow job in a Declarative Automation Bundle, `databricks.yml` + `orchestration/<job>.job.yml` (plugin `orchestration.md`), replacing the Fabric Data Pipeline. Included by user decision on 2026-10-28.
- CI: `domain-ci-databricks-bundle` publishes the production manifest only and runs no PR gates (`ciMode: 'gha'`).
- Data window: Q1 2024, for seed and parity.
- Estate: workspace `uk-vd-spike-dbx`; catalogs `nyctaxi_prod` (Domain) and `nyctaxi_ephm` (Ephemeral); SQL warehouse `nyctaxi-wh`. Nothing in `vd_spike_*`. Tag jobs `project=nyctaxi-databricks`.
- Domain slug: `nyc-taxi-databricks`.
- Every Databricks statement in the prose cites the plugin, Studio's code or design docs, or this ticket's verification doc. A claim none of them backs goes to `skill-changes.md` as "verify in VD-7385".
- Committed coordinates: Domain only, and only where the plugin reads them. Never an Ephemeral catalog, a mirror schema or a workspace host.
- `docs/setup/` is repo maintenance; build agents never read it.

## Review Focus

- A sentence that holds only on Fabric: Livy, `fabricspark`, `dbt_fab_spark`, SQL analytics endpoint, OneLake, a `.Notebook`/`.DataPipeline` item, `logicalId`/`notebookId`, `notebookutils`, Ephemeral/Domain Lakehouse. The Task 1 guard fails on each outside the allow-list.
- A rule whose wording survived but whose reason did not. Spark SQL is shared, so many Lakehouse rules carry over; each still needs a Databricks reason from a probe or the plugin, or goes.
- Cross reads stated as Fabric did them (a schema-enabled Lakehouse, the SQL endpoint lag). On Databricks a source reads through `source_defer.sql` and a `ref()` defers to the published manifest.
- A Databricks claim nobody ran. Task 2's probes back each decision; anything else goes to the ledger.
- A doc linking to a file the port deletes (the Fabric plans and verification). Task 6's link check covers it.

---

### Task 1: Guard: Fabric Lakehouse vocabulary in agent-read prose

**Files:** Modify `tests/test_platform_prose.py`

- [ ] Add `LAKEHOUSE_RUNTIME` (Fabric-only terms: `fabricspark`, `dbt_fab_spark`, `dbt_fabric_compile`, `Livy`, `livy`, `SQL analytics endpoint`, `OneLake`, `onelake`, `.Notebook`, `.DataPipeline`, `notebookutils`, `logicalId`, `notebookId`, `fabric_lakehouse/`, `Ephemeral Lakehouse`, `Domain Lakehouse`, `vibedata.dlt.fabric`, `Data Pipeline`) and `test_agent_read_prose_names_no_lakehouse_runtime`, scanning the same files and repo-map keys as the DuckDB test, skipping `Superseded by` lines and `LAKEHOUSE_PROSE_OWNED_LATER` entries (path or `path#Section` → `"VD-7385"` / `"VD-7386"`). Add `test_lakehouse_allow_list_names_existing_files`. Docstring says Databricks.
- [ ] Run it; expect FAIL with hits. Fill the allow-list with code-coupled files only. The test turns green at Task 5.

### Task 2: Live probes and the Databricks best-practices doc

**Files:** Create `docs/setup/databricks-best-practices.md` and `docs/verify/2026-10-28-vd-7384-databricks-probe.md`. Delete the Fabric-only `docs/setup/fabric-{code,port,release}-plan.md` (they stay in the Lakehouse repo; link there).

- [ ] **Estate:** in `nyctaxi_prod`, schema `bronze` with a 3-row table and a view; in `nyctaxi_ephm`, a mirror schema and a `<prefix>bronze` schema standing in for an Intent. Coordinates in git-ignored `~/src/nyctaxi-ref/dbx/`, never in the repo. Tools in `~/src/.venv-nyctaxi-dbx`.
- [ ] **P1 Sandbox reads the Domain:** dbt-databricks with Studio's profile shape; the plugin's `source_defer.sql` reads `<prefix>bronze` when it holds the table, else `nyctaxi_prod.bronze`; a view and a table over a production source build in the Ephemeral catalog; `--defer --state` against a manifest compiled for production resolves an unbuilt `ref()` to `nyctaxi_prod`; whether an admin's cross-catalog write to production is refused (it is grants, not the engine, that protect it).
- [ ] **P2 Dev-schema cleanup:** the plugin's `drop_dev_mode_schemas.py` Databricks path touches only the Ephemeral catalog's prefixed `_dev_` schemas, never `nyctaxi_prod`. Read its guard; run it.
- [ ] **P3 Bronze preview:** the plugin's Databricks `preview()` reads the prefixed schemas the pipeline loaded (`<prefix>bronze`, …), not the mirror schema.
- [ ] **P4 sqlfluff dialect:** no CI bundle picks one. Lint `transformation/models` with `sparksql` and `databricks` (jinja templater); list parse failures and rule hits.
- [ ] **P5 Evaluator on dbt-duckdb:** parse with dbt-duckdb + `dbt_project_evaluator` after the Databricks configs (`file_format`, `liquid_clustered_by`/`partition_by`, the plugin macros).
- [ ] **P6 Committed config cannot point an Intent load at the Domain:** with the production catalog in `ingestion/.dlt/config.toml` and `DESTINATION__DATABRICKS__CREDENTIALS__CATALOG=nyctaxi_ephm` in the environment, which catalog dlt resolves; confirm the plugin's `dlt_env` override and `assert_destination.py`.
- [ ] **P7 Macros and dialect:** each project macro (`finance` incl. `safe_divide`, `timestamps`, `trip_keys`, `generate_schema_name`, `source_defer`) rendered on Databricks vs DuckDB; `merge` incremental on Delta run twice; `liquid_clustered_by`.
- [ ] Write the best-practices doc (facts with citations; contradictions with the plugin; what Studio does; numbered `DBX-D1…` decisions for VD-7385; still to probe). Drop the probe objects. Commit.

### Task 3: AGENTS, README, CONTRIBUTING, CONTEXT, repo-map notes

- [ ] Rewrite each Lakehouse statement for Databricks: Domain catalog / Ephemeral catalog; dbt as plain `dbt` with `--defer --state /cache/prod-target`; dlt notebooks run by the plugin's `run_notebook.py`; orchestration is a bundle job; README prerequisites (an Azure Databricks workspace with Unity Catalog and a SQL warehouse); Safety (commit only the Domain catalog/warehouse where the plugin reads them).
- [ ] Run the tests; only the Lakehouse-vocabulary test may fail, on files Tasks 4–5 own. Commit.

### Task 4: Convention skills

- [ ] `workarounds`, `dlt`, `dbt-models`, `dbt-testing`, `sql-style`: each Fabric rule gets a Databricks reason from a probe or the plugin, or goes; each workaround names what removes it. Commit.

### Task 5: Onboarding skill, design records and review notes

- [ ] Onboarding references and templates mirror the plugin's Databricks layout; design-record reasons per Task 2; review notes get "Notes after the Databricks port". Run `pytest` and `ruff`: pass, with the allow-list holding only VD-7385/7386 entries. Commit.

### Task 6: Repo-maintenance docs, ledger, and the Studio/plugin alignment check

- [ ] Update `docs/setup/{requirements,upstream-parity,data-provenance,onboarding-skill-design,skill-changes}.md`.
- [ ] Alignment check against Studio `origin/main` and plugin `origin/main`: profile and target, env-var names, `dbt_project.yml` ownership, layout, cross reads, CI, orchestration, preview (P3), cleanup (P2). Each mismatch is a `skill-changes.md` row; file the ones not already in Linear (team Studio, label `nyctaxi-databricks`).
- [ ] Relative-link check over every tracked `.md`; `pytest` and `ruff` pass. Commit.

## Handoff to VD-7385 and VD-7386 (same branch)

- VD-7385 starts from `databricks-best-practices.md` § Decisions; it empties its allow-list entries, swaps the Fabric notebooks for `ingestion/<name>_pipeline.ipynb`, replaces `orchestration/` with `databricks.yml` + `orchestration/<job>.job.yml`, and switches `.sqlfluff`, `requirements-dev.txt` and the dbt profile.
- VD-7385 also gives each source `database:` per DBX-D10 and changes `tests/test_maps.py`, which still asserts that sources name no database; the onboarding template's `test_maps.py` already requires one.
- VD-7386 seeds Q1, publishes the production manifest, and owns `seeding-the-domain.md` and parity (`docs/setup/parity.py`). The Fabric `seed_domain.py` goes: the Databricks seed is `bundle deploy` and `bundle run`.
