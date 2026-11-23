"""Protections avant candidature : doublons, limite quotidienne, score minimum, confirmation explicite."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field

from .config import Config
from .history import History
from .models import Offer
from .scoring import ScoreResult

TOKEN_TTL_SECONDS = 15 * 60


@dataclass
class GuardReport:
    allowed: bool
    checks: list[dict] = field(default_factory=list)

    def add(self, name: str, ok: bool, details: str) -> None:
        self.checks.append({"check": name, "ok": ok, "details": details})
        if not ok:
            self.allowed = False


def run_guards(offer: Offer, score: ScoreResult, config: Config, history: History) -> GuardReport:
    report = GuardReport(allowed=True)
    report.add(
        "offre_disponible",
        offer.available,
        "Offre en ligne" if offer.available else "Offre indisponible",
    )
    applied = history.has_applied(offer.offer_id)
    report.add("doublon", not applied, "Candidature déjà envoyée pour cette offre" if applied else "Aucune candidature précédente")
    today = history.applications_on()
    report.add(
        "limite_quotidienne",
        today < config.max_applications_per_day,
        f"{today} candidature(s) envoyée(s) aujourd'hui sur {config.max_applications_per_day} autorisée(s)",
    )
    report.add(
        "score_minimum",
        score.score >= config.min_score,
        f"Score {score.score}/100, minimum requis {config.min_score}",
    )
    report.add(
        "mots_cles_interdits",
        not score.excluded_keywords_found,
        "Aucun mot-clé interdit"
        if not score.excluded_keywords_found
        else "Mots-clés interdits : " + ", ".join(score.excluded_keywords_found),
    )
    external = bool(offer.external_apply_url) or offer.direct_apply is False
    report.add(
        "candidature_hellowork",
        not external,
        "Candidature directe sur Hellowork"
        if not external
        else "Candidature sur un site externe : utiliser record_external_redirect",
    )
    return report


def _fingerprint(offer_id: str, message: str | None) -> str:
    return hashlib.sha256(f"{offer_id}\n{message or ''}".encode()).hexdigest()


class ConfirmationStore:
    """Jetons à usage unique liant une offre et un message précis à une validation humaine."""

    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str, float]] = {}

    def issue(self, offer_id: str, message: str | None) -> tuple[str, int]:
        self._purge()
        token = secrets.token_urlsafe(16)
        self._tokens[token] = (_fingerprint(offer_id, message), time.monotonic() + TOKEN_TTL_SECONDS)
        return token, TOKEN_TTL_SECONDS

    def consume(self, token: str, offer_id: str, message: str | None) -> tuple[bool, str]:
        self._purge()
        entry = self._tokens.get(token)
        if entry is None:
            return False, "Jeton de confirmation inconnu ou expiré : relancer prepare_application."
        fingerprint, _ = entry
        if fingerprint != _fingerprint(offer_id, message):
            return False, "Le jeton ne correspond pas à cette offre ou le message a été modifié : relancer prepare_application."
        del self._tokens[token]
        return True, "Jeton valide"

    def _purge(self) -> None:
        now = time.monotonic()
        for token in [t for t, (_, exp) in self._tokens.items() if exp < now]:
            del self._tokens[token]
