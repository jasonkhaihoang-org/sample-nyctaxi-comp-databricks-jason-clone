-- Demand against weather, by borough and day.
--
-- The grain is every borough crossed with every day in the reporting window,
-- not every observed weather row. The spine is borough-driven on purpose:
-- weather exists for six boroughs, and a trip in an unresolved or non-weather
-- borough is real demand (ADR 0012), so a weather-driven mart would drop it.
--
-- Each trip is attributed through its own zone surrogate key — the version
-- resolved as of the trip's date — rather than the borough's current version,
-- so a re-designation does not reassign history (ADR 0009). A trip whose zone
-- key is null groups as 'unresolved' rather than disappearing (ADR 0015).
--
-- A borough-day with weather and no trips keeps its row with trip_count 0, and
-- a borough-day with trips and no weather keeps its row with null weather and
-- weather_class 'unknown'. sum(trip_count) therefore equals fct_trip's count
-- in the window, which assert_weather_profile_covers_every_trip holds.
with window_days as (
    select calendar_date, day_name, is_weekend, is_holiday
    from {{ ref('dim_date') }}
    where {{ in_report_window('calendar_date') }}
),

boroughs as (
    select distinct borough_name
    from {{ ref('dim_zone') }}

    union distinct

    select 'unresolved'
),

spine as (
    select
        d.calendar_date,
        b.borough_name,
        d.day_name,
        d.is_weekend,
        d.is_holiday
    from window_days d
    cross join boroughs b
),

trips as (
    select
        f.pickup_date,
        coalesce(z.borough_name, 'unresolved') as borough_name,
        f.trip_key,
        f.total_amount,
        f.trip_distance,
        f.trip_seconds
    from {{ ref('fct_trip') }} f
    left join {{ ref('dim_zone') }} z on f.pickup_zone_key = z.zone_key
    where {{ in_report_window('f.pickup_datetime') }}
)

select
    s.calendar_date as obs_date,
    s.borough_name,
    s.day_name,
    s.is_weekend,
    s.is_holiday,
    w.temp_avg_f,
    w.precip_inches,
    w.snow_inches,
    w.is_wet_day,
    w.is_snow_day,
    case
        when w.observation_id is null then 'unknown'
        when w.snow_inches > 0.5 then 'snow'
        when w.precip_inches > 0.10 then 'wet'
        when w.temp_avg_f > 80 then 'hot'
        when w.temp_avg_f < 32 then 'freezing'
        else 'fair'
    end as weather_class,

    count(t.trip_key) as trip_count,
    sum(t.total_amount) as total_revenue,
    avg(t.trip_distance) as avg_trip_distance,
    avg(t.total_amount) as avg_fare,
    {{ safe_divide('sum(t.trip_seconds) / 3600e0', 'cast(count(t.trip_key) as double)') }} as avg_paid_hours_per_trip
from spine s
left join {{ ref('stg_mdm__weather') }} w
    on w.borough_name = s.borough_name and w.obs_date = s.calendar_date
left join trips t
    on t.pickup_date = s.calendar_date and t.borough_name = s.borough_name
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
