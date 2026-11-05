"""What an agent reads describes the Databricks Domain, and no workspace coordinate is committed."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The DuckDB Domain this repo was first ported from ran on these; on Databricks none of them exists.
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

# The Fabric Lakehouse Domain this repo was ported from ran on these; Databricks has none of them.
# Spark SQL, Delta, `lakehouse_query` and `/cache/prod-target` stay: they hold on Databricks too.
LAKEHOUSE_RUNTIME = [
    "Fabric",
    "fabric_lakehouse",
    "fabricspark",
    "dbt_fab_spark",
    "dbt_fabric_compile",
    "Livy",
    "livy",
    "SQL analytics endpoint",
    "OneLake",
    "onelake",
    "notebookutils",
    ".Notebook",
    ".DataPipeline",
    "Data Pipeline",
    "logicalId",
    "notebookId",
    "Ephemeral Lakehouse",
    "Domain Lakehouse",
    "vibedata.dlt.fabric",
    "vibedata-dlt-fabric",
    "ephemeral_dev",
    "SQL endpoint",
    "schema-enabled",
]
# Prose that describes code a later change replaces, on the same branch, as path or
# path#Section -> the issue that replaces it. Empty once the Databricks code is in.
LAKEHOUSE_PROSE_OWNED_LATER: dict[str, str] = {}

GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
# The CI config is where the plugin reads the Domain's coordinates, so it may carry ids.
DOMAIN_COORDINATE_FILES = {".workflow/ci-config.yml"}
# The all-zeros id is a placeholder, never a coordinate.
PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"
CONTRACT_ID = re.compile(r"^id: [0-9a-f-]{36}$", re.MULTILINE)
VENDORED_STANDARDS = (".agents/skills/data-contract/scripts/odcs_vendor/",
                      ".agents/skills/semantic-model/scripts/ossie_vendor/",
                      ".github/data-contract/scripts/odcs_vendor/")
# The contract tool's tests build contracts with fixed, obviously fake ids.
FIXTURE_ID = re.compile(r"c0ffee00-0000-4000-8000-[0-9]{12}")
# A workspace host, a SQL warehouse path or a personal access token points at one workspace;
# none belongs in git. The bundle and Studio pass them at run time.
# `offline.cloud.databricks.com` is the CI bundle's placeholder for a parse that opens no connection.
WORKSPACE_COORDINATE = re.compile(
    r"adb-\d+\.\d+\.azuredatabricks\.net|\b(?!offline\.)[a-z0-9-]+\.cloud\.databricks\.com|/sql/1\.0/warehouses/[0-9a-f]{8,}|\bdapi[0-9a-f]{32}\b",
    re.IGNORECASE,
)
# An Intent's own schema names (ephm__<domain>__<intent>__...) belong only in the maintenance records.
INTENT_SCHEMA = re.compile(r"\bephm__[a-z0-9_]+?__[a-z0-9]+__[a-z0-9_]*")
INTENT_SCHEMA_RECORDS = ("docs/setup/", "docs/verify/")


def _superseded_adr(path: Path) -> bool:
    return path.parent.name == "adr" and re.search(r"^status:\s*rejected", path.read_text(), re.M) is not None


def _agent_read_files() -> list[Path]:
    # Bytecode the skills' scripts leave beside them when a test imports them is no prose.
    files = [p for p in (ROOT / ".agents").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files += [ROOT / "AGENTS.md", ROOT / "CONTEXT.md"]
    files += [p for p in (ROOT / "docs" / "adr").glob("*.md") if not _superseded_adr(p)]
    files += list((ROOT / "docs" / "design").rglob("*.md"))
    return files


def test_agent_read_prose_names_no_duckdb_runtime():
    hits = []
    for path in _agent_read_files():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            # A superseded design decision stays as history; its successor carries the current statement.
            if "Superseded by" in line:
                continue
            hits += [f"{path.relative_to(ROOT)}:{number}: {term}" for term in DUCKDB_RUNTIME if term in line]
    repo_map = json.loads((ROOT / "repo-map.json").read_text())
    for key in ("notes_for_agents", "applications"):
        text = json.dumps(repo_map[key])
        hits += [f"repo-map.json {key}: {term}" for term in DUCKDB_RUNTIME if term in text]
    assert hits == []


def _term_hits(name: str, text: str, terms: list[str]) -> list[str]:
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        if "Superseded by" in line:
            continue
        hits += [f"{name}:{number}: {term}" for term in terms if term in line]
    return hits


# A design record's History lists what each port changed, so it names the platforms before this one.
HISTORY_SECTION = "History"


def _file_hits(name: str, text: str, owned: dict[str, str]) -> list[str]:
    if name in owned:
        return []
    sections = {key.split("#", 1)[1] for key in owned if key.startswith(f"{name}#")}
    if name.startswith("docs/design/"):
        sections.add(HISTORY_SECTION)
    kept, skipping = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            skipping = line.lstrip("#").strip() in sections
        kept.append("" if skipping else line)
    return _term_hits(name, "\n".join(kept), LAKEHOUSE_RUNTIME)


def _repo_map_hits(repo_map: dict, owned: dict[str, str]) -> list[str]:
    hits = []
    for key, value in repo_map.items():
        if f"repo-map.json#{key}" not in owned:
            hits += _term_hits(f"repo-map.json {key}", json.dumps(value, indent=1), LAKEHOUSE_RUNTIME)
    return hits


def test_agent_read_prose_names_no_lakehouse_runtime():
    hits = []
    for path in _agent_read_files() + [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]:
        hits += _file_hits(str(path.relative_to(ROOT)), path.read_text(), LAKEHOUSE_PROSE_OWNED_LATER)
    hits += _repo_map_hits(json.loads((ROOT / "repo-map.json").read_text()), LAKEHOUSE_PROSE_OWNED_LATER)
    assert hits == []


def test_lakehouse_guard_skips_superseded_lines():
    assert _term_hits("x.md", "Superseded by ADR 0019; ran on fabricspark", LAKEHOUSE_RUNTIME) == []
    assert _term_hits("x.md", "runs on fabricspark", LAKEHOUSE_RUNTIME) == ["x.md:1: fabricspark"]


def test_lakehouse_guard_skips_only_a_design_records_history():
    text = "# tlc\n\nRuns on fabricspark.\n\n## History\n\n- 2026-10-18 — fabric-port — a Fabric notebook\n\n## Notes\n\nOn livy.\n"
    assert _file_hits("docs/design/pipelines/x.md", text, {}) == [
        "docs/design/pipelines/x.md:3: fabricspark", "docs/design/pipelines/x.md:11: livy"]
    assert _file_hits("docs/adr/x.md", text, {}) == [
        "docs/adr/x.md:3: fabricspark", "docs/adr/x.md:7: Fabric", "docs/adr/x.md:11: livy"]


def test_lakehouse_allow_list_names_existing_files():
    missing = []
    for key in LAKEHOUSE_PROSE_OWNED_LATER:
        name, _, part = key.partition("#")
        text = (ROOT / name).read_text() if (ROOT / name).exists() else None
        if text is None:
            missing.append(key)
        elif part and name == "repo-map.json" and part not in json.loads(text):
            missing.append(key)
        elif part and name != "repo-map.json" and not re.search(rf"^#+ {re.escape(part)}$", text, re.M):
            missing.append(key)
    assert missing == []


def _tracked() -> list[tuple[str, str]]:
    names = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    files = []
    for name in names:
        try:
            files.append((name, (ROOT / name).read_text()))
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
    return files


def test_no_committed_coordinate():
    hits = []
    for name, text in _tracked():
        # Third-party schemas the CI bundle vendors carry their own example hosts.
        if name.startswith(".github/") and "_vendor/" in name:
            continue
        hits += _guid_hits(name, text) + _coordinate_hits(name, text)
    assert hits == []


def _guid_hits(name: str, text: str) -> list[str]:
    if name in DOMAIN_COORDINATE_FILES:
        return []
    if name.startswith("contracts/") and name.endswith(".odcs.yaml"):
        # An ODCS contract's top-level `id` names the contract itself, not a workspace.
        text = CONTRACT_ID.sub("", text)
    return [f"{name}: {m}" for m in GUID.findall(text) if m != PLACEHOLDER_ID and not FIXTURE_ID.fullmatch(m)]


def _coordinate_hits(name: str, text: str) -> list[str]:
    if name.startswith(VENDORED_STANDARDS):
        # Upstream schema copies, kept as-is; their example hosts point at no workspace.
        return []
    hits = [f"{name}: {m}" for m in WORKSPACE_COORDINATE.findall(text)]
    if not name.startswith(INTENT_SCHEMA_RECORDS):
        hits += [f"{name}: {m}" for m in INTENT_SCHEMA.findall(text)]
    return hits


def test_coordinate_guard_catches_what_points_at_one_workspace():
    # Built, not written out, so this file holds no coordinate of its own.
    guid = "-".join(["1b2c3d4e", "0000", "4000", "8000", "0123456789ab"])
    host = "adb-" + "1234567890" + ".1.azuredatabricks.net"
    warehouse = "/sql/1.0/warehouses/" + "abcdef0123456789"
    prefix = "ephm__" + "nyc_taxi__probe__bronze"
    assert _guid_hits(".workflow/ci-config.yml", f"VD_DOMAIN_ID: {guid}") == []
    assert _guid_hits(".github/profiles/profiles.yml", f'workspaceid: "{PLACEHOLDER_ID}"') == []
    assert _guid_hits("docs/setup/notes.md", f"workspace {guid}") == [f"docs/setup/notes.md: {guid}"]
    assert _coordinate_hits("transformation/profiles.yml", f"host: {host}\nhttp_path: {warehouse}") == [
        f"transformation/profiles.yml: {host}", f"transformation/profiles.yml: {warehouse}"]
    assert _coordinate_hits("docs/verify/run.md", f"loaded {prefix}") == []
    assert _coordinate_hits(".github/profiles/profiles.yml", "host: offline.cloud.databricks.com") == []
    aws_host = "dbc-1a2b3c4d" + ".cloud.databricks.com"
    assert _coordinate_hits("AGENTS.md", f"host: {aws_host}") == [f"AGENTS.md: {aws_host}"]
    assert _coordinate_hits("AGENTS.md", f"host: {aws_host.upper()}") == [f"AGENTS.md: {aws_host.upper()}"]
    assert _coordinate_hits("AGENTS.md", f"loaded {prefix}") == [f"AGENTS.md: {prefix}"]
    assert _coordinate_hits("AGENTS.md", "prefixed `ephm__<domain>__<intent>__`") == []


def test_dbt_project_is_databricks():
    import yaml

    project = ROOT / "transformation"
    profile = yaml.safe_load((project / "profiles.yml").read_text())["dbt_databricks"]
    assert profile["target"] == "prod"
    assert profile["outputs"]["prod"]["type"] == "databricks"
    for key in ("host", "http_path", "token"):
        assert profile["outputs"]["prod"][key].startswith("{{ env_var("), key
    # Literal: the job's dbt task cannot find a profile named through env_var().
    assert yaml.safe_load((project / "dbt_project.yml").read_text())["profile"] == "dbt_databricks"
    assert not (project / "macros" / "relations.sql").exists()


def test_ci_publishes_the_manifest_for_the_production_coordinates():
    """The publish workflow parses with a profile the bundle installs, for the catalog and schema the prod target names."""
    import yaml

    workflow = (ROOT / ".github/workflows/publish-prod-manifest-databricks.yml").read_text()
    profile = re.search(r"--profile (\S+)", workflow).group(1)
    assert profile in yaml.safe_load((ROOT / ".github/profiles/profiles.yml").read_text())
    config = yaml.safe_load((ROOT / ".workflow/ci-config.yml").read_text())
    prod = yaml.safe_load((ROOT / "transformation/profiles.yml").read_text())["dbt_databricks"]["outputs"]["prod"]
    assert config["VD_DOMAIN_DATA_PLATFORM"] == "databricks"
    assert (config["VD_DOMAIN_DATABRICKS_CATALOG"], config["VD_DOMAIN_DATABRICKS_PRIMARY_SCHEMA"]) == (
        prod["catalog"], prod["schema"])
