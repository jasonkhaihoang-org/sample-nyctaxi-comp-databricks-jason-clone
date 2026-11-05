#!/usr/bin/env python3
"""One lint for the Domain's canonical artifacts: shape, coverage and agreement.

Runs the structural commands from `repo-map.json` — the Ossie model and ontology,
and the ODCS data contracts — then the mechanical checks those commands cannot
see: a mapping that identifies a version surrogate, a concept mapped on part of
its identity, and a declaration the standard allows but nothing reads.
`glossary` is printed and never fails the run. A tree with no `contracts/` has
no contracts to check and skips that gate: not adopting contracts is not broken.

Every check compares two declarations. Nothing here judges meaning — whether a
term denotes identity, or whether a mapping's population is honest, is a review.

Usage: python3 tools/ossie_lint.py [--quiet]
Exit 0 when every blocking check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OSSIE = ROOT / ".agents" / "skills" / "semantic-model" / "scripts" / "ossie.py"
REPO_MAP = json.loads((ROOT / "repo-map.json").read_text())


def _declared(key: str) -> Path:
    """The path a repo-map pattern names, up to its first placeholder."""
    raw = REPO_MAP["artifact_paths"][key]
    prefix = raw.split("{")[0].split("*")[0].rstrip("/")
    return ROOT / prefix if prefix else ROOT


MODEL = _declared("logical_model")
ONTOLOGY = _declared("ontology")
ADRS = _declared("adr")
CONTEXT = _declared("context")
CONTRACTS = _declared("data_contract") if "data_contract" in REPO_MAP.get("artifact_paths", {}) else None
def _role(layer: dict) -> str:
    """The layer's declared role, else the plugin's derivation (a dlt layer is input, any other internal)."""
    return layer.get("role") or ("input" if layer.get("built_by") == "dlt" else "internal")


BOUNDARY_ROOTS = [ROOT / layer["path"] for layer in REPO_MAP["layers"].values() if _role(layer) == "boundary"]
EXCLUDES = [e["relation"] for e in REPO_MAP.get("semantic_exclusions", [])]
TESTS = ROOT / REPO_MAP["artifact_paths"]["singular_tests"]
DECLARATION_KEYS = ("requires", "derived_by", "prefixes")
# The generated tests are written for the platform the Domain runs on: the dialect flag the
# map's `ossie_generate_tests` command passes, so `--check` compares what that command writes.
_GENERATE = shlex.split(REPO_MAP.get("commands", {}).get("ossie_generate_tests", ""))
DIALECT = _GENERATE[_GENERATE.index("--dialect"):_GENERATE.index("--dialect") + 2] if "--dialect" in _GENERATE else []


def run(name: str, args: list[str], blocking: bool = True,
        script: Path = OSSIE) -> list[dict]:
    """Run one gate script; return its JSON diagnostics, failing the lint."""
    result = subprocess.run([sys.executable, str(script), *args],
                            cwd=ROOT, capture_output=True, text=True)
    try:
        diags = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        diags = [{"severity": "error", "code": "lint/bad-output",
                  "message": f"{name}: stdout was not JSON: {result.stdout[:200]}"}]
    diags = diags if isinstance(diags, list) else []  # `glossary` prints an object
    warnings = [d for d in diags if isinstance(d, dict) and d.get("severity") == "warning"]
    print(f"  {name:<28} exit {result.returncode}"
          + (f", {len(warnings)} warning(s)" if warnings else ""), file=sys.stderr)
    if blocking and result.returncode != 0:
        return diags or [{"severity": "error", "code": "lint/failed",
                          "message": f"{name} failed"}]
    return []


def contracts() -> list[dict]:
    """The data-contract gate, from the command the map declares.

    Errors block and warnings do not, as `odcs.py` itself decides. A tree with no
    `contracts/`, or a map that declares no contract artifact at all, has not adopted
    contracts: there is nothing to check, and the absence is not a finding against the
    relations the layers declare.
    """
    if CONTRACTS is None:
        print(f"  {'contracts':<28} skipped: the map declares no contracts", file=sys.stderr)
        return []
    if not CONTRACTS.is_dir():
        print(f"  {'contracts':<28} skipped: no {CONTRACTS.name}/", file=sys.stderr)
        return []
    command = shlex.split(REPO_MAP["commands"]["odcs_check"])
    script = next(word for word in command if word.endswith(".py"))
    return run("contracts", [*command[command.index(script) + 1:], "--root", str(ROOT)],
               script=ROOT / script)


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def load(directory: Path, suffix: str) -> list[tuple[Path, dict]]:
    import yaml
    out = []
    for path in sorted(directory.glob(f"*{suffix}")):
        doc = yaml.safe_load(path.read_text())
        if isinstance(doc, dict):
            out.append((path, doc))
    return out


def natural_keys(doc: dict) -> dict[str, dict]:
    """Per dataset: the declared natural key (SCD) and the declared primary key."""
    import json as _json
    keys = {}
    for dataset in doc.get("datasets") or []:
        name = dataset.get("name")
        natural = None
        for ext in dataset.get("custom_extensions") or []:
            payload = _json.loads(ext.get("data") or "{}")
            scd = payload.get("scd") or {}
            if scd.get("natural_key"):
                natural = scd["natural_key"]
        keys[name] = {"natural": natural, "primary": list(dataset.get("primary_key") or [])}
    return keys


def identity_lint() -> list[dict]:
    """A mapping must identify the entity by its natural key, not a version of it."""
    models = {doc.get("name"): (path, doc) for path, doc in load(MODEL, ".ossie.yaml")}
    diags = []
    for path, mapping in load(ONTOLOGY, ".mapping.yaml"):
        ref = mapping.get("semantic_model_ref") or {}
        model = models.get(ref.get("name"))
        if not model:
            continue  # refs already reports the unresolved document
        keys = natural_keys(model[1])
        for block in mapping.get("concept_mappings") or []:
            for node in walk(block):
                expression = node.get("expression")
                if not expression or "." not in str(expression):
                    continue
                dataset, field = str(expression).split(".", 1)
                declared = keys.get(dataset) or {}
                natural, primary = declared.get("natural"), declared.get("primary") or []
                if natural and field == natural:
                    continue
                if not natural and field in primary:
                    continue
                if natural and field in primary and field != natural:
                    diags.append({
                        "severity": "error", "code": "lint/surrogate-identity", "file": str(path),
                        "message": f"'{expression}' identifies {block.get('concept')} by a key "
                                   f"that is not the declared natural key '{natural}' of "
                                   f"'{dataset}'; a surrogate over the natural key is a version"})
    return diags


def partial_identity_lint() -> list[dict]:
    """A mapped concept must map every relationship its identify_by names."""
    diags = []
    concepts = {}
    for _, doc in load(ONTOLOGY, ".ontology.yaml"):
        for component in doc.get("ontology") or []:
            if isinstance(component, dict) and component.get("identify_by"):
                concepts[component["concept"]] = set(component["identify_by"])
    mapped = {}
    for _, mapping in load(ONTOLOGY, ".mapping.yaml"):
        for block in mapping.get("concept_mappings") or []:
            seen = mapped.setdefault(block.get("concept"), set())
            seen.update(node.get("relationship") for node in walk(block)
                        if node.get("relationship"))
    for concept, needed in sorted(concepts.items()):
        missing = sorted(needed - mapped.get(concept, set()))
        if missing and concept in mapped:
            diags.append({"severity": "error", "code": "lint/partial-identity",
                          "message": f"'{concept}' is mapped but its identity components "
                                     f"{missing} are not"})
    return diags


def declaration_lint() -> list[dict]:
    """A construct nothing reads is a declaration; refuse it where it pretends otherwise."""
    diags = []
    for path, doc in load(ONTOLOGY, ".ontology.yaml"):
        for node in walk(doc):
            used = [key for key in DECLARATION_KEYS if node.get(key)]
            if used:
                diags.append({"severity": "error", "code": "lint/declaration-only",
                              "file": str(path),
                              "message": f"uses {used}, which no evaluator reads"})
        for component in doc.get("ontology") or []:
            if not isinstance(component, dict):
                continue
            if component.get("iri"):
                diags.append({"severity": "error", "code": "lint/iri",
                              "file": str(path),
                              "message": f"concept '{component.get('concept')}' carries an iri; "
                                         f"name the vocabulary and its release, or omit it"})
    return diags


def main() -> int:
    print("Structural gates", file=sys.stderr)
    diags = []
    diags += run("validate model", ["validate", str(MODEL)])
    diags += run("validate ontology", ["validate", str(ONTOLOGY)])
    diags += run("refs", ["refs", str(ONTOLOGY), str(MODEL)])
    diags += run("coverage", ["coverage", str(MODEL), *map(str, BOUNDARY_ROOTS),
                                    *[arg for rel in EXCLUDES for arg in ("--exclude", rel)]])
    diags += run("suppliers", ["suppliers", str(MODEL)])
    diags += run("notes", ["notes", str(MODEL), str(TESTS), str(ADRS)])
    diags += run("generate-tests", ["generate-tests", str(MODEL), str(TESTS), "--check", *DIALECT])
    diags += contracts()
    run("glossary", ["glossary", str(ONTOLOGY), str(CONTEXT)], blocking=False)

    print("Lints", file=sys.stderr)
    diags += identity_lint()
    diags += partial_identity_lint()
    diags += declaration_lint()

    errors = [d for d in diags if d.get("severity") == "error"]
    if errors and "--quiet" not in sys.argv:
        print(json.dumps(errors, indent=2))
    print(f"{len(errors)} blocking finding(s).", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
