-- The demand cube's grain, as its description states it: one row per pickup zone,
-- day of week, non-working-day flag, daypart, peak flag and fleet.
select pickup_location_id, day_of_week, is_non_working_day, daypart_code, is_peak, service_type_key, count(*) as n
from {{ ref('agg_trip_zone_daypart_dow') }}
group by all
having count(*) > 1
