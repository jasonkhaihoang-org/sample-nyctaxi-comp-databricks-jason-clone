-- Date spine over the calendar master, with the derived parts every rollup
-- needs. Holiday and school-term flags come from master data rather than being
-- computed, so a calendar correction restates reports without a code change.
select
    cast(date_format(c.calendar_date, 'yyyyMMdd') as integer) as date_key,
    c.calendar_date,
    extract(year from c.calendar_date) as calendar_year,
    extract(quarter from c.calendar_date) as calendar_quarter,
    extract(month from c.calendar_date) as calendar_month,
    date_format(c.calendar_date, 'MMMM') as month_name,
    extract(week from c.calendar_date) as iso_week,
    trunc(c.calendar_date, 'MM') as month_start_date,
    trunc(c.calendar_date, 'week') as week_start_date,
    -- Spark numbers Sunday 1; the warehouse numbers it 0, as it always has.
    dayofweek(c.calendar_date) - 1 as day_of_week,
    date_format(c.calendar_date, 'EEEE') as day_name,
    c.is_weekend,
    c.is_holiday,
    c.holiday_name,
    c.holiday_class,
    c.is_school_term,
    -- A holiday falling on a weekday behaves like a weekend for demand, which
    -- is why the two flags are kept separate and a third combines them.
    (c.is_weekend or c.is_holiday) as is_non_working_day
from {{ ref('stg_mdm__calendar') }} c
