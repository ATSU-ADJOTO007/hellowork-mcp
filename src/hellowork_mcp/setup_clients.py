"""Configuration automatique de Claude Desktop (et Claude Code si présent).

Appelé par `hellowork-mcp --setup-claude` et par les scripts install.ps1 / install.sh.
Le fichier existant est fusionné (les autres serveurs sont conservés) et une copie de sauvegarde est faite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SERVER_NAME = "hellowork"
ENV_CONFIG = "HELLOWORK_MCP_CLAUDE_CONFIG"  # chemin forcé (tests, installations atypiques)


def executable_path() -> str:
    """Chemin absolu de la commande hellowork-mcp de cette installation."""
    scripts = Path(sys.executable).parent
    for name in ("hellowork-mcp.exe", "hellowork-mcp"):
        candidate = scripts / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which("hellowork-mcp")
    if found:
        return str(Path(found).resolve())
    raise FileNotFoundError("Commande hellowork-mcp introuvable : réinstaller le paquet.")


def claude_desktop_config_paths() -> list[Path]:
    """Emplacements possibles du fichier de configuration de Claude Desktop, du plus probable au moins probable."""
    override = os.environ.get(ENV_CONFIG)
    if override:
        return [Path(override)]
    paths: list[Path] = []
    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA")
        if local:
            # Version Microsoft Store : dossier virtualisé du paquet
            for pkg in sorted(Path(local, "Packages").glob("Claude_*")):
                paths.append(pkg / "LocalCache" / "Roaming" / "Claude" / "claude_desktop_config.json")
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    elif sys.platform == "darwin":
        paths.append(Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
    else:
        paths.append(Path.home() / ".config" / "Claude" / "claude_desktop_config.json")
    return paths


def _target_config() -> Path:
    paths = claude_desktop_config_paths()
    for path in paths:
        if path.exists():
            return path
    for path in paths:
        if path.parent.exists():
            return path
    return paths[-1]


def configure_claude_desktop(command: str | None = None) -> dict:
    command = command or executable_path()
    path = _target_config()
    data: dict = {}
    backup = None
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path} n'est pas un JSON valide ({exc}). Corriger ou supprimer ce fichier puis relancer."
                ) from exc
        backup = path.with_name(f"{path.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
    if not isinstance(data, dict):
        raise ValueError(f"{path} ne contient pas un objet JSON.")
    servers = data.setdefault("mcpServers", {})
    previous = servers.get(SERVER_NAME)
    servers[SERVER_NAME] = {"command": command}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "client": "Claude Desktop",
        "config": str(path),
        "backup": str(backup) if backup else None,
        "command": command,
        "replaced_existing_entry": previous is not None,
        "next_step": "Quitter complètement Claude Desktop puis le relancer.",
    }


def configure_claude_code(command: str | None = None) -> dict | None:
    """Ajoute le serveur à Claude Code (portée utilisateur) si la CLI `claude` est installée."""
    claude = shutil.which("claude")
    if not claude:
        return None
    command = command or executable_path()
    subprocess.run([claude, "mcp", "remove", "--scope", "user", SERVER_NAME], capture_output=True, check=False)
    result = subprocess.run(
        [claude, "mcp", "add", "--scope", "user", SERVER_NAME, "--", command],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "client": "Claude Code",
        "ok": result.returncode == 0,
        "details": (result.stdout or result.stderr).strip()[:300],
    }


def setup_all(include_claude_code: bool = True) -> dict:
    command = executable_path()
    report = {"command": command, "clients": [configure_claude_desktop(command)]}
    if include_claude_code and os.environ.get("HELLOWORK_MCP_SETUP_CLAUDE_CODE", "1") != "0":
        code = configure_claude_code(command)
        if code:
            report["clients"].append(code)
    return report
