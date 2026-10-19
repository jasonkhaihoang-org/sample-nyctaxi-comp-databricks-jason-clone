---
status: decided
date: 2026-10-14
---

# `trip_key` has one definition, in dbt, and the operator source carries natural columns

`trip_key` is the md5 of the trip's natural columns: service type, vendor, pickup and dropoff time, pickup and dropoff zone, distance and total. The `trip_natural_key` macro is its only definition, used by `int_trips_conformed` and by the extras models. The fleet operator's source identifies a trip by those natural columns, as an external system would, and `stg_ops__trip_assignments` derives the key with the same macro.

## Considered options

- **Mint the key in a loading script and carry it in the operator source** (the earlier arrangement) — rejected: a source system cannot know the warehouse's key, and a second copy of the expression drifts silently.
- **Carry the key in the operator source** — rejected for the same reason.
- **Natural columns in the source, key derived in dbt** — chosen.

## Consequences

- Any model that needs the key calls the macro; none writes the expression out.
- The inputs must be the same plain timestamps everywhere. Staging converts UTC-tagged values before the key is computed.
- The operator's generator attributes trips by hashing the natural columns, so which trips it attributes differs from the earlier arrangement.

## Affected designs

- [`models/intermediate/int_trips_conformed.md`](../design/models/intermediate/int_trips_conformed.md)
- [`models/staging/stg_ops__trip_assignments.md`](../design/models/staging/stg_ops__trip_assignments.md)
- [`pipelines/ops.md`](../design/pipelines/ops.md)
- [`models/core/fct_trip.md`](../design/models/core/fct_trip.md)
- [`trips/trip-identity.md`](../design/trips/trip-identity.md)
