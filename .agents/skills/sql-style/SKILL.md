---
name: sql-style
description: "Use when writing, formatting or linting SQL in dbt models, tests or macros."
---

# SQL style (B7)

- Lowercase keywords.
- `snake_case` identifiers.
- Explicit `join ... on`; never an implicit join in `where`.
- One clause per line for anything beyond a trivial select.
- Comments explain why, not what.

## Enforcement

Formatting is checked before every push by sqlfluff (`databricks` dialect, jinja templater with every project macro but `source_defer.sql`; the Databricks CI bundle runs no lint gate) using the repo's `.sqlfluff`: lines up to 120 characters, and these rules switched off because they conflict with the established style: implicit table aliases (AL01), bare `join` (AM05), select-target order (ST06, ST09), quoted source column names (RF06), reference qualification (RF02) and one-select-target-per-line layout (LT09). Run it locally with `sqlfluff lint transformation/models` and fix with care: check the diff, because `sqlfluff fix` has dropped a `values` column alias list before.
