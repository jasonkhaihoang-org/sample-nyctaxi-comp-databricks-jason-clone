select
    lease_id,
    driver_id,
    primary_vehicle_id,
    lease_type,
    lease_rate,
    revenue_share_pct,
    {{ utc_date('lease_start_date') }} as lease_start_date,
    {{ utc_date('lease_end_date') }} as lease_end_date
from {{ source('ops_raw', 'lease_agreement') }}
