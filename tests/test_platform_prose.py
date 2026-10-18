"""What an agent reads describes the Fabric Lakehouse Domain, and no Ephemeral or item id is committed."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The DuckDB Domain this repo was ported from ran on these; on the Lakehouse none of them exists.
DUCKDB_RUNTIME = [
    "domain.duckdb",
    "VD_EPHM_DUCKDB_LOCAL_PATH",
    "relations.sql",
    "run_ingest.py",
    "run_transform.py",
    "run_all.py",
    "duckdb_local",
    "vibedata.dlt.duckdb",
    "vibedata-dlt-duckdb-studio",
    "dbt-duckdb",
    "--target dev",
]

GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
# The Domain's own coordinates are committed where the plugin reads them: the `prod` dbt target,
# the dlt destination and the CI config. Studio retargets an Intent run to its Ephemeral Lakehouse.
DOMAIN_COORDINATE_FILES = {"transformation/profiles.yml", "ingestion/.dlt/config.toml", ".workflow/ci-config.yml"}
# Portable ids Fabric binds on deploy: an item's logicalId, a Data Pipeline activity's reference
# to one (`notebookId`), and the all-zeros workspace placeholder.
PORTABLE_ID_LINE = re.compile(r'"logicalId"|"notebookId"|00000000-0000-0000-0000-000000000000')


def _superseded_adr(path: Path) -> bool:
    return path.parent.name == "adr" and re.search(r"^status:\s*rejected", path.read_text(), re.M) is not None


def _agent_read_files() -> list[Path]:
    files = [p for p in (ROOT / ".agents").rglob("*") if p.is_file()]
    files += [ROOT / "AGENTS.md", ROOT / "CONTEXT.md"]
    files += [p for p in (ROOT / "docs" / "adr").glob("*.md") if not _superseded_adr(p)]
    files += list((ROOT / "docs" / "design").rglob("*.md"))
    return files


def test_agent_read_prose_names_no_duckdb_runtime():
    hits = []
    for path in _agent_read_files():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            # A superseded design decision stays as history; its successor carries the Fabric statement.
            if "Superseded by" in line:
                continue
            hits += [f"{path.relative_to(ROOT)}:{number}: {term}" for term in DUCKDB_RUNTIME if term in line]
    repo_map = json.loads((ROOT / "repo-map.json").read_text())
    for key in ("notes_for_agents", "applications"):
        text = json.dumps(repo_map[key])
        hits += [f"repo-map.json {key}: {term}" for term in DUCKDB_RUNTIME if term in text]
    assert hits == []


def test_no_committed_guid():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for name in tracked:
        try:
            text = (ROOT / name).read_text()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        hits += _guid_hits(name, text)
    assert hits == []


def _guid_hits(name: str, text: str) -> list[str]:
    if name.startswith(".github/") or name in DOMAIN_COORDINATE_FILES:
        return []
    return [f"{name}: {m}" for line in text.splitlines() if not PORTABLE_ID_LINE.search(line) for m in GUID.findall(line)]


def test_guid_guard_allows_the_ids_the_plugin_requires():
    # Built, not written out, so this file holds no id of its own.
    guid = "-".join(["1b2c3d4e", "0000", "4000", "8000", "0123456789ab"])
    activity = f'          "notebookId": "{guid}",'
    assert _guid_hits("orchestration/nyc_taxi_refresh.DataPipeline/pipeline-content.json", activity) == []
    assert _guid_hits(".workflow/ci-config.yml", f"VD_DOMAIN_FABRIC_LAKEHOUSE_ID: {guid}") == []
    assert _guid_hits("docs/setup/notes.md", f"workspace {guid}") == [f"docs/setup/notes.md: {guid}"]


def test_dbt_project_is_fabricspark():
    import yaml

    project = ROOT / "transformation"
    profile = yaml.safe_load((project / "profiles.yml").read_text())["nyc_taxi_analytics"]
    assert profile["target"] == "prod"
    assert profile["outputs"]["prod"]["type"] == "fabricspark"
    assert (project / "macros" / "source_defer.sql").exists()
    assert not (project / "macros" / "relations.sql").exists()
    # The Lakehouse SQL analytics endpoint cannot read a Spark view.
    sql = [(project / "dbt_project.yml").read_text()] + [p.read_text() for p in (project / "models").rglob("*.sql")]
    assert not [s for s in sql if re.search(r"materialized\s*[:=]\s*['\"]?view", s)]
