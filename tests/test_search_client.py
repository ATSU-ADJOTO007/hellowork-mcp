from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from hellowork_mcp.parsing import OfferUnavailableError
from hellowork_mcp.search import HelloworkClient, HelloworkHTTPError, build_search_url, contract_code


def test_build_search_url():
    url = build_search_url("développeur python", "Lyon", ["CDI", "intérim"], ["partial"], page=2, sort="date")
    query = parse_qs(urlparse(url).query)
    assert query["k"] == ["développeur python"]
    assert query["l"] == ["Lyon"]
    assert query["c"] == ["CDI", "Travail_temp"]
    assert query["t"] == ["Partiel"]
    assert query["p"] == ["2"] and query["st"] == ["date"]
    assert build_search_url() == "https://www.hellowork.com/fr-fr/emploi/recherche.html"


def test_invalid_parameters():
    with pytest.raises(ValueError):
        contract_code("CDX")
    with pytest.raises(ValueError):
        build_search_url("a", sort="prix")
    with pytest.raises(ValueError):
        build_search_url("a", remote=["toujours"])


def _client(handler) -> HelloworkClient:
    client = HelloworkClient(delay_seconds=0.5, transport=httpx.MockTransport(handler))
    client.delay_seconds = 0  # pas d'attente pendant les tests
    return client


def test_search_with_mock_transport(fixture_html):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text=fixture_html("search.html"))

    client = _client(handler)
    offers, total, urls = client.search("python", "Lyon", max_results=10)
    assert [o.offer_id for o in offers] == ["10000001", "10000002"]
    assert total == 3
    assert len(seen) == 1  # moins de 30 résultats : pas de page suivante
    assert "hellowork-mcp" in client._client.headers["User-Agent"]


def test_search_respects_max_results(fixture_html):
    client = _client(lambda r: httpx.Response(200, text=fixture_html("search.html")))
    offers, _, _ = client.search("python", max_results=1)
    assert len(offers) == 1


def test_search_http_error():
    client = _client(lambda r: httpx.Response(503, text="indisponible"))
    with pytest.raises(HelloworkHTTPError):
        client.search("python")


def test_get_offer(fixture_html):
    client = _client(lambda r: httpx.Response(200, text=fixture_html("offer.html")))
    offer = client.get_offer("10000001")
    assert offer.company == "Exemple Data"


def test_get_offer_gone():
    client = _client(lambda r: httpx.Response(410))
    with pytest.raises(OfferUnavailableError):
        client.get_offer("10000001")


def test_get_offer_redirected_to_search():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/emplois/" in request.url.path:
            return httpx.Response(301, headers={"Location": "https://www.hellowork.com/fr-fr/emploi.html"})
        return httpx.Response(200, text="<html></html>")

    client = _client(handler)
    with pytest.raises(OfferUnavailableError):
        client.get_offer("10000001")


@pytest.mark.live
def test_live_search_returns_offers():
    client = HelloworkClient(delay_seconds=1.0)
    try:
        offers, _, _ = client.search("développeur", "Lyon", max_results=5)
        assert offers, "aucune offre renvoyée par hellowork.com"
        offer = client.get_offer(offers[0].offer_id)
        assert offer.title
    finally:
        client.close()
