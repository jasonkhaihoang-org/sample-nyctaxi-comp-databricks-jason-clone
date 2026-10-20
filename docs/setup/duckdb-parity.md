# Keeping up with the DuckDB repo

Repo maintenance. Build agents do not read this document.

This repo is the Fabric Lakehouse copy of [`sample-nyctaxi-comp`](https://github.com/accelerate-data/sample-nyctaxi-comp). A change that lands there after the port is either taken here or recorded below with the reason it does not apply. A difference that is only the platform (paths, the dbt profile, the pipeline notebook layout, tables instead of views) is not listed; [`fabric-port-plan.md`](fabric-port-plan.md) records those.

| DuckDB change | Here | Why |
| --- | --- | --- |
| VD-6902: the plugin's `init` skill is retired; onboarding replaces it (`docs/setup/skill-changes.md`, 2026-10-19) | Applies; nothing to change in this repo | The work is in the plugin and Studio, not in a Domain repo. The row and its disposition live in the DuckDB repo's `skill-changes.md`, which this repo's [`skill-changes.md`](skill-changes.md) links for every row inherited from it. |
| VD-6424: onboarding checks the inherited DuckDB views before any build (`.agents/skills/onboarding/references/base-setup.md` § Inherited DuckDB views, 2026-10-19) | Does not apply | The check exists because a DuckDB Intent's sandbox is a renamed copy of the uploaded Domain file, so a view that names the old catalog breaks in every Intent and a rebuild hides it. Here the Intent's sandbox is its own Ephemeral Lakehouse, which starts empty and reads the Domain through `source_defer.sql` and `--defer`: it inherits no view and no catalog name. The nearest Lakehouse risk, a Spark view the SQL analytics endpoint cannot read, is already ruled out by the `dbt-models` skill (every model is a table, never a view). |
| `tools/dq.py`: local profile, join-evidence and SQL helpers | Not needed | It opens a local DuckDB file read-only, and a Lakehouse has none. An agent gets the same measurements from Studio's data tools (`profile_data`, `lakehouse_query`) against the Ephemeral or the Domain. Removed in the port ([`fabric-port-plan.md`](fabric-port-plan.md)). |
