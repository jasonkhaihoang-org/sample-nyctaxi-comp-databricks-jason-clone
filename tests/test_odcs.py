"""Tests for the data-contract tool (`.agents/skills/data-contract/scripts/odcs.py`)."""

import json
import sys
import uuid
from pathlib import Path

import pytest

# odcs.py's own dependencies (scripts/requirements.txt); without them the suite skips,
# and plugin-python-scripts.test.js names that gap.
for _module in ("duckdb", "jsonschema", "typer", "yaml"):
    pytest.importorskip(_module)

import yaml  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

SKILL_SCRIPTS = (
    Path(__file__).resolve().parent.parent / ".agents" / "skills" / "data-contract" / "scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS))

import odcs  # noqa: E402
from odcs import app  # noqa: E402

RUNNER = CliRunner()
WAREHOUSE = "domain.duckdb"


@pytest.fixture(autouse=True)
def _sandbox(tmp_path, monkeypatch):
    """The Intent's sandbox is a local database file at the fixture root, built or not."""
    monkeypatch.setattr(odcs, "_platform_destination", lambda repo_map: {
        "family": "duckdb", "path": str(tmp_path / WAREHOUSE), "platform": "local"})


def _run(*args):
    """Invoke the CLI; stdout is always pure JSON, so a crash fails here instead of passing as []."""
    result = RUNNER.invoke(app, list(args))
    assert result.stdout.strip(), f"no JSON on stdout: {result.exception!r}"
    assert result.exit_code in (0, 1, 2), result.output
    return result.exit_code, json.loads(result.stdout)


def _generated(tmp_path):
    """Write the keys `generate` owns, for the fixtures whose subject is not staleness."""
    assert _run("generate", "--root", str(tmp_path)) == (0, [])


def _reversed(tmp_path, *args):
    """`reverse` writes its drafts and reports what it could not settle; it must still succeed.

    Findings are the expected output of a pass over a warehouse, so the assertion is the exit
    code and the absence of errors, never an empty diagnostic list.
    """
    code, diags = _run("reverse", "--root", str(tmp_path), *args)
    assert code == 0
    assert all(diag["severity"] != "error" for diag in diags)
    return diags


def _codes(diags):
    return [d["code"] for d in diags]


def _doc(table, **overrides):
    doc = {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "c0ffee00-0000-4000-8000-000000000001",
        "name": table,
        "version": "1.0.0",
        "schema": [{"name": table, "dataGranularityDescription": "One row per event."}],
    }
    doc.update(overrides)
    return doc


def _repo(tmp_path, models=(), seeds=(), sources=None, logical_model=None, files=None,
          staging=(), contract_layers=None):
    """A minimal repo: layers, their gold declaration, seeds, a source's docs and a canonical model.

    `files` writes hand-written properties files, as `{relative path: text or document}`.
    """
    artifacts = {
        "data_contract": "contracts/{schema}/{table}.odcs.yaml",
        "ingestion_root": "ingestion/",
    }
    if logical_model is not None:
        artifacts["logical_model"] = "logical-model/*.ossie.yaml"
        target = tmp_path / "logical-model" / "model.ossie.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(logical_model))
    repo_map = {
        "artifact_paths": artifacts,
        "gold_layers": ["core"],
        "data_platform": "duckdb_local",
        "layers": {
            "bronze": {"schema": "bronze", "path": "ingestion/", "built_by": "dlt"},
            "staging": {"schema": "staging", "path": "models/staging/", "built_by": "dbt"},
            "core": {"schema": "core", "path": "models/core/", "built_by": "dbt"},
            "seeds": {"schema": "seeds", "path": "seeds/", "built_by": "dbt"},
        },
        "sources": {},
    }
    if contract_layers is not None:
        repo_map["contract_layers"] = list(contract_layers)
    for model in staging:
        target = tmp_path / "models" / "staging" / f"{model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("select 1\n")
    for model in models:
        target = tmp_path / "models" / "core" / f"{model}.sql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("select 1\n")
    for seed in seeds:
        target = tmp_path / "seeds" / f"{seed}.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("a\n1\n")
    for name, (dataset, resources) in (sources or {}).items():
        docs = tmp_path / "ingestion" / "docs" / f"{name}.yml"
        docs.parent.mkdir(parents=True, exist_ok=True)
        docs.write_text(
            yaml.safe_dump(
                {"dataset": dataset, "resources": {r: {"description": r} for r in resources}}
            )
        )
        repo_map["sources"][name] = {
            "kind": "dlt",
            "dataset": dataset,
            "docs": f"ingestion/docs/{name}.yml",
        }
    (tmp_path / "repo-map.json").write_text(json.dumps(repo_map))
    for relative, content in (files or {}).items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str) else yaml.safe_dump(content))
    return tmp_path


def _model(*datasets):
    """A canonical document naming one dataset per `(table, fields, primary_key)` tuple."""
    return {
        "version": "0.2.0.dev0",
        "name": "model",
        "datasets": [
            {
                "name": table,
                "source": f"core.{table}",
                "primary_key": list(primary_key),
                "fields": [
                    {"name": field, "datatype": datatype, "description": field}
                    for field, datatype in fields.items()
                ],
            }
            for table, fields, primary_key in datasets
        ],
        "relationships": [],
    }


def _element(table, *properties):
    return [{"name": table, "dataGranularityDescription": "One row per event.",
             "properties": list(properties)}]


PHYSICAL_TYPES = {
    "string": "VARCHAR",
    "integer": "BIGINT",
    "number": "DECIMAL(10,2)",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
}


def _prop(name, logical_type, **overrides):
    """A contract property; every one carries a `physicalType`, as `reverse` writes it.

    It also carries a description: a consumer reads the contract, and `check` warns about a
    boundary property that gives none. A test about that passes `description=None`.
    """
    prop = {"name": name, "logicalType": logical_type,
            "physicalType": PHYSICAL_TYPES.get(logical_type, "VARCHAR"),
            "description": f"The {name}."}
    prop.update(overrides)
    return {key: value for key, value in prop.items() if value is not None}


def _contract(tmp_path, schema_name, table_name, **overrides):
    overrides.setdefault(
        "servers",
        [{"server": "a_model", "type": "duckdb", "database": "domain.duckdb", "schema": schema_name}],
    )
    target = tmp_path / "contracts" / schema_name / f"{table_name}.odcs.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(_doc(table_name, **overrides)))
    return target


def test_check_accepts_a_declared_relation_with_its_contract(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model")
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_check_requires_a_contract_for_every_boundary_relation(tmp_path):
    """Gold models and documented dlt resources owe one, from the map alone; nothing else does."""
    _repo(tmp_path, models=["a_model", "b_model"], seeds=["band"], staging=["stg_a"],
          sources={"src": ("raw", ["t"])})
    _contract(tmp_path, "core", "a_model")
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1
    assert _codes(diags) == ["contract/missing", "contract/missing"]
    assert any("core.b_model" in d["message"] for d in diags)
    assert any("raw.t" in d["message"] for d in diags)
    assert not any("seeds.band" in d["message"] or "stg_a" in d["message"] for d in diags)


def test_contract_layers_replaces_the_default_boundary(tmp_path):
    """Named layers are the whole boundary: gold and inputs drop out unless they are named."""
    _repo(tmp_path, models=["a_model"], staging=["stg_a"], sources={"src": ("bronze", ["t"])},
          contract_layers=["staging"])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/missing"])
    assert "staging.stg_a" in diags[0]["message"]


def test_contract_layers_names_a_dlt_layer_by_its_sources(tmp_path):
    _repo(tmp_path, models=["a_model"], sources={"src": ("bronze", ["t"])},
          contract_layers=["bronze"])
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/missing"])
    assert "bronze.t" in diags[0]["message"]


def test_contract_layers_naming_no_layer_is_an_error(tmp_path):
    _repo(tmp_path, models=["a_model"], contract_layers=["core", "platinum"])
    _contract(tmp_path, "core", "a_model")
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["map/contract-layers"])
    assert "platinum" in diags[0]["message"]


def test_a_contract_off_the_boundary_is_checked_not_required(tmp_path):
    """A staging contract is allowed; it is validated like any other."""
    _repo(tmp_path, models=["a_model"], staging=["stg_a", "stg_b"])
    _contract(tmp_path, "core", "a_model")
    _contract(tmp_path, "staging", "stg_a", tags=[])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/empty-section"])
    assert "stg_a" in diags[0]["message"]


def test_check_rejects_a_contract_naming_no_declared_relation(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model")
    _contract(tmp_path, "core", "gone")
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/orphan"])


def test_a_seed_layer_named_something_else_still_generates_seed_keys(tmp_path):
    """The `.csv` suffix follows the files a dbt layer holds, not the name `seeds`."""
    _repo(tmp_path, files={"seeds/band.csv": "band_order\n1\n"})
    map_path = tmp_path / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    repo_map["layers"] = {"bands": {"schema": "seeds", "path": "seeds/", "built_by": "dbt"}}
    repo_map.pop("gold_layers")
    map_path.write_text(json.dumps(repo_map))
    _contract(tmp_path, "seeds", "band")
    _generated(tmp_path)

    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_check_rejects_a_present_but_empty_section(tmp_path):
    """Absence is the only honest 'no promise'; an empty `servers` claims one."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", servers=[])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/empty-section"])
    assert "servers" in diags[0]["message"]


def test_check_warns_but_passes_when_the_grain_is_unstated(tmp_path):
    """Onboarding may leave the grain to review; the gate warns, the review refuses."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=[{"name": "a_model"}])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/no-grain"])
    assert diags[0]["severity"] == "warning"


def test_check_says_so_when_the_map_declares_no_contract_path(tmp_path):
    """A repo that has not adopted contracts gets a diagnosis, not a traceback."""
    (tmp_path / "repo-map.json").write_text(json.dumps({"artifact_paths": {}, "layers": {}}))
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/unconfigured"])


ORDER_FIELDS = {"order_key": "String", "ordered_date": "Date", "total_amount": "Decimal"}


def _orders(tmp_path, fields=ORDER_FIELDS, primary_key=("order_key",)):
    """A gold contract and the canonical document that declares the same relation."""
    _repo(tmp_path, models=["a_model"], logical_model=_model(("a_model", fields, primary_key)))
    return _contract(
        tmp_path,
        "core",
        "a_model",
        schema=_element(
            "a_model",
            _prop("order_key", "string", primaryKey=True),
            _prop("ordered_date", "date"),
            _prop("total_amount", "number"),
        ),
    )


def test_gold_agreement_passes_when_the_contract_matches_the_model(tmp_path):
    _orders(tmp_path)
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_gold_omission_fails_and_names_the_relation_and_field(tmp_path):
    """The contract carries less than the canonical document declares for that relation."""
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True), _prop("total_amount", "number")))
    _repo(tmp_path, models=["a_model"], logical_model=_model(("a_model", ORDER_FIELDS, ["order_key"])))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["boundary/omits-declared"])
    assert "core.a_model" in diags[0]["message"] and "ordered_date" in diags[0]["message"]


def test_gold_logical_type_disagreement_names_both_sides(tmp_path):
    """A `Decimal` reduces to `number`; a contract saying otherwise contradicts the model."""
    _orders(tmp_path)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"),
        _prop("total_amount", "string")))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["boundary/divergent"])
    assert "'number'" in diags[0]["message"] and "'string'" in diags[0]["message"]


def test_gold_datetimetz_needs_the_timezone_option(tmp_path):
    """`DateTimeTz` reduces to a timestamp that carries the timezone option, and only it does."""
    _orders(tmp_path)
    loaded_at = _element("a_model",
                         _prop("order_key", "string", primaryKey=True),
                         _prop("ordered_date", "date"),
                         _prop("total_amount", "number"),
                         _prop("loaded_at", "timestamp"))
    _contract(tmp_path, "core", "a_model", schema=loaded_at)
    _repo(tmp_path, models=["a_model"], logical_model=_model(
        ("a_model", {**ORDER_FIELDS, "loaded_at": "DateTimeTz"}, ["order_key"])))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["boundary/divergent"])
    assert "timezone" in diags[0]["message"]
    loaded_at[0]["properties"][-1]["logicalTypeOptions"] = {"timezone": True}
    _contract(tmp_path, "core", "a_model", schema=loaded_at)
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_gold_datetime_must_not_carry_the_timezone_option(tmp_path):
    """`DateTime` reduces to a timezone-free timestamp; the option would claim an offset it lacks."""
    _orders(tmp_path)
    schema = _element("a_model",
                      _prop("order_key", "string", primaryKey=True),
                      _prop("ordered_date", "date"),
                      _prop("total_amount", "number"),
                      _prop("loaded_at", "timestamp", logicalTypeOptions={"timezone": True}))
    _contract(tmp_path, "core", "a_model", schema=schema)
    _repo(tmp_path, models=["a_model"], logical_model=_model(
        ("a_model", {**ORDER_FIELDS, "loaded_at": "DateTime"}, ["order_key"])))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["boundary/divergent"])
    assert "timezone" in diags[0]["message"]


def test_gold_contract_with_no_document_fails(tmp_path):
    """A gold relation inside a modelled schema that no document names has no agreed shape."""
    _repo(tmp_path, models=["a_model", "b_model"],
          logical_model=_model(("a_model", ORDER_FIELDS, ["order_key"])))
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"), _prop("total_amount", "number")))
    _contract(tmp_path, "core", "b_model")
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/no-document", "boundary/undeclared"])
    assert "core.b_model" in diags[1]["message"]


def test_gold_ignores_a_property_the_model_does_not_declare(tmp_path):
    """The canonical model is curated: a contract may carry columns it never declares."""
    _orders(tmp_path)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"),
        _prop("total_amount", "number"),
        _prop("audit_note", "string")))
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_no_canonical_model_means_no_gold_diagnostics(tmp_path):
    """Not adopting a canonical model is not a broken contract set, whatever the map says."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model")
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])

    elsewhere = tmp_path / "absent"
    _repo(elsewhere, models=["a_model"])
    _contract(elsewhere, "core", "a_model")
    map_path = elsewhere / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    repo_map["artifact_paths"]["logical_model"] = "logical-model/*.ossie.yaml"
    map_path.write_text(json.dumps(repo_map))
    _generated(elsewhere)
    assert _run("check", "--root", str(elsewhere)) == (0, [])


def test_a_map_declaring_no_boundary_layers_checks_none_and_says_so(tmp_path):
    """The map declares the boundary: without one nothing is boundary, and the gate reports the gap."""
    _repo(tmp_path, models=["a_model", "b_model"],
          logical_model=_model(("a_model", ORDER_FIELDS, ["order_key"])))
    map_path = tmp_path / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    del repo_map["gold_layers"]
    map_path.write_text(json.dumps(repo_map))
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"), _prop("total_amount", "number")))
    _contract(tmp_path, "core", "b_model")
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))

    # No `contract/no-document` and no `boundary/undeclared`: an undeclared boundary set names no relation,
    # so the warning about the missing declaration is the whole answer.
    assert (code, _codes(diags)) == (0, ["map/no-boundary-layers"])
    assert "role: boundary" in diags[0]["message"]


CORE_PROPERTIES = """version: 2

models:
  - name: a_model
    description: >
      Hand-written prose the generator must not touch.
    columns:
      - name: order_key
        description: '{{ doc("order_key") }}'
        tests: [unique, not_null]
      - name: total_amount
        description: The amount total, as billed.
"""

SEED_PROPERTIES = """version: 2

seeds:
  - name: band
    description: Amount banding.
    columns:
      - name: band_order
        tests: [unique, not_null]
"""

ZERO_INDENT_PROPERTIES = """version: 2
models:
- name: a_model
  columns:
  - name: order_key
    description: kept
  - name: note
    description: hand-written
"""

MODEL_WITH_DATA_TESTS = """version: 2

models:
  - name: a_model
    columns:
      - name: order_key
        data_tests: [unique, not_null]
"""

SEED_WITH_DATA_TYPE = """version: 2

seeds:
  - name: band
    columns:
      - name: band_order
        data_type: INTEGER
        data_tests: [unique]
"""

SEED_WITH_LEFTOVER = """version: 2

seeds:
  - name: band
    columns:
      - name: band_order
        data_tests: [unique]
"""

MODEL_WITH_DATA_TYPE = """version: 2

models:
  - name: a_model
    columns:
      - name: order_key
        data_type: VARCHAR
"""


def _entries(path, section="models"):
    """A properties file's entries, by the name dbt resolves them with."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc, {entry["name"]: entry for entry in doc[section]}


def _rule(metric, **overrides):
    rule = {"type": "library", "metric": metric, "mustBe": 0}
    rule.update(overrides)
    return rule


def test_generate_writes_the_contract_and_a_data_type_per_column(tmp_path):
    """The generator augments the hand-written file: dbt rejects a second entry for one model."""
    _repo(tmp_path, models=["a_model", "b_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", physicalType="VARCHAR", primaryKey=True),
        _prop("total_amount", "number", physicalType="DECIMAL(10,2)", description=None)))
    _contract(tmp_path, "core", "b_model", schema=_element(
        "b_model", _prop("store_id", "integer", physicalType="BIGINT", description=None)))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    doc, entries = _entries(tmp_path / "models" / "core" / "_core.yml")
    assert [entry["name"] for entry in doc["models"]] == ["a_model"]
    model = entries["a_model"]
    assert model["contract"] == {"enforced": True}
    assert model["description"] == "Hand-written prose the generator must not touch.\n"
    columns = {column["name"]: column for column in model["columns"]}
    assert columns["order_key"]["data_type"] == "VARCHAR"
    assert columns["order_key"]["description"] == '{{ doc("order_key") }}'
    assert columns["order_key"]["tests"] == ["unique", "not_null"]
    assert columns["total_amount"]["data_type"] == "DECIMAL(10,2)"
    assert columns["total_amount"]["description"] == "The amount total, as billed."

    generated = _entries(tmp_path / "models" / "core" / "_generated.yml")[1]
    assert generated["b_model"]["contract"] == {"enforced": True}
    assert generated["b_model"]["columns"] == [
        {"name": "store_id", "data_type": "BIGINT"}
    ]


def test_generate_adds_an_entry_for_a_column_the_file_lacks(tmp_path):
    """`contract: enforced` fails on an output column with no entry, so one is added."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", physicalType="VARCHAR"),
        _prop("ordered_date", "date", physicalType="DATE")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    model = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]
    assert model["columns"][-1] == {"name": "ordered_date", "data_type": "DATE",
                                    "description": "The ordered_date."}
    assert [column["name"] for column in model["columns"]] == [
        "order_key", "total_amount", "ordered_date"
    ]


def test_generate_writes_data_tests_for_a_seed_and_no_contract(tmp_path):
    """A seed cannot carry a contract; its enforcement is the generated tests list."""
    _repo(tmp_path, seeds=["band"], files={"seeds/seeds.yml": SEED_PROPERTIES})
    _contract(tmp_path, "seeds", "band", schema=_element(
        "band",
        _prop("band_order", "integer", physicalType="INTEGER",
              quality=[_rule("duplicateValues")]),
        _prop("band_label", "string", physicalType="VARCHAR",
              quality=[_rule("nullValues")])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    seed = _entries(tmp_path / "seeds" / "seeds.yml", "seeds")[1]["band"]
    assert "contract" not in seed
    columns = {column["name"]: column for column in seed["columns"]}
    assert columns["band_order"]["data_tests"] == ["unique"]
    assert columns["band_order"]["tests"] == ["unique", "not_null"]
    assert columns["band_label"] == {"name": "band_label", "data_tests": ["not_null"]}


MODEL_WITHOUT_TESTS = """version: 2

models:
  - name: a_model
    columns:
      - name: order_key
"""


def test_generate_writes_a_model_column_data_tests_from_its_quality(tmp_path):
    """A model's rules live in the contract; the properties file only carries them out."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR",
                         quality=[_rule("nullValues"), _rule("duplicateValues")])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column == {"name": "order_key", "data_type": "VARCHAR",
                      "data_tests": ["not_null", "unique"], "description": "The order_key."}
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_renders_required_and_a_single_column_key_as_tests(tmp_path):
    """`required` is enforced as not_null and a one-column primaryKey as unique on every platform;
    a composite key has no per-column test and is left to `profile`."""
    _repo(tmp_path, models=["a_model", "b_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", primaryKey=True,
                         required=True, quality=[_rule("nullValues")])))
    _contract(tmp_path, "core", "b_model", schema=_element(
        "b_model", _prop("day", "date", primaryKey=True, required=True),
        _prop("store", "string", primaryKey=True)))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["data_tests"] == ["not_null", "unique"]
    b_model = _entries(tmp_path / "models" / "core" / "_generated.yml")[1]["b_model"]
    tests = {c["name"]: c.get("data_tests") for c in b_model["columns"]}
    assert tests == {"day": ["not_null"], "store": None}
    assert _run("check", "--root", str(tmp_path)) == (0, [])


BLOCK_TESTS_PROPERTIES = """version: 2

models:
  - name: a_model
    columns:
      - name: order_key
        tests:
          - not_null
          - unique
"""


def test_generate_drops_a_block_sequence_tests_list_it_restates_exactly(tmp_path):
    """A block sequence is the same declaration as a flow list; both are one rename away."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": BLOCK_TESTS_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR",
                         quality=[_rule("nullValues"), _rule("duplicateValues")])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    text = (tmp_path / "models" / "core" / "_core.yml").read_text(encoding="utf-8")
    assert not [line for line in text.splitlines() if line.strip().startswith("tests:")]
    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column == {"name": "order_key", "data_type": "VARCHAR",
                      "data_tests": ["not_null", "unique"], "description": "The order_key."}
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_leaves_a_block_sequence_tests_list_the_contract_only_partly_restates(tmp_path):
    """A list carrying a rule the contract does not is left whole: deleting it drops a test."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": BLOCK_TESTS_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("duplicateValues")])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["tests"] == ["not_null", "unique"]
    assert column["data_tests"] == ["unique"]

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "a_model.columns.order_key.tests" in diags[0]["message"]


def test_generate_writes_accepted_values_with_its_arguments(tmp_path):
    """A constrained column keeps the set it is constrained to, not just the test's name."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("invalidValues", arguments={"validValues": ["online", "in_store"]})])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["data_tests"] == [
        {"accepted_values": {"arguments": {"values": ["online", "in_store"]}}}
    ]


def test_generate_still_reads_the_legacy_valid_values_spelling(tmp_path):
    """A contract written before the ODCS spelling keeps its test."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("invalidValues", arguments={"valid_values": ["online", "in_store"]})])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["data_tests"] == [
        {"accepted_values": {"arguments": {"values": ["online", "in_store"]}}}
    ]


def test_generate_writes_a_relationships_test_from_the_property(tmp_path):
    """A declared foreign key becomes the test dbt enforces it with, naming its target."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR",
                         relationships=[{"to": "core.dim_customer.customer_key"}])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["data_tests"] == [
        {"relationships": {"arguments": {"to": "ref('dim_customer')", "field": "customer_key"}}}
    ]
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_refuses_a_relationship_that_names_no_column(tmp_path):
    """A foreign key with no column to check would be dropped silently, which is worse."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITHOUT_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR",
                         relationships=[{"to": "dim_customer"}])))

    code, diags = _run("generate", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/unmapped-relationship"])
    assert "core.a_model.order_key" in diags[0]["message"]
    assert (tmp_path / "models" / "core" / "_core.yml").read_text() == MODEL_WITHOUT_TESTS


def test_generate_renames_a_model_tests_list_it_restates_exactly(tmp_path):
    """The migration: the contract carries the rules the hand-written list already stated."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("duplicateValues"), _rule("nullValues")]),
        _prop("total_amount", "number", physicalType="DECIMAL(10,2)")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    columns = {column["name"]: column
               for column in _entries(tmp_path / "models" / "core" / "_core.yml")[1][
                   "a_model"]["columns"]}
    assert "tests" not in columns["order_key"]
    assert columns["order_key"]["data_tests"] == ["unique", "not_null"]
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_writes_the_dlt_column_hints(tmp_path):
    """One hints module for every dlt-loaded table, typed from the contract's `physicalType`."""
    _repo(tmp_path, sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata",
        _prop("store_id", "integer", physicalType="BIGINT", required=True),
        _prop("amount", "number", physicalType="DECIMAL(10,2)"),
        _prop("ordered", "date", physicalType="DATE"),
        _prop("loaded_at", "timestamp", physicalType="TIMESTAMP WITH TIME ZONE")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    module = tmp_path / "ingestion" / "contracts.py"
    namespace: dict = {}
    exec(compile(module.read_text(encoding="utf-8"), str(module), "exec"), namespace)
    assert namespace["COLUMNS"] == {
        "orderdata": {
            "store_id": {"data_type": "bigint", "nullable": False},
            "amount": {"data_type": "decimal", "nullable": True},
            "ordered": {"data_type": "date", "nullable": True},
            "loaded_at": {"data_type": "timestamp", "nullable": True},
        }
    }


def test_generate_writes_hints_for_a_proposed_dlt_input_but_no_dbt_keys(tmp_path):
    """Contract-first: the input's COLUMNS land its table; a proposed dbt relation gets no keys."""
    _repo(tmp_path, models=["a_model"], sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "bronze", "orderdata", status="proposed", schema=_element(
        "orderdata", _prop("store_id", "integer", physicalType="BIGINT", required=True)))
    _contract(tmp_path, "core", "a_model", status="proposed", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True)))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    module = tmp_path / "ingestion" / "contracts.py"
    namespace: dict = {}
    exec(compile(module.read_text(encoding="utf-8"), str(module), "exec"), namespace)
    assert namespace["COLUMNS"] == {
        "orderdata": {"store_id": {"data_type": "bigint", "nullable": False}}}
    assert not list((tmp_path / "models" / "core").glob("*.yml"))
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_twice_changes_nothing(tmp_path):
    """A re-run reproduces every generated file byte for byte."""
    _repo(tmp_path, models=["a_model"], sources={"shop": ("bronze", ["orderdata"])},
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("duplicateValues"), _rule("nullValues")]),
        _prop("total_amount", "number", physicalType="DECIMAL(10,2)",
              relationships=[{"to": "core.dim_customer.customer_key"}])))
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata", _prop("store_id", "integer", physicalType="BIGINT")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    written = [tmp_path / "models" / "core" / "_core.yml",
               tmp_path / "ingestion" / "contracts.py"]
    first = [path.read_text(encoding="utf-8") for path in written]
    assert _run("generate", "--root", str(tmp_path)) == (0, [])
    assert [path.read_text(encoding="utf-8") for path in written] == first
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_check_reports_a_generated_key_removed_by_hand(tmp_path):
    """One computation: `check` diffs exactly what `generate` would write."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("duplicateValues"), _rule("nullValues")]),
        _prop("total_amount", "number", physicalType="DECIMAL(10,2)")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])
    assert _run("check", "--root", str(tmp_path)) == (0, [])

    path = tmp_path / "models" / "core" / "_core.yml"
    doc, _ = _entries(path)
    model = doc["models"][0]
    del model["contract"]
    del model["columns"][1]["data_type"]
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale", "generated/stale"])
    assert all("_core.yml" in diag["message"] for diag in diags)
    assert any("a_model.contract" in diag["message"] for diag in diags)
    assert any("a_model.columns.total_amount.data_type" in diag["message"] for diag in diags)

    assert _run("generate", "--root", str(tmp_path)) == (0, [])
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_generate_says_so_when_the_map_declares_no_contract_path(tmp_path):
    """A repo that has not adopted contracts gets a diagnosis, not a traceback."""
    (tmp_path / "repo-map.json").write_text(json.dumps({"artifact_paths": {}, "layers": {}}))
    code, diags = _run("generate", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/unconfigured"])


def test_generate_refuses_a_contract_whose_servers_disagree_with_the_map(tmp_path):
    """Write nothing from a contract that is already inconsistent with the map."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    servers = [{"type": "duckdb", "database": "domain.duckdb", "schema": "staging"}]
    _contract(tmp_path, "core", "a_model", servers=servers, schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR")))

    code, diags = _run("generate", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["servers/mismatch"])
    assert "'staging'" in diags[0]["message"] and "'core'" in diags[0]["message"]
    assert (tmp_path / "models" / "core" / "_core.yml").read_text() == CORE_PROPERTIES

    _contract(tmp_path, "core", "a_model", servers=[{**servers[0], "schema": "core"}],
              schema=_element(
                  "a_model", _prop("order_key", "string", physicalType="VARCHAR")))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])


def test_check_reports_a_generated_module_that_no_longer_parses(tmp_path):
    """A hand-mangled module is stale, not a traceback: stdout stays JSON."""
    _repo(tmp_path, sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata", _prop("store_id", "integer", physicalType="BIGINT")))
    _generated(tmp_path)

    module = tmp_path / "ingestion" / "contracts.py"
    module.write_text(module.read_text(encoding="utf-8") + "(\n", encoding="utf-8")

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "ingestion/contracts.py" in diags[0]["message"]
    assert "COLUMNS" in diags[0]["message"]


def test_check_reports_a_missing_generated_module(tmp_path):
    """Contract present and `generate` never run is the staleness the gate exists for."""
    _repo(tmp_path, sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata", _prop("store_id", "integer", physicalType="BIGINT")))

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "ingestion/contracts.py" in diags[0]["message"]


def test_check_reports_a_model_with_no_generated_entry(tmp_path):
    """A contract whose properties entry was never generated is stale, not silent."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR")))

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "models/core/_generated.yml" in diags[0]["message"]
    assert "models.a_model" in diags[0]["message"]


def test_check_reports_a_contract_hand_written_on_a_seed(tmp_path):
    """Seeds never carry a contract; one added by hand is a generated key out of place."""
    _repo(tmp_path, seeds=["band"], files={"seeds/seeds.yml": """version: 2

seeds:
  - name: band
    contract: {enforced: true}
    columns:
      - name: band_order
        data_tests: [unique]
"""})
    _contract(tmp_path, "seeds", "band", schema=_element(
        "band", _prop("band_order", "integer", quality=[_rule("duplicateValues")])))

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "band.contract" in diags[0]["message"]


def test_check_reports_a_data_type_on_a_column_the_contract_never_declares(tmp_path):
    """`check` proves the owned keys are absent where the contract does not own them, too."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR", quality=[
            _rule("duplicateValues"), _rule("nullValues")])))
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])

    path = tmp_path / "models" / "core" / "_core.yml"
    doc, _ = _entries(path)
    doc["models"][0]["columns"][1]["data_type"] = "VARCHAR"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "a_model.columns.total_amount.data_type" in diags[0]["message"]


def test_check_reports_a_tests_list_the_contract_does_not_restate(tmp_path):
    """The legacy key is `generate`'s to remove: a list it cannot rename is drift, not dbt's error."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": BLOCK_TESTS_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR")))
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "a_model.columns.order_key.tests" in diags[0]["message"]


def test_check_reports_a_model_data_tests_the_contract_does_not_declare(tmp_path):
    """`generate` owns a model column's `data_tests`; a list it does not produce is drift.

    Including where the contract states no rule at all: the key is one `generate` writes for
    every model, so its absence from this contract's rules does not make it someone else's.
    """
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITH_DATA_TESTS})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", physicalType="VARCHAR"),
        _prop("amount", "number", physicalType="DOUBLE")))
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "a_model.columns.order_key.data_tests" in diags[0]["message"]
    column = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]["columns"][0]
    assert column["data_tests"] == ["unique", "not_null"]


def test_hand_written_data_type_on_a_seed_column_is_not_stale(tmp_path):
    """A seed carries generated `data_tests`; a `data_type` there is hand-written and not ours."""
    _repo(tmp_path, seeds=["band"], files={"seeds/seeds.yml": SEED_WITH_DATA_TYPE})
    _contract(tmp_path, "seeds", "band", schema=_element(
        "band", _prop("band_order", "integer", quality=[_rule("duplicateValues")])))
    _generated(tmp_path)

    assert _run("check", "--root", str(tmp_path)) == (0, [])
    column = _entries(tmp_path / "seeds" / "seeds.yml", "seeds")[1]["band"]["columns"][0]
    assert column == {"name": "band_order", "data_type": "INTEGER", "data_tests": ["unique"]}


def test_generate_augments_a_zero_indent_properties_file(tmp_path):
    """A block sequence at its key's indent is one entry; a second is dbt's hard parse error."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": ZERO_INDENT_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", physicalType="VARCHAR"),
        _prop("note", "string", physicalType="VARCHAR", description=None)))
    _generated(tmp_path)

    # `note` keeps its hand-written text: no source names it, so it is neither rewritten nor stale.
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/undescribed"])
    text = (tmp_path / "models" / "core" / "_core.yml").read_text(encoding="utf-8")
    assert text.count("- name: a_model") == 1
    model = yaml.safe_load(text)["models"][0]
    assert model["contract"] == {"enforced": True}
    assert model["columns"] == [
        {"name": "order_key", "description": "The order_key.", "data_type": "VARCHAR"},
        {"name": "note", "description": "hand-written", "data_type": "VARCHAR"},
    ]


def test_check_reports_a_seed_data_tests_the_contract_cannot_translate(tmp_path):
    """`generate` never deletes: a rule it cannot translate yet must not hide the leftover."""
    _repo(tmp_path, seeds=["band"], files={"seeds/seeds.yml": SEED_WITH_LEFTOVER})
    _contract(tmp_path, "seeds", "band", schema=_element(
        "band", _prop("band_order", "integer", quality=[_rule("nullValues", mustBe=100)])))

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "band.columns.band_order.data_tests" in diags[0]["message"]


def test_check_reports_a_data_type_when_the_contract_declares_no_properties(tmp_path):
    """A model element with no properties yields no column vocabulary; the absence half still runs."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": MODEL_WITH_DATA_TYPE})
    _contract(tmp_path, "core", "a_model")
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["generated/stale"])
    assert "a_model.columns.order_key.data_type" in diags[0]["message"]


REVERSE_PROPERTIES = """version: 2

models:
  - name: a_model
    description: One row per order.
    columns:
      - name: order_key
        description: Surrogate key.
        tests: [not_null, unique]
      - name: channel
        tests:
          - accepted_values:
              arguments:
                values: ['online', 'in_store']
"""


def _warehouse(tmp_path, relations):
    """A local database of `{(schema, table): [(column, physical type, nullable)]}`."""
    import duckdb

    con = duckdb.connect(str(tmp_path / WAREHOUSE))
    try:
        for (schema_name, table_name), columns in relations.items():
            con.execute(f"create schema if not exists {schema_name}")
            body = ", ".join(
                f'"{name}" {physical}{"" if nullable else " NOT NULL"}'
                for name, physical, nullable in columns
            )
            con.execute(f'create table {schema_name}."{table_name}" ({body})')
    finally:
        con.close()


def _written(tmp_path, schema_name, table_name):
    """The contract `reverse` wrote, parsed."""
    path = tmp_path / "contracts" / schema_name / f"{table_name}.odcs.yaml"
    assert path.is_file(), f"no contract at {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _properties_by_name(doc):
    return {prop["name"]: prop for prop in doc["schema"][0]["properties"]}


def test_reverse_drafts_a_grounded_contract_from_the_catalog(tmp_path):
    """A nullable, undescribed column yields no quality, no primaryKey and no `required: true`."""
    _repo(tmp_path, models=["a_model"])
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", True), ("amount", "DOUBLE", True)]})

    _reversed(tmp_path)

    doc = _written(tmp_path, "core", "a_model")
    assert (doc["apiVersion"], doc["kind"]) == ("v3.2.0", "DataContract")
    assert (doc["name"], doc["version"], doc["status"]) == ("a_model", "1.0.0", "active")
    assert doc["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "core.a_model"))
    element = doc["schema"][0]
    assert element["name"] == "a_model"
    assert "dataGranularityDescription" not in element
    assert element["properties"] == [
        {"name": "order_key", "logicalType": "string", "physicalType": "VARCHAR"},
        {"name": "amount", "logicalType": "number", "physicalType": "DOUBLE"},
    ]
    assert "quality" not in element and "primaryKey" not in element
    assert "authoritativeDefinitions" not in doc

    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/no-grain", "contract/undescribed",
                                         "contract/undescribed"])


def test_reverse_carries_a_generic_test_as_a_quality_rule(tmp_path):
    """Only an existing dbt test becomes a rule, in the shape `generate` translates back."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": REVERSE_PROPERTIES})
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False),
        ("channel", "VARCHAR", True),
        ("amount", "DOUBLE", True)]})

    _reversed(tmp_path)

    props = _properties_by_name(_written(tmp_path, "core", "a_model"))
    assert props["order_key"]["quality"] == [_rule("nullValues"), _rule("duplicateValues")]
    assert props["order_key"]["description"] == "Surrogate key."
    assert props["channel"]["quality"] == [
        {"type": "library", "metric": "invalidValues",
         "arguments": {"validValues": ["online", "in_store"]}, "mustBe": 0}
    ]
    assert "quality" not in props["amount"]


def test_reverse_takes_the_timezone_option_from_the_model(tmp_path):
    """`DateTimeTz` carries the offset; `DateTime` does not, even over a timezone-aware column."""
    fields = {"order_key": "String", "loaded_at": "DateTimeTz", "booked_at": "DateTime"}
    _repo(tmp_path, models=["a_model"],
          logical_model=_model(("a_model", fields, ["order_key"])))
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False),
        ("loaded_at", "TIMESTAMP", True),
        ("booked_at", "TIMESTAMP WITH TIME ZONE", True)]})

    _reversed(tmp_path)

    props = _properties_by_name(_written(tmp_path, "core", "a_model"))
    assert props["loaded_at"]["logicalTypeOptions"] == {"timezone": True}
    assert "logicalTypeOptions" not in props["booked_at"]


def test_reverse_grounds_a_gold_contract_in_its_canonical_document(tmp_path):
    """The model's `Decimal` wins over the catalog's VARCHAR, and the contract links the document."""
    _repo(tmp_path, models=["a_model"], logical_model=_model((
        "a_model", {"order_key": "String", "total_amount": "Decimal"}, ["order_key"])))
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False), ("total_amount", "VARCHAR", True)]})

    _reversed(tmp_path)

    doc = _written(tmp_path, "core", "a_model")
    props = _properties_by_name(doc)
    assert props["total_amount"]["logicalType"] == "number"
    assert props["total_amount"]["physicalType"] == "VARCHAR"
    assert props["order_key"]["primaryKey"] is True
    assert doc["authoritativeDefinitions"] == [
        {"url": "logical-model/model.ossie.yaml", "type": "businessDefinition"}
    ]


def test_reverse_reproduces_its_files_byte_for_byte(tmp_path):
    """The id is derived from the relation, so a forced rewrite is the same file, not a new one."""
    _repo(tmp_path, models=["a_model"], logical_model=_model((
        "a_model", {"order_key": "String", "total_amount": "Decimal"}, ["order_key"])))
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False), ("total_amount", "DECIMAL(10,2)", True)]})

    _reversed(tmp_path)
    path = tmp_path / "contracts" / "core" / "a_model.odcs.yaml"
    first = path.read_bytes()
    _reversed(tmp_path, "--force")
    assert path.read_bytes() == first


def test_reverse_drafts_the_boundary_and_nothing_else(tmp_path):
    """Inputs and gold are drafted; audit, `_dlt_*`, staging, seeds and strays are not."""
    _repo(tmp_path, models=["a_model"], staging=["stg_a"], seeds=["band"],
          sources={"shop": ("bronze", ["orderdata"])})
    _warehouse(tmp_path, {
        ("bronze", "orderdata"): [("store_id", "BIGINT", True)],
        ("bronze", "audit_runs"): [("load_id", "VARCHAR", True)],
        ("bronze", "_dlt_loads"): [("load_id", "BIGINT", True)],
        ("core", "a_model"): [("amount", "DOUBLE", True)],
        ("staging", "stg_a"): [("amount", "DOUBLE", True)],
        ("seeds", "band"): [("band_order", "BIGINT", True)],
        ("main", "stray_relation"): [("day", "DATE", True)],
    })

    diags = _reversed(tmp_path)

    written = sorted(path.relative_to(tmp_path).as_posix()
                     for path in (tmp_path / "contracts").rglob("*.odcs.yaml"))
    assert written == ["contracts/bronze/orderdata.odcs.yaml", "contracts/core/a_model.odcs.yaml"]
    # Gold first, then inputs: the order a reviewer triages in.
    schemas = [d["message"].split(".", 1)[0] for d in diags]
    assert schemas == sorted(schemas, key=["core", "bronze"].index) and "bronze" in schemas

    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 0 and set(_codes(diags)) <= {"contract/no-grain", "contract/undescribed"}
    hints = (tmp_path / "ingestion" / "contracts.py").read_text(encoding="utf-8")
    assert "orderdata" in hints and "audit_runs" not in hints


def test_reverse_says_so_when_no_warehouse_resolves(tmp_path):
    """A missing catalog is a diagnosis naming the path, not a traceback on stdout."""
    _repo(tmp_path, models=["a_model"])

    code, diags = _run("reverse", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["catalog/missing"])
    assert WAREHOUSE in diags[0]["message"]
    assert not (tmp_path / "contracts").exists()


SEED_WITH_BOTH_SPELLINGS = """version: 2

seeds:
  - name: band
    columns:
      - name: band_order
        tests: [unique, not_null]
"""


def test_generate_renames_a_seed_tests_list_it_restates_exactly(tmp_path):
    """dbt refuses `tests` and `data_tests` on one column; the same rules are one declaration."""
    _repo(tmp_path, seeds=["band"], files={"seeds/seeds.yml": SEED_WITH_BOTH_SPELLINGS})
    _contract(tmp_path, "seeds", "band", schema=_element(
        "band", _prop("band_order", "integer", quality=[
            _rule("duplicateValues"), _rule("nullValues")])))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])

    column = _entries(tmp_path / "seeds" / "seeds.yml", "seeds")[1]["band"]["columns"][0]
    assert column == {"name": "band_order", "data_tests": ["unique", "not_null"]}
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_gold_relation_in_a_schema_the_model_never_covers_is_not_a_gap(tmp_path):
    """The model partitions the Domain by star: a schema it names nothing in warns, never fails."""
    _orders(tmp_path)
    map_path = tmp_path / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    repo_map["layers"]["agg"] = {"schema": "agg", "path": "models/agg/", "built_by": "dbt"}
    repo_map["gold_layers"] = ["core", "agg"]
    map_path.write_text(json.dumps(repo_map))
    (tmp_path / "models" / "agg").mkdir(parents=True)
    (tmp_path / "models" / "agg" / "agg_mart.sql").write_text("select 1\n")
    _contract(tmp_path, "agg", "agg_mart")
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/no-document"])
    assert "agg.agg_mart" in diags[0]["message"]


def _set_map(tmp_path, edit):
    map_path = tmp_path / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    edit(repo_map)
    map_path.write_text(json.dumps(repo_map))
    return repo_map


def test_role_derived_from_legacy_keys(tmp_path):
    """No `role` key: dlt is input, a `gold_layers` name is boundary, everything else internal."""
    _repo(tmp_path, models=["a_model"])
    repo_map = json.loads((tmp_path / "repo-map.json").read_text())
    assert odcs._role_for(repo_map, "bronze") == "input"
    assert odcs._role_for(repo_map, "core") == "boundary"
    assert odcs._role_for(repo_map, "staging") == "internal"
    assert odcs._role_for(repo_map, "seeds") == "internal"
    assert odcs._roles(repo_map) == {
        "bronze": "input", "staging": "internal", "core": "boundary", "seeds": "internal"}
    repo_map["gold_layers"] = ["core", "bronze"]
    assert odcs._role_for(repo_map, "bronze") == "input"  # built_by dlt wins over gold_layers


def test_explicit_role_overrides_derivation(tmp_path):
    """A dlt layer marked boundary ranks first, a gold_layers dbt layer marked internal owes none,
    and a dbt layer marked input owes contracts for its relations."""
    _repo(tmp_path, models=["a_model"], staging=["stg_a"], sources={"src": ("bronze", ["t"])})
    repo_map = _set_map(tmp_path, lambda m: (
        m["layers"]["bronze"].__setitem__("role", "boundary"),
        m["layers"]["core"].__setitem__("role", "internal"),
        m["layers"]["staging"].__setitem__("role", "input")))
    declared = odcs.declared_relations(tmp_path, repo_map)
    assert set(odcs.boundary_relations(repo_map, declared)) == {("bronze", "t"), ("staging", "stg_a")}
    assert ("core", "a_model") not in odcs.boundary_relations(repo_map, declared)
    assert odcs._boundary_rank(("bronze", "t"), repo_map, declared) == 0
    assert odcs._boundary_rank(("core", "a_model"), repo_map, declared) == 2
    code, diags = _run("check", "--root", str(tmp_path))
    assert sorted(d["message"] for d in diags if d["code"] == "contract/missing") == [
        "bronze.t: declared by source src, on the contract boundary, and has no contract",
        "staging.stg_a: declared by layer staging, on the contract boundary, and has no contract"]


def test_explicit_internal_role_on_a_dlt_layer_exempts_its_sources(tmp_path):
    _repo(tmp_path, models=["a_model"], sources={"src": ("bronze", ["t"])})
    repo_map = _set_map(tmp_path, lambda m: m["layers"]["bronze"].__setitem__("role", "internal"))
    declared = odcs.declared_relations(tmp_path, repo_map)
    assert ("bronze", "t") not in odcs.boundary_relations(repo_map, declared)


def test_a_derived_internal_layer_still_owes_contracts_for_sources_landing_in_it(tmp_path):
    _repo(tmp_path, models=["a_model"], sources={"src": ("bronze", ["t"])})

    def edit(m):
        m["layers"]["bronze"].pop("built_by")
        m["layers"]["bronze"].pop("path")
    repo_map = _set_map(tmp_path, edit)
    assert odcs._role_for(repo_map, "bronze") == "internal"
    declared = odcs.declared_relations(tmp_path, repo_map)
    assert ("bronze", "t") in odcs.boundary_relations(repo_map, declared)


def test_generate_replaces_a_block_scalar_description_without_a_blank_line(tmp_path):
    star = _star(tmp_path, description="One row per order.",
                 fields=[_field("order_key", "Surrogate key.")])
    block = ("version: 2\n\nmodels:\n  - name: a_model\n    description: >\n      Old text\n"
             "      wrapped.\n\n    columns:\n      - name: order_key\n        description: |\n"
             "          Old column.\n\n        data_tests: [unique]\n")
    _repo(tmp_path, models=["a_model"], logical_model=star, files={"models/core/_core.yml": block})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _generated(tmp_path)
    path = tmp_path / "models" / "core" / "_core.yml"
    first = path.read_text(encoding="utf-8")
    assert "description: One row per order.\n" in first
    assert "description: Surrogate key.\n        data_tests" in first
    assert "\n\n\n" not in first
    _generated(tmp_path)
    assert path.read_text(encoding="utf-8") == first


def test_explicit_input_role_on_a_dbt_layer_owes_contracts(tmp_path):
    _repo(tmp_path, models=["a_model"], staging=["stg_a"])
    repo_map = _set_map(tmp_path, lambda m: m["layers"]["staging"].__setitem__("role", "input"))
    declared = odcs.declared_relations(tmp_path, repo_map)
    assert ("staging", "stg_a") in odcs.boundary_relations(repo_map, declared)


def test_contract_layers_wins_over_explicit_roles(tmp_path):
    _repo(tmp_path, models=["a_model"], staging=["stg_a"], sources={"src": ("bronze", ["t"])})
    repo_map = _set_map(tmp_path, lambda m: (
        m["layers"]["core"].__setitem__("role", "boundary"),
        m.__setitem__("contract_layers", ["staging"])))
    declared = odcs.declared_relations(tmp_path, repo_map)
    assert set(odcs.boundary_relations(repo_map, declared)) == {("staging", "stg_a")}


def test_gold_layers_naming_an_undeclared_layer_is_reported(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _set_map(tmp_path, lambda m: m.__setitem__("gold_layers", ["core", "platinum"]))
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1
    assert [d["message"] for d in diags if d["code"] == "map/gold-layers"] == [
        "repo-map.json `gold_layers` names `platinum`, which `layers` does not declare"]


def test_invalid_role_is_reported(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _set_map(tmp_path, lambda m: m["layers"]["core"].__setitem__("role", "gold"))
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1
    assert {"severity": "error", "code": "map/layer-role",
            "message": "repo-map.json layers.core.role must be input, internal or boundary"} in diags


def test_reverse_drops_the_loader_columns_from_a_dlt_relation(tmp_path):
    """dlt adds `_dlt_*` itself: a raw contract declares what the resource yields, not the loader's."""
    _repo(tmp_path, sources={"shop": ("bronze", ["orderdata"])})
    _warehouse(tmp_path, {("bronze", "orderdata"): [
        ("store_id", "BIGINT", True),
        ("_dlt_load_id", "VARCHAR", False),
        ("_dlt_id", "VARCHAR", False)]})

    _reversed(tmp_path)

    properties = _written(tmp_path, "bronze", "orderdata")["schema"][0]["properties"]
    assert [prop["name"] for prop in properties] == ["store_id"]

    _generated(tmp_path)
    assert "_dlt" not in (tmp_path / "ingestion" / "contracts.py").read_text(encoding="utf-8")


def test_check_allows_a_loader_column_only_where_a_dbt_model_propagates_it(tmp_path):
    """An enforced dbt contract rejects an undeclared output column, so a model keeps it."""
    _repo(tmp_path, models=["a_model"], sources={"shop": ("bronze", ["orderdata"])})
    loader = {"name": "_dlt_load_id", "logicalType": "string", "physicalType": "VARCHAR"}
    _contract(tmp_path, "bronze", "orderdata",
              schema=_element("orderdata", loader, _prop("store_id", "integer")))
    _contract(tmp_path, "core", "a_model", schema=_element("a_model", loader))
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["contract/loader-column", "contract/undescribed"])
    assert "bronze.orderdata" in diags[0]["message"] and "_dlt_load_id" in diags[0]["message"]

    _contract(tmp_path, "bronze", "orderdata", schema=_element("orderdata", _prop("store_id", "integer")))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 0 and set(_codes(diags)) <= {"contract/no-grain", "contract/undescribed"}
    model = _written(tmp_path, "core", "a_model")["schema"][0]["properties"]
    assert model[0]["name"] == "_dlt_load_id"


TEMPLATED_PROPERTIES = """version: 2

models:
  - name: a_model
    description: '{{ doc("model_grain") }}'
    columns:
      - name: order_key
        description: '{{ doc("order_key") }}'
      - name: amount
        description: The amount total, as billed.
"""


def test_reverse_omits_a_dbt_doc_reference_instead_of_copying_it(tmp_path):
    """`{{ doc(...) }}` is a pointer dbt resolves; a contract states prose or nothing."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": TEMPLATED_PROPERTIES})
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False), ("amount", "DOUBLE", True)]})

    _reversed(tmp_path)

    doc = _written(tmp_path, "core", "a_model")
    assert "dataGranularityDescription" not in doc["schema"][0]
    props = _properties_by_name(doc)
    assert "description" not in props["order_key"]
    assert props["amount"]["description"] == "The amount total, as billed."

    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/no-grain", "contract/undescribed"])


def test_check_calls_a_templated_grain_no_grain(tmp_path):
    """A `{{ ... }}` grain states nothing a reader can use, so the warning it would silence fires."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=[{
        "name": "a_model", "dataGranularityDescription": '{{ doc("model_grain") }}'}])
    _generated(tmp_path)

    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["contract/no-grain"])
    assert diags[0]["severity"] == "warning"


def test_reverse_leaves_an_existing_contract_alone_unless_forced(tmp_path):
    """The review edits a draft; a second pass must not quietly revert it."""
    _repo(tmp_path, models=["a_model"])
    _warehouse(tmp_path, {("core", "a_model"): [("order_key", "VARCHAR", True)]})
    _reversed(tmp_path)

    path = tmp_path / "contracts" / "core" / "a_model.odcs.yaml"
    written = path.read_text(encoding="utf-8")
    reviewed = written.replace("version: 1.0.0", "version: 2.0.0")
    path.write_text(reviewed, encoding="utf-8")

    code, diags = _run("reverse", "--root", str(tmp_path))
    assert code == 0
    exists = _findings(diags, "contract/exists")
    assert len(exists) == 1 and exists[0]["severity"] == "warning"
    assert "1" in exists[0]["message"]
    assert path.read_text(encoding="utf-8") == reviewed

    _reversed(tmp_path, "--force")
    assert path.read_text(encoding="utf-8") == written


RELATIONSHIP_PROPERTIES = """version: 2

models:
  - name: a_model
    columns:
      - name: customer_key
        tests:
          - relationships: {arguments: {to: ref('dim_customer'), field: customer_key}}
"""


def test_reverse_carries_a_relationships_test_as_a_property_relationship(tmp_path):
    """A `relationships` test is a declared foreign key, never a quality rule."""
    _repo(tmp_path, models=["a_model"],
          files={"models/core/_core.yml": RELATIONSHIP_PROPERTIES})
    _warehouse(tmp_path, {("core", "a_model"): [("customer_key", "VARCHAR", True)]})

    _reversed(tmp_path)

    prop = _properties_by_name(_written(tmp_path, "core", "a_model"))["customer_key"]
    assert prop["relationships"] == [{"to": "dim_customer.customer_key"}]
    assert "quality" not in prop


def _findings(diags, code):
    return [diag for diag in diags if diag["code"] == code]


def _finding_codes(diags):
    return [diag["code"] for diag in diags if diag["code"].startswith("finding/")]


def _load(tmp_path, schema_name, table_name, columns, rows):
    """Insert `rows` into a table `_warehouse` created, one list of values per row."""
    import duckdb

    con = duckdb.connect(str(tmp_path / WAREHOUSE))
    try:
        placeholders = ", ".join("?" for _ in columns)
        con.executemany(
            f'insert into {schema_name}."{table_name}" values ({placeholders})', rows)
    finally:
        con.close()


def test_reverse_reports_a_table_with_no_grain(tmp_path):
    """The question the review must answer before a contract can present itself as complete."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=[{
        "name": "a_model",
        "properties": [_prop("amount", "number", description="The amount total.")]}])
    _warehouse(tmp_path, {("core", "a_model"): [("amount", "DOUBLE", True)]})

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    findings = _findings(diags, "finding/no-grain")
    assert len(findings) == 1
    assert findings[0]["severity"] == "warning"
    assert findings[0]["message"].startswith("core.a_model: ")
    assert "one row" in findings[0]["message"]


def test_a_primary_key_states_the_grain(tmp_path):
    """A keyed contract needs no grain statement: neither `check` nor `reverse` asks for one."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=[{
        "name": "a_model",
        "properties": [_prop("order_key", "string", primaryKey=True, required=True,
                             description="The order key.")]}])
    _generated(tmp_path)
    _, diags = _run("check", "--root", str(tmp_path))
    assert "contract/no-grain" not in _codes(diags)
    _warehouse(tmp_path, {("core", "a_model"): [("order_key", "VARCHAR", False)]})
    _, diags = _run("reverse", "--root", str(tmp_path))
    assert not _findings(diags, "finding/no-grain")


def test_reverse_settles_a_nullable_column_the_data_never_nulls(tmp_path):
    """A null rate of zero is evidence: the question is answered, not queued."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("amount", "number", description="The amount total.")))
    _warehouse(tmp_path, {("core", "a_model"): [("amount", "DOUBLE", True)]})
    _load(tmp_path, "core", "a_model", ["amount"], [[1.0], [2.0]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _findings(diags, "finding/unproven-nullable") == []


def test_reverse_asks_about_a_nullable_column_the_data_fills_with_nulls(tmp_path):
    """Nulls present, no rule either way: the contract has not decided what null means."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("amount", "number", description="The amount total.")))
    _warehouse(tmp_path, {("core", "a_model"): [("amount", "DOUBLE", True)]})
    _load(tmp_path, "core", "a_model", ["amount"], [[1.0], [None]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    findings = _findings(diags, "finding/unproven-nullable")
    assert len(findings) == 1
    assert findings[0]["message"].startswith("core.a_model.amount: ")
    assert "null" in findings[0]["message"] and findings[0]["message"].endswith("?")


def test_reverse_asks_what_a_reference_shaped_column_points_at(tmp_path):
    """`customer_key` names a reference; without a `relationships` test nothing states its target."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("customer_key", "string", description="The ordered customer.")))
    _warehouse(tmp_path, {("core", "a_model"): [("customer_key", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["customer_key"], [["z1"], ["z2"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    findings = _findings(diags, "finding/undeclared-foreign-key")
    assert len(findings) == 1
    assert findings[0]["message"].startswith("core.a_model.customer_key: ")
    assert "relationships" in findings[0]["message"]


def test_reverse_leaves_a_reference_shaped_column_that_declares_its_target(tmp_path):
    """A declared relationship is the answer the class asks for; nothing is queued twice."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("customer_key", "string", description="The ordered customer.",
                         relationships=[{"to": "core.dim_customer.customer_key"}])))
    _warehouse(tmp_path, {("core", "a_model"): [("customer_key", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["customer_key"], [["z1"], ["z2"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _findings(diags, "finding/undeclared-foreign-key") == []


def test_reverse_asks_whether_a_low_cardinality_column_is_a_closed_set(tmp_path):
    """Few distinct values is the shape of an enum; only a rule says its set is closed."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("channel", "string", description="Online or in_store.")))
    _warehouse(tmp_path, {("core", "a_model"): [("channel", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["channel"],
          [["online"], ["in_store"], ["online"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    findings = _findings(diags, "finding/open-enum")
    assert len(findings) == 1
    assert findings[0]["message"].startswith("core.a_model.channel: ")
    assert "accepted_values" in findings[0]["message"]


def test_reverse_leaves_an_enum_alone_when_a_rule_closes_it(tmp_path):
    """`accepted_values` is the evidence that the value set is not open."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("channel", "string", description="Online or in_store.",
                         quality=[_rule("invalidValues",
                                        arguments={"validValues": ["online", "in_store"]})])))
    _warehouse(tmp_path, {("core", "a_model"): [("channel", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["channel"],
          [["online"], ["in_store"], ["online"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _findings(diags, "finding/open-enum") == []


def test_reverse_reports_a_key_shaped_column_the_data_repeats(tmp_path):
    """A key that repeats is not the row's key: one doubt, asked once, not twice."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description="Order key.")))
    _warehouse(tmp_path, {("core", "a_model"): [("order_key", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["order_key"], [["a"], ["a"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _finding_codes(diags) == ["finding/key-repeats"]
    assert _findings(diags, "finding/key-repeats")[0]["message"].startswith(
        "core.a_model.order_key: ")


def test_reverse_asks_a_repeating_key_what_it_targets(tmp_path):
    """A repeating key-shaped column is asked once, and the question must name its target.

    Class 4 already asks whether the column is a key or a repeated reference; a repeated
    reference is still a foreign key with no declared target, so the same question carries both.
    """
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("driver_key", "string", description="The driver.")))
    _warehouse(tmp_path, {("core", "a_model"): [("driver_key", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["driver_key"], [["d1"], ["d1"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _finding_codes(diags) == ["finding/key-repeats"]
    message = _findings(diags, "finding/key-repeats")[0]["message"]
    assert "identify one row" in message
    assert "what does it target" in message


def test_reverse_keeps_a_key_shaped_column_out_of_the_value_set_question(tmp_path):
    """A key is an identifier; "which values are valid" is a question it cannot answer."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("garage_key", "string", description="The garage.")))
    _warehouse(tmp_path, {("core", "a_model"): [("garage_key", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["garage_key"], [["g1"], ["g2"], ["g1"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    assert _findings(diags, "finding/open-enum") == []
    assert "finding/key-repeats" in _finding_codes(diags)


def test_reverse_asks_whether_an_identifier_is_the_relations_own(tmp_path):
    """A raw relation declares no primary key, so `garage_id` may name its own row, not another's."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("garage_id", "string", description="The garage.")))
    _warehouse(tmp_path, {("core", "a_model"): [("garage_id", "VARCHAR", True)]})
    _load(tmp_path, "core", "a_model", ["garage_id"], [["g1"], ["g2"]])

    code, diags = _run("reverse", "--root", str(tmp_path))

    assert code == 0
    findings = _findings(diags, "finding/undeclared-foreign-key")
    assert len(findings) == 1
    assert findings[0]["message"].startswith("core.a_model.garage_id: ")
    assert "own identifier" in findings[0]["message"]


def test_reverse_findings_are_unique_and_identical_on_a_second_run(tmp_path):
    """Deterministic on the same warehouse, and one finding per relation, column and class."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", schema=[{
        "name": "a_model",
        "properties": [
            _prop("order_key", "string"),
            _prop("amount", "number", description="The amount total."),
            _prop("channel", "string", description="Online or in_store."),
            _prop("customer_key", "string", description="The ordered customer."),
        ]}])
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", True),
        ("amount", "DOUBLE", True),
        ("channel", "VARCHAR", True),
        ("customer_key", "VARCHAR", True),
    ]})
    _load(tmp_path, "core", "a_model",
          ["order_key", "amount", "channel", "customer_key"],
          [["t", None, "online", "z1"], ["t", 2.0, "in_store", "z1"]])

    first = _run("reverse", "--root", str(tmp_path))
    second = _run("reverse", "--root", str(tmp_path))

    assert first == second
    code, diags = first
    assert code == 0
    keys = [(diag["code"], diag["message"].split(": ", 1)[0])
            for diag in diags if diag["code"].startswith("finding/")]
    assert len(keys) == len(set(keys))
    declared = {"order_key", "amount", "channel", "customer_key"}
    for _, location in keys:
        parts = location.split(".")
        assert len(parts) in (2, 3), location
        if len(parts) == 3:
            assert parts[2] in declared, location


# ---------------------------------------------------------------------------
# The catalog: the half no file check can see
# ---------------------------------------------------------------------------


def _catalog(tmp_path, columns):
    """A local database file holding `core.a_model` with the given column names."""
    import duckdb

    path = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema core")
        con.execute(f"create table core.a_model ({', '.join(f'{c} varchar' for c in columns)})")
    finally:
        con.close()
    return path


def _relations_run(tmp_path, monkeypatch, catalog):
    # The generated keys are Task 3's subject; this run is about the catalog, so write them first
    # as an author would, and let `check` report only what the relation comparison adds.
    _run("generate", "--root", str(tmp_path))
    given = ["--catalog", str(catalog)] if catalog is not None else []
    return _run("check", "--root", str(tmp_path), "--relations", *given)


def _contract_with(tmp_path, columns, **overrides):
    properties = [{"name": c, "logicalType": "string", "physicalType": "VARCHAR",
                   "description": f"The {c}."} for c in columns]
    _contract(
        tmp_path,
        "core",
        "a_model",
        schema=[
            {
                "name": "a_model",
                "dataGranularityDescription": "One row per event.",
                "properties": properties,
            }
        ],
        **overrides,
    )


def test_relations_pass_when_the_catalog_matches_the_contract(tmp_path, monkeypatch):
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"])
    code, diags = _relations_run(tmp_path, monkeypatch, _catalog(tmp_path, ["x"]))
    assert code == 0 and [d for d in diags if d["code"].startswith(("relations/", "servers/"))] == []


def test_a_contract_column_the_catalog_lacks_is_a_mismatch(tmp_path, monkeypatch):
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x", "gone"])
    code, diags = _relations_run(tmp_path, monkeypatch, _catalog(tmp_path, ["x"]))
    assert code == 1
    assert [d["code"] for d in diags] == ["relations/mismatch"]
    assert "gone" in diags[0]["message"]


def test_a_catalog_column_the_contract_dropped_is_a_mismatch(tmp_path, monkeypatch):
    """Case C: the contract says the shape, and the landed relation still carries a column."""
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"])
    code, diags = _relations_run(tmp_path, monkeypatch, _catalog(tmp_path, ["x", "surprise"]))
    assert code == 1
    assert [d["code"] for d in diags] == ["relations/mismatch"]
    assert "surprise" in diags[0]["message"]


def test_relations_without_a_catalog_fail_rather_than_skip(tmp_path, monkeypatch):
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"])
    code, diags = _relations_run(tmp_path, monkeypatch, None)
    assert code == 1
    assert [d["code"] for d in diags] == ["catalog/missing"]


def test_a_server_that_disagrees_with_the_platform_is_a_mismatch(tmp_path, monkeypatch):
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"], servers=[{"server": "a_model", "type": "custom"}])
    code, diags = _relations_run(tmp_path, monkeypatch, _catalog(tmp_path, ["x"]))
    assert code == 1
    assert [d["code"] for d in diags] == ["servers/mismatch"]
    assert "custom" in diags[0]["message"]


def test_a_loader_column_in_the_catalog_is_not_a_mismatch(tmp_path, monkeypatch):
    """The loader adds `_dlt_*` to a raw relation; that is not the relation's shape."""
    _repo(tmp_path, sources={"src": ("bronze", ["t"])})
    _contract(
        tmp_path,
        "bronze",
        "t",
        schema=[
            {
                "name": "t",
                "dataGranularityDescription": "One row per event.",
                "properties": [{"name": "x", "logicalType": "string", "physicalType": "VARCHAR"}],
            }
        ],
    )
    _run("generate", "--root", str(tmp_path))
    catalog = tmp_path / "warehouse.duckdb"
    import duckdb

    con = duckdb.connect(str(catalog))
    try:
        con.execute("create schema bronze")
        con.execute("create table bronze.t (x varchar, _dlt_id varchar, _dlt_load_id varchar)")
    finally:
        con.close()
    code, diags = _run("check", "--root", str(tmp_path), "--relations", "--catalog", str(catalog))
    assert [d["code"] for d in diags if d["code"].startswith(("relations/", "servers/"))] == []


def test_a_relation_the_catalog_does_not_hold_is_a_mismatch(tmp_path, monkeypatch):
    """A partial build must fail the comparison, not pass it by having nothing to compare."""
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"])
    empty = tmp_path / "warehouse.duckdb"
    import duckdb

    con = duckdb.connect(str(empty))
    try:
        con.execute("create schema core")
    finally:
        con.close()
    code, diags = _relations_run(tmp_path, monkeypatch, empty)
    assert code == 1
    assert [d["code"] for d in diags] == ["relations/mismatch"]
    assert "no such relation" in diags[0]["message"]


def test_a_contract_whose_name_is_not_its_relation_is_misnamed(tmp_path):
    """The path places the file; the name is what a consumer reads."""
    _repo(tmp_path, models=["a_model"])
    _contract(
        tmp_path,
        "core",
        "a_model",
        schema=[{"name": "dim_something_else", "dataGranularityDescription": "One row."}],
    )
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1
    assert "contract/misnamed" in [d["code"] for d in diags]


def _gold_document(relationships=(), unique_keys=None):
    dataset = {
        "name": "orders",
        "source": "core.a_model",
        "primary_key": ["id"],
        "fields": [{"name": "id", "datatype": "String"}],
    }
    if unique_keys:
        dataset["unique_keys"] = unique_keys
    return {
        "version": "0.2.0.dev0",
        "name": "doc",
        "datasets": [dataset],
        "relationships": list(relationships),
    }


def _gold_contract(tmp_path, relationships=None):
    prop = {"name": "id", "logicalType": "string", "physicalType": "VARCHAR", "primaryKey": True}
    if relationships is not None:
        prop["relationships"] = relationships
    _contract(
        tmp_path,
        "core",
        "a_model",
        schema=[
            {
                "name": "a_model",
                "dataGranularityDescription": "One row per order.",
                "properties": [prop],
            }
        ],
    )


def test_a_declared_relationship_the_contract_drops_is_reported(tmp_path):
    """The document states the identity graph; a contract that drops an edge cannot be joined."""
    _repo(
        tmp_path,
        models=["a_model"],
        logical_model=_gold_document(
            relationships=[
                {
                    "name": "order_to_order",
                    "from": "orders",
                    "to": "orders",
                    "from_columns": ["id"],
                    "to_columns": ["id"],
                }
            ]
        ),
    )
    _gold_contract(tmp_path)
    _run("generate", "--root", str(tmp_path))
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 0
    assert [d["code"] for d in diags] == ["boundary/missing-relationship"]
    assert diags[0]["severity"] == "warning"
    assert "order_to_order" in diags[0]["message"]


def test_a_declared_relationship_the_contract_carries_passes(tmp_path):
    _repo(
        tmp_path,
        models=["a_model"],
        logical_model=_gold_document(
            relationships=[
                {
                    "name": "order_to_order",
                    "from": "orders",
                    "to": "orders",
                    "from_columns": ["id"],
                    "to_columns": ["id"],
                }
            ]
        ),
    )
    _gold_contract(tmp_path, relationships=[{"to": "a_model.id"}])
    _run("generate", "--root", str(tmp_path))
    code, diags = _run("check", "--root", str(tmp_path))
    assert [d["code"] for d in diags if d["code"].startswith("boundary/")] == []


def test_a_composite_unique_key_is_reported_as_inexpressible(tmp_path):
    """ODCS states uniqueness per property, so a multi-column key is a warning, not silence."""
    _repo(tmp_path, models=["a_model"], logical_model=_gold_document(unique_keys=[["id", "name"]]))
    _gold_contract(tmp_path)
    _run("generate", "--root", str(tmp_path))
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 0
    assert [d["code"] for d in diags] == ["boundary/composite-key"]
    assert diags[0]["severity"] == "warning"


def test_a_relationship_naming_the_wrong_target_is_reported(tmp_path):
    """The column alone is not the edge: the target has to be the relation the model names."""
    _repo(
        tmp_path,
        models=["a_model"],
        logical_model=_gold_document(
            relationships=[
                {
                    "name": "order_to_order",
                    "from": "orders",
                    "to": "orders",
                    "from_columns": ["id"],
                    "to_columns": ["id"],
                }
            ]
        ),
    )
    _gold_contract(tmp_path, relationships=[{"to": "a_model.other.id"}])
    _run("generate", "--root", str(tmp_path))
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 0
    assert [d["code"] for d in diags] == ["boundary/missing-relationship"]


# ---------------------------------------------------------------------------
# One owner per fact: keys both ways, exclusions, proposed contracts, star members
# ---------------------------------------------------------------------------


def _map_with(tmp_path, **extra):
    map_path = tmp_path / "repo-map.json"
    repo_map = json.loads(map_path.read_text())
    repo_map.update(extra)
    map_path.write_text(json.dumps(repo_map))


def test_a_contract_key_the_model_does_not_declare_is_divergent(tmp_path):
    """The key check runs both ways: a primaryKey the model's `primary_key` lacks is an error."""
    _orders(tmp_path)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model",
        _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date", primaryKey=True),
        _prop("total_amount", "number")))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (1, ["boundary/divergent"])
    assert "ordered_date" in diags[0]["message"] and "primary_key" in diags[0]["message"]


def test_a_model_declaring_no_key_does_not_police_the_contracts_keys(tmp_path):
    _orders(tmp_path, primary_key=())
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def _excluded_repo(tmp_path, exclusions):
    _repo(tmp_path, models=["a_model", "b_model"],
          logical_model=_model(("a_model", ORDER_FIELDS, ["order_key"])))
    _map_with(tmp_path, semantic_exclusions=exclusions)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"), _prop("total_amount", "number")))
    _contract(tmp_path, "core", "b_model")
    _generated(tmp_path)


def test_an_excluded_relation_is_info_not_undeclared(tmp_path):
    _excluded_repo(tmp_path, [{"relation": "core.b_model", "reason": "a bespoke aggregate"}])
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["boundary/excluded"])
    assert diags[0]["severity"] == "info"
    assert "a bespoke aggregate" in diags[0]["message"] and "core.b_model" in diags[0]["message"]


@pytest.mark.parametrize("exclusions", [
    {"relation": "core.b_model", "reason": "x"},
    [{"relation": "core.b_model"}],
    [{"reason": "x"}],
    [{"relation": "b_model", "reason": "x"}],
    ["core.b_model"],
])
def test_malformed_semantic_exclusions_are_an_error(tmp_path, exclusions):
    _excluded_repo(tmp_path, exclusions)
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1
    assert "map/semantic-exclusions" in _codes(diags)


def _proposed(tmp_path, schema_name="core", table="b_model"):
    return _contract(tmp_path, schema_name, table, status="proposed")


def test_a_proposed_contract_is_not_an_orphan(tmp_path):
    """A contract written before its table names no declared relation yet; that is the point."""
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model")
    _proposed(tmp_path)
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_a_proposed_contract_is_still_checked_for_shape(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model")
    _contract(tmp_path, "core", "b_model", status="proposed", schema=[{"name": "other"}])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert code == 1 and "contract/misnamed" in _codes(diags)


def test_generate_and_stale_skip_a_proposed_contract(tmp_path):
    _repo(tmp_path, models=["a_model"])
    _contract(tmp_path, "core", "a_model", status="proposed", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True)))
    assert _run("generate", "--root", str(tmp_path)) == (0, [])
    assert not list((tmp_path / "models" / "core").glob("*.yml"))
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_relations_skip_a_proposed_contract(tmp_path, monkeypatch):
    _repo(tmp_path, models=["a_model"])
    _contract_with(tmp_path, ["x"], status="proposed")
    code, diags = _relations_run(tmp_path, monkeypatch, _catalog(tmp_path, ["x", "surprise"]))
    assert (code, diags) == (0, [])


STAR_FIELDS = {"order_key": "String", "total_amount": "Decimal"}


def test_reverse_drafts_a_star_member_without_grain_or_descriptions(tmp_path):
    """The model owns the grain and the column prose; the contract states neither."""
    _repo(tmp_path, models=["a_model"], logical_model=_model(
        ("a_model", STAR_FIELDS, ["order_key"])),
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _warehouse(tmp_path, {("core", "a_model"): [
        ("order_key", "VARCHAR", False), ("total_amount", "DECIMAL(10,2)", True)]})

    diags = _reversed(tmp_path)

    element = _written(tmp_path, "core", "a_model")["schema"][0]
    assert "dataGranularityDescription" not in element
    assert all("description" not in prop for prop in element["properties"])
    assert not {"finding/no-grain", "finding/undescribed"} & set(_codes(diags))


def test_reverse_keeps_grain_and_descriptions_for_a_relation_outside_the_model(tmp_path):
    _repo(tmp_path, models=["a_model", "b_model"], logical_model=_model(
        ("a_model", STAR_FIELDS, ["order_key"])),
          files={"models/core/_core.yml": CORE_PROPERTIES})
    _warehouse(tmp_path, {("core", "a_model"): [("order_key", "VARCHAR", False)],
                          ("core", "b_model"): [("order_key", "VARCHAR", False)]})

    diags = _reversed(tmp_path)

    assert any(d["code"] == "finding/no-grain" and d["message"].startswith("core.b_model")
               for d in diags)
    assert not any(d["code"] == "finding/no-grain" and d["message"].startswith("core.a_model")
                   for d in diags)


def test_check_does_not_ask_a_star_member_for_a_grain(tmp_path):
    _orders(tmp_path)
    path = tmp_path / "contracts" / "core" / "a_model.odcs.yaml"
    doc = yaml.safe_load(path.read_text())
    del doc["schema"][0]["dataGranularityDescription"]
    path.write_text(yaml.safe_dump(doc))
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_a_proposed_gold_contract_passes_beside_a_canonical_model(tmp_path):
    """Contract-first: the model does not name the relation yet, and that is not a failure."""
    _repo(tmp_path, models=["a_model"],
          logical_model=_model(("a_model", ORDER_FIELDS, ["order_key"])))
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"), _prop("total_amount", "number")))
    _proposed(tmp_path)
    _generated(tmp_path)
    assert _run("check", "--root", str(tmp_path)) == (0, [])


def test_an_exclusion_outside_the_gold_schemas_is_not_reported(tmp_path):
    _excluded_repo(tmp_path, [{"relation": "staging.stg_x", "reason": "scratch"}])
    code, diags = _run("check", "--root", str(tmp_path))
    assert "boundary/excluded" not in _codes(diags)


def _aggregate_model(tmp_path, exclusions=()):
    """A model whose one dataset has an aggregate source in `core.agg_orders`, no dataset of its own."""
    model = _model(("a_model", ORDER_FIELDS, ["order_key"]))
    dataset = model["datasets"][0]
    dataset["custom_extensions"] = [{"vendor_name": "VIBEDATA", "data": json.dumps({
        "logical_sources": [{"name": "LTS2", "physical_table": "agg_orders"}]})}]
    model["custom_extensions"] = [{"vendor_name": "VIBEDATA", "data": json.dumps({
        "physical_tables": [
            {"name": "agg_orders", "source": "core.agg_orders", "table_type": "TABLE"}]})}]
    _repo(tmp_path, models=["a_model", "agg_orders", "other"], logical_model=model)
    _map_with(tmp_path, semantic_exclusions=list(exclusions))
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", primaryKey=True),
        _prop("ordered_date", "date"), _prop("total_amount", "number")))
    _contract(tmp_path, "core", "agg_orders", schema=[{"name": "agg_orders"}])
    _contract(tmp_path, "core", "other")


def test_an_aggregate_source_is_documented_by_the_model(tmp_path):
    """No `contract/no-document`, no grain warning, and no dataset fields invented to compare."""
    _aggregate_model(tmp_path, [{"relation": "core.other", "reason": "bespoke"}])
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["boundary/excluded"])
    assert "core.other" in diags[0]["message"]


def test_an_aggregate_source_is_drafted_as_a_star_member(tmp_path):
    _aggregate_model(tmp_path)
    for table in ("agg_orders", "other"):
        (tmp_path / "contracts" / "core" / f"{table}.odcs.yaml").unlink()
    _warehouse(tmp_path, {("core", "a_model"): [("order_key", "VARCHAR", False)],
                          ("core", "agg_orders"): [("order_date", "DATE", True)],
                          ("core", "other"): [("order_date", "DATE", True)]})

    diags = _reversed(tmp_path)

    assert "dataGranularityDescription" not in _written(tmp_path, "core", "agg_orders")["schema"][0]
    assert not any(d["code"] == "finding/no-grain" and d["message"].startswith("core.agg_orders")
                   for d in diags)
    assert any(d["code"] == "finding/no-grain" and d["message"].startswith("core.other")
               for d in diags)


def test_a_catalog_qualified_physical_table_names_its_last_two_parts(tmp_path):
    _aggregate_model(tmp_path, [{"relation": "core.other", "reason": "bespoke"}])
    model_path = tmp_path / "logical-model" / "model.ossie.yaml"
    model = yaml.safe_load(model_path.read_text())
    model["custom_extensions"][0]["data"] = json.dumps({"physical_tables": [
        {"name": "agg_orders", "source": "cat.core.agg_orders", "table_type": "TABLE"}]})
    model_path.write_text(yaml.safe_dump(model))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert (code, _codes(diags)) == (0, ["boundary/excluded"])


def test_an_aggregate_source_alone_in_its_gold_schema_leaves_an_excluded_neighbour_reported(
        tmp_path):
    _aggregate_model(tmp_path, [{"relation": "core.other", "reason": "bespoke"}])
    # Nothing but the aggregate source and the excluded relation remain in the schema.
    (tmp_path / "contracts" / "core" / "a_model.odcs.yaml").unlink()
    model_path = tmp_path / "logical-model" / "model.ossie.yaml"
    model = yaml.safe_load(model_path.read_text())
    model["datasets"][0]["source"] = "elsewhere.a_model"
    model_path.write_text(yaml.safe_dump(model))
    _generated(tmp_path)
    code, diags = _run("check", "--root", str(tmp_path))
    assert "boundary/excluded" in _codes(diags)
    assert [d["code"] for d in diags if d["code"].startswith("boundary/")] == ["boundary/excluded"]


def test_a_relation_both_excluded_and_modelled_warns(tmp_path):
    _excluded_repo(tmp_path, [{"relation": "core.a_model", "reason": "scratch"}])
    code, diags = _run("check", "--root", str(tmp_path))
    assert "boundary/excluded-but-modelled" in _codes(diags)
    assert [d["severity"] for d in diags if d["code"] == "boundary/excluded-but-modelled"] == ["warning"]


# derived descriptions: `generate` writes them, `check` reports a boundary property with none

def _star(tmp_path, *, tables=(), metrics=(), **dataset):
    """A canonical document with one dataset, `core.a_model`, and optional aggregate tables."""
    model = _model(("a_model", {}, ["order_key"]))
    model["datasets"][0].update(dataset)
    if metrics:
        model["metrics"] = list(metrics)
    if tables:
        model["custom_extensions"] = [{"vendor_name": "VIBEDATA", "data": json.dumps(
            {"physical_tables": list(tables)})}]
    return model


def _field(name, description, expression=None):
    field = {"name": name, "datatype": "String", "description": description}
    if expression is not None:
        field["expression"] = {"dialects": [{"dialect": "ANSI_SQL", "expression": expression}]}
    return field


def _model_entry(tmp_path, table="a_model"):
    return _entries(tmp_path / "models" / "core" / "_generated.yml")[1][table]


def test_generate_writes_a_star_members_prose_from_the_ossie_field(tmp_path):
    """The model owns what a column means: a field named for the column, not a computed one."""
    star = _star(tmp_path, description="One row per order.", fields=[
        _field("order_key", "Surrogate key.", "order_key"),
        _field("total_amount", "Order total.")])
    star["datasets"][0]["fields"].append(_field("margin", "A computed field.", "a - b"))
    _repo(tmp_path, models=["a_model"], logical_model=star)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True),
        _prop("total_amount", "number", description="Contract wording loses."),
        _prop("margin", "number", description=None)))
    _generated(tmp_path)

    model = _model_entry(tmp_path)
    assert model["description"] == "One row per order."
    columns = {column["name"]: column for column in model["columns"]}
    assert columns["order_key"]["description"] == "Surrogate key."
    assert columns["total_amount"]["description"] == "Order total."
    assert "description" not in columns["margin"]
    code, diags = _run("check", "--root", str(tmp_path))
    assert "generated/stale" not in _codes(diags) and "contract/undescribed" not in _codes(diags)


def test_generate_writes_an_aggregate_relations_prose_from_the_ossie_metric(tmp_path):
    """An aggregate has no dataset; the `physical_tables` entry and the metric describe it."""
    star = _star(
        tmp_path, fields=[_field("order_key", "Surrogate key.")],
        tables=[{"name": "agg_model", "source": "core.agg_model",
                 "description": "Orders per day."}],
        metrics=[{"name": "order_count", "description": "Orders placed.",
                  "expression": {"dialects": [{"dialect": "ANSI_SQL",
                                               "expression": "COUNT(*)"}]}}])
    _repo(tmp_path, models=["a_model", "agg_model"], logical_model=star)
    _contract(tmp_path, "core", "agg_model", schema=_element(
        "agg_model", _prop("order_count", "integer", description=None),
        _prop("day", "date", description=None)))
    _generated(tmp_path)

    model = _model_entry(tmp_path, "agg_model")
    assert model["description"] == "Orders per day."
    columns = {column["name"]: column for column in model["columns"]}
    assert columns["order_count"]["description"] == "Orders placed."
    assert "description" not in columns["day"]


def test_generate_takes_a_non_star_relations_prose_from_the_contract(tmp_path):
    _contract(tmp_path, "core", "b_model", description={"purpose": "Daily  store\nsales.",
                                                        "usage": "Not this."},
              schema=_element("b_model", _prop("store_id", "integer",
                                               description="The   store.")))
    _contract(tmp_path, "core", "c_model", description="A plain string.",
              schema=_element("c_model", _prop("store_id", "integer")))
    _repo(tmp_path, models=["a_model", "b_model", "c_model"],
          logical_model=_star(tmp_path, fields=[_field("order_key", "Surrogate key.")]))
    _generated(tmp_path)

    entries = _entries(tmp_path / "models" / "core" / "_generated.yml")[1]
    assert entries["b_model"]["description"] == "Daily store sales."
    assert entries["b_model"]["columns"][0]["description"] == "The store."
    assert entries["c_model"]["description"] == "A plain string."


POINTER_PROPERTIES = """version: 2

models:
  - name: a_model
    description: '{{ doc("a_model") }}'
    columns:
      - name: order_key
        description: '{{ doc("order_key") }}'
      - name: note
        description: Hand-written, no source names it.
      - name: embedded
        description: 'Text first. {{ doc("embedded") }}'
"""


def test_a_doc_pointer_and_an_unnamed_column_are_left_alone_and_not_stale(tmp_path):
    star = _star(tmp_path, description="One row per order.",
                 fields=[_field("order_key", "Surrogate key."),
                         _field("embedded", "Would overwrite.")])
    _repo(tmp_path, models=["a_model"], logical_model=star,
          files={"models/core/_core.yml": POINTER_PROPERTIES})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True),
        _prop("note", "string", description=None),
        _prop("embedded", "string", description=None)))
    _generated(tmp_path)

    model = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]
    assert model["description"] == '{{ doc("a_model") }}'
    columns = {column["name"]: column for column in model["columns"]}
    assert columns["order_key"]["description"] == '{{ doc("order_key") }}'
    assert columns["note"]["description"] == "Hand-written, no source names it."
    assert columns["embedded"]["description"] == 'Text first. {{ doc("embedded") }}'
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_a_description_that_differs_from_the_derived_one_is_stale(tmp_path):
    star = _star(tmp_path, description="One row per order.",
                 fields=[_field("order_key", "Surrogate key.")])
    _repo(tmp_path, models=["a_model"], logical_model=star)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _generated(tmp_path)
    path = tmp_path / "models" / "core" / "_generated.yml"
    path.write_text(path.read_text(encoding="utf-8").replace("Surrogate key.", "Edited by hand.")
                    .replace("One row per order.", "Also edited."), encoding="utf-8")

    stale = [d["message"] for d in _run("check", "--root", str(tmp_path))[1]
             if d["code"] == "generated/stale"]
    assert len(stale) == 2
    assert any("a_model.description" in m for m in stale)
    assert any("order_key.description" in m for m in stale)
    _generated(tmp_path)
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_check_warns_a_boundary_property_no_one_describes(tmp_path):
    """A star member is described by its field; input and boundary relations are asked."""
    star = _star(tmp_path, fields=[_field("order_key", "Surrogate key.")])
    _repo(tmp_path, models=["a_model", "b_model"], logical_model=star,
          sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _contract(tmp_path, "core", "b_model", schema=_element(
        "b_model", _prop("store_id", "integer", description=None)))
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata", _prop("store_id", "integer", description=None)))
    _generated(tmp_path)

    _, diags = _run("check", "--root", str(tmp_path))
    undescribed = [d for d in diags if d["code"] == "contract/undescribed"]
    assert [d["severity"] for d in undescribed] == ["warning", "warning"]
    assert sorted(d["message"] for d in undescribed) == [
        "bronze.orderdata.store_id: no description; what does store_id mean?",
        "core.b_model.store_id: no description; what does store_id mean?"]


def test_check_warns_an_input_property_no_one_describes_but_not_its_loader_column(tmp_path):
    _repo(tmp_path, models=["a_model"], sources={"shop": ("bronze", ["orderdata"])})
    _contract(tmp_path, "bronze", "orderdata", schema=_element(
        "orderdata", _prop("store_id", "integer", description=None),
        _prop("_dlt_load_id", "string", description=None)))
    _generated(tmp_path)
    undescribed = [d["message"] for d in _run("check", "--root", str(tmp_path))[1]
                   if d["code"] == "contract/undescribed"]
    assert undescribed == [
        "bronze.orderdata.store_id: no description; what does store_id mean?"]


def test_a_block_scalar_description_equal_to_the_derived_one_is_not_stale(tmp_path):
    star = _star(tmp_path, description="One row per order.",
                 fields=[_field("order_key", "Surrogate key.")])
    _repo(tmp_path, models=["a_model"], logical_model=star)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _generated(tmp_path)
    path = tmp_path / "models" / "core" / "_generated.yml"
    text = path.read_text(encoding="utf-8")
    assert "description: One row per order." in text
    path.write_text(text.replace("description: One row per order.",
                                 "description: >\n      One row per order.\n"), encoding="utf-8")
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_a_doc_pointer_without_inner_spaces_is_protected_and_not_stale(tmp_path):
    star = _star(tmp_path, description="One row per order.",
                 fields=[_field("order_key", "Surrogate key.")])
    _repo(tmp_path, models=["a_model"], logical_model=star,
          files={"models/core/_core.yml": POINTER_PROPERTIES.replace('{{ doc("a_model") }}', '{{doc("a_model") }}')})
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _generated(tmp_path)
    model = _entries(tmp_path / "models" / "core" / "_core.yml")[1]["a_model"]
    assert model["description"] == '{{doc("a_model") }}'
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_two_canonical_documents_naming_one_relation_read_the_first(tmp_path):
    star = _star(tmp_path, fields=[_field("order_key", "First.")])
    _repo(tmp_path, models=["a_model"], logical_model=star)
    second = tmp_path / "logical-model" / "z_other.ossie.yaml"
    other = json.loads(json.dumps(star))
    other["datasets"][0]["fields"][0]["description"] = "Last."
    second.write_text(yaml.safe_dump(other))
    repo_map = json.loads((tmp_path / "repo-map.json").read_text())
    dataset, path = odcs._canonical_datasets(tmp_path, repo_map)[("core", "a_model")]
    assert path.name == "model.ossie.yaml"


def test_check_does_not_ask_a_proposed_contract_for_a_description(tmp_path):
    _repo(tmp_path, models=["a_model"], logical_model=_star(
        tmp_path, fields=[_field("order_key", "Surrogate key.")]))
    _contract(tmp_path, "core", "b_model", status="proposed", schema=_element(
        "b_model", _prop("store_id", "integer", description=None)))
    _generated(tmp_path)
    assert "contract/undescribed" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_generate_writes_a_long_unicode_description_as_one_valid_line(tmp_path):
    long = "Total \u2014 " + "word " * 300
    star = _star(tmp_path, description="Orders \u2014 one per row.",
                 fields=[_field("order_key", long.strip())])
    _repo(tmp_path, models=["a_model"], logical_model=star)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_key", "string", description=None, primaryKey=True)))
    _generated(tmp_path)

    text = (tmp_path / "models" / "core" / "_generated.yml").read_text(encoding="utf-8")
    assert len(long) > 1500
    assert "\u2014" in text and "\\u2014" not in text
    assert len([line for line in text.splitlines() if "Total" in line]) == 1
    model = _model_entry(tmp_path)
    assert model["description"] == "Orders \u2014 one per row."
    assert model["columns"][0]["description"] == long.strip()
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])


def test_a_star_column_whose_field_is_undescribed_falls_through_to_the_metric(tmp_path):
    star = _star(tmp_path, fields=[_field("order_count", "")],
                 metrics=[{"name": "order_count", "description": "Orders placed."}])
    _repo(tmp_path, models=["a_model"], logical_model=star)
    _contract(tmp_path, "core", "a_model", schema=_element(
        "a_model", _prop("order_count", "integer", description=None)))
    _generated(tmp_path)

    assert _model_entry(tmp_path)["columns"][0]["description"] == "Orders placed."


def test_a_changed_contract_description_on_a_non_star_relation_is_stale(tmp_path):
    _repo(tmp_path, models=["a_model", "b_model"], logical_model=_star(
        tmp_path, fields=[_field("order_key", "Surrogate key.")]))
    target = _contract(tmp_path, "core", "b_model", description="Daily sales.",
                       schema=_element("b_model", _prop("store_id", "integer",
                                                        description="The store.")))
    _generated(tmp_path)
    assert "generated/stale" not in _codes(_run("check", "--root", str(tmp_path))[1])

    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    doc["description"] = "Weekly sales."
    doc["schema"][0]["properties"][0]["description"] = "The shop."
    target.write_text(yaml.safe_dump(doc), encoding="utf-8")

    stale = [d["message"] for d in _run("check", "--root", str(tmp_path))[1]
             if d["code"] == "generated/stale"]
    assert len(stale) == 2
    assert any("b_model.description" in m for m in stale)
    assert any("store_id.description" in m for m in stale)


def test_undescribed_exempts_loader_columns_on_dlt_relations_only():
    repo_map = {"layers": {
        "raw": {"schema": "bronze", "built_by": "dlt"},
        "seeds": {"schema": "seeds", "built_by": "dbt"},
        "core": {"schema": "core", "built_by": "dbt"}}}
    contract = {"schema": [{"name": "t", "properties": [{"name": "_dlt_id"}, {"name": "x"}]}]}

    def names(schema):
        return [d["message"].split(": ")[0]
                for d in odcs._undescribed((schema, "t"), contract, repo_map)]

    assert names("bronze") == ["bronze.t.x"]
    assert names("seeds") == ["seeds.t._dlt_id", "seeds.t.x"]
    assert names("core") == ["core.t._dlt_id", "core.t.x"]
