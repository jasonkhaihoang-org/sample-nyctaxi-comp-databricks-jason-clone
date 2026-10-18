# Skill change notes

Findings that feed `R-11` (list of skill changes, with what `init` must do for greenfield and brownfield). Recorded as they surface; not yet organised.

## init

- Brownfield: detect the existing layout (dbt project dir, design-record layout, test location, existing ADRs and `CONTEXT.md`) and write `repo-map.json` from it, rather than seeding template defaults.
- Greenfield: write `repo-map.json` with default locations, plus `AGENTS.md` and `.agents/skills/`.
- Today `init` writes only `AGENTS.md`, with no Artifact Paths table and a staging layout (`staging/<source>/`) that existing repos may not use.

## Locations

- Skills read `layers.<x>.built_by` from `repo-map.json` to choose a procedure (`dlt` routes to `generating-dlt-pipeline`, `dbt` to `generating-dbt-model`) instead of guessing from folders.

- Skills resolve artifact locations from `artifact-paths.md` defaults plus an `AGENTS.md` override. Decision: they should read `repo-map.json` instead.
- The intent root is set by Studio through `VD_INTENT_DOCS_ROOT`, so it is platform-owned today.

## Conventions restated in skills

- Naming, folder layout, SQL style, test policy, commit format and business defaults are restated across several skills. They move to `.agents/skills/`; see `conventions-inventory.md`.

## add-or-update-source / generating-dlt-pipeline

- `add-or-update-source` assumes a connector from the catalog (`dlt-verified` or `dlt-builtin`), mounted at `/data/connector-sources/`. A source that fetches Parquet over HTTP (TLC) is a custom source; no route covers it.
- Reference data defined inline (`VALUES` lists) has no obvious home under dlt.
- Generated (synthetic) sources have no route either: a generator that writes landing files for dlt is a simulator, not a connector.

- Synthetic or derived sources: a dlt transformer downstream of another resource is not covered by `generating-dlt-pipeline`, which assumes one connector per pipeline.

## Content bars

- `domain-modeling` and `designing` carry the bars for what goes into `CONTEXT.md`, ADRs and design records. Decision: they are operator rules (`.agents/skills/context/SKILL.md`, `adr.md`, `design-records.md`), so the skills shrink to "read the rule, then write". Formats read by CI stay in the skill.

## Orchestration

- `generating-orchestration` has no route for `duckdb_local`: it halts or omits when `_shared/platforms/<platform>/orchestration.md` is absent. A DuckDB lakehouse is run by scripts or notebooks. Propose a `duckdb_local` route that writes the agreed scripts and records them in `repo-map.json` `entrypoints` and `commands`.

## ADR and design links

- The ADR template has no field for the design records an ADR affects. The design-record template already cites ADRs beside each `D-NN`. Decided for this repo: an `## Affected designs` body section in each ADR (no frontmatter key, so `adr_lint.py` is unaffected). Propose adding it to the ADR template, maintained by `domain-modeling` and `designing` in the same commit, so the link is two-way.
- `adr_lint.py` flags dangling `ADR NNNN` citations under `docs/`, but nothing checks that the two sides agree. A symmetry check could sit beside `design_drift.py`.
- Studio's own ADRs link other ADRs inline and use an "Amended by" banner, and its design docs cite `ADR-NNNN` with a link; the plugin template does neither.

## CI-read formats

- `design_drift.py` and `adr_lint.py` read design-record and ADR formats, so those formats stay platform-owned unless the scripts read the rule.
