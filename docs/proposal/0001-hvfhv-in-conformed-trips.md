---
status: proposed
findings: [2026-10-14-onboarding-nyctaxi#R-7]
---

# P-0001: Bring HVFHV trips into the conformed trip grain

## Problem

The conformed trip model unions yellow and green trips only. Once the high-volume for-hire (HVFHV) trip records are loaded as a source, trip counts, revenue and zone demand still exclude the largest segment of New York trips. Adding them is not a union: the records describe a different business.

## Evidence

- `int_trips_conformed.sql` unions `stg_tlc__yellow_tripdata` and `stg_tlc__green_tripdata`.
- HVFHV records carry a base passenger fare, driver pay and the licensee (`hvfhs_license_num`), and no vendor, rate code or payment type.
- ADR 0003 defines a billable trip in terms of fields HVFHV does not have.

## Options

1. Conform HVFHV into `int_trips_conformed` with nulls for the taxi-only columns. One trip grain, but every fare and payment measure needs a service-type filter to stay right.
2. Keep a separate `fct_hvfhv_trip` and a cross-service aggregate for counts and zone demand. Measures stay honest; cross-service questions need the aggregate.
3. Leave HVFHV in bronze only until a use case needs it.

## Recommendation

Option 2. Fares are not comparable across the services, and a single grain would put that caveat on every measure.

## Open questions

- Which questions need taxi and HVFHV together: counts and zones only, or revenue too?
- Does the billable rule (ADR 0003) apply to HVFHV, and if so with which fields?
- Is driver pay in scope for the finance marts?
