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
        {{ trip_natural_key(
            "'green'",
            'g.`vendorid`',
            "to_utc_timestamp(g.lpep_pickup_datetime, current_timezone())",
            "to_utc_timestamp(g.lpep_dropoff_datetime, current_timezone())",
            'g.`pulocationid`',
            'g.`dolocationid`',
            'g.trip_distance',
            'g.total_amount'
        ) }} as trip_key,
        g.ehail_fee,
        g.trip_type,
        to_utc_timestamp(
            g.lpep_pickup_datetime, current_timezone()
        ) as pickup_datetime,
        row_number() over (
            partition by {{ trip_natural_key(
                "'green'",
                'g.`vendorid`',
                "to_utc_timestamp(g.lpep_pickup_datetime, current_timezone())",
                "to_utc_timestamp(g.lpep_dropoff_datetime, current_timezone())",
                'g.`pulocationid`',
                'g.`dolocationid`',
                'g.trip_distance',
                'g.total_amount'
            ) }}
            order by g._dlt_load_id
        ) as dup_rank
    from {{ source('bronze', 'green_tripdata') }} g
) d
where dup_rank = 1
