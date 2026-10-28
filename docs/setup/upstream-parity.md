# Keeping up with the DuckDB and Lakehouse repos

Repo maintenance. Build agents do not read this document.

This repo is the Databricks copy of [`sample-nyctaxi-comp`](https://github.com/accelerate-data/sample-nyctaxi-comp), started from its Fabric Lakehouse copy [`sample-nyctaxi-comp-fabric`](https://github.com/accelerate-data/sample-nyctaxi-comp-fabric) at `be4a547`. Each change that lands in either of them after that is recorded below: taken here, deferred to an issue, or not needed, with the reason. A difference that is only the platform (the dbt adapter and profile, the pipeline notebook layout, the orchestration bundle) is not listed; [`databricks-port-plan.md`](databricks-port-plan.md) and [`databricks-best-practices.md`](databricks-best-practices.md) record those.

The rows below are the Lakehouse repo's record of the DuckDB changes it took, up to `be4a547`. Each one's "Here" column says what it means on Databricks.

| Source | Change | Here | Why |
| --- | --- | --- | --- |
| DuckDB | VD-6902: the plugin's `init` skill and its `agents-md-template.md` are retired; onboarding replaces them (`docs/setup/skill-changes.md`, 2026-10-19) | Applies. Disposition, as the DuckDB repo records it: done (local implementation; publication pending), nothing dropped | The work is in the plugin and Studio, not in a Domain repo. Here only [`onboarding-skill-design.md`](onboarding-skill-design.md) named `init`, and it names onboarding. |
| DuckDB | VD-6424: onboarding checks the inherited views before any build (`.agents/skills/onboarding/references/base-setup.md` § Existing Domain views) | Applies in a Databricks form | An Intent reads a Domain view through `--defer` and cannot repair it. A view over a production relation builds and reads from the Ephemeral catalog ([probe](../verify/2026-10-28-vd-7384-databricks-probe.md) P1); a broken Domain view is still the release's to fix, so onboarding binds each one before the base commands. |
| DuckDB | VD-7053: `safe_divide` brackets both arguments (`transformation/macros/finance.sql`), and `assert_compound_rates_equal_their_ratio` recomputes every rate whose argument is an expression | Applies; inherited | The macro and its call sites are the same here (probe P7). |
| DuckDB | `tools/dq.py`: local profile, join-evidence and SQL helpers | Not needed | It opens a local DuckDB file read-only, and Databricks has none. Studio's `lakehouse_query` and `profile_data` cover most of it against the Ephemeral or the Domain; an agent writes join-evidence SQL through `lakehouse_query`. |
| Lakehouse | VD-7428 (`94177ae`): the defects the Lakehouse golden runs found | Inherited at `be4a547` | Each fix is in the copied tree; a platform-specific one is re-checked by the port's guard and probes. |
