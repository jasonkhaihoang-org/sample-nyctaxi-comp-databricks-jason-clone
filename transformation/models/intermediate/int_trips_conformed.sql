-- Yellow and green trips conformed onto one grain: shared column names, a
-- service_type discriminator, one row per distinct trip. Columns that exist on
-- only one fleet are dropped here rather than carried as a column that is null
-- for a whole fleet (ADR 0006); the
-- fleet-specific columns are rejoined in int_trips_enriched.
--
-- Derived measures that every downstream model would otherwise recompute
-- (duration, speed, calendar keys) land here once. No filtering: completeness
-- is deliberate, so refunds, zero-distance trips and out-of-window pickups all
-- survive.
with unioned as (
    select
        'yellow' as service_type,
        vendor_id, pickup_datetime, dropoff_datetime, pickup_location_id,
        dropoff_location_id, rate_code_id, payment_type, passenger_count,
        store_and_fwd_flag, trip_distance, fare_amount, extra, mta_tax,
        tip_amount, tolls_amount, improvement_surcharge, congestion_surcharge,
        total_amount, _dlt_load_id
    from {{ ref('stg_tlc__yellow_tripdata') }}

    union all

    select
        'green' as service_type,
        vendor_id, pickup_datetime, dropoff_datetime, pickup_location_id,
        dropoff_location_id, rate_code_id, payment_type, passenger_count,
        store_and_fwd_flag, trip_distance, fare_amount, extra, mta_tax,
        tip_amount, tolls_amount, improvement_surcharge, congestion_surcharge,
        total_amount, _dlt_load_id
    from {{ ref('stg_tlc__green_tripdata') }}
),

keyed as (
    select
        {{ trip_natural_key('service_type', 'vendor_id', 'pickup_datetime',
           'dropoff_datetime', 'pickup_location_id', 'dropoff_location_id',
           'trip_distance', 'total_amount') }} as trip_key,
        *,
        row_number() over (
            partition by
                service_type, vendor_id, pickup_datetime, dropoff_datetime,
                pickup_location_id, dropoff_location_id, trip_distance,
                total_amount
            order by _dlt_load_id
        ) as dup_rank
    from unioned
)

select
    trip_key,
    service_type,
    vendor_id,
    pickup_datetime,
    dropoff_datetime,
    cast(pickup_datetime as date) as pickup_date,
    extract(hour from pickup_datetime) as pickup_hour,
    pickup_location_id,
    dropoff_location_id,
    rate_code_id,
    payment_type,
    passenger_count,
    store_and_fwd_flag,
    trip_distance,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    total_amount,
    timestampdiff(second, pickup_datetime, dropoff_datetime) as trip_seconds,
    {{ safe_divide('trip_distance',
        'timestampdiff(second, pickup_datetime, dropoff_datetime) / 3600e0') }} as avg_mph,
    _dlt_load_id
from keyed
where dup_rank = 1
