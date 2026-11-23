"""Contrôle rédactionnel : interdit le tiret cadratin (U+2014) et le tiret demi-cadratin (U+2013).

Usage :
    python scripts/check_dashes.py            # analyse le dépôt courant
    python scripts/check_dashes.py docs README.md

Code de sortie : 0 si aucune occurrence, 1 sinon. Le script ne modifie aucun fichier.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
FORBIDDEN = {EM_DASH: "tiret cadratin (U+2014)", EN_DASH: "tiret demi-cadratin (U+2013)"}

EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".py",
    ".toml",
    ".json",
    ".yml",
    ".yaml",
    ".cfg",
    ".ini",
    ".html",
}
NAMES = {"LICENSE", "CHANGELOG", "CONTRIBUTING", "SECURITY", "README"}
SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build", ".pytest_cache", ".ruff_cache"}
# Le cahier des charges d'origine cite volontairement les caractères interdits.
SKIP_FILES = {"PROMPT DE DÉVELOPPEMENT COMPLET - H.md"}


def iter_files(paths: Iterable[Path]) -> Iterator[Path]:
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if any(part in SKIP_DIRS for part in child.parts) or not child.is_file():
                    continue
                if child.name in SKIP_FILES:
                    continue
                if child.suffix.lower() in EXTENSIONS or child.stem.upper() in NAMES:
                    yield child


def find_forbidden(path: Path) -> list[tuple[int, int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    hits = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for col, char in enumerate(line, start=1):
            if char in FORBIDDEN:
                hits.append((line_no, col, char))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    args = parser.parse_args(argv)

    total = 0
    for file in iter_files(args.paths):
        for line_no, col, char in find_forbidden(file):
            total += 1
            print(f"{file}:{line_no}:{col}: {FORBIDDEN[char]} interdit, remplacer par '-'")
    if total:
        print(f"\n{total} occurrence(s) de tiret long trouvée(s).", file=sys.stderr)
        return 1
    print("Aucun tiret cadratin ou demi-cadratin trouvé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
