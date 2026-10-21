# VD-7052 Domain view check verification

## Scope

How Fabric resolves a Domain Lakehouse's views when an Intent reads them, and the onboarding step that follows from it ([base-setup.md § Existing Domain views](../../.agents/skills/onboarding/references/base-setup.md#existing-domain-views)). It is the Lakehouse form of the DuckDB repo's VD-6424 check. No Domain was written: the probe ran on two throwaway workspaces, deleted afterwards.

## Live probe, 2026-10-21

Two workspaces on an FTL64 trial capacity, each holding a schema-enabled Lakehouse named `vd_eval_p7052`: `vd7052_probe_domain` played the Domain and `vd7052_probe_ephm` the Intent's Ephemeral. Each held `s.t` with one row naming its side (`'domain'` or `'ephemeral'`). Spark ran through Livy sessions attached to each Lakehouse, as an Intent's dbt does. The SQL analytics endpoints were read over TDS.

### Spark views

The Domain's session created views on `s.t` named three ways:

| View | Body as written | Body as Spark stored it |
| --- | --- | --- |
| `s.v2` | `FROM s.t` | `` FROM `vd7052_probe_domain`.`vd_eval_p7052`.`s`.`t` `` |
| `s.v3` | `FROM vd_eval_p7052.s.t` | the same |
| `s.v4` | `` FROM `vd7052_probe_domain`.`vd_eval_p7052`.`s`.`t` `` | the same |

Read from the Ephemeral's session:

| Read | Result |
| --- | --- |
| `s.t`, and `vd_eval_p7052.s.t` | `ephemeral`: a name without a workspace resolves in the session's own workspace |
| `` `vd7052_probe_domain`.`vd_eval_p7052`.`s`.`v2` ``, `v3`, `v4` | `domain` for all three |
| `vd_eval_p7052.s.v2` | `TABLE_OR_VIEW_NOT_FOUND`: the Ephemeral has no such view |

So a same-named Ephemeral Lakehouse never captures a Domain view. What breaks one:

| Change | Result |
| --- | --- |
| Creating a view on a missing object (`other_lh.s.t`, or a workspace that does not exist) | Refused at `CREATE VIEW`: Spark checks the body |
| Dropping a table a view reads (`s.t2` under `s.vt2`) | The view stays in `SHOW VIEWS`; reading it fails `TABLE_OR_VIEW_NOT_FOUND` for `` `vd7052_probe_domain`.`vd_eval_p7052`.`s`.`t2` `` |
| Renaming the Domain's workspace to `vd7052_probe_domain_renamed` | Its tables read under the new name. Every view fails, `v2` included, because its stored body still names `vd7052_probe_domain` |

### SQL analytics endpoint views

T-SQL views made on the Domain's endpoint (`FROM s.t` and `FROM [vd_eval_p7052].[s].[t]`) read `domain`, also after the workspace rename, since a T-SQL name carries no workspace. The two kinds of view do not cross: the endpoint's `sys.views` lists none of the Spark views, and Spark cannot read the T-SQL views. The Ephemeral's endpoint cannot read either Domain view. An Intent's dbt build runs on Spark, so it never reads a T-SQL view; only `lakehouse_query` does.

### How an agent reaches Spark views

`lakehouse_query` runs T-SQL on the endpoint, so it cannot see Spark views. `dbt show --inline` through the runtime wrapper can, checked with dbt-fabricspark from the managed constraints against the Ephemeral:

| Command | Result |
| --- | --- |
| `` dbt show --inline "SHOW VIEWS IN `ws`.`lh`.`s`" --limit -1 `` | Lists the Domain schema's views, `vt2` included |
| `` dbt show --inline "select * from `ws`.`lh`.`s`.`t` where 1 = 0" `` | Binds, no rows |
| the same on `v2` and `vt2` after the rename | `TABLE_OR_VIEW_NOT_FOUND`, naming the missing object |
| `` dbt show --inline "select ... limit 0" `` | Syntax error: dbt-fabricspark appends its own `limit 5` |
| `SHOW SCHEMAS IN` or `SHOW NAMESPACES IN` another workspace's Lakehouse, `information_schema.views` | Not supported: `SCHEMA_NOT_FOUND` or `TABLE_OR_VIEW_NOT_FOUND` |

A second throwaway workspace checked how to bind many views in one statement. `select 1 from <view> where 1 = 0`, joined with `union all`, binds healthy views and fails `TABLE_OR_VIEW_NOT_FOUND` when one view's table was dropped. A view whose column was dropped from its table fails `UNRESOLVED_COLUMN` under `select 1` as under `select *`. `select *` cannot be unioned across views with different columns.

Without `--limit -1`, dbt wraps the statement in a limit, which `SHOW` cannot take. The wrapper runs its argument through `bash -c`, so the backticks are escaped inside an outer single-quoted string; this was checked against a stand-in wrapper with the same `bash -c "$*"` line as the plugin's. Schemas come from `lakehouse_query` on the Domain's `sys.schemas`, plus the production manifest.

### Follow-up probe, the same day

A third throwaway workspace covered what review found untested.

| Case | Result |
| --- | --- |
| T-SQL view `s.tv3` on `s.t3`, then `s.t3` dropped from Spark | `SELECT TOP 0 * FROM [s].[tv3]` kept passing for about five minutes, until the endpoint's metadata sync, then failed `Invalid object name 's.t3'` |
| Lakehouse without schemas (`flat_lh`): view `v` on table `t`, made from its own session | Stored as `FROM t`, unqualified. From another Lakehouse's session, `SHOW VIEWS IN` the flat Lakehouse (with or without `dbo`) returns no rows, and reading the view by three-part or four-part name fails `TABLE_OR_VIEW_NOT_FOUND` |

Not probed: renaming a Lakehouse, as opposed to a workspace, and renaming a table or column. The skill claims only the workspace rename and dropped objects and columns. In the `dbt show` runs above, each invocation submitted its statement to its own new Livy session.

## Outcome

The risk in the issue, a Domain view binding to the Ephemeral, does not occur. The DuckDB check's other half applies: a Domain view can be broken, and an Intent neither shows it before a build that reads it nor repairs it. A workspace rename breaks every Spark view at once. The onboarding skill now checks both kinds of view, read-only, before the base commands, on a schema-enabled Domain. On a Lakehouse without schemas it records the Spark half as unchecked.

## Guidance probe

Fresh Haiku agents read the onboarding skill and a brownfield scenario: a two-year-old Fabric Lakehouse repo, Domain populated, no command run yet. Each listed its tool calls up to the first base command. The scenario does not mention views.

| Arm | Result |
| --- | --- |
| Skill before this change, 3 agents | None checked the Domain's views. All three went straight to the `dbt_project.yml` profile edit and `dbt deps`. |
| Skill after this change, 3 agents | All three took the names from the manifest and listed schemas through `lakehouse_query`. They then listed Spark views with the exact `dbt show ... --limit -1` command, bound them with `where 1 = 0`, checked the endpoint views with `TOP 0`, and filed failures as `bug` plus the one `platform` finding. Two batched the binds as a `union all` of `select *`, which fails across views with different columns. |
| Revised wording (`select 1` in the batch, profile edit and `dbt deps` before `dbt show`), 2 agents | Both put the profile edit and `dbt deps` first. The one that reached the binds batched them as `select 1 ... union all`. |

These are observed decisions, not an onboarding run in Studio.
