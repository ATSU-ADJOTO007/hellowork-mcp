from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch) -> Path:
    """Chaque test utilise un dossier de données temporaire : aucune donnée réelle n'est lue ni écrite."""
    directory = tmp_path / "data"
    monkeypatch.setenv("HELLOWORK_MCP_DATA_DIR", str(directory))
    return directory


@pytest.fixture
def fixture_html():
    def load(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return load


def pytest_collection_modifyitems(config, items):
    if os.environ.get("HELLOWORK_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="test réseau réel : définir HELLOWORK_LIVE_TESTS=1 pour l'exécuter")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
