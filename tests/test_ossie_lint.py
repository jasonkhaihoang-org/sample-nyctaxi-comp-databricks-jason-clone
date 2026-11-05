"""Tests for `tools/ossie_lint.py`, the one gate the pre-commit hook and CI both run."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "tools" / "ossie_lint.py"

# What a fixture borrows from the real tree: every artifact the lint reads except the contracts,
# which each test supplies. The lint finds the repo from its own location, so it runs as a copy.
BORROWED = (".agents", "CONTEXT.md", "docs", "ingestion", "logical-model", "ontology",
            "transformation")


def _fixture(tmp_path, contracts=True):
    """A tree the lint resolves from: the real artifacts, its map, and its own contracts."""
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    shutil.copy(LINT, root / "tools" / "ossie_lint.py")
    shutil.copy(ROOT / "repo-map.json", root / "repo-map.json")
    for name in BORROWED:
        (root / name).symlink_to(ROOT / name)
    if contracts:
        shutil.copytree(ROOT / "contracts", root / "contracts")
    return root


def _lint(root):
    result = subprocess.run([sys.executable, str(root / "tools" / "ossie_lint.py")],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    return result


def _errors(result):
    return [d for d in json.loads(result.stdout or "[]") if d["severity"] == "error"]


def test_a_malformed_contract_fails_the_lint(tmp_path):
    """This repo's contracts warn and pass; a contract that breaks its schema stops the run."""
    root = _fixture(tmp_path)
    clean = _lint(root)
    assert clean.returncode == 0, clean.stderr  # warnings alone never block

    path = next(path for path in sorted((root / "contracts").rglob("*.odcs.yaml")))
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["apiVersion"] = "v1.0.0"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    broken = _lint(root)
    assert broken.returncode == 1
    errors = _errors(broken)
    assert [error["code"] for error in errors] == ["schema/invalid"]
    assert path.name in errors[0]["message"]


def test_a_tree_with_no_contracts_skips_cleanly(tmp_path):
    """A Domain that has not adopted contracts is not a broken one."""
    result = _lint(_fixture(tmp_path, contracts=False))
    assert result.returncode == 0, result.stderr
    assert _errors(result) == []
    assert "contracts" in result.stderr


def test_a_repo_that_declares_no_contracts_skips_that_gate(tmp_path):
    """Not adopting contracts is not broken — and the map may not name the artifact at all."""
    root = _fixture(tmp_path)
    repo_map = root / "repo-map.json"
    data = json.loads(repo_map.read_text())
    data["artifact_paths"].pop("data_contract", None)
    repo_map.write_text(json.dumps(data))
    result = _lint(root)
    assert result.returncode == 0, result.stderr[-800:]
