"""Compile a semantic query against one Ossie model document into SQL.

A query names metrics, the levels to group by (each reached through a relationship
from the fact, as `{via, level, key}`), and an optional filter over the fact's
fields. The compiler answers it from an aggregate source only when that is provably
the same answer as the detail, and otherwise from the detail:

1. the source binds every metric input, with a rollup rule (`aggregation`) of SUM,
   MIN or MAX: a NON_ADDITIVE metric is never read from an aggregate;
2. every role the query groups by is a content level of the source, and the queried
   level is that level or above it in one of the dimension's hierarchies;
3. a versioned dimension is never rolled up from an aggregate: rolling a version up
   to its parent "as of" the fact needs the fact's date, which the aggregate lost;
4. the query filter implies the content filter (every content conjunct appears in the
   query filter, compared in canonical form: sound, not complete);
5. the rest of the query filter reads only fields the source maps;
6. a source marked `navigable: false` is used only when the query names it.

The detail joins each dimension with a LEFT JOIN on a many-to-one relationship, so it
neither drops nor repeats a fact row. The join is the relationship's `join_expression`
when it declares one, else its core from/to columns. A `derived_expression` is applied after its
inputs are aggregated.

A query whose metrics reach a level-based (`at_levels`), time-series or dimension-rule
(`based_on_dimensions`) metric is answered from the detail only, in stages: every row
carries surrogate ids for the groups it belongs to, and each such metric is one gid-keyed
subquery over those rows. A metric that chains more than one such step, metrics over
several datasets, weighted bridges and `scd_rollup: current` raise CompileError rather
than return a wrong answer. `CAPABILITIES` says which constructs compile, with what
restrictions, and which are refused; `ossie.py capabilities` prints it.

A query compiles for one sqlglot dialect, or for none, which returns the SQL as assembled.
The SQL is assembled in one dialect and written for the dialect by sqlglot, which refuses
rather than approximates. The compiler knows no platform and reads no file: the caller passes
the dialect and whether it has an aggregate MEDIAN.
"""

import itertools
import json
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

import ossie_sql

VENDOR = "VIBEDATA"
ROLLUPS = {"SUM", "MIN", "MAX"}
STAGED = ("level", "time", "dimension")  # the metric kinds the staged detail path compiles
RULES = {"AVG": "avg", "SUM": "sum", "MIN": "min", "MAX": "max", "MEDIAN": "median"}
STAGED_ONLY = ("the query has level, time-series or dimension-rule metrics, which are "
               "answered from the detail only")

# What the compiler does with each construct. `ossie.py capabilities` prints this and the
# tests hold every "refused" entry to a refusal in code, so the report cannot drift.
CAPABILITIES = [
    ("base", "compiles", "A metric's core expression, aggregated over detail rows."),
    ("derived", "compiles", "A formula applied after its inputs are aggregated: a rate is "
     "rebuilt from totals."),
    ("filtered_metric", "compiles", "The filter is part of the core expression, which the "
     "compiler reads."),
    ("aggregate_navigation", "restricted", [
        "an aggregate answers only when it binds every metric input with a SUM, MIN or MAX rollup",
        "every grouped role is held at or below the queried level, and never rolled up on a "
        "versioned dimension",
        "the query filter implies the source's content filter",
        "a source marked navigable: false is read only when the query names it",
        "a query with level, time-series or dimension-rule metrics reads the detail only"]),
    ("at_levels", "restricted", [
        "answered from the detail only",
        "the query must group each pinned role, at or below the pinned level in one hierarchy",
        "a versioned dimension must be grouped at exactly the pinned level",
        "the metric's own core expression is evaluated; it cannot be the input of another "
        "level, time-series or dimension-rule metric"]),
    ("time_series_ago", "restricted", [
        "answered from the detail only; periods are the time dimension's members, so an "
        "empty period still takes its place",
        "the query must group the series role at exactly the series level, by its primary key",
        "the level must be in a time hierarchy (is_time)",
        "a time-only filter term chooses the output periods; shifted values read every period",
        "a period with no matching rows is NULL"]),
    ("time_series_todate", "restricted", [
        "answered from the detail only",
        "the query must group the series role at or below the period level in a time hierarchy",
        "a time-only filter term chooses the output periods; to-date values read every period"]),
    ("time_series_rolling", "restricted", [
        "answered from the detail only; the window counts members of the time dimension",
        "the query must group the series role at exactly the series level, by its primary key",
        "the level must be in a time hierarchy (is_time)"]),
    ("based_on_dimensions_avg", "restricted", [
        "answered from the detail only", "only members that have rows take part; a NULL member "
        "counts as one member"]),
    ("based_on_dimensions_sum", "restricted", ["answered from the detail only"]),
    ("based_on_dimensions_min", "restricted", ["answered from the detail only"]),
    ("based_on_dimensions_max", "restricted", ["answered from the detail only"]),
    ("based_on_dimensions_median", "restricted", [
        "answered from the detail only",
        "refused for a dialect with no aggregate MEDIAN"]),
    ("based_on_dimensions_first", "restricted", [
        "answered from the detail only", "exactly one across level, in a time hierarchy",
        "a NULL member is not a chronological member and is skipped"]),
    ("based_on_dimensions_last", "restricted", [
        "answered from the detail only", "exactly one across level, in a time hierarchy",
        "a NULL member is not a chronological member and is skipped"]),
    ("chained_staged_metrics", "refused", "A time-series or dimension-rule metric whose `of` "
     "chain holds another level, time-series or dimension-rule metric: the compiler compiles one "
     "such step per metric."),
    ("multi_fact", "refused", "Metrics that read different datasets need a stitch between facts."),
    ("multi_dataset_metric", "refused", "A metric whose expression reads several datasets."),
    ("weighted_bridge", "refused", "Allocating a measure across a weighted bridge is not compiled."),
    ("unweighted_bridge", "refused", "A many-to-many relationship would repeat fact rows."),
    ("scd_rollup_as_of", "compiles", "A versioned dimension rolls up as of the fact, on the "
     "detail, through the relationship's join."),
    ("scd_rollup_current", "refused", "Rolling a versioned dimension up as it is now needs a "
     "current-version member map."),
    ("unrelated_dimensions", "refused", "A group-by role that is not a relationship from the "
     "metric's fact is refused, whatever the metric's unrelated_dimensions setting."),
    ("query_filter_on_dimension_attributes", "refused", "A query filter reads fields of the "
     "fact only."),
    ("model_variables", "refused", "A :name variable in an expression is not supported."),
    ("computed_fields", "restricted", [
        "a field with no column_map entry whose core expression reads other fields of its "
        "dataset is computed on the detail; an aggregate source maps columns only",
        "the expression may not hold an aggregate, read another dataset, or read itself"]),
]


class CompileError(ValueError):
    """The query cannot be compiled soundly."""


class _Ineligible(Exception):
    """An aggregate source cannot answer the query; the message says why."""


def _payload(node):
    for ext in node.get("custom_extensions") or []:
        if isinstance(ext, dict) and ext.get("vendor_name") == VENDOR:
            try:
                data = json.loads(ext.get("data") or "{}")
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}
    return {}


@dataclass
class Query:
    metrics: list
    group_by: list = field(default_factory=list)
    filter: str | None = None
    source: str | None = None  # an LTS name, or "detail"

    @classmethod
    def from_dict(cls, data):
        return cls(metrics=list(data.get("metrics") or []),
                   group_by=list(data.get("group_by") or []),
                   filter=data.get("filter"), source=data.get("source"))


@dataclass
class Compiled:
    sql: str
    source: str
    columns: list
    rejected: dict
    dialect: str = "duckdb"


@dataclass(frozen=True)
class _Target:
    """What assembly must know about the SQL it writes: the sqlglot dialect and whether it
    has an aggregate MEDIAN. The default is the dialect the SQL is assembled in."""
    dialect: str = "duckdb"
    median: bool = True

    @property
    def name(self):
        return self.dialect

    @property
    def native(self):
        """Text in the assembly dialect is returned as assembled; other dialects get portable input."""
        return self.dialect == "duckdb"


def _target(dialect, aggregate_median=True):
    if dialect is None:
        return _Target(median=aggregate_median)
    try:
        sqlglot.Dialect.get_or_raise(dialect)
    except ValueError as e:
        raise CompileError(f"unknown dialect '{dialect}': {e}") from e
    return _Target(dialect, aggregate_median)


class Model:
    """One parsed Ossie document; `relation(table)` returns the SQL relation for a
    physical_tables entry."""

    def __init__(self, doc, relation):
        self.doc = doc
        self.relation = relation
        model = _payload(doc)
        self.tables = {t["name"]: t for t in model.get("physical_tables") or []}
        self.datasets = {d["name"]: d for d in doc.get("datasets") or []}
        self.payloads = {name: _payload(d) for name, d in self.datasets.items()}
        self.relationships = {r["name"]: r for r in doc.get("relationships") or []}
        self.metrics = {m["name"]: m for m in doc.get("metrics") or []}

    # -- datasets and levels -------------------------------------------------

    def sources(self, dataset):
        return self.payloads[dataset].get("logical_sources") or []

    def detail(self, dataset):
        for src in self.sources(dataset):
            table = self.tables.get(src.get("physical_table"), {})
            if src.get("priority_group", 1) != 0 and table.get("table_type") != "ALIAS":
                return src
        raise CompileError(f"dataset '{dataset}' has no detail source")

    def column(self, src, logical, dataset, alias=None, _seen=()):
        """The SQL for a field of `dataset` read from `src`, qualified with `alias`.

        A mapped field is its physical column. On a detail source, a field with no
        mapping whose core expression reads other fields of its dataset is that
        expression, rewritten onto the physical columns.
        """
        physical = (src.get("column_map") or {}).get(logical)
        if physical is not None:
            return f"{alias}.{physical}" if alias else physical
        if src.get("priority_group", 1) != 0:
            computed = self._computed(src, logical, dataset, alias, _seen)
            if computed is not None:
                return computed
        raise CompileError(f"source '{src['name']}' of '{dataset}' maps no column for "
                           f"'{logical}'")

    def field_expression(self, dataset, logical):
        for fld in self.datasets[dataset].get("fields") or []:
            if fld.get("name") == logical:
                for d in (fld.get("expression") or {}).get("dialects") or []:
                    if d.get("dialect") in ("ANSI_SQL", "OSSIE_SQL_2026"):
                        return d.get("expression")
        return None

    def _computed(self, src, logical, dataset, alias, seen):
        text = self.field_expression(dataset, logical)
        if text is None:
            return None
        key = (dataset, logical)
        if key in seen:
            chain = " -> ".join(n for _, n in seen + (key,))
            raise CompileError(f"computed field '{logical}' of '{dataset}' reads itself "
                               f"({chain})")
        try:
            if ossie_sql.has_aggregate(ossie_sql.parse(text)):
                raise CompileError(f"computed field '{logical}' of '{dataset}' holds an "
                                   "aggregate; a field is computed per row")

            def read(table, name):
                if table not in (None, dataset):
                    raise CompileError(f"computed field '{logical}' of '{dataset}' reads "
                                       f"'{table}.{name}', a field of another dataset")
                try:
                    return self.column(src, name, dataset, alias, seen + (key,))
                except CompileError as e:
                    if str(e).startswith(f"computed field '{logical}'"):
                        raise
                    raise CompileError(f"computed field '{logical}' of '{dataset}' cannot be "
                                       f"compiled: {e}") from e

            return f"({ossie_sql.rewrite(text, column=read)})"
        except ossie_sql.ExpressionError as e:
            raise CompileError(f"computed field '{logical}' of '{dataset}': {e}") from e

    def row_level(self, dataset):
        return (self.payloads[dataset].get("row_level") or {}).get("level")

    def level_name(self, dataset, level):
        return level or self.row_level(dataset)

    def level_fields(self, dataset, level, key=None):
        """The fields of a level's key (default the primary); level None is the row key."""
        if level is None:
            return list(self.datasets[dataset].get("primary_key") or [])
        for lv in self.payloads[dataset].get("levels") or []:
            if lv["name"] == level:
                for k in lv["keys"]:
                    if (key is None and k.get("primary")) or k["name"] == key:
                        return list(k["fields"])
                raise CompileError(f"level '{level}' of '{dataset}' has no key '{key}'")
        raise CompileError(f"dataset '{dataset}' has no level '{level}'")

    def primary_key_name(self, dataset, level):
        for lv in self.payloads[dataset].get("levels") or []:
            if lv["name"] == level:
                return next((k["name"] for k in lv["keys"] if k.get("primary")), None)
        return None

    def at_or_above(self, dataset, upper, lower, time_only=False):
        upper = upper or self.row_level(dataset)
        lower = lower or self.row_level(dataset)
        if upper == lower:
            return True
        for hier in self.payloads[dataset].get("hierarchies") or []:
            if time_only and not hier.get("is_time"):
                continue
            names = hier.get("levels") or []
            if upper in names and lower in names and names.index(upper) < names.index(lower):
                return True
        return False

    def in_time_hierarchy(self, dataset, level):
        return any(h.get("is_time") and level in (h.get("levels") or [])
                   for h in self.payloads[dataset].get("hierarchies") or [])

    def versioned(self, dataset):
        return bool((self.payloads[dataset].get("row_level") or {}).get("versioned"))

    # -- metrics --------------------------------------------------------------

    def expression(self, metric):
        for d in self.metrics[metric]["expression"]["dialects"]:
            if d.get("dialect") in ("ANSI_SQL", "OSSIE_SQL_2026"):
                return d["expression"]
        raise CompileError(f"metric '{metric}' has no ANSI_SQL expression")

    def kind(self, metric):
        """base, derived, level (`at_levels`), time (`time_series`) or dimension
        (`based_on_dimensions`)."""
        if metric not in self.metrics:
            raise CompileError(f"unknown metric '{metric}'")
        payload = _payload(self.metrics[metric])
        if payload.get("at_levels") is not None:
            return "level"
        if payload.get("time_series") is not None:
            return "time"
        if payload.get("based_on_dimensions") is not None:
            return "dimension"
        return "derived" if payload.get("derived_expression") else "base"

    def formula(self, metric):
        return _payload(self.metrics[metric])["derived_expression"]

    def of(self, metric):
        """The metric a time-series or dimension-rule metric evaluates."""
        payload = _payload(self.metrics[metric])
        step = payload.get("time_series") or payload.get("based_on_dimensions") or {}
        if not step.get("of"):
            raise CompileError(f"metric '{metric}' names no `of` metric")
        return step["of"]

    def aggregation(self, metric):
        return _payload(self.metrics[metric]).get("aggregation")

    def base_inputs(self, metric, seen=()):
        if metric in seen:
            raise CompileError(f"metric '{metric}' reaches itself")
        kind = self.kind(metric)
        if kind in ("base", "level"):
            return [metric]
        if kind in ("time", "dimension"):
            return self.base_inputs(self.of(metric), seen + (metric,))
        names, _ = ossie_sql.names(self.formula(metric))
        out = []
        for name in sorted(names):
            out += [m for m in self.base_inputs(name, seen + (metric,)) if m not in out]
        return out

    def time_vias(self, metrics):
        """The relationships the time-series metrics' chains shift by."""
        vias = set()

        def walk(metric, seen):
            if metric in seen:
                raise CompileError(f"metric '{metric}' reaches itself")
            kind = self.kind(metric)
            if kind == "time":
                via = _payload(self.metrics[metric])["time_series"].get("via")
                if via:
                    vias.add(via)
            if kind == "derived":
                for name in sorted(ossie_sql.names(self.formula(metric))[0]):
                    walk(name, seen + (metric,))
            elif kind in ("time", "dimension"):
                walk(self.of(metric), seen + (metric,))

        for metric in metrics:
            walk(metric, ())
        return vias

    def chain_kinds(self, metrics):
        """Every metric kind the metrics' chains reach."""
        kinds = set()

        def walk(metric, seen):
            if metric in seen:
                raise CompileError(f"metric '{metric}' reaches itself")
            kind = self.kind(metric)
            kinds.add(kind)
            if kind == "derived":
                for name in sorted(ossie_sql.names(self.formula(metric))[0]):
                    walk(name, seen + (metric,))
            elif kind in ("time", "dimension"):
                walk(self.of(metric), seen + (metric,))

        for metric in metrics:
            walk(metric, ())
        return kinds

    def require_plain_chain(self, metric):
        """A time-series or dimension-rule metric evaluates base and derived metrics only."""
        def walk(name):
            kind = self.kind(name)
            if kind == "derived":
                for inner in sorted(ossie_sql.names(self.formula(name))[0]):
                    walk(inner)
            elif kind != "base":
                raise CompileError(f"metric '{metric}' chains level, time-series or "
                                   "dimension-rule metrics; the compiler compiles one such "
                                   "step per metric")

        walk(self.of(metric))

    def fact_of(self, metrics):
        facts = set()
        for metric in metrics:
            for base in self.base_inputs(metric):
                columns, _ = ossie_sql.names(self.expression(base))
                tables = {c.split(".")[0] for c in columns if "." in c}
                if len(tables) != 1:
                    raise CompileError(f"metric '{base}' reads {sorted(tables) or 'no dataset'}; "
                                       "the compiler handles single-dataset metrics only")
                facts |= tables
        if len(facts) != 1:
            raise CompileError(f"the metrics read different datasets: {sorted(facts)}")
        return facts.pop()


def _metric_sql(model, metric, base_sql):
    """SQL for a metric: base metrics by `base_sql`, a formula over its inputs' SQL."""
    if model.kind(metric) == "base":
        return base_sql(metric)
    return ossie_sql.rewrite(model.formula(metric),
                             name=lambda n: _metric_sql(model, n, base_sql))


def _alias(ref, i, field_name, many):
    stem = f"{ref['via']}__{ref.get('level') or 'row'}"
    return f"{stem}__{field_name}" if many else stem


def _rewrite(text, target=None, predicate=False, **replace):
    """ossie_sql.rewrite, with an unsupported construct reported as a CompileError."""
    portable = target is not None and not target.native
    try:
        return ossie_sql.rewrite(text, portable=portable, predicate=predicate, **replace)
    except ossie_sql.ExpressionError as e:
        raise CompileError(str(e)) from e


def _assemble(select, relation, alias, joins, where, grouped, group_exprs=None):
    lines = ["select", "    " + ",\n    ".join(select), f"from {relation} as {alias}"]
    lines += joins
    if where:
        lines.append("where " + "\n    and ".join(ossie_sql.grouped(term) for term in where))
    if grouped:
        keys = group_exprs if group_exprs is not None else [str(i + 1) for i in range(grouped)]
        lines.append("group by " + ", ".join(keys))
    return "\n".join(lines)


class _Detail:
    """The detail fact of a query and the dimension joins it needs.

    `level(ref, index)` returns the SQL for one level key of a role, adding the join
    when the fact does not carry the key itself. The aggregate-free path numbers its
    joins by group-by position, one per reference; the staged path shares one join
    per relationship.
    """

    def __init__(self, model, fact, target, share=False):
        self.model, self.fact, self.target, self.share = model, fact, target, share
        self.src = model.detail(fact)
        self.joins = []
        self._joined = {}
        self._count = 0

    def relationship(self, ref, what="group_by"):
        rel = self.model.relationships.get(ref.get("via"))
        if rel is None or rel.get("from") != self.fact:
            raise CompileError(f"{what} via '{ref.get('via')}' is not a relationship from "
                               f"'{self.fact}'")
        payload = _payload(rel)
        if payload.get("weight"):
            raise CompileError(f"relationship '{rel['name']}' is a weighted bridge; the "
                               "compiler does not allocate across a bridge yet")
        cardinality = payload.get("cardinality", "many-to-one")
        if cardinality not in ("many-to-one", "one-to-one"):
            raise CompileError(f"relationship '{rel['name']}' is {cardinality}; joining it "
                               "would repeat fact rows")
        return rel

    def level(self, ref, index, what="group_by"):
        """(SQL expressions, fields) of the level key `ref` names."""
        model, fact, src = self.model, self.fact, self.src
        rel = self.relationship(ref, what)
        target = rel["to"]
        level = ref.get("level")
        fields = model.level_fields(target, level, ref.get("key"))
        if level is None or level == model.row_level(target) and not model.versioned(target) \
                and fields == list(model.datasets[target].get("primary_key") or []):
            # The fact carries the row key itself.
            return [model.column(src, c, fact, "f") for c in rel["from_columns"]], fields
        rollup = next((h.get("scd_rollup") for h in model.payloads[target].get("hierarchies") or []
                       if level in (h.get("levels") or [])), None)
        if model.versioned(target) and rollup == "current":
            raise CompileError(f"'{target}' rolls up as it is now (scd_rollup: current), "
                               "which the compiler does not compile yet")
        dim_src = model.detail(target)
        alias = self._alias(rel, index)
        if alias is not None:
            table = model.tables[dim_src["physical_table"]]
            predicate = _payload(rel).get("join_expression")
            if predicate:
                def side(t, name):
                    if t == fact:
                        return model.column(src, name, fact, "f")
                    return model.column(dim_src, name, target, alias)
                on = _rewrite(predicate, self.target, True, column=side)
            else:
                on = " and ".join(
                    f"{model.column(src, fc, fact, 'f')} = {model.column(dim_src, tc, target, alias)}"
                    for fc, tc in zip(rel["from_columns"], rel["to_columns"]))
            self.joins.append(f"left join {model.relation(table)} as {alias} on {on}")
        else:
            alias = self._joined[rel["name"]]
        return [model.column(dim_src, c, target, alias) for c in fields], fields

    def _alias(self, rel, index):
        """The alias for a new join, or None when the staged path already joined it."""
        if not self.share:
            return f"d{index}"
        if rel["name"] in self._joined:
            return None
        self._joined[rel["name"]] = f"d{self._count}"
        self._count += 1
        return self._joined[rel["name"]]


def _compile_detail(model, query, fact, target=None):
    target = target or _Target()
    d = _Detail(model, fact, target)
    src = d.src
    selects, columns = [], []
    exprs_out = []
    for i, ref in enumerate(query.group_by):
        exprs, fields = d.level(ref, i)
        many = len(fields) > 1
        for expr, name in zip(exprs, fields):
            alias = _alias(ref, i, name, many)
            selects.append(f"{expr} as {alias}")
            exprs_out.append(expr)
            columns.append(alias)
    grouped = len(selects)

    def base_sql(metric):
        return _rewrite(model.expression(metric), target,
                        column=lambda t, n: model.column(src, n, fact, "f"))

    for metric in query.metrics:
        selects.append(f"{_metric_sql(model, metric, base_sql)} as {metric}")
        columns.append(metric)
    where = [_rewrite(term, target, True, column=lambda t, n: model.column(src, n, fact, "f"))
             for term in ossie_sql.conjuncts(query.filter)]
    relation = model.relation(model.tables[src["physical_table"]])
    return _assemble(selects, relation, "f", d.joins, where, grouped,
                     None if target.native else exprs_out), columns


def _compile_aggregate(model, query, fact, src, forced, target=None):
    target = target or _Target()
    if src.get("navigable", True) is False and not forced:
        raise _Ineligible("not navigable: read only when the query names it")
    held = {ref["via"]: ref for ref in src.get("content_levels") or []}
    selects, joins, columns, exprs_out = [], [], [], []
    for i, ref in enumerate(query.group_by):
        content = held.get(ref.get("via"))
        if content is None:
            raise _Ineligible(f"holds no level of role '{ref.get('via')}'")
        dest = model.relationships[ref["via"]]["to"]
        level, key = ref.get("level"), ref.get("key")
        fields = model.level_fields(dest, level, key)
        many = len(fields) > 1
        content_fields = model.level_fields(dest, content.get("level"), content.get("key"))
        same_level = (level or model.row_level(dest)) == (content.get("level") or model.row_level(dest))
        if same_level and fields == content_fields:
            exprs = [f"a.{c}" for c in content["key_columns"]]
        else:
            if not model.at_or_above(dest, level, content.get("level")):
                raise _Ineligible(f"holds '{ref['via']}' at level "
                                  f"'{content.get('level') or 'row'}', which does not roll up "
                                  f"to '{level or 'row'}'")
            if model.versioned(dest):
                raise _Ineligible(f"'{dest}' is versioned; rolling it up from an aggregate "
                                  "needs the fact's date")
            dim_src = model.detail(dest)
            table = model.relation(model.tables[dim_src["physical_table"]])
            have = [model.column(dim_src, c, dest) for c in content_fields]
            want = [model.column(dim_src, c, dest) for c in fields]
            pick = ", ".join([f"{c} as k{j}" for j, c in enumerate(have)]
                             + [f"{c} as v{j}" for j, c in enumerate(want)])
            on = " and ".join(f"d{i}.k{j} = a.{c}" for j, c in enumerate(content["key_columns"]))
            joins.append(f"left join (select distinct {pick} from {table}) as d{i} on {on}")
            exprs = [f"d{i}.v{j}" for j in range(len(want))]
        for expr, name in zip(exprs, fields):
            alias = _alias(ref, i, name, many)
            selects.append(f"{expr} as {alias}")
            exprs_out.append(expr)
            columns.append(alias)
    grouped = len(selects)
    column_map = src.get("column_map") or {}

    def base_sql(metric):
        rule = model.aggregation(metric)
        if rule not in ROLLUPS:
            raise _Ineligible(f"metric '{metric}' has rollup rule {rule}, which an aggregate "
                              "cannot apply")
        if metric not in column_map:
            raise _Ineligible(f"binds no column for '{metric}'")
        return f"{rule.lower()}(a.{column_map[metric]})"

    for metric in query.metrics:
        selects.append(f"{_metric_sql(model, metric, base_sql)} as {metric}")
        columns.append(metric)
    asked = ossie_sql.conjuncts(query.filter)
    content_terms = ossie_sql.conjuncts(src.get("content_filter"))
    missing = [t for t in content_terms if t not in asked]
    if missing:
        raise _Ineligible("the query filter does not imply its content filter (missing "
                          + "; ".join(missing) + ")")

    def mapped(table, name):
        if name not in column_map or name in model.metrics:
            raise _Ineligible(f"the filter reads '{name}', which it does not map")
        return f"a.{column_map[name]}"

    where = [_rewrite(t, target, True, column=mapped) for t in asked if t not in content_terms]
    relation = model.relation(model.tables[src["physical_table"]])
    return _assemble(selects, relation, "a", joins, where, grouped,
                     None if target.native else exprs_out), columns


# -- the staged detail path -----------------------------------------------------


class _Levels:
    """The level-key columns the staged `fact_src` stage selects, one set per distinct
    (role, level, key), under reserved `_c_` aliases."""

    def __init__(self, detail):
        self.detail = detail
        self.sets = {}      # (via, level, fields) -> (aliases, fields)
        self.exprs = {}     # alias -> SQL expression
        self.order = []     # aliases, in selection order

    def cols(self, ref, what="group_by"):
        """(aliases, fields) of the level key `ref` names, added on first use."""
        rel = self.detail.relationship(ref, what)
        fields = self.detail.model.level_fields(rel["to"], ref.get("level"), ref.get("key"))
        ident = (ref["via"], ref.get("level"), tuple(fields))
        if ident not in self.sets:
            exprs, fields = self.detail.level(ref, len(self.sets), what)
            aliases = [f"_c_{len(self.order) + j}" for j in range(len(exprs))]
            for alias, expr in zip(aliases, exprs):
                self.exprs[alias] = expr
            self.order += aliases
            self.sets[ident] = (aliases, fields)
        return self.sets[ident]


def _time_fields(model, fact, vias):
    """The fact fields that say when, in the roles the query's time-series metrics shift by:
    the keys of the relationships those metrics name (`vias`), and the fields marked is_time
    when the fact has one relationship to a time dimension, so the mark names that role.
    With several the mark cannot be attributed, and the field filters like any other."""
    timed = [rel for rel in model.relationships.values() if rel.get("from") == fact and any(
        h.get("is_time") for h in model.payloads[rel["to"]].get("hierarchies") or [])]
    names = set()
    for rel in timed:
        if rel["name"] in vias:
            names |= set(rel.get("from_columns") or [])
    if len(timed) == 1 and timed[0]["name"] in vias:
        names |= {f["name"] for f in model.datasets[fact].get("fields") or []
                  if (f.get("dimension") or {}).get("is_time")}
    return names


def _ranked(columns):
    """`dense_rank()` over `columns` (NULL members compare equal); 1 with no columns."""
    if not columns:
        return "1"
    return "dense_rank() over (order by " + ", ".join(f"s.{c}" for c in columns) + ")"


def _dedupe(items):
    return list(dict.fromkeys(items))


def _compile_staged(model, query, fact, target):
    d = _Detail(model, fact, target, share=True)
    src = d.src
    levels = _Levels(d)
    has_time = "time" in model.chain_kinds(query.metrics)

    # The columns the query returns.
    outputs, columns = [], []  # outputs: (alias, `_c_` alias, role)
    for i, ref in enumerate(query.group_by):
        aliases, fields = levels.cols(ref)
        many = len(fields) > 1
        for c, name in zip(aliases, fields):
            alias = _alias(ref, i, name, many)
            outputs.append((alias, c, ref["via"]))
            columns.append(alias)
    out_cols = [c for _, c, _ in outputs]

    # The filter: time-only terms choose the output periods when a time-series metric
    # reads the others; every other term restricts the rows.
    time_names = _time_fields(model, fact, model.time_vias(query.metrics))
    where_terms, time_terms = [], []
    for term in ossie_sql.conjuncts(query.filter):
        read = {c.split(".")[-1] for c in ossie_sql.names(term)[0]}
        timed = read & time_names
        if has_time and timed and read - time_names:
            raise CompileError(f"the filter term '{term}' mixes time and non-time fields; "
                               "split it so the time-series metric knows which periods it "
                               "may read")
        (time_terms if has_time and timed else where_terms).append(term)

    def as_f(term):
        return _rewrite(term, target, True, column=lambda t, n: model.column(src, n, fact, "f"))

    def leaf(metric):
        return _rewrite(model.expression(metric), target,
                        column=lambda t, n: model.column(src, n, fact, "r"))

    plain = {}      # base metric -> aggregate SQL over `r`
    ids = []        # (column, columns it ranks)
    extras = []     # columns `grain` carries beyond the output
    ctes = []       # staged metric CTEs
    joins = []      # final joins
    cals = {}       # (role, fields) -> (cte name, key aliases, rank column)
    counter = itertools.count()

    def calendar(via, level):
        """The rank column of a time level's members, ranked from the dimension table."""
        aliases, fields = levels.cols({"via": via, "level": level})
        ident = (via, tuple(fields))
        if ident not in cals:
            n = len(cals)
            rel = model.relationships[via]
            dim_src = model.detail(rel["to"])
            relation = model.relation(model.tables[dim_src["physical_table"]])
            keys = [model.column(dim_src, c, rel["to"], "t") for c in fields]
            ks = [f"k{j}" for j in range(len(keys))]
            cals[ident] = (f"cal_{n}", aliases, ks, f"_r_{n}", keys, relation)
        return cals[ident]

    def one_ref(metric, via, what):
        refs = [r for r in query.group_by if r.get("via") == via]
        if not refs:
            raise CompileError(f"metric '{metric}' ({what}) needs the query to group role "
                               f"'{via}', which it does not")
        if len(refs) > 1:
            raise CompileError(f"metric '{metric}' ({what}) needs the query to group role "
                               f"'{via}' once; it is grouped {len(refs)} times")
        return refs[0]

    def level_metric(metric, pins):
        n = next(counter)
        roles = {p.get("via") for p in pins}
        pinned_cols = []
        for pin in pins:
            via = pin.get("via")
            what = f"metric '{metric}' is pinned at level '{pin.get('level')}' of role '{via}'"
            rel = d.relationship(pin, "at_levels")
            dest = rel["to"]
            refs = [r for r in query.group_by if r.get("via") == via]
            if not refs:
                raise CompileError(f"{what}, but the query does not group role '{via}'")
            for ref in refs:
                queried = model.level_name(dest, ref.get("level"))
                pinned = model.level_name(dest, pin.get("level"))
                primary = model.primary_key_name(dest, queried)
                if ref.get("key") is not None and ref.get("key") != primary:
                    raise CompileError(f"{what}, which ranks the members by the primary key of "
                                       f"their level; the query groups role '{via}' at level "
                                       f"'{queried}' by key '{ref.get('key')}'")
                if not model.at_or_above(dest, pinned, queried):
                    raise CompileError(f"{what}, but the query groups the role at level "
                                       f"'{queried}', which is not at or below it in one "
                                       "hierarchy")
                if model.versioned(dest) and queried != pinned:
                    raise CompileError(f"{what}, but '{dest}' is versioned (a member can have "
                                       f"had several parents) and the query groups the role "
                                       f"below it, at level '{queried}'")
            cols, _ = levels.cols({"via": via, "level": model.level_name(dest, pin.get("level"))},
                                  "at_levels")
            pinned_cols += cols
        column = f"_a_{n}"
        # The id ranks the output columns of every role the metric does NOT pin, plus the
        # pinned level's key: one id per (other roles, pinned member), never per output row,
        # so month + channel reads the channel's whole year. Held by the second-role cases
        # in test_ossie_compile_execute.py.
        rest = [c for _, c, via in outputs if via not in roles]
        ids.append((column, _dedupe(rest + pinned_cols)))
        extras.append(column)
        ctes.append(f"al_{n} as (\nselect r.{column} as _k, {leaf(metric)} as v\n"
                    f"from fact_rows as r\nwhere r._q = 1\ngroup by r.{column}\n)")
        joins.append(f"left join al_{n} on al_{n}._k = g.{column}")
        return f"al_{n}.v"

    def time_metric(metric, step):
        model.require_plain_chain(metric)
        n = next(counter)
        fn, via = step.get("function"), step.get("via")
        if fn not in ("AGO", "TODATE", "ROLLING"):
            raise CompileError(f"metric '{metric}' has time-series function '{fn}', which "
                               "the compiler does not compile")
        ref = one_ref(metric, via, fn)
        rel = d.relationship({"via": via}, "time_series")
        dest = rel["to"]
        series = model.level_name(dest, step.get("level"))
        queried = model.level_name(dest, ref.get("level"))
        primary = model.primary_key_name(dest, queried)
        if ref.get("key") is not None and ref.get("key") != primary:
            raise CompileError(f"metric '{metric}' ({fn}) ranks the members of role '{via}' "
                               f"by the primary key of its level; the query groups level "
                               f"'{queried}' by key '{ref.get('key')}'")
        if fn == "TODATE":
            if not model.at_or_above(dest, series, queried, time_only=True) \
                    or not model.in_time_hierarchy(dest, series):
                raise CompileError(f"metric '{metric}' (TODATE) accumulates within level "
                                   f"'{series}' of role '{via}', but the query groups the "
                                   f"role at level '{queried}', which is not at or below it "
                                   "in a time hierarchy (is_time)")
        else:
            if not model.in_time_hierarchy(dest, series):
                raise CompileError(f"metric '{metric}' ({fn}) reads level '{series}' of role "
                                   f"'{via}', which is not in a time hierarchy (is_time)")
            if queried != series:
                raise CompileError(f"metric '{metric}' ({fn}) needs the query to group role "
                                   f"'{via}' at exactly level '{series}', not '{queried}'")
        _, key_aliases, _, rank, _, _ = calendar(via, queried)
        other = [c for _, c, role in outputs if role != via]
        oth = f"_t_{n}_oth"
        if other:
            ids.append((oth, other))
            extras.append(oth)
        extras.append(rank)

        def formula(base_sql=None):
            return _metric_sql(model, step["of"], lambda m: leaf(m))

        on = [f"r.{oth} = g.{oth}"] if other else []
        if fn == "AGO":
            offset = step.get("offset")
            if not isinstance(offset, int) or isinstance(offset, bool):
                raise CompileError(f"metric '{metric}' (AGO) needs an integer offset")
            on.append(f"r.{rank} = g.{rank} - {offset}")
        elif fn == "ROLLING":
            periods = step.get("periods")
            if not isinstance(periods, int) or isinstance(periods, bool) or periods < 1:
                raise CompileError(f"metric '{metric}' (ROLLING) needs a positive integer "
                                   "`periods`")
            on.append(f"r.{rank} between g.{rank} - {periods - 1} and g.{rank}")
        else:
            period = f"_t_{n}_p"
            pcols, _ = levels.cols({"via": via, "level": series})
            ids.append((period, _dedupe(other + pcols)))
            extras.append(period)
            on = [f"r.{period} = g.{period}", f"r.{rank} <= g.{rank}"]
        # An inner join: a group with no matching row is absent here and NULL in the
        # final left join, never the 0 an aggregate over one empty row would give.
        ctes.append(f"ts_{n} as (\nselect g._gid as _gid, {formula()} as v\n"
                    f"from grain as g\njoin fact_rows as r on " + "\n    and ".join(on)
                    + "\ngroup by g._gid\n)")
        joins.append(f"left join ts_{n} on ts_{n}._gid = g._gid")
        return f"ts_{n}.v"

    def dimension_metric(metric, step):
        model.require_plain_chain(metric)
        n = next(counter)
        rule = step.get("rule")
        if rule not in (*RULES, "FIRST", "LAST"):
            raise CompileError(f"metric '{metric}' has dimension rule '{rule}', which the "
                               "compiler does not compile")
        across = step.get("across") or []
        if rule == "MEDIAN" and not target.median:
            raise CompileError(f"metric '{metric}' takes the MEDIAN across a dimension, which "
                               f"dialect '{target.name}' cannot express as an aggregate")
        if rule in ("FIRST", "LAST"):
            if len(across) != 1:
                raise CompileError(f"metric '{metric}' takes the {rule} across {len(across)} "
                                   f"levels; {rule} needs exactly one")
            dest = d.relationship(across[0], "based_on_dimensions")["to"]
            level = model.level_name(dest, across[0].get("level"))
            if not model.in_time_hierarchy(dest, level):
                raise CompileError(f"metric '{metric}' takes the {rule} across level '{level}' "
                                   f"of role '{across[0].get('via')}', which is not in a time "
                                   "hierarchy (is_time)")
        across_cols, chrono = [], []
        for ref in across:
            cols, _ = levels.cols(ref, "based_on_dimensions")
            across_cols += cols
            if rule in ("FIRST", "LAST"):
                chrono = cols
        column = f"_b_{n}"
        ids.append((column, _dedupe(out_cols + across_cols)))
        value = _metric_sql(model, step["of"], lambda m: leaf(m))
        keys = "".join(f", r.{c} as _x{j}" for j, c in enumerate(chrono))
        group = "".join(f", r.{c}" for c in chrono)
        nulls = "".join(f"\n    and r.{c} is not null" for c in chrono)
        ctes.append(f"bd_{n}_in as (\nselect r._gid as _gid, r.{column} as _b{keys}, "
                    f"{value} as v\nfrom fact_rows as r\nwhere r._q = 1{nulls}\n"
                    f"group by r._gid, r.{column}{group}\n)")
        if rule in ("FIRST", "LAST"):
            order = ", ".join(f"_x{j} {'asc' if rule == 'FIRST' else 'desc'}"
                              for j in range(len(chrono)))
            ctes.append(f"bd_{n} as (\nselect _gid, v from (\nselect _gid, v, row_number() "
                        f"over (partition by _gid order by {order}) as _rn\n"
                        f"from bd_{n}_in\n) as t\nwhere _rn = 1\n)")
        else:
            # An AVG of a DECIMAL keeps the decimal's scale on some engines, rounding the mean.
            agg = "avg(cast(v as double))" if rule == "AVG" else f"{RULES[rule]}(v)"
            ctes.append(f"bd_{n} as (\nselect _gid, {agg} as v\n"
                        f"from bd_{n}_in\ngroup by _gid\n)")
        joins.append(f"left join bd_{n} on bd_{n}._gid = g._gid")
        return f"bd_{n}.v"

    done = {}

    def value(metric):
        if metric in done:
            return done[metric]
        kind = model.kind(metric)
        payload = _payload(model.metrics[metric])
        if kind == "base":
            plain.setdefault(metric, leaf(metric))
            ref = f"p._v_{metric}"
        elif kind == "derived":
            ref = ossie_sql.rewrite(model.formula(metric), name=value)
        elif kind == "level":
            ref = level_metric(metric, payload["at_levels"])
        elif kind == "time":
            ref = time_metric(metric, payload["time_series"])
        else:
            ref = dimension_metric(metric, payload["based_on_dimensions"])
        done[metric] = ref
        return ref

    values = []
    for metric in query.metrics:
        try:
            values.append(value(metric))
        except ossie_sql.ExpressionError as e:
            raise CompileError(str(e)) from e
        columns.append(metric)

    # fact_src: the detail rows, the level keys, the calendar ranks and the time filter.
    selects = ["f.*"] + [f"{levels.exprs[c]} as {c}" for c in levels.order]
    joins_src = list(d.joins)
    cal_ctes = []
    for name, aliases, ks, rank, keys, relation in cals.values():
        cal_ctes.append(
            f"{name} as (\nselect {', '.join(ks)}, row_number() over (order by "
            f"{', '.join(ks)}) as rn\nfrom (\nselect distinct "
            + ", ".join(f"{k} as {a}" for k, a in zip(keys, ks))
            + f"\nfrom {relation} as t\nwhere " + " and ".join(f"{k} is not null" for k in keys)
            + "\n) as u\n)")
        selects.append(f"{name}.rn as {rank}")
        joins_src.append(f"left join {name} on " + " and ".join(
            f"{name}.{a} = {levels.exprs[c]}" for a, c in zip(ks, aliases)))
    if time_terms:
        flag = "case when " + " and ".join(ossie_sql.grouped(as_f(t)) for t in time_terms) \
            + " then 1 else 0 end"
    else:
        flag = "1"
    selects.append(f"{flag} as _q")
    src_lines = ["select", "    " + ",\n    ".join(selects),
                 f"from {model.relation(model.tables[src['physical_table']])} as f"] + joins_src
    if where_terms:
        src_lines.append("where " + "\n    and ".join(ossie_sql.grouped(as_f(t))
                                                     for t in where_terms))
    rows_cols = [f"{_ranked(out_cols)} as _gid"] + [f"{_ranked(cols)} as {name}"
                                                    for name, cols in ids]
    parts = cal_ctes + [
        "fact_src as (\n" + "\n".join(src_lines) + "\n)",
        "fact_rows as (\nselect s.*,\n    " + ",\n    ".join(rows_cols) + "\nfrom fact_src as s\n)"]
    if outputs:
        carry = ["r._gid as _gid"] + [f"r.{c} as {c}" for c in _dedupe(out_cols + extras)]
        parts.append("grain as (\nselect distinct " + ", ".join(carry)
                     + "\nfrom fact_rows as r\nwhere r._q = 1\n)")
    else:
        parts.append("grain as (\nselect 1 as _gid\n)")
    if plain:
        body = ",\n    ".join(f"{sql} as _v_{m}" for m, sql in plain.items())
        if outputs:
            parts.append(f"p as (\nselect r._gid as _gid,\n    {body}\nfrom fact_rows as r\n"
                         "where r._q = 1\ngroup by r._gid\n)")
        else:
            parts.append(f"p as (\nselect 1 as _gid,\n    {body}\nfrom fact_rows as r\n"
                         "where r._q = 1\n)")
        joins.insert(0, "left join p on p._gid = g._gid")
    parts += ctes
    final = [f"g.{c} as {alias}" for alias, c, _ in outputs]
    final += [f"{v} as {m}" for v, m in zip(values, query.metrics)]
    sql = ("with " + ",\n".join(parts) + "\nselect\n    " + ",\n    ".join(final)
           + "\nfrom grain as g\n" + "\n".join(joins))
    return sql, columns


def _render(sql, target):
    """`sql` (in the assembly dialect) written for the target dialect."""
    if target.native:
        return sql
    if not target.median and any(
            isinstance(n, exp.Median) or (isinstance(n, exp.Anonymous)
                                          and str(n.name).upper() == "MEDIAN")
            for n in sqlglot.parse_one(sql, dialect=ossie_sql.TARGET).find_all(exp.Func)):
        raise CompileError(f"dialect '{target.name}' has no aggregate MEDIAN, which the query "
                           "uses")
    try:
        return ossie_sql.render(sql, target.dialect)
    except ossie_sql.ExpressionError as e:
        raise CompileError(f"dialect '{target.name}' cannot express the query: {e}") from e


def compile_query(model, query, dialect=None, aggregate_median=True):
    """Compile `query` (a Query) against `model`; return a Compiled.

    `dialect` is a sqlglot dialect name; None returns the SQL as assembled. An unknown
    dialect is a CompileError. `aggregate_median` says whether the dialect has an aggregate
    MEDIAN."""
    plat = _target(dialect, aggregate_median)
    if not query.metrics:
        raise CompileError("a query names at least one metric")
    staged = bool(model.chain_kinds(query.metrics) & set(STAGED))
    fact = model.fact_of(query.metrics)
    rejected = {}
    aggregates = [s for s in model.sources(fact) if s.get("priority_group", 1) == 0]

    def done(sql, source, columns):
        return Compiled(_render(sql, plat), source, columns, rejected, plat.dialect)

    if staged:
        for src in aggregates:
            rejected[src["name"]] = STAGED_ONLY
        if query.source not in (None, "detail"):
            if not any(s["name"] == query.source for s in aggregates):
                raise CompileError(f"'{query.source}' is no aggregate source of '{fact}'")
            raise CompileError(f"'{query.source}' cannot answer the query: {STAGED_ONLY}")
        sql, columns = _compile_staged(model, query, fact, plat)
        return done(sql, model.detail(fact)["name"], columns)
    if query.source not in (None, "detail"):
        chosen = next((s for s in aggregates if s["name"] == query.source), None)
        if chosen is None:
            raise CompileError(f"'{query.source}' is no aggregate source of '{fact}'")
        try:
            sql, columns = _compile_aggregate(model, query, fact, chosen, True, plat)
        except _Ineligible as e:
            raise CompileError(f"'{chosen['name']}' cannot answer the query: {e}") from e
        return done(sql, chosen["name"], columns)
    if query.source is None:
        ranked = sorted(enumerate(aggregates),
                        key=lambda p: (p[1].get("join_cost", float("inf")), p[0]))
        for _, src in ranked:
            try:
                sql, columns = _compile_aggregate(model, query, fact, src, False, plat)
            except _Ineligible as e:
                rejected[src["name"]] = str(e)
                continue
            return done(sql, src["name"], columns)
    sql, columns = _compile_detail(model, query, fact, plat)
    return done(sql, model.detail(fact)["name"], columns)


def capabilities(targets=None):
    """What the compiler does with each construct. `targets` is what the caller knows of
    platforms (name -> dialect, aggregate_median, execution_verified); the compiler has none."""
    constructs = []
    for name, status, detail in CAPABILITIES:
        entry = {"construct": name, "status": status}
        entry["restrictions" if isinstance(detail, list) else "reason"] = detail
        constructs.append(entry)
    return {"expression_dialects": ["ANSI_SQL", "OSSIE_SQL_2026"], "targets": targets or {},
            "constructs": constructs}
