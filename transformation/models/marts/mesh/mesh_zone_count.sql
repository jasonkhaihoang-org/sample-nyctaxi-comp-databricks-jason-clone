select count(*) as zones from {{ ref('nyc_taxi_upstream', 'dim_zone') }}
