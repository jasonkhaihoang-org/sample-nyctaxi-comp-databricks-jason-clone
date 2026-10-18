-- Yellow taxi trip records, one row per bronze row: renamed and typed, nothing
-- else. Bronze timestamps arrive as UTC-tagged values; they are the wall-clock
-- times the meter recorded, so they are brought back to plain timestamps in UTC
-- rather than the session's time zone.
select
    "VendorID" as vendor_id,
    timezone('UTC', tpep_pickup_datetime) as pickup_datetime,
    timezone('UTC', tpep_dropoff_datetime) as dropoff_datetime,
    passenger_count,
    trip_distance,
    "RatecodeID" as rate_code_id,
    store_and_fwd_flag,
    "PULocationID" as pickup_location_id,
    "DOLocationID" as dropoff_location_id,
    payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    total_amount,
    "Airport_fee" as airport_fee,
    _dlt_load_id
from {{ source('bronze', 'yellow_tripdata') }}
