-- A published flow is a pair with at least 25 billable trips (ADR 0017). A row
-- below the floor means the threshold stopped being applied.
select origin_location_id, dest_location_id, trip_count
from {{ ref('agg_od_flow_matrix') }}
where trip_count < 25
