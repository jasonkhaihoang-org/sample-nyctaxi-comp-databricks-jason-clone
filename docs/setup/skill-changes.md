# Skill changes

Repo maintenance. Build agents do not read this document.

What should change in the `vibedata-data-engineering` plugin, found while porting this repo to a Fabric Lakehouse. Paths in the Reference column are relative to the plugin root. The rows inherited from building the DuckDB repo are in that repo's [`docs/setup/skill-changes.md`](https://github.com/accelerate-data/sample-nyctaxi-comp/blob/main/docs/setup/skill-changes.md). The `.agents/skills/workarounds` rules point here when the plugin gap they cover is specific to Fabric.

| Skill | Reference | Suggested change | Status |
| --- | --- | --- | --- |
| `fabric_lakehouse` dbt | `_shared/platforms/fabric_lakehouse/dbt.md` § Sandbox run | Name the full sandbox command: the runtime wrapper `scripts/vd-intent-context-run.sh`, `--target ephemeral_dev` and `--defer --state /cache/prod-target`. Until then `.agents/skills/workarounds` states it. | open |
| `fabric_lakehouse` dialect | `_shared/platforms/fabric_lakehouse/dialect.md` | State how staging converts a dlt-landed UTC timestamp to the wall-clock value on Spark, as the DuckDB guidance gives `timezone('UTC', col)`. The onboarding templates ask the first staging model to prove it instead. | open |
| `generating-dlt-pipeline`, `fabric_lakehouse` dlt | `skills/generating-dlt-pipeline/SKILL.md`; `_shared/platforms/fabric_lakehouse/dlt.md` | State that `DLT_INGEST_LIMIT` bounds pages, not rows (carried over from the DuckDB repo's row for `duckdb_local/dlt.md`). | open |
| `onboarding` (repo draft) | `.agents/skills/onboarding/` | The draft is written for one platform at a time: this repo's copy is Fabric Lakehouse, the DuckDB repo's is DuckDB-local. Before it moves into the plugin, the platform-specific rows (profile, macros, orchestration, materialisation, SQL dialect) need a per-platform reference, as the plugin's `_shared/platforms/` does. | open |
