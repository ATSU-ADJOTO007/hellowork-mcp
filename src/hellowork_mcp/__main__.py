"""Point d'entrée en ligne de commande : `hellowork-mcp` ou `python -m hellowork_mcp`."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from . import __version__
from .paths import data_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hellowork-mcp", description="Serveur MCP Hellowork (stdio).")
    parser.add_argument("--version", action="version", version=f"hellowork-mcp {__version__}")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Vérifie l'installation (imports, dossier de données, navigateur Playwright) puis quitte.",
    )
    parser.add_argument(
        "--install-browser",
        action="store_true",
        help="Télécharge Chromium pour Playwright avec le Python de cette installation, puis quitte.",
    )
    parser.add_argument("--log-level", default="WARNING", help="Niveau de log sur stderr (DEBUG, INFO, WARNING).")
    args = parser.parse_args(argv)

    if args.install_browser:
        import subprocess

        return subprocess.call([sys.executable, "-m", "playwright", "install", "chromium"])

    # stdout est réservé au protocole MCP : tous les logs partent sur stderr.
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.WARNING),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.check:
        report = run_check()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    from .server import mcp

    mcp.run()
    return 0


def run_check() -> dict:
    """Diagnostic utilisé par `hellowork-mcp --check`."""
    report: dict = {"version": __version__, "python": sys.version.split()[0], "ok": True, "checks": {}}
    try:
        directory = data_dir()
        probe = directory / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report["checks"]["data_dir"] = {"ok": True, "path": str(directory)}
    except OSError as exc:
        report["ok"] = False
        report["checks"]["data_dir"] = {"ok": False, "error": str(exc)}

    try:
        from .server import mcp

        report["checks"]["mcp_server"] = {"ok": True, "name": mcp.name}
    except Exception as exc:  # diagnostic : on veut afficher toute erreur d'import
        report["ok"] = False
        report["checks"]["mcp_server"] = {"ok": False, "error": repr(exc)}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = p.chromium.executable_path
        from pathlib import Path

        installed = Path(path).exists()
        report["checks"]["chromium"] = {
            "ok": installed,
            "path": path,
            "hint": None if installed else "Lancer : python -m playwright install chromium",
        }
        if not installed:
            report["ok"] = False
    except Exception as exc:
        report["ok"] = False
        report["checks"]["chromium"] = {
            "ok": False,
            "error": repr(exc),
            "hint": "Lancer : python -m playwright install chromium",
        }
    return report


if __name__ == "__main__":
    raise SystemExit(main())
