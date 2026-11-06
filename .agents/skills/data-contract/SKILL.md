---
name: data-contract
description: "Use when a relation on the Domain's data boundary (an input or boundary relation) is added, changed or removed, when a column a consumer reads needs a type, quality rule, grain or reference stated, when a published shape changes under a consumer, or when adopting an existing repo into ODCS data contracts. Do not use to build the dbt model or pipeline that produces the relation (use generating-dbt-model or generating-dlt-pipeline) or to review a contract (use validating-data-contract)."
user-invocable: false
---

# Data Contract

Leaves one current ODCS `v3.2.0` contract per boundary relation, the dbt and dlt keys generated from it on contracted relations, and every doubt it could not settle in the review queue. A contract is the promise a consumer reads; it is authored, and the keys that make dbt and dlt enforce it are derived from a contract by `generate`, never hand-written.

`SKILL_DIR` in the commands below is `SKILL_DIR=<this skill's directory>`; substitute it, the runtime does not expand it. Every command runs from the Domain's repository root and prints JSON on stdout, exiting 0 when it finds nothing to fix (warnings allowed) and 1 otherwise.

## Process

1. Read `CONTEXT.md`, then resolve from the Domain's `repo-map.json` the contract path (`artifact_paths.data_contract`, default `contracts/{schema}/{table}.odcs.yaml`), the review queue (`artifact_paths.review`), the Ossie documents (`artifact_paths.logical_model`), and the boundary:

   | Relation | Owes a contract |
   | --- | --- |
   | A relation in a layer with role `input` (a resource a dlt source in `sources` loads) | Yes |
   | A relation in a layer with role `boundary` (declared in `layers.<name>.role`, or derived: `built_by: dlt` → `input`; else named in `gold_layers` → `boundary`; else `internal`) | Yes |
   | A relation in a layer with role `internal` | No; one written anyway is checked like any other |
   | Any relation of a layer named in `contract_layers` | Yes, and when the map declares `contract_layers` it replaces the `input` and `boundary` rows |
   | A relation listed in `semantic_exclusions` | Still owes its contract; a boundary relation outside the semantic layer reports `boundary/excluded` (info) rather than `boundary/undeclared` |

   An input contract describes the landed input relation. Dropping or renaming source columns downstream is the developer's choice; dropping a column the contract promised is breaking.

2. Run `python3 "$SKILL_DIR/scripts/odcs.py" version`. When it reports `cli/package-missing` or `cli/package-outdated` (a runtime can carry an older build than the plugin pins), write the effective managed constraints with `python3 <plugin>/scripts/runtime_pins.py --out <scratch dir outside the repo>/constraints.txt`, run `python3 -m pip install -c <scratch dir outside the repo>/constraints.txt -r "$SKILL_DIR/scripts/requirements.txt"` once and retry; halt and report the error if it still fails.
3. Read `references/authoring-rules.md`, then take the path the change needs.

   | The change | Path |
   | --- | --- |
   | A boundary relation or column is added, changed or removed | Step 4 |
   | An existing repo adopts contracts | Step 5, then step 6 |

4. Decide the contract before the SQL or pipeline, where it is the boundary: profile the relation and the column, then edit the contract — property, promise, key, and the version the change needs — and only then change the dbt model or pipeline. A contract written before its table exists carries `status: proposed`: `check` shape-checks it but skips the orphan, no-document, boundary-agreement and `--relations` checks, `generate` writes no dbt enforcement keys for it (a proposed dlt input still gets its `COLUMNS` hints, so write the input contract as proposed, `generate`, run the pipeline, then set it `active`), and `profile` skips it; once the table exists set it `active`, then run them before commit. `check` warns `contract/active-unbuilt` when an `active` dbt contract has no successful build in `target/run_results.json`. A relation removed takes its contract with it in the same change, and a boundary dbt model change updates the Ossie documents, its ontology mapping and the contract in one change.
5. `reverse` is how an existing table gets its contract; adopt in this order, once. Rebuild the warehouse with `--full-refresh`, then run `python3 "$SKILL_DIR/scripts/odcs.py" reverse` while the existing dbt tests still carry the rules: it drafts one contract per boundary relation from the built warehouse, the Ossie documents and those tests, and returns a `finding/*` warning for every doubt. Write the findings into the review queue in the order `reverse` returns them, boundary first, then inputs, each as relation and property → evidence → question; triage each answer into the contract as a description, a rule, a relationship or a stated "no rule, because …", and leave a question nobody can answer open in the queue. Plain `reverse` never touches an existing contract (`contract/exists`), so a Domain that has contracts never runs it again; `--force` rewrites every authored contract.
6. Write the enforcement keys (`data_type`, tests, `contract`, and the dbt `description`) with `python3 "$SKILL_DIR/scripts/odcs.py" generate`, never by hand, then run the static gates and require exit 0 from the chain, where `<base-ref>` is the integration target the change merges into:

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/scripts/odcs.py" check && python3 "$SKILL_DIR/scripts/odcs.py" diff <base-ref>
   ```

   `check` warns `contract/legacy-key` for the old `arguments.valid_values` spelling of an `invalidValues` rule; rename it to `arguments.validValues` in the contract, then re-run `generate`. `check` fails `<command>/ambiguous-platform` when a contract's servers name more than one platform; keep one.

   `generate` refuses and writes nothing when a contract cannot ground a key; fix the contract and re-run. `diff` fails `diff/version-not-bumped` when the version moved less than the change needs.
   On a Domain upgraded from an earlier plugin: (a) the first `generate` writes dbt `description`s from the Ossie fields and contracts, replacing hand-written text except `{{ doc() }}` pointers and columns neither names, so move any nuance into the Ossie document or contract first; (b) until then `check` reports `generated/stale`; (c) diagnostic codes `gold/*` became `boundary/*` and `map/no-gold-layers` became `map/no-boundary-layers`, so update any Domain tooling that matches them; a layer with no `role` keeps today's boundary.
7. After the build, run the dynamic gates for each boundary relation the change touched and require exit 0. They run through the datacontract-cli engine where the engine can connect to the Intent's sandbox, or read the file `--catalog <path>` names. Where it cannot connect (the Intent states no engine credential) or lacks a driver or extra, the tool reports `engine/unavailable`, `<command>/destination-incomplete` or `profile/engine-failed` and the gate is unrun: report it as unrun, never as passing, and leave its items to the review. With no sandbox and no `--catalog` they refuse (`catalog/missing`), `<command>/unsupported-platform` is only a platform with no engine, and `<command>/destination-incomplete` names the coordinate the sandbox lacks. `check --relations --catalog <catalog.json>` compares names against dbt's catalog from `dbt docs generate` instead.

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/scripts/odcs.py" check --relations && python3 "$SKILL_DIR/scripts/odcs.py" profile --relation <schema>.<table>
   ```

   A `profile` error means the data contradicts a claim — a repeating or null primary key, a null in a `required` property, a value outside an `invalidValues` set. Fix the claim or the data; never weaken the claim to clear the run without a review finding that says why. `profile` also tests every other check the contract implies and reports a failed `nullValues`, `duplicateValues`, relationship or other library rule as a warning (`profile/null-values`, `profile/duplicate-values`, `profile/relationship-broken`, `profile/quality-failed`), at the rule's own `severity` when it states a higher one. A `profile/unchecked` warning is a check the engine could not run or measured nothing for: the claim is unproven, so report it as such and never as passing. A `profile/engine-failed` error is a run the engine could not carry out (a schema it cannot open, a missing driver, a database file written by a newer version of its engine than the one installed): fix the cause and re-run. `check --relations` reports `relations/mismatch` for a presence or logical-type difference (and `physicalType` when the platform is the contract's) and `relations/columns-unread` when it could not read the built relation's undeclared columns.
8. Write each doubt you cannot settle from the data or the business into the review queue as a finding, never as contract prose or a chat question. `check`'s warnings (`contract/no-grain` when a non-star contract has no `primaryKey` and no grain statement, `contract/no-document`) are facts; the finding is the question behind one, and a warning the queue already owns is not a second finding.
9. Load `validating-data-contract` for the review before commit, then commit the contracts and the generated keys together, in the change that moved them, and record each gate command with its exit code where the current task keeps its evidence.

`python3 "$SKILL_DIR/scripts/odcs.py" export <sql|jsonschema|avro|html|mermaid> --out <dir> [--relation <schema>.<table>] [--dialect <dialect>]` renders each contract into `<dir>/<schema>/<table>.<ext>` for a consumer who wants the shape in another format. It never writes dbt keys; `generate` owns those. Write the output outside the repository unless the change asks for it.

`python3 "$SKILL_DIR/scripts/odcs.py" results <run_results.json>` maps a dbt run's test results to the contract assertions they enforce, one JSON record per line (contract id and version, relation, property, rule, status, failures, time), reading the `manifest.json` beside it unless `--manifest` names one. It stores nothing; the caller keeps the records.

## Quick reference

| Question | Answer |
| --- | --- |
| Does a relation in an `internal` layer need a contract? | No, unless the map's `contract_layers` names its layer |
| May I write `data_type`, `data_tests`, `contract.enforced` or a dlt column hint? | Not on a contracted relation: `generate` owns them. A dbt model with no contract may carry dbt-native `contract.enforced` by hand, with hand-written `data_type` on every column |
| Which version? | Added: minor. Removed, renamed, retyped, re-keyed, re-grained, a rule withdrawn, `required` turned: major. Prose: patch. `diff` enforces it |
| A rule no dbt test can express? | Declare it in `quality` and say in its `description` that the build does not enforce it |
| Which `logicalType`? | The Ossie document's, where it declares the field; the physical type's otherwise |
| The Ossie document does not declare the column — do I add it? | No. The document is curated; the contract carries every column regardless |
| A star member (a relation an Ossie dataset names)? | No grain text and no column descriptions: the Ossie dataset and fields own them. `primaryKey` states the grain |
| Who writes the dbt `description`? | `generate`, from the Ossie field on a star member and from the contract elsewhere; a `{{ doc() }}` pointer is left alone; a column neither names keeps a hand-written one |
| Nothing to say in a section? | Omit the key |
| No warehouse for `profile`? | Report the gate as unrun with its refusal code; never as passing |
| `reverse` on a platform with no local database file? | It reads properties and logical types through the engine, not rows: `finding/unproven-nullable`, `finding/key-repeats` and `finding/open-enum` are not raised and `reverse/no-evidence` says so, so ask those questions from a `profile` run |

## Common mistakes

- A contract edited to match a hand-edited properties file. `generate` writes the properties from the contract, never the reverse.
- `required: true` or `primaryKey: true` treated as a promise `generate` does not keep. `generate` renders `required` as `not_null` and a one-column `primaryKey` as `unique`; `profile` tests the data against the declaration.
- A field added to an Ossie document so a contract property can resolve.
- A `_dlt_*` property dropped from a dbt model's contract to satisfy the loader-column rule. The enforced contract then rejects the output column.
- A boundary relation shipped with no contract (`contract/missing`), or a relation deleted while its contract stays (`contract/orphan`).
- `reverse --force` run to draft one new relation. It rewrites every authored contract.

## Red flags — stop and re-check

- "`data_type` has to land in the same commit as the SQL, so I'll write it." Run `generate`.
- "The column is missing from the contract, so append the property." A property appended is a shape copied, not a promise made: decide its promise and its version.
- "`check` is green." It compares values; it cannot see a generated key written by hand, and it never reads the data.
- "No warehouse, so `profile` can be skipped." A refusal is reported as a gate that did not run.

All of these mean: the contract is the decision, `generate` writes the keys, and the gates prove both.
