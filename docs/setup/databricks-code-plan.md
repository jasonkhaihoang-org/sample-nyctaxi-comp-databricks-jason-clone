# Databricks code port (VD-7385) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The repo's dlt pipelines, dbt project and scheduled refresh run on Databricks in the plugin's `databricks` layout, following [`databricks-best-practices.md`](databricks-best-practices.md) § Decisions (DBX-D1…D11), and the Fabric allow-list in `tests/test_platform_prose.py` loses every `VD-7385` entry.

**Architecture:** Same branch as VD-7384. Code first, one commit per layer (dbt shell, pipelines, orchestration), then the live runs, then the prose that describes the code. Live runs are Intent-shaped: the plugin's own `run_notebook.py` and Studio's dbt profile shape against the Ephemeral catalog `nyctaxi_ephm`, with a prefix named as Studio names it (`ephm__nyc_taxi_databricks__vd7385__`), from a workstation. Studio's vde pin predates the Databricks notebook work (ledger row "Studio: vde pin"), so no Studio Intent can run them yet; the journey (VD-7387) is the first.

**Tech Stack:** dbt-core 1.12.5 + dbt-databricks 1.12.6, dlt 1.30.0 + vibedata-dlt-databricks-notebook 0.1.0 on serverless environment 4, Databricks CLI 1.21.0 (bundles, `sync`, `jobs submit`), sqlfluff 4.4.0, pytest, ruff.

**Spec:** Linear VD-7385. Plugin vde `origin/main` `5ec5dbe5f` or later: `_shared/platforms/databricks/{dbt,dlt,orchestration}.md` and `templates/`, `scripts/platforms/databricks/{run_notebook,validate-job}.py`. domain-cicd `domain-ci-databricks-bundle` (offline `dbt_databricks_compile` profile).

## Global Constraints

- Committed coordinates: the Domain's only, and only in `transformation/profiles.yml` (and, from VD-7386, `.workflow/ci-config.yml`). No host, warehouse id or token anywhere in git; Ephemeral catalog and prefix names only in `docs/setup/` and `docs/verify/` records, never where an agent or a run reads them.
- A notebook keeps the template's cells and order; only the source, resources and hints are authored.
- `.github/managed-constraints.txt` takes the plugin's base file (the notebook installs under it); the CI bundle (VD-7386) owns it afterwards.
- The Fabric CI files under `.github/` stayed until VD-7386 installed the Databricks bundle (DBX-D8).

## Tasks

### Task 1: dbt project on dbt-databricks

- [ ] `transformation/profiles.yml`: profile `dbt_databricks`, target `prod`, catalog `nyctaxi_prod`, schema `main`; host, warehouse path and token from the environment.
- [ ] `dbt_project.yml`: profile `dbt_databricks` (made literal in VD-7386); the table-materialisation comment gives DBX-D2's reason.
- [ ] Macros (DBX-D1): the plugin's `_family/shared-container/templates/{source_defer,generate_schema_name}.sql`, unchanged.
- [ ] Sources (DBX-D10, DBX-D5): `database: "{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`; column names as they land.
- [ ] `.sqlfluff`, `requirements-dev.txt` (DBX-D6); `tests/test_maps.py` and `tests/test_platform_prose.py` assert the Databricks shape.
- [ ] `dbt parse` and `dbt ls` offline; sqlfluff over `models/`. Commit.

### Task 2: dlt pipeline notebooks

- [ ] `ingestion/{tlc,ops,mdm}_pipeline.ipynb` from the template: the Fabric notebooks' sources, datasets (`bronze`, `ops_raw`, `mdm_raw`), resources and hints; `ops` keeps `trips=yellow_trips`, `mdm` keeps `zone_lookup=zone_rows`.
- [ ] `ingestion/.dlt/config.toml`: the template merged in (DBX-D7), the Fabric destination and Key Vault provider out; `ingestion/requirements.txt` comment.
- [ ] Delete the `.Notebook` folders. Tests that read a notebook read the `.ipynb`. Commit.

### Task 3: orchestration bundle

- [ ] `databricks.yml` (bundle `nyc-taxi-databricks`) and `orchestration/nyc_taxi_refresh.job.yml`: three notebook tasks in parallel, then `dbt build`; no schedule (the Fabric pipeline had none); tags `project=nyctaxi-databricks`.
- [ ] Delete `orchestration/nyc_taxi_refresh.DataPipeline` and `nyc_taxi_build_dbt.Notebook`. `validate-job.py` exits 0; `--sandbox` exits 1 (DBX-D11). `databricks bundle validate -t sandbox`. Commit.

### Task 4: live runs (Intent-shaped)

- [ ] Each notebook: a safety run (`--limit 1 --dev-mode`), then a full load (`--limit -1`) into the Intent's prefixed schemas. Settle VD-7442 from the first run.
- [ ] dbt `build` of every model, test, seed and snapshot on Studio's profile shape with `--defer --state` against a manifest compiled offline for production, reading the Intent's own loads through `source()`.
- [ ] Record both in `docs/verify/2026-10-28-vd-7385-databricks-runs.md`; drop the Intent's schemas. Commit.

### Task 5: prose that describes the code

- [ ] Every `VD-7385` entry in `LAKEHOUSE_PROSE_OWNED_LATER` leaves: ADR 0017 superseded by a Databricks ADR, `docs/design/pipelines/*.md`, the onboarding templates, `repo-map.json`'s sections, `test-map.json`.
- [ ] `databricks-best-practices.md` § Still to probe, `skill-changes.md`. `pytest`, `ruff`. Commit.
