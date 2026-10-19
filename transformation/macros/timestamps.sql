{#-
  dlt lands a source date as a timestamp at UTC midnight, and Spark shows a timestamp
  in the session time zone, which is not always UTC. Taken as it lands, a date column
  moves to the previous day behind UTC, and day arithmetic loses a day ahead of it.
  Staging brings it back to the calendar date the source recorded.
-#}
{% macro utc_date(column) -%}
    cast(to_utc_timestamp({{ column }}, current_timezone()) as date)
{%- endmacro %}
