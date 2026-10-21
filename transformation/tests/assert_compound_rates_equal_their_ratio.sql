-- A rate whose numerator or denominator is itself an expression must equal that
-- expression's ratio (ADR 0016). Unbracketed, `revenue / seconds / 3600e0` reads
-- as revenue per hour and is off by 3600 squared, so each such rate is recomputed
-- here from the columns published beside it.
with checks as (
    select
        'int_shift_economics.revenue_per_online_hour' as rate,
        revenue_per_online_hour as actual,
        gross_revenue / (online_seconds / 3600e0) as expected
    from {{ ref('int_shift_economics') }}
    where online_seconds > 0

    union all

    select
        'agg_driver_daily.revenue_per_online_hour' as rate,
        revenue_per_online_hour as actual,
        gross_revenue / online_hours as expected
    from {{ ref('agg_driver_daily') }}
    where online_hours > 0

    union all

    select
        'int_trips_conformed.avg_mph' as rate,
        avg_mph as actual,
        trip_distance / (trip_seconds / 3600e0) as expected
    from {{ ref('int_trips_conformed') }}
    where trip_seconds != 0

    union all

    select
        'agg_od_flow_matrix.avg_corridor_mph' as rate,
        avg_corridor_mph as actual,
        avg_distance / (avg_minutes / 60e0) as expected
    from {{ ref('agg_od_flow_matrix') }}
    where avg_minutes != 0

    union all

    select
        'mart_vehicle_utilisation.net_revenue_per_active_day' as rate,
        net_revenue_per_active_day as actual,
        (gross_revenue - maintenance_cost) / active_days as expected
    from {{ ref('mart_vehicle_utilisation') }}
    where active_days > 0
)

select rate, actual, expected
from checks
where
    expected is not null
    and (actual is null or abs(actual - expected) > 1e-6 * greatest(abs(expected), 1))
