{{ config(materialized='view') }}

-- Green-only columns dropped when conforming (ADR 0006). Same natural-key
-- reconstruction as the yellow side, the same timestamp conversion, and the
-- same first-occurrence rule. Staging reads only source().
select
    trip_key,
    ehail_fee,
    trip_type,
    pickup_datetime
from (
    select
        {{ trip_natural_key("'green'", 'g."VendorID"', "timezone('UTC', g.lpep_pickup_datetime)",
           "timezone('UTC', g.lpep_dropoff_datetime)", 'g."PULocationID"', 'g."DOLocationID"',
           'g.trip_distance', 'g.total_amount') }} as trip_key,
        g.ehail_fee,
        g.trip_type,
        timezone('UTC', g.lpep_pickup_datetime) as pickup_datetime,
        row_number() over (
            partition by {{ trip_natural_key("'green'", 'g."VendorID"', "timezone('UTC', g.lpep_pickup_datetime)",
               "timezone('UTC', g.lpep_dropoff_datetime)", 'g."PULocationID"', 'g."DOLocationID"',
               'g.trip_distance', 'g.total_amount') }}
            order by g._dlt_load_id
        ) as dup_rank
    from {{ source('bronze', 'green_tripdata') }} g
) d
where dup_rank = 1
