-- The operator identifies a trip by its natural columns, as an external system
-- would. The warehouse's trip_key is derived here, with the same macro that
-- derives it everywhere else, so the join to fct_trip cannot drift.
with source as (
    select
        assignment_id,
        service_type,
        vendor_id,
        to_utc_timestamp(pickup_datetime, current_timezone()) as pickup_datetime,
        to_utc_timestamp(dropoff_datetime, current_timezone()) as dropoff_datetime,
        pickup_location_id,
        dropoff_location_id,
        trip_distance,
        total_amount,
        shift_id,
        driver_id,
        vehicle_id,
        to_utc_timestamp(assigned_ts, current_timezone()) as assigned_ts,
        assignment_method
    from {{ source('ops_raw', 'trip_assignment') }}
)

select
    assignment_id,
    {{ trip_natural_key('service_type', 'vendor_id', 'pickup_datetime',
       'dropoff_datetime', 'pickup_location_id', 'dropoff_location_id',
       'trip_distance', 'total_amount') }} as trip_key,
    shift_id,
    driver_id,
    vehicle_id,
    assigned_ts,
    assignment_method
from source
