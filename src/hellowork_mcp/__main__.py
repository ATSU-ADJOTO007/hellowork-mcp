"""Point d'entrée en ligne de commande : `hellowork-mcp` ou `python -m hellowork_mcp`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from . import __version__
from .paths import data_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hellowork-mcp", description="Serveur MCP Hellowork (stdio par défaut, HTTP avec --transport http)."
    )
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
    http = parser.add_argument_group("mode HTTP (connecteur distant par URL)")
    http.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=os.environ.get("HELLOWORK_MCP_TRANSPORT", "stdio"),
        help="stdio pour un client local, http pour exposer le serveur à une URL (Streamable HTTP).",
    )
    http.add_argument("--host", default=os.environ.get("HELLOWORK_MCP_HOST", "127.0.0.1"), help="Adresse d'écoute HTTP.")
    http.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT") or os.environ.get("HELLOWORK_MCP_PORT") or 8000),
        help="Port HTTP (variable PORT reconnue pour les hébergeurs).",
    )
    http.add_argument(
        "--path",
        default=os.environ.get("HELLOWORK_MCP_PATH", "/mcp"),
        help="Chemin de l'endpoint MCP. Un chemin long et aléatoire limite l'accès aux personnes qui le connaissent.",
    )
    http.add_argument(
        "--allowed-host",
        action="append",
        default=[h for h in os.environ.get("HELLOWORK_MCP_ALLOWED_HOSTS", "").split(",") if h.strip()],
        help="Nom d'hôte public accepté (répétable), par exemple mon-app.onrender.com.",
    )
    http.add_argument(
        "--enable-browser",
        action="store_true",
        default=os.environ.get("HELLOWORK_MCP_ENABLE_BROWSER") == "1",
        help="Autorise en HTTP les outils qui pilotent Chromium sur la machine du serveur (usage personnel uniquement).",
    )
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

    if args.transport == "http":
        return run_http(args)

    from .server import mcp

    mcp.run()
    return 0


def run_http(args: argparse.Namespace) -> int:
    """Sert le MCP en Streamable HTTP pour les connecteurs ajoutés par URL."""
    import anyio
    from mcp.server.transport_security import TransportSecuritySettings

    from . import server

    path = "/" + args.path.strip("/")
    server.configure_http_mode(enable_browser=args.enable_browser)
    loopback = args.host in {"127.0.0.1", "localhost", "::1"}
    if args.allowed_host:
        hosts = []
        for host in args.allowed_host:
            host = host.strip()
            hosts += [host, f"{host}:*"]
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            # Les connecteurs Claude appellent depuis les serveurs d'Anthropic, sans en-tête Origin.
            allowed_origins=["https://claude.ai", "https://claude.com"] + [f"https://{h.strip()}" for h in args.allowed_host],
        )
    elif loopback:
        security = None  # protection par défaut du SDK pour localhost
    else:
        # Derrière le proxy HTTPS d'un hébergeur, l'en-tête Host est le domaine public : sans liste explicite,
        # la protection contre le DNS rebinding (utile pour un serveur local) bloquerait toutes les requêtes.
        logging.getLogger(__name__).warning(
            "Écoute sur %s sans --allowed-host : contrôle de l'en-tête Host désactivé.", args.host
        )
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

    print(f"Hellowork MCP {__version__} : http://{args.host}:{args.port}{path}", file=sys.stderr)
    anyio.run(
        lambda: server.mcp.run_streamable_http_async(
            host=args.host,
            port=args.port,
            streamable_http_path=path,
            stateless_http=True,
            json_response=True,
            transport_security=security,
        )
    )
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
