"""Classification et suivi des redirections vers des sites de candidature externes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse, urlunparse

from .paths import data_dir
from .storage import read_json, update_json

Category = Literal["job_board", "company_careers", "ats", "other"]

CATEGORY_LABELS = {
    "job_board": "site d'annonce",
    "company_careers": "site de recrutement de l'entreprise",
    "ats": "ATS",
    "other": "autre destination",
}

ATS_DOMAINS = (
    "myworkdayjobs.com",
    "workday.com",
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "taleo.net",
    "successfactors.com",
    "successfactors.eu",
    "icims.com",
    "teamtailor.com",
    "recruitee.com",
    "workable.com",
    "jobvite.com",
    "bamboohr.com",
    "softy.pro",
    "flatchr.io",
    "digitalrecruiters.com",
    "jobaffinity.fr",
    "werecruit.io",
    "talent-soft.com",
    "talentsoft.com",
    "cegid.com",
    "beetween.com",
    "taleez.com",
    "breezy.hr",
    "personio.de",
    "personio.com",
    "jazzhr.com",
    "ashbyhq.com",
    "oraclecloud.com",
    "csod.com",
    "hrflowtalents.com",
    "welcomekit.co",
    "gestmax.fr",
)

JOB_BOARD_DOMAINS = (
    "indeed.com",
    "indeed.fr",
    "linkedin.com",
    "welcometothejungle.com",
    "monster.fr",
    "francetravail.fr",
    "pole-emploi.fr",
    "apec.fr",
    "cadremploi.fr",
    "meteojob.com",
    "jobteaser.com",
    "glassdoor.fr",
    "glassdoor.com",
    "keljob.com",
    "optioncarriere.com",
    "jobijoba.com",
    "staffme.fr",
    "leboncoin.fr",
    "figaro.fr",
    "talent.com",
    "jooble.org",
)

CAREERS_HINTS = ("careers", "carrieres", "carriere", "recrutement", "jobs", "emploi", "talents", "join", "rejoindre")


def _domain_matches(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def classify_url(url: str) -> Category:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return "other"
    if _domain_matches(host, ATS_DOMAINS):
        return "ats"
    if _domain_matches(host, JOB_BOARD_DOMAINS):
        return "job_board"
    first_label = host.split(".")[0]
    path = parsed.path.lower()
    if first_label in CAREERS_HINTS or any(f"/{hint}" in path for hint in CAREERS_HINTS):
        return "company_careers"
    return "other"


def normalize_url(url: str) -> str:
    """Clé de déduplication : schéma et hôte en minuscules, sans fragment ni paramètres de suivi."""
    parsed = urlparse(url.strip())
    query = "&".join(
        part
        for part in parsed.query.split("&")
        if part and not part.lower().startswith(("utm_", "gclid=", "fbclid=", "xtor=", "source="))
    )
    return urlunparse(
        (parsed.scheme.lower(), (parsed.netloc or "").lower(), parsed.path.rstrip("/") or "/", "", query, "")
    )


def is_safe_external_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


class RedirectRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "redirects.json"

    def all(self) -> list[dict]:
        return read_json(self.path, list)

    def find(self, external_url: str) -> dict | None:
        key = normalize_url(external_url)
        return next((r for r in self.all() if r.get("key") == key), None)

    def record(
        self,
        *,
        offer_id: str,
        title: str,
        company: str | None,
        hellowork_url: str,
        external_url: str,
    ) -> tuple[dict, bool]:
        """Enregistre la redirection. Retourne (entrée, créée). Une URL déjà connue n'est pas dupliquée."""
        if not is_safe_external_url(external_url):
            raise ValueError(f"URL externe refusée (http ou https attendu) : {external_url!r}")
        key = normalize_url(external_url)
        category = classify_url(external_url)

        def mutate(entries: list[dict]) -> tuple[dict, bool]:
            for entry in entries:
                if entry.get("key") == key:
                    return entry, False
            entry = {
                "key": key,
                "date": datetime.now().isoformat(timespec="seconds"),
                "offer_id": offer_id,
                "title": title,
                "company": company,
                "hellowork_url": hellowork_url,
                "external_url": external_url,
                "category": category,
                "category_label": CATEGORY_LABELS[category],
                "opened_in_browser": False,
                "opened_at": None,
            }
            entries.append(entry)
            return entry, True

        return update_json(self.path, list, mutate)

    def mark_opened(self, external_url: str) -> dict | None:
        key = normalize_url(external_url)

        def mutate(entries: list[dict]) -> dict | None:
            for entry in entries:
                if entry.get("key") == key:
                    entry["opened_in_browser"] = True
                    entry["opened_at"] = datetime.now().isoformat(timespec="seconds")
                    return entry
            return None

        return update_json(self.path, list, mutate)
