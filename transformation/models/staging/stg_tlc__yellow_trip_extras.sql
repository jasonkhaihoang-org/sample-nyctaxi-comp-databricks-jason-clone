-- Yellow-only columns that conforming drops. Recomputes the trip natural key so
-- the fleet-specific fee can be rejoined to a trip. Staging reads only source():
-- the same timestamp conversion as stg_tlc__yellow_tripdata is applied before the
-- key is computed, or the key would match nothing.
--
-- Bronze is not deduplicated, so the same natural key can appear more than
-- once; taking the first occurrence keeps this one-row-per-trip and stops the
-- rejoin multiplying the fact.
select
    trip_key,
    airport_fee,
    pickup_location_id,
    pickup_datetime
from (
    select
        {{ trip_natural_key(
            "'yellow'",
            'y.`VendorID`',
            "to_utc_timestamp(y.tpep_pickup_datetime, current_timezone())",
            "to_utc_timestamp(y.tpep_dropoff_datetime, current_timezone())",
            'y.`PULocationID`',
            'y.`DOLocationID`',
            'y.trip_distance',
            'y.total_amount'
        ) }} as trip_key,
        y.`Airport_fee` as airport_fee,
        y.`PULocationID` as pickup_location_id,
        to_utc_timestamp(
            y.tpep_pickup_datetime, current_timezone()
        ) as pickup_datetime,
        row_number() over (
            partition by {{ trip_natural_key(
                "'yellow'",
                'y.`VendorID`',
                "to_utc_timestamp(y.tpep_pickup_datetime, current_timezone())",
                "to_utc_timestamp(y.tpep_dropoff_datetime, current_timezone())",
                'y.`PULocationID`',
                'y.`DOLocationID`',
                'y.trip_distance',
                'y.total_amount'
            ) }}
            order by y._dlt_load_id
        ) as dup_rank
    from {{ source('bronze', 'yellow_tripdata') }} y
) d
where dup_rank = 1
