-- Green taxi trip records, one row per bronze row: renamed and typed, nothing
-- else. See stg_tlc__yellow_tripdata for the timestamp handling.
select
    `VendorID` as vendor_id,
    to_utc_timestamp(lpep_pickup_datetime, current_timezone()) as pickup_datetime,
    to_utc_timestamp(lpep_dropoff_datetime, current_timezone()) as dropoff_datetime,
    passenger_count,
    trip_distance,
    `RatecodeID` as rate_code_id,
    store_and_fwd_flag,
    `PULocationID` as pickup_location_id,
    `DOLocationID` as dropoff_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    total_amount,
    ehail_fee,
    trip_type,
    _dlt_load_id
from {{ source('bronze', 'green_tripdata') }}
