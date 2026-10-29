{{ config(materialized='table') }}

-- Daily time spine the dbt Semantic Layer (MetricFlow) requires before any
-- metric in the project will parse. Infrastructure, not a business model:
-- nothing refs it, and it is committed alongside the first semantic YAML.
-- Written in this platform's own dialect, so it is copied unchanged.
{% set start_date = '2020-01-01' %}
{% set end_date = '2035-12-31' %}

select explode(sequence(to_date('{{ start_date }}'), to_date('{{ end_date }}'), interval 1 day)) as date_day
