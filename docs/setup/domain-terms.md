# Domain terms for CONTEXT.md

Candidate `## Language` entries drawn from the silver and gold models. All agreed for inclusion (user answer). Business language only: no columns, values or design decisions. Existing terms (Trip, Fleet / service type, Zone, Billable trip, Reporting window) are kept and conformed to the template.

## Trips and revenue

- **Fare component** and **fare residual**: the parts a trip total is built from, and what is left unexplained. Source: `int_trip_fare_components`, `mart_revenue_component_bridge`.
- **Measurable tip rate**: tip as a share of fare, counting only payment methods where tips are recorded. _Not_: a blended tip rate. Source: `agg_trip_zone_daypart_dow`.
- **Trip quality verdict**: a flag on a trip; trips are flagged, never deleted. Source: `int_trip_quality_flags`, `dim_trip_quality`.
- **Daypart**: a named band of the day, defined by the business. Source: `dim_daypart`.
- **Trip band**: the distance, duration and fare bands used in profiles. Source: `agg_trip_band_profile`.
- **Origin-destination flow**: trips between a pickup zone and a dropoff zone. Source: `agg_od_flow_matrix`.

## Fleet operations (the Harbour Point fleet; synthetic)

- **Fleet attribution**: a TLC trip matched to one of the operator's vehicles and drivers. Not every trip is attributed. Source: `fct_trip`.
- **Shift**: a driver's working period on one vehicle; when no logout is recorded it has an effective end. Source: `fct_shift`.
- **Status interval**: the time between one driver status event and the next. Source: `fct_status_interval`.
- **Occupancy** and **occupancy rate**: the share of time a driver is on a trip, collected separately from revenue. Source: `int_shift_occupancy`.
- **Locatable idle time**: time waiting rather than earning, with a place attached. Source: `fct_status_interval`.
- **Online hour**: the basis driver performance is ranked on, rather than gross revenue. Source: `mart_driver_scorecard`.
- **Asset utilisation** and **labour utilisation**: a medallion idle in the depot is an asset question; a driver idle on the road is a labour question. Source: `agg_vehicle_daily`.
- **Lease type**: owner-operators pay a revenue share, lease drivers a fixed rate. Source: `int_shift_economics`.
- **Maintenance downtime**: days a vehicle is unavailable, removed from its availability. Source: `agg_vehicle_monthly`.
- **Medallion**: the taxi licence and the vehicle it covers. _Not_: the bronze, silver and gold layering, which is a platform term defined elsewhere.
- **Garage**: a depot where vehicles are kept; the level depot managers are measured on. Source: `agg_garage_monthly`.

## Reference data

- **Zone version**: TLC re-designates zones, so a zone can have more than one version; the current version is the one in force now. Source: `dim_zone`, `int_zone_attributes`.
- **Technology vendor**: a vendor that supplies meters; vendors are renamed and acquired, so a vendor has a history. Source: `dim_vendor`.
- **Fare regime** and **rate plan**: surcharge rates with effective dates, and flat-fare amounts. Source: `dim_fare_regime`, `dim_rate_plan`.

## Terms for the data characteristics (each also has an ADR: 0004, 0011, 0012, 0013)

- Refund, zero-distance trip, unknown zone, unmeasured tip, no-charge and dispute payments.

## Left out as design detail

Junk dimension, bridge table, half-open intervals, SCD2 mechanics.
