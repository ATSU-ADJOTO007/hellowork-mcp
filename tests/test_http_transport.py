"""Lance le serveur en Streamable HTTP dans un sous-processus et s'y connecte par URL."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def http_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("http")
    port = _free_port()
    path = "/mcp-secret-test"
    env = {
        **os.environ,
        "HELLOWORK_MCP_DATA_DIR": str(tmp_path / "data"),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "hellowork_mcp", "--transport", "http", "--port", str(port), "--path", path],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}{path}"
    deadline = time.monotonic() + 90  # démarrage lent possible sur les runners CI Windows
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail("le serveur HTTP s'est arrêté : " + proc.stderr.read().decode("utf-8", "replace"))
        try:
            if httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    else:
        proc.terminate()
        pytest.fail("le serveur HTTP n'a pas répondu sur /healthz en 90 secondes")
    try:
        yield url, port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


async def test_connect_by_url(http_server):
    url, port = http_server
    async with Client(url) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert {"search_offers", "analyze_offers", "prepare_application"} <= tools
        status = await client.call_tool("hellowork_status", {})
        data = json.loads(status.content[0].text)
        assert data["transport"] == "http"
        assert data["browser_tools_enabled"] is False
        login = await client.call_tool("hellowork_login", {})
        assert login.is_error and "mode HTTP" in login.content[0].text


def test_wrong_path_is_not_served(http_server):
    _, port = http_server
    response = httpx.post(f"http://127.0.0.1:{port}/mcp", json={}, timeout=5)
    assert response.status_code == 404
