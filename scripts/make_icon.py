"""Génère les PNG de l'icône à partir de src/hellowork_mcp/assets/icon.svg.

Le rendu passe par Chromium (Playwright, déjà requis par le projet) pour obtenir un PNG lissé
à fond transparent. Sorties : src/hellowork_mcp/assets/icon.png et icon.png à la racine (README).

Usage : python scripts/make_icon.py [taille]   (256 par défaut)
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "src" / "hellowork_mcp" / "assets" / "icon.svg"
TARGETS = [ROOT / "src" / "hellowork_mcp" / "assets" / "icon.png", ROOT / "icon.png"]


def render(size: int = 256) -> bytes:
    style = f'style="width:{size}px;height:{size}px;display:block" '
    svg = SVG.read_text(encoding="utf-8").replace("<svg ", "<svg " + style, 1)
    html = (
        "<!doctype html><html><body style='margin:0;background:transparent'>"
        f"<div id='icon' style='width:{size}px;height:{size}px'>{svg}</div>"
        "</body></html>"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": size, "height": size})
        page.set_content(html)
        data = page.locator("#icon").screenshot(omit_background=True)
        browser.close()
    return data


def main() -> None:
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 256
    data = render(size)
    for target in TARGETS:
        target.write_bytes(data)
        print(f"{target} ({len(data)} octets)")


if __name__ == "__main__":
    main()
