---
kinds: [transformation]
---

# Requirement: The trip fact

Reconstructed from the repository for demonstration and context. The requirement was not captured when the models were first built; each line below is traceable to a model, test or design record in this repo.

## Ask

A trip-level fact that anyone can use: one row per TLC trip across yellow and green, with measures, conformed dimensions, quality status and the optional link to the fleet operator's vehicles and drivers. Revenue and flow reporting must be able to count only billable trips, and quality reporting must still see every trip.

## Requirements

- [x] `R-01` One row per distinct TLC trip across yellow and green, with none dropped or added by the fact — accept when `assert_fct_trip_matches_conformed_rowcount` returns no rows — source: `transformation/models/marts/core/fct_trip.sql`, `docs/design/models/core/fct_trip.md`
- [x] `R-02` Fleet-specific fields (airport fee, e-hail fee, trip type) are available on the trip, and a missing airport fee is distinguishable from one that does not exist for the fleet — accept when `airport_fee_status` is `present`, `missing` or `not_applicable`, and `assert_enrichment_rejoin_matches_every_trip` returns no rows — source: `transformation/models/intermediate/int_trips_enriched.sql`
- [x] `R-03` Every trip carries its quality verdicts and a billable flag, and nothing is deleted because of a verdict — accept when `fct_trip` exposes `is_billable` and `trip_quality_key` and its row count equals the conformed trips — source: `transformation/models/intermediate/int_trip_quality_flags.sql`, `docs/adr/0004-quality-verdicts-flag-trips-and-never-delete-them.md`
- [x] `R-04` Zone and vendor are resolved as of the trip's pickup date — accept when the `relationships` tests on the zone and vendor keys pass and `assert_scd2_zone_intervals_do_not_overlap` returns no rows — source: `docs/adr/0009-type-2-only-where-the-source-versions-history.md`
- [x] `R-05` Fleet attribution is explicit — accept when `is_fleet_attributed` is true exactly when driver, vehicle and shift are present — source: `docs/adr/0015-unmatched-dimension-keys-stay-null.md`
- [x] `R-06` `trip_key` has one definition — accept when only the `trip_natural_key` macro writes the expression and the `int_trips_conformed` unit tests pin it — source: `docs/adr/0007-trip-key-has-one-definition.md`

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Grain of `fct_trip` | One row per distinct TLC trip | `docs/design/models/core/fct_trip.md` |
| Billable trip | A positive total, applied where revenue and flows are reported | `docs/adr/0003-billable-trip-definition-and-where-it-applies.md` |
| Tips | Measured only where the payment method records them | `docs/adr/0011-tips-are-measured-only-where-the-meter-records-them.md` |
| Unmatched dimension keys | Null, with no placeholder member | `docs/adr/0015-unmatched-dimension-keys-stay-null.md` |

## Out of scope

- Aggregates and marts built on the fact.
- Fleet-operations measures (see `docs/requirement/2026-08-29-driver-status-occupancy-and-utilisation.md`).

## Open questions

None.

## Approvals

- 2026-08-29 — requirement approved — reconstructed from the repository; no recorded answer exists — 97862f7
- 2026-08-29 — ship approved — reconstructed: shipped before Studio recorded ship approvals; no recorded answer exists — 97862f7
