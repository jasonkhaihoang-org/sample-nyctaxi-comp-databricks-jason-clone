-- The semantic model treats bridge_zone_poi as a weighted bridge: a zone-level
-- measure grouped by POI category is multiplied by allocation_factor, and the parts
-- must sum back to the zone's total. That holds only while each zone's factors sum
-- to 1, so every zone whose shares drift from 1 is a violation.
select
    zone_natural_key,
    sum(allocation_factor) as allocation_total
from {{ ref('bridge_zone_poi') }}
group by zone_natural_key
having abs(sum(allocation_factor) - 1) > 1e-9
