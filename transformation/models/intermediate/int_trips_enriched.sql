{{ config(materialized='view') }}

-- The cross-layer model. int_trips_conformed is the conformed intersection of the
-- two fleet schemas, so the fleet-specific columns it drops have to be
-- rejoined from bronze by recomputing the natural key on both sides.
--
-- Both joins are optional many-to-one: a yellow trip has at most one yellow
-- extras row and no green one. Multiplication here would be a defect, which is
-- why the staging models deduplicate rather than leaving it to this join.
select
    t.trip_key,
    t.service_type,
    t.vendor_id,
    t.pickup_datetime,
    t.dropoff_datetime,
    t.pickup_date,
    t.pickup_hour,
    t.pickup_location_id,
    t.dropoff_location_id,
    t.rate_code_id,
    t.payment_type,
    t.passenger_count,
    t.store_and_fwd_flag,
    t.trip_distance,
    t.fare_amount,
    t.extra,
    t.mta_tax,
    t.tip_amount,
    t.tolls_amount,
    t.improvement_surcharge,
    t.congestion_surcharge,
    t.total_amount,
    t.trip_seconds,
    t.avg_mph,
    t._dlt_load_id,
    y.airport_fee,
    g.ehail_fee,
    g.trip_type,
    -- Green never carries an airport fee. Distinguishing "no such column for
    -- this fleet" from "column present but null" is what stops a fleet-blind
    -- average from silently treating one as the other.
    case
        when t.service_type = 'green' then 'not_applicable'
        when y.airport_fee is null then 'missing'
        else 'present'
    end as airport_fee_status
from {{ ref('int_trips_conformed') }} t
left join {{ ref('stg_tlc__yellow_trip_extras') }} y on t.trip_key = y.trip_key
left join {{ ref('stg_tlc__green_trip_extras') }} g on t.trip_key = g.trip_key
