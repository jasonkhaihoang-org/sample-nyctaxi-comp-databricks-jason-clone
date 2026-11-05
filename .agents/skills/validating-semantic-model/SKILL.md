---
name: validating-semantic-model
description: "Use when the Domain's semantic layer must be checked before commit or after a boundary dbt model change, or when asked whether the Ossie documents are valid or a metric in them is trustworthy. Do not use to author or change the Ossie documents (use semantic-model)."
user-invocable: false
---

# Validating a Semantic Model

Returns a verdict on the Domain's semantic layer with a finding per problem, after two passes that both need evidence: the tools prove the documents are well-formed, and only a read of the boundary dbt model SQL proves a mapping honest.

`SKILL_DIR` in the commands below is `SKILL_DIR=<this skill's directory>`; substitute it, the runtime does not expand it. The scripts belong to the `semantic-model` skill; what each check reads, and what it cannot see, is in `references/checks.md`.

## Process

1. Resolve the Ossie directory, semantic roots, singular tests and decision-record directories as step 1 of `../semantic-model/SKILL.md` does. The ontology and its mappings are a separate step: run `validating-ontology` for them when the Domain has an ontology; content items 13–15 check the Ossie documents' side of the same facts.
2. Run the structural gates from the Domain's repository root and record each command with its exit code. Require exit 0 from `validate`, `0 coverage error(s)` from `coverage` (the `layers.<name>.path` of every layer with role `boundary`, explicit, or derived: `built_by: dlt` is `input`, else a `gold_layers` name is `boundary`, as roots, each `semantic_exclusions` relation as `--exclude`), an empty list from `suppliers` (the instrument behind content item 1), none dangling from `notes`, and nothing stale from `generate-tests --check`.

   ```bash
   SKILL_DIR="<this skill's directory>" && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" validate <model-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" coverage <model-dir> <boundary-layer-root>... [--exclude <relation>]... && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" suppliers <model-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" notes <model-dir> <tests-dir> <adr-dir> && python3 "$SKILL_DIR/../semantic-model/scripts/ossie.py" generate-tests <model-dir> <tests-dir> --check --dialect databricks
   ```

   An error means a document is malformed: fix it and re-run before going further, because nothing in the content review compensates for a document that does not parse.

   Then run the checks that read the marts, and record each one, or record that it could not run and why:
   - `bindings <model-dir> <manifest.json>` after `dbt compile`. It needs no warehouse.
   - `columns <model-dir> <catalog.json>` after `dbt docs generate` on a built warehouse.

   Both exit 1 only on a mismatch the SQL or the catalog proves:
   - a bound metric's column computed with an aggregation that cannot roll up to it;
   - a content-level key the aggregate does not group by;
   - a field's `datatype` of a different class from its column's type.

   Fix each one before the content review, because the review must not re-argue what code has settled. Each warning is a lead for the item it names. `bindings/unproven` means the SQL could not be traced; the content test still holds that binding on data.
3. Review the content from the SQL of the boundary dbt model, never from the Ossie documents' own prose; each item's evidence is a file you read and the line that settles it. Where a check in step 2 already settles part of an item, cite its result for that part and spend the review on the part code cannot see.

   <content-review>
   1. **Every declared field resolves.** Each field's `column_map` right side is a column its mart's `SELECT` produces; for a `table_type: ALIAS` handle, check the table it is an alias of. After a build, `ossie.py columns <model-dir> <catalog.json>` proves every mapped column exists; it cannot prove the right one is mapped. A field with no `column_map` entry in any source is unsupplied — a finding.
   2. **Every aggregate metric binding is honest.** `bindings` proves the aggregation function and the grouping; the population is still yours. The aggregate column computes the same aggregation over the same population as the metric: a filtered metric bound to an unfiltered column fails, and so does any table whose rows are a subset of the metric's population. Record the confirming sentence in that source's `note` and in your report — a binding whose note does not carry it is itself a finding.
   3. **Rates are rebuilt, never averaged.** A rate or ratio metric is a `derived_expression` over its numerator and denominator metrics and binds to no column; `validate` fails a binding (`computed-metric-mapped`). Check the formula against the ADR that defines the rate. A `based_on_dimensions` metric's `rule` and `across` level match the question its description states, and where a weighted and an unweighted figure both exist, each description names its weighting.
   4. **Population matches the bound metric, not the table's name.** A star-population rollup is an aggregate source even when it carries the report window or a billable filter, because the metric it supplies has the same population. It is excluded, or a filtered metric, for any metric whose population is wider — a truncation, a row-dropping join, a different denominator.
   5. **Filters, reach and bridges say what the SQL does.** A metric's `filter` restates the `CASE WHEN` or `FILTER (WHERE ...)` in its expression, no more and no less. Every `unrelated_dimensions: total` metric is a separate metric whose description says it repeats; its base still errors. A `weight` names the column that allocates, and the test the bridge `note` cites holds the sum of 1. A coarser dimension source maps only fields its level determines. Read `ossie.py dimensionality` for any metric a multi-fact query will mix.
   6. **Content is the SQL, not a guess.** Each aggregate's `content_filter` restates its `WHERE` plus every row its inner joins drop, and its `content_levels` match its `GROUP BY` level by level, with the role (`via`) the join actually uses. Each level's keys come from the dbt metadata (`primary_key`, `unique` tests, constraints) and intent, a repeating name is an attribute not a key, and every aggregate content level names the `key_columns` that carry the level's key.
   7. **The generated tests hold on data.** Against a built warehouse, run `dbt test --select assert_semantic_content_holds assert_semantic_level_keys_hold assert_semantic_levels_hold`, or report them as unrun. A content or level-key failure is a finding; what `assert_semantic_levels_hold` warns on is listed as a data finding, never a reason to weaken a declaration.
   8. **Semi-additive measures are not plain sums.** Down-days, balances, snapshots, stock levels: no `SUM` metric, and no aggregate whose grain crosses the forbidden dimension.
   9. **Refusals are recorded.** Every declared field or metric an aggregate declines to supply, and every table that cannot be mapped, carries a `note` naming why; a relation the repo map lists in `semantic_exclusions` carries its reason there instead. Refusing an undeclared physical column needs no note.
   10. **Coverage is complete.** `coverage` proves the Ossie documents' reach; the notes and the repo map's exclusions prove the gaps. A boundary table with no handle, no note and no `semantic_exclusions` entry is a finding.
   11. **Datatypes and SCD are honest.** `columns` proves each single-column field's type class against the catalog; read the SQL only for computed fields and for the SCD claim. Each field's `datatype` matches the column the upstream or ingestion SQL produces, and each `scd` claim matches the ADR that rules it — a Type 2 claim on a Type 1 source is a finding.
   12. **Documents hold whole stars.** A dataset that exists only to bridge two documents is a partition error, not a table.
   13. **The Ossie documents' terms agree with the ontology's concepts.** Every business object a description or `ai_context` names is a concept, a metric that measures an object uses that object's term, and no dataset description asserts an identity the concept contradicts. A business name `CONTEXT.md` does not hold is a finding; it shows up in the ontology review's `glossary` report as a `terms_without_concept` entry.
   14. **Every dataset a concept populates is mapped.** `refs` warns `refs/unmapped-identity-dataset` when another dataset is keyed by the same identity field; judge the rest. A dataset whose key is a concept's identity and which no mapping names understates the semantic layer, even when another dataset states the same concept.
   15. **A rename or reinterpretation lands in both.** When an Ossie document renames a business object, changes its grain or changes what a key identifies, the concept, its `CONTEXT.md` sentence and its mapping move in the same change; a concept still stating the old meaning is a finding even when every expression resolves.

   Skip items 13–15 when the Domain has no ontology.
   </content-review>

4. Fix what the Ossie documents can settle without a business decision — a missing confirming sentence, a `datatype` traceable to the upstream or ingestion SQL, an unsupplied metric whose column is obvious, a dangling reference, a note that contradicts the SQL — then re-run step 2.
5. Escalate a fix that changes what a number means — withdrawing a mapping, reclassifying a table as excluded, accepting a truncated or row-dropping source, resolving a contradiction between the Ossie documents and an ADR — through `grilling`: one finding at a time, location → evidence → options → recommendation, waiting for the ruling before raising the next. Never edit a dbt model's SQL, a seed or a macro to satisfy the Ossie documents; a wrong dbt model is a finding about that dbt model, reported.
6. Report the verdict, then each finding as location → evidence → fix, then the checks you could not run and why (no warehouse, no dbt, no catalog). A verdict of "passes" cites a file per claim, and every content fix is followed by re-running step 2: a content edit is an edit. Close with which artifacts were checked for shape and which expressions no tool reads.

## Red flags — stop and re-check

- "The tool says green." It says the file parses. The content review is unstarted.
- "The note says it was checked." Read the SQL; a note is a claim, not evidence.
- "No warehouse, so I'll assume the keys are unique." Report the unknown as unknown; never convert it into a pass.
- "One mapping looked odd but validate passed." That is a finding.
- "The Ossie document states its own intent, so it is consistent." Read the mart and the ADR; an Ossie document can be green and wrong.
- "I fixed it while reviewing, so the review is done." Re-run the gates after any fix, or the verdict describes a file that no longer exists.

All of these mean: no verdict without a cited file per claim.
