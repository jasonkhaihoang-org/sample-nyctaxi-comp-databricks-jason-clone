{#-
  Render every ref() and source() as schema.table, without the catalog.

  dbt-duckdb otherwise writes "<catalog>"."<schema>"."<table>" into each view it
  creates, and DuckDB stores that text. A Studio Intent sandbox is a byte copy of
  the Domain file under another name, so its catalog differs and every such view
  fails with `Catalog ... does not exist`. Unqualified names resolve in whatever
  database file opens them.
-#}
{% macro ref() -%}
    {{ return(builtins.ref(*varargs, **kwargs).include(database=False)) }}
{%- endmacro %}

{% macro source() -%}
    {{ return(builtins.source(*varargs, **kwargs).include(database=False)) }}
{%- endmacro %}
