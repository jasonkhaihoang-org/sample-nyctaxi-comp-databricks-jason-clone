"""The plugin's `odcs` launcher: the vibedata-odcs command with the Intent's sandbox resolved.

Everything the tool does lives in the `vibedata-odcs` package, pinned by the managed constraints.
This file adds only what the plugin knows and the package must not: which platform the Intent
runs on, and where that platform's sandbox is. Run it exactly as the package's `odcs` command:

  python3 odcs.py check | reverse | generate | diff <base-ref> | profile | export <format> --out DIR | results <file> | version
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import TypedDict

# The plugin's own scripts, where the platform modules and the Intent-context reader live.
PLUGIN_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
# A Domain repo vendors this file into `.agents/skills/data-contract/scripts/`, where the path
# above names nothing. The runtime installs the plugin at Studio's default-plugin path, one
# directory per version, the same path the plugin's own hooks resolve (ADR-0009); no
# environment variable names it.
INSTALLED_PLUGIN = Path("/data/default-plugins/vibedata-data-engineering")

INSTALL = (
    "write the effective constraints with `python3 <plugin>/scripts/runtime_pins.py --out <scratch>/constraints.txt`, "
    "then run `python3 -m pip install -c <scratch>/constraints.txt -r <skill>/scripts/requirements.txt`"
)


class Destination(TypedDict, total=False):
    """What the resolver tells the package about the Intent's sandbox."""

    family: str
    path: str
    platform: str
    database: str
    host: str
    http_path: str
    port: str
    user: str
    sslmode: str


def _version_key(name: str) -> tuple:
    """A version directory's order: numeric parts compared as numbers, so 0.145 follows 0.99."""
    if re.fullmatch(r"\d+(?:\.\d+)*", name):
        return (1, tuple(int(part) for part in name.split(".")))
    return (0, ())


def plugin_scripts() -> Path | None:
    """The plugin's `scripts/`: beside this file in the plugin, else the newest installed one."""
    if (PLUGIN_SCRIPTS / "platforms").is_dir():
        return PLUGIN_SCRIPTS
    try:
        installed = [version / "scripts" for version in INSTALLED_PLUGIN.glob("*")
                     if (version / "scripts" / "platforms").is_dir()]
    except OSError:  # an unreadable mount: resolve nothing, so the caller's own error reports it
        return None
    return max(installed, key=lambda scripts: _version_key(scripts.parent.name), default=None)


def plugin_destination(repo_map: dict) -> Destination | None:
    """What the plugin's platform module says the Intent's sandbox is; None outside a runtime."""
    scripts = plugin_scripts()
    if scripts is None:
        return None
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        from intent_context import IntentContextError, load_intent_context
    except ImportError:  # no Intent-context reader beside this copy: the caller passes --catalog
        return None
    try:
        context = dict(load_intent_context())
    except (IntentContextError, OSError):  # no Intent context: the caller passes --catalog
        return None
    from platforms import UnknownPlatformError, load

    platform = context.get("VD_DOMAIN_DATA_PLATFORM") or str(repo_map.get("data_platform") or "")
    try:
        module = load(platform)
    except UnknownPlatformError:
        return {"platform": platform}
    destination = {**module.expected_destination(context), "platform": platform}
    # Coordinates only the plugin knows (a host, a name), read by the platform module from the context.
    destination = {**destination, **getattr(module, "engine_coordinates", lambda _context: {})(context)}
    # A login the engine reads from the environment (a minted password). The package asks for the
    # destination only when a command is about to connect, so nothing is minted for any other.
    try:
        os.environ.update(getattr(module, "engine_environment", lambda _context: {})(context))
    except Exception as error:  # noqa: BLE001 - one JSON diagnostic, never a traceback
        print(json.dumps([{"severity": "error", "code": "catalog/unreadable",
                           "message": f"the `{platform}` sandbox login is unavailable: {error}"}]))
        sys.exit(1)
    return destination


def run() -> None:
    try:
        from vibedata.odcs.cli import main
    except ImportError as error:  # absent, or installed without what this launcher needs
        print(json.dumps([{
            "severity": "error",
            "code": "cli/package-missing",
            "message": f"vibedata-odcs cannot be imported ({error}): {INSTALL}",
        }]))
        sys.exit(1)
    main(destination_resolver=plugin_destination)


if __name__ == "__main__":
    run()
