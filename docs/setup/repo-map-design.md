# repo-map.json design

Modelled on the studio `repo-map.json` (`~/src/studio/repo-map.json`, schema in `~/src/studio/.claude/repo-map.schema.json`), tailored for a data-engineering repo. Describes the repo as it will be after the build in `requirements.md`; not yet created.

## Role

- `repo-map.json`: where things are. Directories, artifact locations, entrypoints, commands. Skills resolve it to find or write a file.
- `.agents/skills/`: how to work. Naming, style, test policy, commit format, business defaults.
- `AGENTS.md`: the entry point that indexes both.

Test for edge cases: if a skill must resolve it to find or write a file, it goes in the repo-map; if it is a judgment applied while writing, it is a rule.

## Fields

Kept from studio: `generated_at`, `repo_root`, `primary_languages`, `package_managers`, `build_systems`, `test_frameworks`, `entrypoints`, `modules`, `key_directories`, `commands`, `key_references`, `notes_for_agents`.

Dropped: `deleted_directories`, web-app dependency maps, `conventions` (moved to rules).

Added for data engineering: `layers` (one entry per schema), `sources`, `artifact_paths`.

## Sketch

```json
{
  "generated_at": "2026-10-14T00:00:00Z",
  "repo_root": "sample-nyctaxi-comp",
  "primary_languages": ["SQL", "Python", "YAML", "Markdown"],
  "package_managers": [{"name": "pip", "manifest": "ingestion/requirements.txt"}],
  "build_systems": [
    {"name": "dbt (duckdb)", "config_files": ["transformation/dbt_project.yml", "transformation/profiles.yml"]},
    {"name": "dlt", "config_files": ["ingestion/.dlt/config.toml"]}
  ],
  "test_frameworks": [
    {"name": "dbt tests", "scope": "generic tests in _*.yml, singular tests, unit tests", "config_files": ["test-map.json"]}
  ],
  "layers": {
    "bronze":       {"schema": "bronze",       "built_by": "dlt",    "path": "ingestion/"},
    "staging":      {"schema": "staging",      "built_by": "dbt",    "path": "transformation/models/staging/"},
    "intermediate": {"schema": "intermediate", "built_by": "dbt",    "path": "transformation/models/intermediate/"},
    "core":         {"schema": "core",         "built_by": "dbt",    "path": "transformation/models/marts/core/"},
    "agg":          {"schema": "agg",          "built_by": "dbt",    "path": "transformation/models/marts/agg/"},
    "finance":      {"schema": "finance",      "built_by": "dbt",    "path": "transformation/models/marts/finance/"},
    "ops":          {"schema": "ops",          "built_by": "dbt",    "path": "transformation/models/marts/ops/"},
    "ops_raw":      {"schema": "ops_raw",      "built_by": "dlt",    "path": "ingestion/"},
    "mdm_raw":      {"schema": "mdm_raw",      "built_by": "dlt",    "path": "ingestion/"}
  },
  "sources": {
    "tlc": {"kind": "dlt", "dataset": "bronze",  "pipeline": "ingestion/tlc_pipeline.py", "docs": "ingestion/docs/tlc.yml"},
    "ops": {"kind": "dlt", "dataset": "ops_raw", "pipeline": "ingestion/ops_pipeline.py", "docs": "ingestion/docs/ops.yml"},
    "mdm": {"kind": "dlt", "dataset": "mdm_raw", "pipeline": "ingestion/mdm_pipeline.py", "docs": "ingestion/docs/mdm.yml"}
  },
  "artifact_paths": {
    "design_record_model": "docs/design/models/{layer}/{model}.md",
    "design_record_pipeline": "docs/design/pipelines/{pipeline}.md",
    "context": "CONTEXT.md",
    "adr": "docs/adr/{nnnn}-{slug}.md",
    "dbt_project": "transformation/",
    "dbt_sources": "transformation/models/staging/_sources.yml",
    "singular_tests": "transformation/tests/",
    "ingestion_root": "ingestion/",
    "pipeline": "ingestion/{name}_pipeline.py",
    "resource_docs": "ingestion/docs/{connection}.yml",
    "orchestration": "orchestration/",
    "test_map": "test-map.json"
  },

  "entrypoints": {"ingest": "ingestion/tlc_pipeline.py", "transform": "transformation/dbt_project.yml"},
  "modules": {"intermediate": {"path": "transformation/models/intermediate/", "description": "..."}},
  "commands": {
    "ingest": "cd ingestion && python tlc_pipeline.py",
    "build": "cd transformation && dbt build",
    "unit_tests": "cd transformation && dbt test --select test_type:unit",
    "docs": "cd transformation && dbt docs generate"
  },
  "key_references": {"provenance": "docs/setup/data-provenance.md", "rules": ".agents/skills/"},
  "notes_for_agents": {
    "reporting_window": "report_start/report_end are dbt vars, not a sampling control",
    "synthetic_data": "ops_raw and mdm_raw are generated; see docs/setup/data-provenance.md"
  }
}
```

## Decisions

- `artifact_paths` keys are as in the sketch. Intent paths are not included (skill-owned). Skills read `layers.<x>.built_by` to choose a procedure. User answer.
- The orchestration scripts and the test map are listed in `entrypoints`, `commands` and `artifact_paths`. User answer.
- `ops_raw` and `mdm_raw` are loaded by dlt like TLC bronze (`built_by: dlt`); the generators become source simulators that write landing files. User answer.
- Each schema has its own `layers` entry (`core`, `agg`, `finance`, `ops` are separate), not one combined gold entry. User answer.

## Open

