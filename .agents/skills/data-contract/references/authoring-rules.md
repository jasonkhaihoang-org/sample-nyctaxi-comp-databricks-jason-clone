# Authoring rules for a data contract

What a contract may say, where each statement goes, and which version a change to it needs. Read it before writing or changing a contract.

## The contract is authored; the keys are generated

**Authored:** the document itself — `version`, `status` (`proposed` until the table exists), `schema[].name`, an optional `dataGranularityDescription` (non-star relations only), and each property's `name`, `logicalType`, `physicalType`, `required`, `primaryKey`, `description`, `quality` and `relationships`.

**Generated:** the relation entry's `contract: {enforced: true}`, every `data_type` and `data_tests` under it, the tests for a relation dbt loads from a CSV, and the column hints for a relation dlt loads (the `COLUMNS` mapping `generate` writes to `contracts.py` under the ingestion root, which the pipeline passes as each resource's `columns=` under its `columns: freeze` contract).

`generate` finds the properties file that already names the relation and writes its keys there, or creates `_generated.yml` in the layer's directory. It writes nothing it cannot ground: a property with no `physicalType`, a relationship naming no `<relation>.<column>`, a `servers[].schema` that disagrees with the map — the run refuses, writes no file at all, and exits 1. Fix the contract and run it again.

`check` then compares what `generate` would write with what is on disk (`generated/stale`). That is a comparison of values, so a hand-written `data_type` that happens to be correct passes; only running `generate` proves the key was generated. `generate` never deletes a key, so a withdrawn rule or a dropped property leaves a key `check` reports until you remove it.

## A new property is a decision about the promise

Decide these in order:

1. **What it holds.** `physicalType` from the built relation — or, before the column exists, from the profiled expression; `logicalType` as the Ossie-document section below says; `required` only when null is impossible or forbidden.
2. **What it promises.** A `description` a consumer can act on (omitted on a star member, whose column descriptions the Ossie fields own); a `quality` rule, or the stated reason there is none; a `relationships` entry where it points into another relation. `required: true` declares that a null is not allowed, and `generate` renders it as `not_null`; a one-column `primaryKey` renders as `unique`. A composite key has no per-column test, so `profile` checks it.
3. **Whether the grain moved.** `primaryKey` states it. A new column leaves it alone unless it changes what one row is.
4. **The version**, by the table below.

```yaml
version: 1.1.0                    # 1.0.0 -> 1.1.0: a property added, no consumer query breaks
schema:
  - name: <relation>
    properties:
      - name: <property>
        logicalType: boolean      # the Ossie field's datatype where it declares the field
        physicalType: BOOLEAN     # the expression's profiled type; the build proves it
        description: <what true means to a consumer>
        quality:
          - type: library
            metric: nullValues
            mustBe: 0
```

`generate` then adds `contract: {enforced: true}` to the relation, and `data_type: BOOLEAN` and `data_tests: [not_null]` to the property.

A new relation, in a Domain that already has contracts, is the same path from a sibling's document: copy its `apiVersion`, `kind` and `servers`, give it its own `id` and `version: 1.0.0`, and change every place it names the relation — `name`, `schema[].name`, `servers[].schema`.

## The version

`odcs.py diff <base-ref>` classifies every change and fails `diff/version-not-bumped` when the version moved less than the change needs. The rule it applies:

| Change | Bump |
| --- | --- |
| A property removed or renamed; a `logicalType`, `physicalType`, `logicalTypeOptions` or `primaryKey` changed; a quality rule or relationship withdrawn (a rule edited is one withdrawn and one added); `required` turned either way | Major |
| A property, quality rule or relationship added | Minor |
| A description, a `dataGranularityDescription`, `authoritativeDefinitions`, or any other prose | Patch |

`1.0.0` is a version, not a placeholder: a `1.0.0` contract that gains a column becomes `1.1.0`. A new contract needs only a valid `MAJOR.MINOR.PATCH`. A removed contract is reported (`diff/contract-removed`), because the relation's removal is the consumer-facing change.

## `quality` is the rule; the dbt test is its rendering

A rule is `{type: library, metric, mustBe}`. `generate` renders three library metrics as dbt tests, and a property's `relationships` entry as a `relationships` test: `nullValues` with `mustBe: 0` to `not_null`, `duplicateValues` with `mustBe: 0` to `unique`, and `invalidValues` with `mustBe: 0` and `arguments.validValues` to `accepted_values`. Any other metric or operator, and any `text`, `sql` or `custom` rule, states a promise the build does not enforce: keep it when it is the honest statement of the rule, and say so in the rule's own `description`. Never write the dbt test beside it, and never let a rule live only as a hand-written test.

`primaryKey` and `required` are declarations too: `generate` renders `required` as `not_null` and a one-column `primaryKey` as `unique`, a composite key has no per-column test, and `profile` tests the claims against the data.

## The Ossie document owns the logical type, not the column set

On a relation an Ossie dataset names, the contract is a projection of that document. Every field the document declares must appear — a missing one fails `check`; `logicalType` is the document's `datatype` under the standard's mapping; `DateTimeTz` carries `logicalTypeOptions: {timezone: true}` and `DateTime` carries none; a field in the document's `primary_key` sets `primaryKey: true`. A disagreement on any of those fails `check`, and the Ossie document is right.

A property the document does not declare is the contract's business: the Ossie document is a curated subset for the semantic layer, and a relation column does not enlarge it. When the field's meaning has to enter the document, that is `semantic-model`'s decision, and the two change in one commit.

## What the loader adds is not the relation's shape

A `_dlt_*` column on a relation dlt loads is added by the loader, not yielded by the resource, so the contract does not declare it; `check` fails `contract/loader-column` when one appears. A dbt model that selects such a column through is the exception: its enforced contract must declare every output column. Read which one the relation is from the map's layer, never from the column name.

## Prose, grain and type are never invented

- **Prose is authored or absent; a star member's column descriptions belong to the Ossie field.** A `{{ doc(...) }}` reference is a dbt parse-time pointer; omit it rather than copy it. `generate` writes the dbt `description` from the Ossie field on a star member and from the contract elsewhere.
- **The grain is the `primaryKey`.** A star member carries no grain text. `dataGranularityDescription` is optional, for a non-star relation whose key would mislead; never invent it. `check` warns `contract/no-grain` only when a non-star contract has neither a `primaryKey` nor one.
- **`physicalType` on every property, verbatim.** It is the warehouse's type string, never a normalized one. Read it from the built relation, or profile the expression for a column the change adds; never build first to read the type. A property without one, or a type the mapper does not know, is a refusal (`contract/unmapped-type`).
- **`servers` states the platform.** `reverse` drafts one `custom` server with `customProperties: [{property: platform, value: <the map's data_platform>}]`; the standard's own type for the platform is accepted only with the coordinates its schema requires.

## Absence is the only honest no-promise

An empty `servers`, `tags` or `authoritativeDefinitions`, or an empty `quality` on a schema element, claims a promise nobody made, and `check` fails `contract/empty-section`. A property-level `quality: []` passes both the schema and `check`, so it is the author's own omission to avoid. Omit the key in every case.

## The published standard outranks the schema

The vendored JSON schema under `../scripts/odcs_vendor/` is a checker pinned to ODCS `v3.2.0`. Where it and the standard disagree, write the standard's form and treat the schema as the defect. It is closed on root keys and constrains `logicalTypeOptions` per logical type: a timestamp accepts `timezone`, not `timeZone`; a string accepts `maxLength`, not `length`. Read its `$defs` before writing a key you half-remember. Leave out `price`, `support`, `team`, `roles` and `slaProperties`: nothing reads them.
