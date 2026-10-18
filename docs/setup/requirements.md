---
kinds: [project-config]
---

# Requirement: Port sample-nyctaxi-comp to a Fabric Lakehouse Domain

Repo maintenance. Build agents do not read this document.

## Ask

Make this repo the Fabric Lakehouse version of [`accelerate-data/sample-nyctaxi-comp`](https://github.com/accelerate-data/sample-nyctaxi-comp), the DuckDB model-answer Domain repo. It should have the same data product, conventions, context documents and seeding story, laid out the way the `vibedata-data-engineering` plugin expects for `fabric_lakehouse`. Then Studio onboarding and journeys can run against Fabric the same way they run against DuckDB.

The DuckDB repo was copied in unchanged from `main` at `b2be6db`. How that repo was built (its requirements, work plan, conventions inventory and skill-change notes) stays in that repo's `docs/setup/`. This folder holds only what the port adds.

Tracked in Linear as VD-6996, with sub-issues VD-6997 (context layer), VD-6998 (code) and VD-6999 (release and seeding).

## Requirements

- [ ] `R-01` The agent-context layer describes a Fabric Lakehouse Domain — accept when `AGENTS.md`, `.agents/skills/`, `CONTEXT.md`, the ADRs, the design records and `repo-map.json` `notes_for_agents` name no DuckDB-only runtime (`domain.duckdb`, `VD_EPHM_DUCKDB_LOCAL_PATH`, `relations.sql`, the `run_*.py` scripts, `duckdb_local`), checked by `tests/test_platform_prose.py` — source: VD-6997
- [ ] `R-02` The repo uses the plugin's `fabric_lakehouse` layout — accept when the dlt pipelines are `ingestion/<name>_pipeline.Notebook/`, orchestration is `orchestration/nyc_taxi_refresh.DataPipeline/` with `orchestration/nyc_taxi_build_dbt.Notebook/`, and `repo-map.json` and `test-map.json` name those paths and `tests/test_maps.py` passes — source: VD-6997, VD-6998
- [ ] `R-03` The data product is unchanged — accept when the dbt project has the DuckDB repo's model set, tests and semantic model, builds on `dbt-fabricspark`, and `int_trips_conformed` matches the DuckDB build's row count for the same months — source: VD-6998
- [ ] `R-04` Only Domain coordinates and portable item ids are committed — accept when the only ids in the repo are the Domain's (the `prod` target of `transformation/profiles.yml`, `[destination.filesystem]` of `ingestion/.dlt/config.toml`, `.workflow/ci-config.yml`) and each Fabric item's `logicalId` with the activity references to it, and no Ephemeral Lakehouse or workspace object id appears, checked by `tests/test_platform_prose.py` — source: VD-6997, plugin `fabric_lakehouse/destination-staging.md` and `_family/fabric/dbt-job-notebook.md`
- [ ] `R-05` A Domain can be seeded from the repo — accept when `docs/setup/seeding-the-domain.md` produces a released Domain (Q1 2024 loaded, every model built, production manifest published) that an Intent's `--defer` build resolves against — source: VD-6999
- [ ] `R-06` Plugin gaps are recorded — accept when every gap found during the port has a row in `skill-changes.md` — source: VD-6997

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Platform | Fabric Lakehouse first. A Fabric Warehouse version follows as its own repo or branch | user answer |
| Layout | The plugin's `fabric_lakehouse` layout, not the Fabric Git `src/` tree the repo had before | user answer |
| Data window | Q1 2024, as in the DuckDB repo. The Domain is seeded with the full Q1 in one `nyc_taxi_refresh` run (2026-10-19): Fabric has no upload limit, and the run took about 19 min | user answer |
| Starting point | The DuckDB repo's `main`, imported whole and then retargeted. The earlier Fabric tree (fork of `97862f7`) was removed | user answer |
| Names | Pipeline notebooks `tlc_pipeline`, `ops_pipeline`, `mdm_pipeline`; Data Pipeline `nyc_taxi_refresh`; dbt job notebook `nyc_taxi_build_dbt`; Domain slug `nyc-taxi-fabric-demo` | plan |
| Delivery | One branch and one PR for VD-6997, VD-6998 and VD-6999 | user answer |
