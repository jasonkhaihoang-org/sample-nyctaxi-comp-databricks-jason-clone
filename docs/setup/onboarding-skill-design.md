# Onboarding skill: design

Repo maintenance. Build agents do not read this document.

## Purpose

A customer brings a repo that already uses dbt and dlt. Onboarding turns it into a Vibedata domain repo, the way this repo was set up: the conventions in the code are captured as rules, `repo-map.json` and domain skills, the context documents are written, and everything the onboarding finds that should change is filed in a review for triage. Converting raw scripts to dlt and generating synthetic data are out of scope.

The drafts live in this repo under `.agents/skills/` so they can be dry run against representative customer repos (the two skill folders are copied into each). They assume the plugin changes in [`skill-changes.md`](skill-changes.md) have shipped. Onboarding replaces the plugin's retired `init` (VD-6902). They point at plugin skills; they do not restate them.

## Decisions

| ID | Decision |
| --- | --- |
| O-01 | Two stages. Stage 1 is the onboarding intent: context only, one PR, no model or pipeline changes beyond what the build and the map tests need. Stage 2 is the triage of the review: each item an engineer picks up is a normal intent (requirement, design, build, verify, ship). An intent that changes code does its own side-by-side comparison. Onboarding keeps no baseline. |
| O-02 | Conventions go to one destination each. `repo-map.json`: facts about location and identity a script can check. Rule: a "must" or "never" for every change of a kind, read by a plugin skill. Domain skill: a multi-step procedure only this repo has and no plugin skill covers. When a plugin skill covers the task, the repo-specific part is a rule, not a competing skill. |
| O-03 | It runs as a Studio build agent in the sandbox, with the customer in the conversation. |
| O-04 | Infer, then confirm. Build the whole inventory from the code and docs (grill-with-docs), show it as one table, and ask one question at a time only about inconsistent conventions, decisions the code does not explain, and conventions with no clear destination. |
| O-05 | The review holds five kinds of finding: `platform` (something a plugin skill or audit surface needs), `convention` (code that breaks the repo's own confirmed convention), `bug`, `gap`, `style`. Nothing is fixed during onboarding; all five are filed for triage. |
| O-06 | Reviews are not only for onboarding. One `reviewing` skill writes any review type (onboarding, security, performance, cost, data quality) to `docs/review/`. |
| O-07 | A finding is triaged to `intent`, `proposal → P-NNNN`, `declined: <reason>` or `deferred`. Proposals are optional, for major functional or design items that need discussion, and can come from anywhere, not only a review. |
| O-08 | Design records follow the `designing` skill and `.agents/skills/design-records/SKILL.md`: only what the code and catalog cannot tell a reader, no SQL. Written only for models and pipelines with a decision worth recording. A decision's source is `convention`, `ADR NNNN`, or `inferred from code`; inferred ones are filed in the review for confirmation. A model without a record is not a gap. |
| O-09 | Domain skills are mined from READMEs, runbooks, Makefile or script targets, CI jobs, `dbt_project.yml` comments and files that change together in git history. Candidates are confirmed in the grilling; only confirmed ones are written, a handful at most; uncertain ones become `gap` findings. |
| O-10 | Existing documentation is adopted in place, except per-piece-of-work documents (O-18). Existing ADRs and design documents stay where they are; their paths and numbering go into `artifact_paths`, and format differences are `style` findings. Agent instruction files (`CLAUDE.md`, `.cursor/rules`, `.github/copilot-instructions.md`) are mined into `.agents/skills/` and reduced to a one-line pointer to `AGENTS.md`. An existing `AGENTS.md` becomes the index, and the PR description lists where each of its conventions went. dbt YAML descriptions stay. README and other human documents are left alone and agents are told not to read them. |
| O-11 | Verification is mechanical checks plus a dry run. Checks: `tests/test_maps.py`, the CI bundle, ADR citations and the two-way ADR and design-record links. Dry run: three representative tasks (add a source, add or change a mart model, the top domain skill); for each, predict from `AGENTS.md`, the repo-map and the rules alone which files are read and changed and which command runs, then check the prediction against the repo. A miss is fixed in the context or filed as a finding. |
| O-12 | After merge, the PR description recommends a real trial: a standard prompt run as its own intent, and its trajectory reviewed. |
| O-13 | Onboarding is an intent kind. The `onboarding` skill is the kind playbook and maps each loop phase to its work; `reviewing` is a separate skill it calls. |
| O-14 | Skill descriptions are narrow so neither is picked up by a build task (below). |
| O-15 | Every onboarded repo gets the base setup: base commands in `repo-map.json`, run once in the design phase with failures filed; two `dbt_project.yml` lines the sandbox build needs (the profile from `DBT_PROFILE_NAME`, the evaluator gated by a var); `packages.yml` evaluator entry, `tests/test_maps.py`, `ruff.toml` and `.gitignore` lines added when absent; the platform rule files (`context.md`, `design-records.md`, `adr.md`, `git-and-prs.md`, `workarounds.md`) from templates in the skill; base rules in the repo's own rule files (sample loads and one full load, profile once, source existence from the repo-map, UTC conversion of dlt timestamps, rejoin tests); the `AGENTS.md` startup section and base `notes_for_agents`; five checks filed as review findings when they fail; and the repo checks (the map tests and the ADR link test), run where the user chooses. Learned from setting up this repo and four HVFHV runs on it. |
| O-16 | dbt sources name no database, `ref()` and `source()` render without a catalog (a macro template in the skill, added as part of the dbt setup), and the repo's own profile reads its path from `VD_EPHM_DUCKDB_LOCAL_PATH`. The Studio sandbox is a byte copy of the Domain file under another name, so any source catalog fails there; an empty Domain gives an empty sandbox, so onboarding sample-loads and builds it in its own sandbox, or writes a seeding proposal when that is a lot of work. |
| O-17 | The base parse is made warning-free with behaviour-free cleanups (generic-test `arguments:`, unused config paths), proven by an identical test list and identical compiled test SQL. Agents in the seventh run spent calls reading dbt's source to explain pre-existing deprecation warnings. |
| O-18 | Onboarding lays the repo out as if the plugin's artifact-path convention had always been used: existing per-piece-of-work documents move to `docs/requirement/`, `docs/plans/` and `docs/verify/` with their citations updated. No `AGENTS.md` `## Artifact Paths` table; layout the repo keeps (layered design records) is declared in `repo-map.json` `artifact_paths`. |
| O-19 | Onboarding is the single setup path and replaces the plugin's `init`. It decides at the requirement step: an empty repo with an empty Domain takes the greenfield path (an empty, working project from templates, set by grilling file by file and section by section, each section carrying a recommended answer); a repo with dbt or dlt code takes the brownfield path; an empty repo with an existing warehouse is not supported yet (migration assessment is future work). |

## Skills

### `onboarding`

Description: "Use this skill only when asked to onboard this repository into a Vibedata domain: capture its conventions as rules, repo-map and domain skills, write the context documents, and file the onboarding review. Not for adding sources, models or any build task."

| Loop phase | Onboarding work |
| --- | --- |
| Requirement | Scope: which dbt projects and dlt pipelines, which areas. The deliverable is the context and the review, not code changes. |
| Design | Discover: dbt project, dlt pipelines, profiles, CI, existing documents; a build on the sandbox `dev` target. Inventory every convention with evidence and a proposed destination. Grill (O-04). Mine domain-skill candidates (O-09). |
| Build | Onboarding writes `repo-map.json`, `test-map.json`, the map tests, the `AGENTS.md` index and `.agents/skills/`. Write confirmed domain skills under `.agents/skills/`, `CONTEXT.md`, ADRs for the decisions already in the code, and design records (O-08). Adopt existing documents (O-10). Declare `docs/review/` and `docs/proposal/`. Install the CI bundle. Call `reviewing` with type `onboarding`. |
| Verify | O-11. |
| Ship | One PR. The description lists where each existing convention went and recommends the trial (O-12). |

References: `inventory.md` (columns and the destination test), `grilling.md` (the three triggers), `domain-skills.md` (mining, confirmation, cap), `existing-docs.md` (O-10), `dry-run.md` (O-11).

### `reviewing`

Description: "Use this skill only when asked to run a review of this repository (onboarding, security, performance, cost, data quality) and write the findings to `docs/review/` for triage. Not for code review of a pull request or for verifying an intent."

It writes one file per run, from `templates/review.md`. `templates/proposal.md` is the proposal template.

## Formats

**Review**: `docs/review/<YYYY-MM-DD>-<type>-<slug>.md`. Frontmatter: `type`, `date`, `commit` (the commit reviewed), `source` (who ran it). Body: scope, then one table row per finding: `R-n`, kind, finding, evidence (path and line, or a query and its result), suggested action, status. The file is append-only except the status column; triage edits only that column.

**Proposal**: `docs/proposal/<NNNN>-<slug>.md`, numbered like ADRs. Frontmatter: `status` (`proposed`, `accepted`, `in-intent: <intent>`, `shipped: <PR>`, `rejected`) and `findings` (review IDs, may be empty). Body: problem, evidence, options, recommendation, open questions. An intent that starts from a proposal links to it from its `requirement.md`; shipping sets the status. A proposal that makes a decision still gets its ADR from the intent.

## This repo

- `docs/review/` and `docs/proposal/` with samples:
  - `docs/review/2026-10-14-onboarding-nyctaxi.md`: real findings from this repo's setup (the trip-key mismatch, `bug`, shipped through an intent; `dbt deps` missing before build, `platform`, shipped; no CI job runs pytest, `gap`; the sqlfluff exceptions, `style`, declined and kept as a rule; some left `open`).
  - `docs/review/2026-10-14-performance-nyctaxi.md`: a second review type.
  - `docs/proposal/0001-hvfhv-in-conformed-trips.md`: bringing HVFHV trips into `int_trips_conformed`, which needs discussion because HVFHV has a different fare structure.
- `repo-map.json`: `artifact_paths.review`, `artifact_paths.proposal`, both in `key_directories`, and `notes_for_agents`: build tasks do not read reviews; read a proposal only when the intent links to it. Schema and `tests/test_maps.py` updated to match.
- `AGENTS.md`: one line on reviews and proposals.

## Out of scope

- Converting raw scripts to dlt; synthetic data.
- Plugin skill changes (assumed shipped).
- Any baseline or parity store.
