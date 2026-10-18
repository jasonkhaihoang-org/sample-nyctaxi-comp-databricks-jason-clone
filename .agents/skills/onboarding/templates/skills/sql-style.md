---
name: sql-style
description: "Use when writing, formatting or linting SQL in dbt models, tests or macros."
---

# SQL style (B7)
<!-- onboarding
ask: yes
question: Which SQL style?
recommended: Lowercase keywords, `snake_case` identifiers, explicit `join ... on`, one clause per line, comments say why.
alternatives: uppercase keywords.
-->

- Lowercase keywords.
- `snake_case` identifiers.
- Explicit `join ... on`; never an implicit join in `where`.
- One clause per line for anything beyond a trivial select.
- Comments explain why, not what.

## Enforcement
<!-- onboarding
ask: yes
question: How is style enforced?
recommended: sqlfluff in CI, Spark SQL dialect, 120-character lines; list every excluded rule and why.
alternatives: no linter; a longer line limit.
-->

Formatting is checked in CI by sqlfluff (`sparksql` dialect) using the repo's `.sqlfluff`: lines up to 120 characters. List here every rule `.sqlfluff` switches off and why. Fix with care: check the diff, because `sqlfluff fix` can drop a `values` column alias list.
