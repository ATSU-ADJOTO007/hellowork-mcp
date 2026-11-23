from __future__ import annotations

import pytest

from hellowork_mcp.parsing import (
    OfferUnavailableError,
    StructureChangedError,
    offer_id_from_url,
    offer_url,
    parse_offer,
    parse_search_results,
)


def test_parse_search_results(fixture_html):
    offers, total = parse_search_results(fixture_html("search.html"))
    assert total == 3
    assert [o.offer_id for o in offers] == ["10000001", "10000002"]  # doublon supprimé
    first = offers[0]
    assert first.title == "Développeur Python Senior H/F"
    assert first.company == "Exemple Data"
    assert first.location == "Lyon - 69"
    assert first.contract == "CDI"
    assert "Télétravail partiel" in first.tags
    assert first.url == "https://www.hellowork.com/fr-fr/emplois/10000001.html"
    assert offers[1].url.endswith("/10000002.html")  # paramètres retirés


def test_parse_search_results_empty_page():
    offers, _ = parse_search_results("<html><body><p>Aucune offre ne correspond à votre recherche</p></body></html>")
    assert offers == []


def test_parse_search_results_structure_changed():
    with pytest.raises(StructureChangedError):
        parse_search_results("<html><body><div class='nouvelle-carte'>Offre</div></body></html>")


def test_parse_offer_json_ld(fixture_html):
    url = "https://www.hellowork.com/fr-fr/emplois/10000001.html"
    offer = parse_offer(fixture_html("offer.html"), url)
    assert offer.offer_id == "10000001"
    assert offer.title == "Développeur Python Senior H/F"
    assert offer.company == "Exemple Data"
    assert offer.location == "Lyon"
    assert offer.postal_code == "69000"
    assert offer.contract == "CDI"
    assert offer.employment_type == "Temps plein"
    assert offer.remote == "partial"
    assert offer.salary.min == 45000 and offer.salary.max == 55000
    assert offer.salary.annual_min() == 45000
    assert offer.salary.text == "45 000 - 55 000 € / an"
    assert "Django" in offer.description and "<b>" not in offer.description
    assert "5 ans d'expérience" in offer.description
    assert offer.skills == ["Python", "Django", "Docker", "PostgreSQL"]
    assert offer.direct_apply is True
    assert offer.external_apply_url is None


def test_parse_offer_external(fixture_html):
    offer = parse_offer(fixture_html("offer_external.html"), "https://www.hellowork.com/fr-fr/emplois/10000003.html")
    assert offer.contract == "Stage"
    assert offer.direct_apply is False
    assert offer.external_apply_url.startswith("https://marque-fictive.wd3.myworkdayjobs.com/")


def test_parse_offer_unavailable():
    html = "<html><body><h1>Cette offre n'est plus disponible</h1></body></html>"
    with pytest.raises(OfferUnavailableError):
        parse_offer(html, "https://www.hellowork.com/fr-fr/emplois/1.html")


def test_parse_offer_structure_changed():
    with pytest.raises(StructureChangedError):
        parse_offer("<html><body><p>rien</p></body></html>", "https://www.hellowork.com/fr-fr/emplois/1.html")


def test_offer_url_helpers():
    assert offer_id_from_url("https://www.hellowork.com/fr-fr/emplois/84561625.html?x=1") == "84561625"
    assert offer_id_from_url("https://example.com") is None
    assert offer_url("42") == "https://www.hellowork.com/fr-fr/emplois/42.html"
    with pytest.raises(ValueError):
        offer_url("../../etc")
