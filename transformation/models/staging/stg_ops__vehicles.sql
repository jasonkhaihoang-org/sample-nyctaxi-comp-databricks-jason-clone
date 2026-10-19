select
    vehicle_id,
    medallion_number,
    vin,
    make,
    model,
    model_year,
    fuel_type,
    wheelchair_accessible,
    garage_id,
    {{ utc_date('in_service_date') }} as in_service_date,
    {{ utc_date('retired_date') }} as retired_date,
    retired_date is null as is_in_service
from {{ source('ops_raw', 'vehicle') }}
