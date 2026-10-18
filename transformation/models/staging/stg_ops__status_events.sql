-- The occupancy stream. Sessionizing happens in intermediate; staging only
-- normalises and exposes the clock-skew between assigned and received time,
-- which is what makes an interval come out negative if you pick the wrong one.
with source as (
    select
        event_id,
        shift_id,
        driver_id,
        vehicle_id,
        to_utc_timestamp(event_ts, current_timezone()) as event_ts,
        to_utc_timestamp(received_ts, current_timezone()) as received_ts,
        status_code,
        zone_id,
        source_system
    from {{ source('ops_raw', 'driver_status_event') }}
)

select
    event_id,
    shift_id,
    driver_id,
    vehicle_id,
    event_ts,
    received_ts,
    status_code,
    zone_id,
    source_system,
    timestampdiff(second, event_ts, received_ts) as skew_seconds,
    status_code in ('ON_TRIP') as is_occupied_status,
    status_code in ('AVAILABLE', 'DISPATCHED') as is_available_status
from source
