-- Distance, duration and fare banding in one profile.
--
-- Three independent range joins against the banding seeds. Range joins are
-- easy to get wrong at the boundary: the bands are half-open [min, max), so a
-- trip of exactly three miles lands in "3 - 6", once, rather than in two bands
-- or none.
--
-- The joins are LEFT joins on purpose. A refund carries a negative total and so
-- has no fare band, a negative duration has no duration band, and ADR 0004 says
-- no model removes a trip because of a verdict -- so a trip with no matching
-- band appears once with 'unbanded' in that column and an order of 0, and
-- sum(trip_count) here equals the count of in-window trips in fct_trip. The dimension joins are LEFT joins for
-- the same reason: ADR 0015 keeps an unmatched zone key null, so an inner join
-- to dim_zone would drop those trips instead of grouping them as unresolved.
select
    coalesce(db.distance_band, 'unbanded') as distance_band,
    coalesce(db.band_order, 0) as distance_band_order,
    coalesce(ub.duration_band, 'unbanded') as duration_band,
    coalesce(ub.band_order, 0) as duration_band_order,
    coalesce(fb.fare_band, 'unbanded') as fare_band,
    coalesce(fb.band_order, 0) as fare_band_order,
    f.service_type_key,
    coalesce(z.borough_name, 'unresolved') as pickup_borough,
    coalesce(dp.daypart_code, 'unknown') as daypart_code,

    count(*) as trip_count,
    sum(f.total_amount) as total_revenue,
    avg(f.total_amount) as avg_total_amount,
    avg(f.measurable_tip_rate) as avg_measurable_tip_rate,
    count(*) filter (where not f.is_billable) as non_billable_count
from {{ ref('fct_trip') }} f
left join {{ ref('dim_zone') }} z on f.pickup_zone_key = z.zone_key
left join {{ ref('dim_daypart') }} dp on f.pickup_hour = dp.hour_of_day
left join {{ ref('distance_bands') }} db
    on f.trip_distance >= db.min_miles and f.trip_distance < db.max_miles
left join {{ ref('duration_bands') }} ub
    on f.trip_seconds / 60e0 >= ub.min_minutes and f.trip_seconds / 60e0 < ub.max_minutes
left join {{ ref('fare_bands') }} fb
    on f.total_amount >= fb.min_total and f.total_amount < fb.max_total
where {{ in_report_window('f.pickup_datetime') }}
group by 1, 2, 3, 4, 5, 6, 7, 8, 9
