from __future__ import annotations

import json

import pytest

from hellowork_mcp import setup_clients


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "Claude" / "claude_desktop_config.json"
    monkeypatch.setenv(setup_clients.ENV_CONFIG, str(path))
    return path


def test_creates_config_when_missing(config_file):
    report = setup_clients.configure_claude_desktop("C:/outils/hellowork-mcp.exe")
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data == {"mcpServers": {"hellowork": {"command": "C:/outils/hellowork-mcp.exe"}}}
    assert report["backup"] is None and report["replaced_existing_entry"] is False


def test_merges_with_existing_servers_and_backs_up(config_file):
    config_file.parent.mkdir(parents=True)
    existing = {"mcpServers": {"autre": {"command": "autre.exe", "args": ["-x"]}}, "theme": "dark"}
    config_file.write_text(json.dumps(existing), encoding="utf-8")
    report = setup_clients.configure_claude_desktop("/opt/hellowork-mcp")
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["mcpServers"]["autre"] == {"command": "autre.exe", "args": ["-x"]}
    assert data["mcpServers"]["hellowork"] == {"command": "/opt/hellowork-mcp"}
    assert data["theme"] == "dark"
    with open(report["backup"], encoding="utf-8") as fh:
        assert json.load(fh) == existing


def test_replaces_previous_entry(config_file):
    setup_clients.configure_claude_desktop("ancien")
    report = setup_clients.configure_claude_desktop("nouveau")
    assert report["replaced_existing_entry"] is True
    assert json.loads(config_file.read_text(encoding="utf-8"))["mcpServers"]["hellowork"]["command"] == "nouveau"


def test_invalid_json_is_not_overwritten(config_file):
    config_file.parent.mkdir(parents=True)
    config_file.write_text("{ cassé", encoding="utf-8")
    with pytest.raises(ValueError):
        setup_clients.configure_claude_desktop("x")
    assert config_file.read_text(encoding="utf-8") == "{ cassé"


def test_cli_setup_claude(config_file, monkeypatch, capsys):
    from hellowork_mcp.__main__ import main

    monkeypatch.setattr(setup_clients, "executable_path", lambda: "C:/x/hellowork-mcp.exe")
    monkeypatch.setattr(setup_clients, "configure_claude_code", lambda command=None: None)
    assert main(["--setup-claude"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["clients"][0]["client"] == "Claude Desktop"
    assert json.loads(config_file.read_text(encoding="utf-8"))["mcpServers"]["hellowork"]["command"] == "C:/x/hellowork-mcp.exe"
