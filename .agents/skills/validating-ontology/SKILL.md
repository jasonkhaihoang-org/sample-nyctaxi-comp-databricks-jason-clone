---
name: validating-ontology
description: "Use when the Domain's business ontology or its mappings onto the semantic layer's Ossie documents must be checked before commit or after an Ossie document change, or when asked whether a concept, its identity or a mapping is honest. Do not use to author the ontology (use ontology) or to review the Ossie documents themselves (use validating-semantic-model)."
user-invocable: false
---

# Validating an Ontology

Returns a verdict on the Domain's ontology and its mappings with a finding per problem. It is a separate step from `validating-semantic-model`: this skill checks the ontology against the Ossie documents, and that one checks the Ossie documents' side of the shared terms. Tools prove shape, names, resolution and the identity lint; coverage and meaning are a read.

`SKILL_DIR` in the commands below is `SKILL_DIR=<this skill's directory>`; substitute it, the runtime does not expand it. The scripts belong to the `semantic-model` skill; what each check reads, and what it cannot see, is in `../validating-semantic-model/references/checks.md` § "Coverage of the checks" and § "Behaviours worth knowing".

## Process

1. Resolve the ontology and Ossie directories as step 1 of `../ontology/SKILL.md` does, and read `CONTEXT.md`.
2. **Structure.** Run the gates from the Domain's repository root and record each command with its exit code. Require exit 0 and zero errors from each; a warning is read, not ignored.

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" validate <ontology-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" refs <ontology-dir> <model-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" glossary <ontology-dir> CONTEXT.md
   ```

   - `validate` proves each document against the vendored spec, fails an `EntityType` with no `identify_by`, and warns on `requires`, `derived_by`, `prefixes`, `custom_extensions` and a concept or relationship `iri`.
   - `refs` proves each mapping's document resolves, each concept and relationship is declared, and each expression is a `dataset.field` the document declares. Its identity lint fails an identity mapped to a version surrogate (`refs/identity-version-surrogate`) or on only some of its components (`refs/partial-identity`). It warns on an identity column that is neither the dataset's natural key nor its row-level primary key (`refs/identity-not-natural-key`, naming the keys it compared), which is legitimate for a degenerate key or a code held as an attribute: confirm each from the SQL. `mapping/none` warns on an Ossie document no mapping covers. It cannot see whether a natural-looking key is natural, or what an expression means.
   - `glossary` fails on `entity_types_without_term`. Adjudicate every `terms_without_concept` entry: a rule, measure, population, period, classification or version stays prose, and a term naming a thing with identity is a missing concept. `value_types_without_term` is expected. The report carries all three lists and the call made on each term.

3. **Coverage.** Classify every dimension and fact the Ossie documents register with `../ontology/references/classification.md`, then check:
   1. **Every table is classified.** Each has a concept or carries its exemption where a reader finds it. An unclassified table is a finding, so is a concept invented for an exempt kind, and a table the author could not classify is a blocked finding with its question.
   2. **Every concept reaches a dataset,** or its description says it is declared ahead of its data.
   3. **Every document is accounted for.** Each `mapping/none` document's description says why no concept reaches it.
   4. **Every dataset carrying a concept's identity is mapped,** even when another dataset states the same concept.
4. **Content.** Work from the dataset SQL and the Ossie documents, never from the mapping's prose.
   1. **Identity is natural.** Each `identify_by` reaches the column holding the natural key in the dbt model SQL or its staging; a key with no natural code beside it is named as a surrogate.
   2. **Direction and multiplicity match the foreign key.** A declared inverse, or two relationships where one would do, is a finding.
   3. **Cross-document identity holds.** Where two documents map one concept, both expressions identify the same real-world object.
   4. **A re-grained or versioned dataset has re-derived mappings.** A mapping that still resolves can identify the wrong thing after a grain change, a Type 1 to Type 2 change, or a natural key replaced by a surrogate.
   5. **Declaration status.** Each `validate` warning names a rule its ADR states, or is a finding.
5. Fix what needs no business decision (a missing exemption reason, an expression `refs` names, a missing mapping entry) and re-run step 2. Escalate a concept added, dropped or re-identified, or a missing term, through `grilling`, one finding at a time.
6. Report the verdict, then each finding as location → evidence → fix, then the checks you could not run and why. A verdict of "passes" cites a file per claim. Close with **Coverage** (one row per table: concept, or exempt with the reason and where it is recorded) and **Declaration versus executable** (what was checked for shape, which expressions no tool reads, and which concepts or documents are unmapped and why).

## Red flags — stop and re-check

- "The identity lint passed, so identity is natural." It reads key declarations, not the SQL; step 4 is unstarted.
- "It validates, so the mapping works." Nothing executes a mapping.
- "The glossary is the coverage list." It names what the business says, not what the lakehouse holds.
- "An aggregate is a fact." A rollup's rows are a population; it gets metrics, not a concept.
- "The name matches, so the concept is covered." A term and a concept can be spelled alike and disagree.
- "The nearest row will do." That is a question for the user.

All of these mean: no verdict without a cited file per claim.
