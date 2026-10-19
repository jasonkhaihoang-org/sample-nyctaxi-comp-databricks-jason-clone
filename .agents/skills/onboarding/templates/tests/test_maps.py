"""The repo-map and test-map match the repo. Driven by the maps, so it holds from an empty project on."""

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_MAP = json.loads((ROOT / "repo-map.json").read_text())
TEST_MAP = json.loads((ROOT / "test-map.json").read_text())
DBT_PROJECT = ROOT / REPO_MAP["artifact_paths"]["dbt_project"]
PROFILE = yaml.safe_load((DBT_PROJECT / "dbt_project.yml").read_text())["name"]
# Name the repo's own profile: in the Studio sandbox DBT_PROFILES_DIR and DBT_PROFILE_NAME point at the runtime's.
DBT = [sys.executable, "-m", "dbt.cli.main"]
DBT_PROFILE = ["--profiles-dir", str(DBT_PROJECT), "--profile", PROFILE]
# Parsing and listing never open a Spark session, so the prod target needs no credential here.
DBT_ENV = dict(os.environ)


def _is_pattern(path: str) -> bool:
    return bool(re.search(r"[{*]", path))


def _literal_paths() -> list[str]:
    paths = [layer["path"] for layer in REPO_MAP["layers"].values()]
    paths += REPO_MAP["artifact_paths"].values()
    paths += REPO_MAP["entrypoints"].values()
    paths += REPO_MAP["key_directories"].keys()
    paths += [module["path"] for module in REPO_MAP["modules"].values()]
    for source in REPO_MAP["sources"].values():
        paths += [source[k] for k in ("pipeline", "docs", "module", "tests", "design_record") if k in source]
    return [p for p in paths if not _is_pattern(p)]


def test_repo_map_validates_against_its_schema():
    schema = json.loads((ROOT / "repo-map.schema.json").read_text())
    jsonschema.validate(REPO_MAP, schema)


def test_every_layer_has_one_builder():
    assert {layer["built_by"] for layer in REPO_MAP["layers"].values()} <= {"dlt", "dbt"}


def test_repo_map_paths_exist():
    assert [p for p in _literal_paths() if not (ROOT / p).exists()] == []


def test_every_source_is_registered_in_the_dlt_config():
    config = tomllib.loads((ROOT / REPO_MAP["artifact_paths"]["source_config"]).read_text())
    for name, source in REPO_MAP["sources"].items():
        section = config
        for key in source["config_section"].split("."):
            section = section.get(key, {})
        assert section, f"{name}: [{source['config_section']}] missing"


def test_test_map_paths_exist():
    missing = []
    for name, module in TEST_MAP["modules"].items():
        for key in ("sources", "unit", "data", "structural"):
            missing += [f"{name}.{key}: {p}" for p in module.get(key, []) if not (ROOT / p).exists()]
    assert missing == []


def test_dbt_sources_name_a_schema_and_never_a_catalog():
    path = ROOT / REPO_MAP["artifact_paths"]["dbt_sources"]
    sources = (yaml.safe_load(path.read_text()) or {}).get("sources") or []
    assert [s["name"] for s in sources if "database" in s] == []
    assert [s["name"] for s in sources if "{{" in str(s.get("schema", ""))] == []


def test_source_defers_to_the_domain():
    """dbt's --defer rewrites ref() only; without this override every source fails in a sandbox build."""
    text = (DBT_PROJECT / "macros/source_defer.sql").read_text()
    assert "macro source(" in text


@pytest.fixture(scope="session")
def dbt_packages():
    if not (DBT_PROJECT / "dbt_packages").exists():
        subprocess.run([*DBT, "deps", *DBT_PROFILE], cwd=DBT_PROJECT, env=DBT_ENV, capture_output=True, check=True)


def test_dbt_project_parses(dbt_packages):
    subprocess.run([*DBT, "parse", *DBT_PROFILE], cwd=DBT_PROJECT, env=DBT_ENV, capture_output=True, check=True)


DBT_SELECTORS = [
    (name, kind, module["selectors"][kind])
    for name, module in TEST_MAP["modules"].items()
    for kind in ("data", "unit")
    if kind in module.get("selectors", {})
]


@pytest.mark.parametrize("name,kind,select", DBT_SELECTORS, ids=lambda v: str(v))
def test_test_map_dbt_selectors_resolve_to_at_least_one_test(dbt_packages, name, kind, select):
    command = [*DBT, "ls", *DBT_PROFILE, "--select", select, "--resource-type", "unit_test" if kind == "unit" else "test"]
    if kind == "data":
        command += ["--exclude", "test_type:unit"]
    out = subprocess.run(command, cwd=DBT_PROJECT, env=DBT_ENV, capture_output=True, text=True, check=True).stdout
    assert [line for line in out.splitlines() if ":" in line and not line.startswith(" ")], f"{name}.{kind} selects nothing"
