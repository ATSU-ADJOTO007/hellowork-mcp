"""Correspondance de mots-clés insensible à la casse et aux accents."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def normalize(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def contains_keyword(text: str, keyword: str) -> bool:
    """Recherche `keyword` comme mot ou expression entière (« java » ne trouve pas « javascript »)."""
    norm_kw = normalize(keyword)
    if not norm_kw:
        return False
    pattern = r"(?<![\w])" + re.escape(norm_kw) + r"(?![\w])"
    return re.search(pattern, normalize(text)) is not None


def match_keywords(text: str, keywords: Iterable[str]) -> tuple[list[str], list[str]]:
    """Retourne (trouvés, absents)."""
    found: list[str] = []
    missing: list[str] = []
    for keyword in keywords:
        (found if contains_keyword(text, keyword) else missing).append(keyword)
    return found, missing


def strip_html(html: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d)\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
