---
name: ontology
description: "Use when the Domain's business ontology (Apache Ossie concepts and relationships rendered from the glossary) or an ontology mapping onto the semantic layer's Ossie documents must be created, extended or brought up to date after an Ossie document change, or when asked which concept a table carries or why it has none. Do not use to review the ontology before commit (use validating-ontology), to author the Ossie documents (use semantic-model) or to change the glossary itself (use domain-modeling)."
user-invocable: false
---

# Ontology

Leaves the Domain's business ontology current and structurally green: one ontology document of concepts and relationships, rendered from `CONTEXT.md`, plus one mapping document per Ossie document. The ontology is the only artifact that states an object is the same object across the Ossie documents. It is a declaration: nothing parses, converts or executes a mapping.

`SKILL_DIR` in the commands below is `SKILL_DIR=<this skill's directory>`; substitute it, the runtime does not expand it. The scripts belong to the `semantic-model` skill. Every command runs from the Domain's repository root and prints JSON on stdout.

## Process

1. Read `CONTEXT.md`, then resolve the paths below from the Domain's `repo-map.json`, taking the default where the Domain declares none.

   | Path | Read from `repo-map.json` | Default |
   | --- | --- | --- |
   | Ontology directory | the directory of `artifact_paths.ontology` | `ontology/` |
   | Ossie directory | the directory of `artifact_paths.logical_model` | `logical-model/` |

2. Read the glossary, every Ossie document the change reaches, and the SQL of every dataset a concept could reach. Read the allowed fields from the vendored Ossie ontology and mapping specs under `../semantic-model/scripts/ossie_vendor/` (its README names each file) before writing a construct: a field you half-remember is not in the spec.
3. Classify every table the change reaches with `references/classification.md` before declaring or omitting any concept. A table that fits no row is a question for the user, never the nearest row.
4. Declare the value types, then the entity types with `identify_by`, then the relationships, under the rules below.
5. Write one mapping per Ossie document the concepts reach. A document no concept reaches gets no mapping, and its own description says why.
6. Run the structural gates and require exit 0 from the whole chain; fix a failure and re-run before going further.

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" validate <ontology-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" refs <ontology-dir> <model-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" glossary <ontology-dir> CONTEXT.md
   ```

7. Load `validating-ontology` for the coverage and content review before commit.
8. Report the concepts declared and mapped, each table's classification, each document and relationship left unmapped with its reason, and that the ontology is declaration-only.

## Rules

1. **The glossary is the source.** Every concept names a `CONTEXT.md` term. A term for a thing with identity gets a concept; a term for a rule, decision, measure, period or classification stays prose. A concept whose term is missing is one change with the term, through `domain-modeling`, or it is not declared: the ontology never invents vocabulary.
2. **One ontology, one mapping per document.** Concepts are global and never cloned per document; a mapping references exactly one Ossie document.
3. **Identity is natural.** `identify_by` names a relationship to a `ValueType` holding the natural key: never a surrogate, never a version. A relationship's referent expression carries the target concept's own identity; a foreign key that is a version of the target leaves the relationship unmapped. `refs` fails a version surrogate and a partial identity and warns on a key that is not the dataset's natural or row-level primary key, and a report names a key with no natural code beside it as a surrogate rather than inventing a code.
4. **One direction per relationship.** Declare the direction the foreign key has, `ManyToOne`; only an identifying relationship is `OneToOne`. The inverse is implicit and never declared. Two roles to one concept are two relationships, each named for its role.
5. **Versioning is not a concept.** History, valid time and as-of belong to the Ossie documents. A document that exposes only a version surrogate for a concept leaves the relationship unmapped and reports the gap.
6. **Layer-agnostic expressions.** A mapping expression is exactly `dataset.field` as the referenced document declares it: never a schema, table or layer, never a bare field. A dataset at any layer can populate a concept, and a concept can be declared ahead of any dataset when its description says so.
7. **Declaration-only.** `validate` warns on `requires`, `derived_by`, `prefixes`, `custom_extensions` and an `iri` on a concept or relationship, because nothing evaluates them: state such a rule in the Domain's decision record (ADR) instead, unless the user decides otherwise. A mapping's `ontology_ref` and `semantic_model_ref` may carry an `iri`; it names a document, not a meaning.

## When an Ossie document changes

The Ossie document change and the ontology change are one change: a mapping can still name a real `dataset.field` while the column now holds a version, a different grain or a narrower population.

- Re-run `refs` after the Ossie document edit; it catches a renamed document, dataset or field, a concept mapped on only some of its identity, and identity moved onto a surrogate.
- Add the mapping entry for every new dataset that carries a concept.
- When identity moves (a grain change, a Type 1 dimension becoming Type 2, a natural key replaced by a surrogate), change the concept, its `CONTEXT.md` sentence and every mapping of it in the same commit.

## Red flags — stop and re-check

- "The join column is the identity." A surrogate that changes per version is not identity, and a join column is a referent only when it carries the target's identity.
- "It validates, so it works." Validation proves shape; no evaluator reads an expression.
- "The term is implied." Add the term in the same change, or drop the concept.
- "This document has no concepts, so it needs no mapping note." Say why in its description; silence reads as covered.
- "Every table needs a concept," or "the glossary is the coverage list." Classify the tables, then check the terms.
- "It is close enough to one of the rows." Ask.
- "The schema allows `requires`." Allowed is not evaluated; the rule belongs in an ADR.

All of these mean: read the glossary and the SQL, and let a missing answer be a question, not an omission.
