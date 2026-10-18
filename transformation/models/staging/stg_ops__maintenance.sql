select
    maintenance_id,
    vehicle_id,
    {{ utc_date('started_date') }} as started_date,
    down_days,
    date_add({{ utc_date('started_date') }}, cast(down_days as int)) as ended_date,
    maintenance_type,
    cost_usd
from {{ source('ops_raw', 'maintenance_event') }}
