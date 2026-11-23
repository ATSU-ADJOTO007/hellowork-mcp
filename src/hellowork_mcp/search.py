"""Recherche d'offres et récupération des pages offre via HTTP.

Les pages publiques de Hellowork sont rendues côté serveur : une requête HTTP suffit pour la
recherche et la lecture des offres. Le navigateur Playwright n'est utilisé que pour la connexion
et les candidatures.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlencode

import httpx

from . import HELLOWORK_BASE_URL, __version__
from .filters import normalize
from .models import Offer, OfferSummary
from .parsing import OfferUnavailableError, offer_url, parse_offer, parse_search_results

log = logging.getLogger(__name__)

SEARCH_PATH = "/fr-fr/emploi/recherche.html"
RESULTS_PER_PAGE = 30
MAX_PAGES = 10

# Valeurs du paramètre « c » relevées dans le formulaire de recherche Hellowork.
CONTRACT_CODES = {
    "cdi": "CDI",
    "cdd": "CDD",
    "interim": "Travail_temp",
    "intérim": "Travail_temp",
    "travail temporaire": "Travail_temp",
    "stage": "Stage",
    "alternance": "Alternance",
    "independant": "Independant",
    "indépendant": "Independant",
    "franchise": "Franchise",
    "associe": "Associe",
    "associé": "Associe",
    "fonctionnaire": "Fonctionnaire",
    "freelance": "Freelance",
}

REMOTE_CODES = {"full": "Complet", "partial": "Partiel", "occasional": "Occasionnel", "none": "Pas_teletravail"}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/131.0 Safari/537.36 hellowork-mcp/{__version__}"
)


class HelloworkHTTPError(RuntimeError):
    pass


def contract_code(contract: str) -> str:
    code = CONTRACT_CODES.get(normalize(contract)) or CONTRACT_CODES.get(contract.lower().strip())
    if not code:
        raise ValueError(f"Type de contrat inconnu : {contract!r}. Valeurs acceptées : {', '.join(sorted(set(CONTRACT_CODES)))}")
    return code


def build_search_url(
    keywords: str = "",
    location: str = "",
    contracts: list[str] | None = None,
    remote: list[str] | None = None,
    page: int = 1,
    sort: str = "relevance",
) -> str:
    if sort not in {"relevance", "date"}:
        raise ValueError("sort doit valoir 'relevance' ou 'date'")
    params: list[tuple[str, str]] = []
    if keywords.strip():
        params.append(("k", keywords.strip()))
    if location.strip():
        params.append(("l", location.strip()))
    for contract in contracts or []:
        params.append(("c", contract_code(contract)))
    for mode in remote or []:
        if mode not in REMOTE_CODES:
            raise ValueError(f"Mode de télétravail inconnu : {mode!r}. Valeurs : {', '.join(REMOTE_CODES)}")
        params.append(("t", REMOTE_CODES[mode]))
    if sort != "relevance":
        params.append(("st", sort))
    if page > 1:
        params.append(("p", str(page)))
    return f"{HELLOWORK_BASE_URL}{SEARCH_PATH}" + (f"?{urlencode(params)}" if params else "")


class HelloworkClient:
    def __init__(self, delay_seconds: float = 1.5, timeout: float = 20.0, transport: httpx.BaseTransport | None = None):
        self.delay_seconds = delay_seconds
        self._last_request = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _get(self, url: str) -> httpx.Response:
        wait = self.delay_seconds - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = self._client.get(url)
        except httpx.HTTPError as exc:
            raise HelloworkHTTPError(f"Requête impossible vers {url} : {exc}") from exc
        finally:
            self._last_request = time.monotonic()
        return response

    def search(
        self,
        keywords: str = "",
        location: str = "",
        contracts: list[str] | None = None,
        remote: list[str] | None = None,
        max_results: int = 30,
        sort: str = "relevance",
    ) -> tuple[list[OfferSummary], int | None, list[str]]:
        """Parcourt les pages jusqu'à `max_results` offres uniques. Retourne (offres, total annoncé, URLs lues)."""
        seen: set[str] = set()
        offers: list[OfferSummary] = []
        visited: list[str] = []
        total: int | None = None
        pages = min(MAX_PAGES, max(1, -(-max_results // RESULTS_PER_PAGE)))
        for page in range(1, pages + 1):
            url = build_search_url(keywords, location, contracts, remote, page, sort)
            response = self._get(url)
            visited.append(url)
            if response.status_code == 404:
                break
            if response.status_code >= 400:
                raise HelloworkHTTPError(f"Hellowork a répondu {response.status_code} pour {url}")
            page_offers, page_total = parse_search_results(response.text)
            total = total if total is not None else page_total
            new = [o for o in page_offers if o.offer_id not in seen]
            for offer in new:
                seen.add(offer.offer_id)
                offers.append(offer)
                if len(offers) >= max_results:
                    return offers, total, visited
            if not new or len(page_offers) < RESULTS_PER_PAGE:
                break
        return offers, total, visited

    def get_offer(self, offer_id: str) -> Offer:
        url = offer_url(offer_id)
        response = self._get(url)
        if response.status_code in (404, 410):
            raise OfferUnavailableError(f"L'offre {offer_id} n'est plus disponible (HTTP {response.status_code}).")
        if response.status_code >= 400:
            raise HelloworkHTTPError(f"Hellowork a répondu {response.status_code} pour {url}")
        final_url = str(response.url)
        if "/emplois/" not in final_url:
            raise OfferUnavailableError(f"L'offre {offer_id} redirige vers {final_url} : elle n'est plus en ligne.")
        return parse_offer(response.text, url)
