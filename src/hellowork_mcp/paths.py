"""Emplacements des données locales selon le système d'exploitation.

Ordre de priorité :
1. variable d'environnement HELLOWORK_MCP_DATA_DIR
2. Windows : %LOCALAPPDATA%\\hellowork-mcp (repli %USERPROFILE%\\AppData\\Local\\hellowork-mcp)
3. macOS : ~/Library/Application Support/hellowork-mcp
4. Linux et autres : $XDG_DATA_HOME/hellowork-mcp (repli ~/.local/share/hellowork-mcp)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "hellowork-mcp"
ENV_DATA_DIR = "HELLOWORK_MCP_DATA_DIR"


def default_data_dir(platform: str | None = None, env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    """Calcule le dossier par défaut sans le créer. Les paramètres servent aux tests."""
    platform = platform or sys.platform
    env = dict(os.environ) if env is None else env
    home = home or Path.home()

    if platform.startswith("win"):
        base = env.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_NAME
        profile = env.get("USERPROFILE")
        root = Path(profile) if profile else home
        return root / "AppData" / "Local" / APP_NAME
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    xdg = env.get("XDG_DATA_HOME")
    # La spécification XDG impose un chemin absolu ; une valeur relative est ignorée.
    if xdg and (xdg.startswith("/") or Path(xdg).is_absolute()):
        return Path(xdg) / APP_NAME
    return home / ".local" / "share" / APP_NAME


def data_dir() -> Path:
    """Retourne le dossier de données (créé si besoin)."""
    override = os.environ.get(ENV_DATA_DIR)
    directory = Path(override).expanduser() if override else default_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def browser_profile_dir() -> Path:
    path = data_dir() / "browser-profile"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir() -> Path:
    path = data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path
