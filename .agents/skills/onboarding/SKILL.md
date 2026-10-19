---
name: onboarding
description: "Use only when the user asks to onboard this repository into a Vibedata domain: an empty repo, or an existing dbt and dlt repo that has no repo-map.json or convention skills in .agents/skills/ yet. Do not use for adding sources or models, for any other build task, or to refresh an already onboarded repo."
user-invocable: true
triggers: [onboard this repo, onboard into vibedata, onboard into a vibedata domain]
---

# Onboarding

Onboarding is an intent kind. It captures what the repo already does, so later intents can work in it, and files everything that should change for triage. It ships context, not code.

## When it applies

Decide at the requirement step, from the repo and the Domain Lakehouse:

| Repo | Domain Lakehouse | Path |
| --- | --- | --- |
| Empty | Empty | Greenfield: [greenfield.md](references/greenfield.md) |
| Has dbt or dlt code | Has data | Brownfield: the rest of this skill |
| Has dbt or dlt code | Empty | Brownfield, proposing the Domain's seeding first: [base-setup.md](references/base-setup.md) (Empty Domain Lakehouse) |
| Empty | Has data | Not supported yet: say so and stop. A migration assessment of an existing warehouse is future work |

## The two stages

1. **This intent**: capture conventions, write the context, file the onboarding review, ship one PR.
2. **Later intents**: each review finding an engineer picks up is a normal intent (requirement, design, build, verify, ship). An intent that changes code compares output before and after in its own session.

So during onboarding you change no model, pipeline or human document. A problem you find goes in the review, even when the fix is one line. The only other changes are the base setup in [base-setup.md](references/base-setup.md): two `dbt_project.yml` lines the sandbox build needs, and files added where the repo has none.

## Loop phases

| Phase | Work |
| --- | --- |
| Requirement | Scope: which dbt projects and dlt pipelines. The deliverable is the context and the review. |
| Design | Discover the repo (dbt project, dlt pipelines, profiles, CI, existing documents) and run a build on the sandbox `ephemeral_dev` target, deferring to the Domain. The runtime provides that profile; the repo's own `profiles.yml` `prod` target is the Domain's, for its job notebooks and releases, so do not ask which target the sandbox uses. First run the base commands: [base-setup.md](references/base-setup.md). Then build the inventory: [inventory.md](references/inventory.md). Confirm it: [grilling.md](references/grilling.md). Find domain-skill candidates: [domain-skills.md](references/domain-skills.md). |
| Build | Write `repo-map.json`, `test-map.json`, the map tests, the `AGENTS.md` index and `.agents/skills/` from the confirmed inventory, starting from [templates/](templates/), plus the base setup files and base convention skills in base-setup.md. Write confirmed domain skills under `.agents/skills/`. `domain-modeling` writes `CONTEXT.md` and the ADRs for decisions already in the code. Write design records as the `designing` skill and `.agents/skills/design-records/SKILL.md` say, only where a model or pipeline makes a decision its code does not explain. A `D-NN` line is a choice plus its reason; a line that only says what the code does is not a decision. Handle existing documents: [existing-docs.md](references/existing-docs.md). Declare `docs/review/` and `docs/proposal/` in `repo-map.json`. Run `install-ci`. Run `reviewing` with type `onboarding`, including the checks in base-setup.md. |
| Verify | Base commands, map tests in the sandbox, CI, ADR citations, then the dry run: [dry-run.md](references/dry-run.md). |
| Ship | One PR. The description lists where each existing convention went, and recommends a trial intent after merge: a standard prompt, with its trajectory reviewed. |

## Where things go

| Thing found | Destination |
| --- | --- |
| A location or identity a script can check | `repo-map.json` |
| A must or never for every change of a kind | A convention skill in `.agents/skills/` |
| A multi-step procedure only this repo has, confirmed by the user | A procedure (domain) skill in `.agents/skills/` |
| A decision with a reason (why this grain, this filter, this key) | ADR |
| A business term | `CONTEXT.md` |
| A decision one model or pipeline makes that its code does not explain | That model's design record |
| Anything that should change | Onboarding review finding |

## Common mistakes

| Mistake | Instead |
| --- | --- |
| Design record lists inputs, tests, columns, SQL, or decisions that only describe the code ("vendor resolved the same way", "key is an md5 of the flags") | Grain, `D-NN` decisions with their source, rejected alternatives, consumers, history. Figures and check results go in a verification file, never the record. No record when there is nothing beyond the code. |
| Conventions written into `AGENTS.md` | `AGENTS.md` is an index; conventions go to convention skills. |
| Editing README or CONTRIBUTING, or linking agents to them | Leave human documents alone. Tell agents not to read them. |
| Fixing a tracked generated file, a broken config path or a lint setting now | A review finding. |
| Asking the user what the code already answers | Infer, show the inventory, ask only the three kinds of question in grilling.md. |
| An ADR rationale you made up | Write the decision, mark the reason `inferred from code`, and file it for confirmation. |
