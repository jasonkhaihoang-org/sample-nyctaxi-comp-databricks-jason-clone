-- Vehicle-month, with maintenance downtime netted out of the denominator.
--
-- A vehicle in the shop for six days has 24 fewer available days, and charging
-- it with those days makes a well-run asset look idle. Availability is
-- published alongside utilisation so the two can be told apart.
with monthly as (
    select
        trunc(a.shift_date, 'MM') as month_start_date,
        a.vehicle_key,
        a.medallion_number,
        a.make_model,
        a.fuel_type,
        a.garage_key,
        count(*) as active_days,
        sum(a.shift_count) as shift_count,
        sum(a.trip_count) as trip_count,
        sum(a.online_hours) as online_hours,
        sum(a.on_trip_hours) as on_trip_hours,
        sum(a.gross_revenue) as gross_revenue,
        sum(a.paid_miles) as paid_miles
    from {{ ref('agg_vehicle_daily') }} a
    group by 1, 2, 3, 4, 5, 6
),

downtime as (
    select
        trunc(m.started_date, 'MM') as month_start_date,
        m.vehicle_key,
        sum(m.down_days) as down_days,
        sum(m.cost_usd) as maintenance_cost
    from {{ ref('fct_maintenance') }} m
    group by 1, 2
)

select
    mo.month_start_date,
    mo.vehicle_key,
    mo.medallion_number,
    mo.make_model,
    mo.fuel_type,
    mo.garage_key,
    mo.active_days,
    mo.shift_count,
    mo.trip_count,
    mo.online_hours,
    mo.on_trip_hours,
    mo.gross_revenue,
    mo.paid_miles,
    coalesce(dt.down_days, 0) as down_days,
    coalesce(dt.maintenance_cost, 0) as maintenance_cost,
    datediff(add_months(mo.month_start_date, 1), mo.month_start_date) as calendar_days,
    datediff(add_months(mo.month_start_date, 1), mo.month_start_date)
    - coalesce(dt.down_days, 0) as available_days,
    {{ safe_divide(
        'cast(mo.active_days as double)',
        'cast(datediff(add_months(mo.month_start_date, 1), mo.month_start_date)'
        ~ ' - coalesce(dt.down_days, 0) as double)'
    ) }} as availability_adjusted_activity_rate,
    {{ safe_divide('mo.on_trip_hours', 'nullif(mo.online_hours, 0)') }} as occupancy_rate,
    {{ safe_divide('mo.gross_revenue', 'nullif(mo.online_hours, 0)') }} as revenue_per_online_hour
from monthly mo
left join downtime dt
    on
        mo.vehicle_key = dt.vehicle_key
        and mo.month_start_date = dt.month_start_date
