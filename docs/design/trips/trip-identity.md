---
artifacts: [trip_natural_key, int_trips_conformed, stg_tlc__yellow_trip_extras, stg_tlc__green_trip_extras, stg_ops__trip_assignments, fct_trip]
---

# Trip identity

How a trip is identified everywhere in the warehouse. One decision shared by six artifacts, so it is recorded once here; each model's own record cites it.

## Grain

One `trip_key` per distinct TLC trip: the md5 of service type, vendor, pickup and dropoff time, pickup and dropoff zone, distance and total.

## Decisions

- `D-01` The `trip_natural_key` macro is the only definition of the key. `int_trips_conformed`, both extras models and `stg_ops__trip_assignments` call it; none writes the expression out. Two copies drift, and a drifted copy joins nothing without failing ([ADR 0007](../../adr/0007-trip-key-has-one-definition.md)). Source: docs/requirement/2026-08-29-the-trip-fact.md R-06, [ADR 0007](../../adr/0007-trip-key-has-one-definition.md).
- `D-02` The macro's inputs are the staging forms of each column: timestamps converted with `timezone('UTC', col)`. dlt lands TLC timestamps as `TIMESTAMPTZ`; hashing that on one side and the converted value on the other produces different keys for the same trip (see [the case record](../../cases/2026-10-14-airport-fee-rejoin-matches-nothing.md)). Superseded by `D-05`. Source: [the case record](../../cases/2026-10-14-airport-fee-rejoin-matches-nothing.md), [ADR 0007](../../adr/0007-trip-key-has-one-definition.md).
- `D-03` The fleet operator's source carries the trip's natural columns, not the key; `stg_ops__trip_assignments` derives the key with the same macro. A source system cannot know the warehouse's key ([ADR 0007](../../adr/0007-trip-key-has-one-definition.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-03, [ADR 0007](../../adr/0007-trip-key-has-one-definition.md).
- `D-04` Service type is part of the key, so a yellow and a green trip with identical other columns are two trips. Source: [ADR 0007](../../adr/0007-trip-key-has-one-definition.md).
- `D-05` The macro's inputs are the staging forms of each column: timestamps converted with `to_utc_timestamp(col, current_timezone())`, and every input cast to a string inside the macro. Hashing an unconverted timestamp on one side and the converted value on the other produces different keys for the same trip (see [the case record](../../cases/2026-10-14-airport-fee-rejoin-matches-nothing.md)). Source: [`dbt-models`](../../../.agents/skills/dbt-models/SKILL.md) B17, [ADR 0007](../../adr/0007-trip-key-has-one-definition.md).

## Rejected

- Minting the key in a loading script and carrying it in bronze or the operator source: a second copy of the expression outside dbt ([ADR 0007](../../adr/0007-trip-key-has-one-definition.md)).
- A surrogate sequence: it is not reproducible from the source rows, so the extras and the operator assignments could not rejoin.

## Rerun behaviour

Deterministic: the same source rows give the same keys on every run and in every copy of the database.

## Consumers

Everything downstream of `int_trips_conformed` and `fct_trip`; see their design records.

## Gotchas

- A key mismatch does not fail the build: the left join reports every fee as missing and everything stays green. Only the rejoin test catches it.
- The column order and the `'|'` separator are part of the definition; changing either changes every key.

## History

- 2026-10-14 — setup-dlt-ingestion — area record written; staging-form inputs after the airport-fee case — D-01, D-02, D-03, D-04
- 2026-10-19 — fabric-port — Spark conversion and explicit string casts — D-05
