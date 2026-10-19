# Fabric Lakehouse release and seeding (VD-6999) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From the repo alone, an operator can release and seed the Fabric Lakehouse Domain. Seeding means delivering the code, applying the items, running `nyc_taxi_refresh` and publishing the production manifest. An Intent-shaped `--defer` build then resolves against the result.

**Architecture:**
- Install the `fabric_lakehouse` CI bundle from `domain-cicd`.
- Play the bundle's own `deploy_orchestration.py` from the host with the operator's `az login`, as CD does after its OIDC login. That delivers `Files/nyc-taxi-fabric-demo/{ingestion,transformation}` with the `prod-target` manifest, and applies the notebooks and the Data Pipeline.
- Run `nyc_taxi_refresh` once to seed the full Q1.
- Prove defer from a scratch Lakehouse with the sandbox's dbt command.
- Write the procedure as `docs/setup/seeding-the-domain.md` with a small script.

**Tech Stack:** `domain-cicd` `domain-ci-fabric-bundle`, Fabric REST (job instances), dbt-fabricspark over Livy, az CLI.

**Spec:** Linear VD-6999; `docs/setup/requirements.md` R-05. Decisions: seed the full Q1 in one `nyc_taxi_refresh` run (user, 2026-10-19); prove defer with a sandbox-shaped check, leaving a real Studio Intent to VD-7000 (user, 2026-10-19).

## Global Constraints

- **Domain:** workspace `nyc-taxi-fabric-demo`; Lakehouse `nyc_taxi_lakehouse`, schema `dbo`; slug `nyc-taxi-fabric-demo`. The ids are in `transformation/profiles.yml` `prod`. No id is written into any document.
- **Bundle source:** `accelerate-data/domain-cicd` `origin/main`, exported read-only. No local git hooks: the branch lives in a worktree (VD-6929), as the DuckDB repo also skipped them.
- **Schedules:** the release applies none (`--enable-schedules` is not passed).
- **Scratch resources:** the defer check runs in a separate scratch workspace, which is deleted afterwards. It never writes the Domain.

## Review Focus

- A `ci-config.yml` value that `validate_ci_config.py` accepts but the publish or deploy reads differently, such as a workspace name that doesn't match the real one. Task 2 runs the deploy, which reads it.
- The released manifest describes a project that differs from the one built, because of a `+workspace_name` injection miss (VD-6925). Task 4 defers against the manifest the deploy wrote.
- The seed run leaves a stale January table. `replace` reloads every table; Task 3 compares Q1 counts with the DuckDB full build.
- The scratch defer build writes a model into the Domain. Task 4 lists the Domain's tables before and after.

---

### Task 1: Install the fabric_lakehouse CI bundle

**Files:**
- Replace: `.github/` (the DuckDB bundle) and `.workflow/ci-config.yml`, using the fabric bundle's `bundle_deploy.py --platform fabric_lakehouse --target .`.
- Delete: DuckDB-bundle files the fabric bundle does not deliver.
- Modify: `.workflow/ci-config.yml` (fill the placeholders from the Domain's coordinates per the plugin's `fabric_lakehouse/ci.md`), `.sqlfluff` (the bundle profile `dbt_fab_spark` / `dbt_fabric_compile` under `.github/profiles`).

- [ ] **Step 1:** Run `python3 .github/scripts/validate_ci_config.py` before filling the placeholders. Expected: exit 1, listing the placeholder keys.
- [ ] **Step 2:** Fill the placeholders and rerun it. Expected: exit 0. Run `pytest tests -q` (the GUID guard allows `.workflow/ci-config.yml`) and `sqlfluff lint transformation/models` through the bundle profile. Expected: pass.
- [ ] **Step 3: Commit.** `ci: install the fabric_lakehouse CI bundle (VD-6999)`

### Task 2: Release from the host

- [ ] Export the bundle's `deploy_orchestration.py` (already delivered under `.github/scripts/`). Run it with `--dry-run`, then for real: `--repo-root . --workspace-id <Domain workspace>`. Expected:
  - `Files/nyc-taxi-fabric-demo/ingestion`, `…/transformation` and `…/transformation/prod-target/manifest.json` exist in the Domain Lakehouse.
  - The workspace holds `tlc_pipeline`, `ops_pipeline`, `mdm_pipeline`, `nyc_taxi_build_dbt` and `nyc_taxi_refresh`.
- [ ] Record any deploy failure as a repo fix with a test, or as a `skill-changes.md` row when the bundle is at fault.

### Task 3: Seed: one `nyc_taxi_refresh` run

- [ ] Start the pipeline through Fabric's job API and poll it to completion. Expected: Succeeded, and every activity succeeded. This is also the first run of each notebook's `setup_environment()` cell and of the dbt job notebook.
- [ ] Count over Livy. Expected: `int_trips_conformed` has 9,722,362 rows, the DuckDB repo's full Q1 figure (`docs/setup/requirements.md` there, R-10/R-12); the core facts and the `ops` tables are non-empty; and `bronze.yellow_tripdata` covers 2024-01 to 2024-03.
- [ ] Record the wall time per activity and the session count.

### Task 4: Defer proof from a scratch Lakehouse

- [ ] Create a scratch workspace `nyc-taxi-fabric-demo-defer-check` on the same capacity, with a schema-enabled Lakehouse.
- [ ] Take the released `prod-target` manifest from the Domain's Files. Run `dbt build --select mart_daily_zone_revenue --defer --state <dir> --target ephemeral_dev`, from a scratch profile shaped like the sandbox's: Livy, the scratch ids, CLI auth. Expected:
  - The build passes.
  - The scratch Lakehouse holds only `finance.mart_daily_zone_revenue`.
  - Its row count equals the Domain's.
  - The Domain's table list is unchanged.
- [ ] Delete the scratch workspace.

### Task 5: Seeding doc and script

**Files:**
- Create: `docs/setup/seeding-the-domain.md`. It covers creating the workspace and schema-enabled Lakehouse, filling `profiles.yml`, `.dlt/config.toml` and `ci-config.yml`, releasing (CD on merge, or the host command), running `nyc_taxi_refresh`, the manifest release on merge, and the measured time and capacity cost.
- Create: `docs/setup/seed_domain.py`. It releases with the bundle's `deploy_orchestration.py`, starts `nyc_taxi_refresh` and waits, using stdlib and the az CLI token only.
- Create: `tests/setup/test_seed_domain.py`. It tests the job URL and the poll loop's terminal-state handling, offline with a stubbed transport.
- Modify: `repo-map.json` (`docs/setup/` description), README and CONTRIBUTING if their pointers need it.

- [ ] **Step 1:** Write the failing tests:
  - `test_job_url_names_the_pipeline_item`
  - `test_wait_stops_on_each_terminal_state`
  - `test_wait_gives_up_after_the_deadline`
- [ ] **Step 2:** Run them. Expected: FAIL (no module).
- [ ] **Step 3:** Write the script. Then run `pytest tests -q` and `ruff check .`. Expected: pass.
- [ ] **Step 4: Commit.** `docs: seed a Fabric Lakehouse Domain from the repo (VD-6999)`
