"""Tests des outils MCP via le client en mémoire du SDK (aucun accès réseau)."""

from __future__ import annotations

import json

import httpx
import pytest
from mcp import Client

from hellowork_mcp import search, server
from hellowork_mcp.history import History
from hellowork_mcp.redirects import RedirectRegistry

EXPECTED_TOOLS = {
    "hellowork_status",
    "get_config",
    "update_config",
    "hellowork_login",
    "check_session",
    "clear_session",
    "search_offers",
    "get_offer",
    "analyze_offers",
    "mark_offer",
    "prepare_application",
    "submit_application",
    "record_external_redirect",
    "open_external_redirect",
    "list_redirects",
    "classify_external_url",
    "get_history",
    "list_tracked_offers",
    "export_data",
}


@pytest.fixture
def fake_site(monkeypatch, fixture_html):
    """Remplace hellowork.com par les pages fictives du dossier fixtures."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/recherche.html"):
            return httpx.Response(200, text=fixture_html("search.html"))
        if path.endswith("/10000003.html"):
            return httpx.Response(200, text=fixture_html("offer_external.html"))
        if path.endswith("/10000404.html"):
            return httpx.Response(404)
        if "/emplois/" in path:
            return httpx.Response(200, text=fixture_html("offer.html"))
        return httpx.Response(404)

    original = search.HelloworkClient.__init__

    def init(self, delay_seconds=1.5, timeout=20.0, transport=None):
        original(self, delay_seconds=delay_seconds, timeout=timeout, transport=httpx.MockTransport(handler))
        self.delay_seconds = 0

    monkeypatch.setattr(search.HelloworkClient, "__init__", init)


async def call(name: str, args: dict | None = None):
    async with Client(server.mcp) as client:
        result = await client.call_tool(name, args or {})
    text = result.content[0].text if result.content else ""
    if result.is_error:
        return None, text
    return json.loads(text), None


async def test_tools_are_listed_with_descriptions():
    async with Client(server.mcp) as client:
        tools = (await client.list_tools()).tools
    names = {t.name for t in tools}
    assert names >= EXPECTED_TOOLS
    for tool in tools:
        assert tool.description and len(tool.description) > 20, tool.name
        assert tool.input_schema["type"] == "object"


async def test_status_and_config_roundtrip():
    data, err = await call("hellowork_status")
    assert err is None and data["dry_run"] is True
    data, err = await call("update_config", {"changes": {"job_titles": ["Développeur Python"], "locations": ["Lyon"]}})
    assert err is None and data["config"]["job_titles"] == ["Développeur Python"]
    data, err = await call("get_config")
    assert data["config"]["locations"] == ["Lyon"]
    _, err = await call("update_config", {"changes": {"min_score": 300}})
    assert err and "refusée" in err


async def test_search_and_analyze(fake_site):
    await call("update_config", {"changes": {"job_titles": ["Développeur Python"], "locations": ["Lyon"], "contract_types": ["CDI"]}})
    data, err = await call("search_offers", {})
    assert err is None
    assert data["count"] == 2
    assert {o["offer_id"] for o in data["offers"]} == {"10000001", "10000002"}
    assert History().offer("10000001")["status"] == "detected"

    data, err = await call("analyze_offers", {"offer_ids": ["10000001", "10000404", "abc"]})
    assert err is None
    first = data["results"][0]["analysis"]
    assert first["score"] == 100 and first["decision"] == "relevant"
    assert data["results"][1]["available"] is False
    assert "invalide" in data["results"][2]["error"]


async def test_search_requires_criteria():
    _, err = await call("search_offers", {})
    assert err and "Aucun critère" in err


async def test_application_flow_dry_run(fake_site):
    data, err = await call("prepare_application", {"offer_id": "10000001", "message": "Bonjour"})
    assert err is None
    assert data["allowed"] and data["human_validation_required"] and data["application_sent"] is False
    token = data["confirmation_token"]

    _, err = await call(
        "submit_application", {"offer_id": "10000001", "confirmation_token": token, "user_confirmed": False, "message": "Bonjour"}
    )
    assert err and "accord explicite" in err

    data, err = await call(
        "submit_application", {"offer_id": "10000001", "confirmation_token": token, "user_confirmed": True, "message": "Bonjour"}
    )
    assert err is None
    assert data["application_sent"] is False and data["status"] == "simulated"
    assert History().offer("10000001")["status"] == "simulated"

    _, err = await call(
        "submit_application", {"offer_id": "10000001", "confirmation_token": token, "user_confirmed": True, "message": "Bonjour"}
    )
    assert err and "Jeton" in err  # jeton déjà consommé


async def test_prepare_blocks_external_offer(fake_site):
    data, err = await call("prepare_application", {"offer_id": "10000003"})
    assert err is None
    assert data["allowed"] is False
    assert "confirmation_token" not in data


async def test_external_redirect_flow(fake_site, monkeypatch):
    data, err = await call("record_external_redirect", {"offer_id": "10000003"})
    assert err is None and data["recorded"] and data["entry"]["category"] == "ats"
    assert data["external_link_opened"] is False
    data, _ = await call("record_external_redirect", {"offer_id": "10000003"})
    assert data["already_known"] is True
    assert len(RedirectRegistry().all()) == 1

    opened = []
    monkeypatch.setattr(server.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    url = RedirectRegistry().all()[0]["external_url"]
    data, err = await call("open_external_redirect", {"external_url": url})
    assert err is None and data["external_link_opened"] is True
    data, _ = await call("open_external_redirect", {"external_url": url})
    assert data["external_link_opened"] is False  # pas de seconde ouverture
    assert len(opened) == 1

    _, err = await call("open_external_redirect", {"external_url": "https://inconnu.example/x"})
    assert err and "inconnue" in err
    _, err = await call("open_external_redirect", {"external_url": "file:///etc/passwd"})
    assert err


async def test_history_mark_and_export(fake_site):
    data, err = await call("mark_offer", {"offer_id": "10000002", "status": "rejected", "note": "trop loin", "title": "Data Engineer H/F"})
    assert err is None and data["event"]["event"] == "rejected"
    data, _ = await call("get_history", {"event": "rejected"})
    assert data["count"] == 1
    _, err = await call("get_history", {"event": "bidon"})
    assert err
    data, _ = await call("list_tracked_offers", {"status": "rejected"})
    assert data["offers"][0]["offer_id"] == "10000002"
    for dataset in ("offers", "events", "redirects"):
        for fmt in ("csv", "markdown"):
            data, err = await call("export_data", {"dataset": dataset, "format": fmt})
            assert err is None and data["path"].endswith(".csv" if fmt == "csv" else ".md")


async def test_parameter_validation():
    _, err = await call("analyze_offers", {"offer_ids": []})
    assert err
    _, err = await call("search_offers", {"keywords": "python", "max_results": 1000})
    assert err
    _, err = await call("mark_offer", {"offer_id": "1", "status": "applied"})
    assert err
    data, err = await call("classify_external_url", {"url": "https://jobs.lever.co/a/1"})
    assert data["category"] == "ats"


async def test_every_tool_has_directory_annotations():
    """Exigence de l'annuaire Anthropic : un titre et readOnlyHint ou destructiveHint pour chaque outil."""
    async with Client(server.mcp) as client:
        tools = (await client.list_tools()).tools
    for tool in tools:
        ann = tool.annotations
        assert ann is not None and ann.title, tool.name
        assert ann.read_only_hint is not None and ann.destructive_hint is not None, tool.name
        assert len(tool.name) <= 64
        if ann.read_only_hint:
            assert ann.destructive_hint is False, tool.name
    by_name = {t.name: t.annotations for t in tools}
    assert by_name["submit_application"].destructive_hint is True
    assert by_name["clear_session"].destructive_hint is True
    assert by_name["get_offer"].read_only_hint is True


def test_server_icon_is_declared():
    icons = server._icons()
    assert icons[0].src.startswith("data:image/png;base64,")
    assert icons[1].mime_type == "image/svg+xml"


@pytest.fixture
def http_mode(monkeypatch):
    monkeypatch.setattr(server, "_http_mode", True)
    monkeypatch.setattr(server, "_browser_allowed", False)


async def test_http_mode_blocks_browser_tools(http_mode):
    for name, args in (
        ("hellowork_login", {}),
        ("check_session", {}),
        ("clear_session", {}),
        ("open_external_redirect", {"external_url": "https://jobs.lever.co/a/1"}),
    ):
        _, err = await call(name, args)
        assert err and "mode HTTP" in err, name
    data, _ = await call("hellowork_status")
    assert data["transport"] == "http" and data["browser_tools_enabled"] is False


async def test_http_mode_submit_only_simulates(http_mode, fake_site):
    await call("update_config", {"changes": {"dry_run": False}})
    data, _ = await call("prepare_application", {"offer_id": "10000001"})
    data, err = await call(
        "submit_application",
        {"offer_id": "10000001", "confirmation_token": data["confirmation_token"], "user_confirmed": True},
    )
    assert err is None and data["application_sent"] is False and data["status"] == "simulated"


async def test_http_mode_export_returns_content(http_mode):
    await call("mark_offer", {"offer_id": "10000002", "status": "selected", "title": "Data Engineer H/F"})
    data, _ = await call("export_data", {"dataset": "offers", "format": "csv"})
    assert data["content"].startswith("offer_id;title")
    assert "Data Engineer H/F" in data["content"]
