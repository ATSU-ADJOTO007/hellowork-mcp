"""Exports CSV (Excel, séparateur ;) et Markdown horodatés."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import exports_dir

# Les valeurs commençant par ces caractères seraient interprétées comme formules par Excel.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    text = str(value).replace("\r\n", " ").replace("\n", " ")
    if text.startswith(_FORMULA_PREFIXES):
        text = "'" + text
    return text


def _target(name: str, suffix: str, directory: Path | None) -> Path:
    directory = directory or exports_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name).strip("-") or "export"
    path = directory / f"{safe}-{stamp}{suffix}"
    counter = 1
    while path.exists():
        path = directory / f"{safe}-{stamp}-{counter}{suffix}"
        counter += 1
    return path


def export_csv(
    rows: Iterable[dict[str, Any]], columns: Sequence[str], name: str, directory: Path | None = None
) -> Path:
    path = _target(name, ".csv", directory)
    # utf-8-sig ajoute le BOM : Excel détecte l'UTF-8 et affiche correctement les accents.
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_cell(row.get(col)) for col in columns])
    return path


def _md(value: Any) -> str:
    text = _cell(value)
    if text.startswith("'") and len(text) > 1 and text[1] in "=+-@":
        text = text[1:]
    return text.replace("|", "\\|")


def export_markdown(
    rows: Iterable[dict[str, Any]],
    columns: Sequence[str],
    name: str,
    title: str,
    directory: Path | None = None,
) -> Path:
    path = _target(name, ".md", directory)
    rows = list(rows)
    lines = [
        f"# {title}",
        "",
        f"Export généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} ({len(rows)} ligne(s)).",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md(row.get(col)) for col in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


HISTORY_COLUMNS = ["offer_id", "title", "company", "status_label", "score", "first_seen", "updated", "url"]
EVENT_COLUMNS = ["date", "label", "offer_id", "title", "company", "score", "details", "url"]
REDIRECT_COLUMNS = [
    "date",
    "title",
    "company",
    "category_label",
    "opened_in_browser",
    "hellowork_url",
    "external_url",
]
