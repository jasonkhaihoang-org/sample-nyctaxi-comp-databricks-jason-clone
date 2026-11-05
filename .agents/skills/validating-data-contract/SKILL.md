---
name: validating-data-contract
description: "Use when an ODCS data contract must be reviewed before commit or before a change that touches one merges, when asked whether a contract is complete or trustworthy, or when triaging the contract review queue. Do not use to author or change a contract (use data-contract)."
user-invocable: false
---

# Validating a Data Contract

Returns a verdict on each contract in scope with a finding per problem. The tool settles shape, version and the data's agreement with each claim; this review judges only what no code can: whether the promises mean what the business means.

`SKILL_DIR` in the commands below is `SKILL_DIR=<this skill's directory>`; substitute it, the runtime does not expand it. The tool belongs to the `data-contract` skill.

## Process

1. Resolve the contract path, the review queue and the Ossie documents as step 1 of `../data-contract/SKILL.md` does, plus the business vocabulary (`artifact_paths.context`) and the decision records (`artifact_paths.adr`). The scope is every contract the change touches, every contract that declares a key one of them declares, and every contract whose Ossie document or ADR the change amends.
2. Gather the evidence from code and record each command with its exit code, from the Domain's repository root. `<base-ref>` is the integration target the change merges into.

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/../data-contract/scripts/odcs.py" check && python3 "$SKILL_DIR/../data-contract/scripts/odcs.py" diff <base-ref>
   ```

   Then, against the built warehouse, run each dynamic gate as its own command:

   ```bash
   python3 "$SKILL_DIR/../data-contract/scripts/odcs.py" check --relations
   ```

   ```bash
   python3 "$SKILL_DIR/../data-contract/scripts/odcs.py" profile
   ```

   `profile` skips contracts with `status: proposed`, which have no built relation yet, and refuses one named with `--relation`.

   | Tool | Settles | Leaves to this review |
   | --- | --- | --- |
   | `check` | Schema, boundary coverage, empty sections, agreement with the Ossie document field by field, generated keys current, loader columns | Every judgement below; a green run is the entry condition, never evidence for an item |
   | `diff` | The version moved as far as the change needs | Nothing: a `diff/version-not-bumped` is a defect for `data-contract` to fix |
   | `check --relations` | The contract and the built relation have the same columns | — |
   | `profile` | The primary key does not repeat, `required` properties hold no null, values stay inside each `invalidValues` set | Whether the key is the grain the Ossie document and SQL state |

   A static gate that fails goes back to `data-contract` before the review starts. A dynamic gate that refuses (`catalog/missing`, `<command>/unsupported-platform`) leaves its items unjudged, reported as such and never as passing.
3. Read, per contract in scope: the contract; its Ossie document, where one names the relation; the open rows of the review queue, which are doubts already asked; the relation's design record and SQL; the `CONTEXT.md` terms its prose uses; and every ADR a rule, a grain or a `required` touches.
4. Judge each item, citing a profile, a diff or a file and line for each.

   <contract-review>
   1. **The `primaryKey` is the grain.** The relation's SQL and the `profile` of its key support it, and so does the Ossie dataset where the relation is a star member. A key that is finer or coarser than the rows the SQL emits is a finding even when it holds; a `dataGranularityDescription`, where one exists, must say the same.
   2. **Each description says something a consumer can act on, and it is true.** A `{{ doc(...) }}` pointer, a sibling column's text copied over, a term `CONTEXT.md` does not hold, or a sentence the column's values contradict is a finding. On a non-star relation, count the consumer-facing properties left undescribed; a relation no Ossie document names is not exempt, its prose is its only promise. A star member carries none: the Ossie fields own them.
   3. **Each quality rule encodes the real business answer.** A rule that passes because nothing can violate it (a filter no value reaches, a threshold beyond the domain) is vacuous. A rule that forbids a value an ADR sanctions is wrong even when every row satisfies it today, and a rule narrower than the ADR it cites is the same defect from the other side. Only three library metrics with `mustBe: 0` render a dbt test; any other rule must say in its `description` that the build does not enforce it.
   4. **The contract means what its Ossie document means.** `check` proves each declared field is present with the same `logicalType` and key; read the document's purpose, key and field statements against the contract's prose. Agreement on every field and a different story in the sentences is the failure.
   5. **One key has one type across contracts.** Read the property out of every contract that declares the same key: `check` compares each contract with its own document only, so `string` in one and `integer` in another passes twice. A divergence is a finding against the document, for whoever owns the key's meaning.
   </contract-review>

5. Write each doubt the data and the business cannot settle into the review queue, in its shape: relation and property, the evidence gathered, the question that would settle it. A `finding/*` from `reverse` and a `check` warning are already questions or facts; a row the queue already holds is not a second finding, and a row nobody can settle stays open with its evidence. A defect goes back to `data-contract`, which re-runs `generate` and the gates.
6. Report the verdict, then each finding as location → evidence → the check that cannot see it → the question. Carry each `check` warning by its code, name each item left unjudged and why, and close with which items rested on profiled data, which on documents alone, and which contracts you read beside the changed one.

## Red flags — stop and re-check

- "`check` is green, so the contract is right." It proves the file is well-formed, not that its key is the grain.
- "The profile passed, so the key is the grain." It proves the key holds, not that it names what one row is.
- "No warehouse, so I'll trust `required`." Report the item as unjudged.
- "I fixed the contract while reviewing." Hand it back to `data-contract`; the review that approved the old file does not describe this one.

All of these mean: no verdict without a cited profile, diff or file per item.
