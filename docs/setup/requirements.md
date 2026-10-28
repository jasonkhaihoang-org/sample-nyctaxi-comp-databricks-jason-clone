---
kinds: [project-config]
---

# Requirement: Port sample-nyctaxi-comp to a Databricks Domain

Repo maintenance. Build agents do not read this document.

## Ask

Make this repo the Databricks version of [`accelerate-data/sample-nyctaxi-comp`](https://github.com/accelerate-data/sample-nyctaxi-comp), the DuckDB model-answer Domain repo. It should have the same data product, conventions, context documents and seeding story, laid out the way the `vibedata-data-engineering` plugin expects for `databricks`, so that Studio onboarding and journeys run against Databricks the same way they run against DuckDB, Fabric and Redshift.

This repo was started from the Fabric Lakehouse version, [`accelerate-data/sample-nyctaxi-comp-fabric`](https://github.com/accelerate-data/sample-nyctaxi-comp-fabric), at `be4a547` (its `main`), the closest sibling: both run Spark SQL on Delta. How the earlier ports were done stays in those repos' `docs/setup/`. This folder holds only what the Databricks port adds: [`databricks-port-plan.md`](databricks-port-plan.md) is its plan and [`databricks-best-practices.md`](databricks-best-practices.md) its decisions.

Tracked in Linear as VD-7383, with sub-issues VD-7384 (context layer and probes), VD-7385 (code and orchestration), VD-7386 (release, seeding and parity) and VD-7387 (the vde journey fixture).

## Requirements

- [ ] `R-01` The agent-context layer describes a Databricks Domain — accept when `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `.agents/skills/`, `CONTEXT.md`, the ADRs, the design records and `repo-map.json` name no Fabric Lakehouse runtime, checked by `tests/test_platform_prose.py` with an empty `LAKEHOUSE_PROSE_OWNED_LATER` — source: VD-7384, VD-7385
- [ ] `R-02` The repo uses the plugin's `databricks` layout — accept when the pipelines are `ingestion/<name>_pipeline.ipynb` from the plugin template, orchestration is `databricks.yml` with `orchestration/nyc_taxi_refresh.job.yml` and the plugin's `validate-job.py` exits 0, and `tests/test_maps.py` passes — source: VD-7385
- [ ] `R-03` The data product is unchanged — accept when the dbt project has the same model set, tests and semantic model, builds on `dbt-databricks`, and the Q1 counts equal the DuckDB Q1 reference — source: VD-7385, VD-7386
- [ ] `R-04` Only Domain coordinates are committed — accept when no Ephemeral catalog, Intent schema, workspace host or warehouse id appears outside the files the plugin reads Domain coordinates from — source: VD-7384, VD-7385
- [ ] `R-05` A Domain can be seeded from the repo — accept when `docs/setup/seeding-the-domain.md` produces a released Domain (Q1 2024 loaded, every model built, production manifest published) that an Intent's `--defer` build resolves against — source: VD-7386
- [ ] `R-06` Gaps are recorded — accept when every plugin, Studio or CI gap found during the port has a row in [`skill-changes.md`](skill-changes.md) — source: VD-7384
- [ ] `R-07` Every Databricks statement the agent reads is backed — accept when each cites the plugin's `databricks` guidance, Studio, or [the probe record](../verify/2026-10-28-vd-7384-databricks-probe.md), or is listed in `skill-changes.md` as still to verify — source: VD-7384

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Repo | A new repo, not a branch: CI config, releases and the vde fixture pins are per platform | VD-7383 |
| Starting point | The Fabric Lakehouse repo at `be4a547`, aligned with Studio `origin/main` and plugin `origin/main` | user answer (2026-10-27) |
| Data window | Q1 2024, for the seed and for parity (ADR 0003) | user answer (2026-10-27) |
| Orchestration | A Lakeflow job in a Declarative Automation Bundle, as the plugin's `databricks/orchestration.md` gives it | user answer (2026-10-28) |
| Plugin | The plugin's Databricks work is owned elsewhere; this port changes no plugin file and files what it finds | user answer (2026-10-27) |
| Estate | Workspace `uk-vd-spike-dbx`; catalogs `nyctaxi_prod` (Domain) and `nyctaxi_ephm` (Ephemeral); SQL warehouse `nyctaxi-wh`. Nothing in the platform matrix's `vd_spike_*` catalogs | user answer (2026-10-28) |
| Names | Pipelines `tlc_pipeline`, `ops_pipeline`, `mdm_pipeline`; job `nyc_taxi_refresh`; Domain slug `nyc-taxi-databricks`; Primary Schema `main` | plan |
| Delivery | One branch and one PR for VD-7384, VD-7385 and VD-7386 | VD-7383 |
