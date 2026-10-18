# Skill changes

What should change in the `vibedata-data-engineering` plugin (`~/src/studio/ext/vd-data-engineering/plugins/vibedata-data-engineering`), derived from building this repo. Paths in the Reference column are relative to the plugin root. The conventions behind each row are in `conventions-inventory.md`; the gaps found while building are in `skill-change-notes.md`.

Rows whose change has shipped, or whose target no longer exists after the VD-6872 simplification (vibedata-data-engineering#797), were removed on 2026-10-16. What remains is open or partly done. On the same day the rest were filed in Linear (below), or done in this repo's onboarding: the ADR link test and the repo-checks workflow (`tests/test_adr_links.py`, `.github/workflows/repo-checks.yml`), and loading an empty Domain database in the onboarding sandbox or proposing its seeding. The dlt preview row was dropped: onboarding's `.gitignore` lines cover it. The `duckdb_local` orchestration row was dropped: DuckDB has no native orchestrator, so orchestration is the repo's own run scripts (`orchestration/`, from onboarding's templates, named in `repo-map.json` `entrypoints` and `commands`).

## Principle

A convention belongs to one of three owners:

- **Skill** (platform): safety, correctness of the loop, and anything a CI script reads. It stays in the plugin.
- **Rule** (operator): naming, layout, style, test policy and content bars. It lives in the repo's `.agents/skills/`, and the skills read it.
- **Repo-map** (operator): where things are. It lives in `repo-map.json`, and the skills resolve locations from it.
- Standing business answers are ADRs in the repo; a skill checks them before asking.

There is no "default in the skill, override in the repo". A skill that restates a rule today should link to it and drop the text.

## `init` is retired

The onboarding skill (`.agents/skills/onboarding/`) replaces `init` for both an empty repo and an existing dbt and dlt repo. It carries what this section used to ask `init` for: the `repo-map.json`, `repo-map.schema.json`, `test-map.json` and `AGENTS.md` templates, every rule template, a generic `tests/test_maps.py`, the dbt, dlt and orchestration templates, the base commands, `ruff.toml` and the `.gitignore` lines. Each template section is marked for grilling with a recommended answer.

## Changes by skill

| Skill | Reference | Suggested change |
| --- | --- | --- |
| platform (Studio runtime) | conversation condensation | Once VD-6910 has shipped, check in the next long run that the agent still follows the repo's rules after a condensation. In run b2f37191 and the seventh HVFHV run it stopped following `workarounds` after condensing (repeated `verify.md` edits, a missed contract-check workaround). If it still drifts, the fix is to keep `AGENTS.md` and the skills it names in context through a condensation. |

## Tracked in Linear

A row that becomes a Linear issue moves here; the issue holds the work and its acceptance criteria. Status as of 2026-10-16.

| Issue | Owner | Skill or area | What it covers | Status |
| --- | --- | --- | --- | --- |
| VD-6902 | hemanta | init | Retire the `init` skill; onboarding replaces it. A plugin PR, then Studio's skill snapshot, `workflow.ts` maps and compatibility contract; `artifact-kinds.md` points at onboarding, not `/init`. | Todo |
| VD-6904 | hemanta | platform (data tools) | `summarize_data`, `profile_data`, `compare_data_profiles`, `load_tabular_to_ephemeral` and `visualize_data` read Parquet within their size bounds. | Done |
| VD-6905 | hemanta | platform (Studio runtime) | The first call after a condensation is rejected on DeepSeek thinking mode because `reasoning_content` is not passed back. | Todo |
| VD-6901 | Jason | install-ci | The shipped CI bundle carries `FAKE_WORLD` hooks, internal ticket IDs and a wrong intent-branch message into customer repos; a check keeps them out. Follow-ups: the plugin's `managed-constraints.txt` ticket IDs (VD-6939) and the Fabric live-E2E test step (VD-6940). | Done |
| VD-6910 | hemanta | platform (Studio runtime) | Studio loads the Domain repo's `AGENTS.md` and project skills (`load_project_skills: true`). | In Progress |
| VD-6912 | Trang | platform (evals); plugin fixtures | The eval provider mirrors Studio's persona, `soul_content` and project skills; the `v2-nyctaxi` fixture is re-vendored with the convention skills; the in-tree nyctaxi and project fixtures drop their `database:` vars and `../domain.duckdb` path; a capture regression eval checks the call budget, out-of-scope reads, repeated reads and credential probing. | Todo |
| VD-6914 | hemanta | this repo | Operator conventions are skills in `.agents/skills/`, not `.agents/rules/`. | Done |
| VD-6919 | Umesh | domain-modeling, designing, generating-dbt-model, generating-dlt-pipeline, shipping, planning, executing-the-plan; plugin layout | Build skills read the Domain's convention skills, `repo-map.json` and `test-map.json` instead of restating them: the ADR template, CONTEXT and design-record bars, audit columns, the `src_<connection>` default and PR body sections; artifact paths and the new-source footprint from `repo-map.json`; gates from `test-map.json`; the plugin root stated once. | Todo |
| VD-6920 | Pradip | generating-dbt-model, generating-dlt-pipeline, onboarding; platform duckdb_local | The duckdb_local and dlt platform facts: Arrow `TIMESTAMPTZ` and `timezone('UTC', col)`, `--full-refresh` after upstream change, `DLT_INGEST_LIMIT` bounds pages, the sandbox dbt command, no source `database:`, the `relations.sql` override, generic-test `arguments:`. | Todo |
| VD-6921 | Pradip | generating-dlt-pipeline, add-or-update-source | File sources and custom connectors as source kinds, with `naming = "direct"` and the parquet normalizer load columns for file sources. | Todo |
| VD-6922 | Umesh | generating-semantic-model | Helper metrics for MetricFlow ratio metrics; the semantic YAML location from `repo-map.json`. | Todo |
| VD-6924 | Umesh | planning, executing-the-plan, verifying, shipping | `plan.md` and `verify.md` written once per phase; base commands on the base commit; the Tier-1 dev dataset; verify figures from the landed table; the contract skip on duckdb_local; follow-up scope stays out of the PR; resume after a teardown autosave. | Todo |
| VD-6929 | Jason | install-ci | Deploy tracked paths only and install hooks safely in worktrees; run as a step of onboarding; ask for `VD_DOMAIN_SLUG`; `design_drift` accepts a `## Semantic Model` section. | Todo |
| VD-6934 | Umesh | Build persona; capturing-requirements, designing, planning, shipping | Each stage stop prints its summary as a message, which stays in the transcript, then asks a short question naming the artifact and the decision. Today the whole approval content goes into the question and the card renders it as one paragraph. | Todo |
| VD-6923 | hemanta | platform (Studio cost meter) | Run cost charges cache reads at the full input price. | Done |

## Order

1. Ship the onboarding skill with its templates, and retire `init`. Nothing else depends on the content rules until the skills read them.
2. Change the skills that restate a rule to read it (`domain-modeling`, `designing`, `generating-dbt-model`, `generating-dlt-pipeline`, `shipping`), one at a time, each with its eval cases.
3. Add the new routes (`add-or-update-source` for custom sources, `generating-orchestration` for `duckdb_local`).
4. Update CI (`install-ci`, `adr_lint.py`, `design_drift.py`).

## VD-6872 journey findings (2026-10-15)

Two journeys replayed real Studio intents on this repo through to shipping (vibedata-data-engineering#797, branch `feature/vd-6872-simplify-ways-of-working`): the surcharge split and tip rate (transformation, 20 min, 160 LLM calls) and the HVFHV 2024-01 source (ingestion, 40 min, 171 LLM calls). Both shipped; each failed one judged criterion.

| Owner | Reference | Finding | Change | Status |
| --- | --- | --- | --- | --- |
| add-or-update-source | `agents/build.md` `## Sizing` | The ingestion run loaded `add-or-update-source` before `capturing-requirements`; it wrote nothing before the Requirement | None yet; watch in the next runs | not reproduced in the HVFHV run of 2026-10-16 (ea85380d), which loaded `capturing-requirements` first |
