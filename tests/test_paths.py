from __future__ import annotations

from pathlib import Path

from hellowork_mcp.paths import data_dir, default_data_dir, exports_dir


def test_windows_localappdata():
    path = default_data_dir("win32", {"LOCALAPPDATA": r"C:\Users\exemple\AppData\Local"}, Path("/home/x"))
    assert path == Path(r"C:\Users\exemple\AppData\Local") / "hellowork-mcp"


def test_windows_userprofile_fallback():
    path = default_data_dir("win32", {"USERPROFILE": r"C:\Users\exemple"}, Path("/home/x"))
    assert path == Path(r"C:\Users\exemple") / "AppData" / "Local" / "hellowork-mcp"


def test_macos():
    assert default_data_dir("darwin", {}, Path("/Users/exemple")) == Path(
        "/Users/exemple/Library/Application Support/hellowork-mcp"
    )


def test_linux_xdg_and_default():
    home = Path("/home/exemple")
    assert default_data_dir("linux", {"XDG_DATA_HOME": "/data/xdg"}, home) == Path("/data/xdg/hellowork-mcp")
    assert default_data_dir("linux", {"XDG_DATA_HOME": "relatif"}, home) == home / ".local/share/hellowork-mcp"
    assert default_data_dir("linux", {}, home) == home / ".local/share/hellowork-mcp"


def test_env_override_is_created(isolated_data_dir):
    assert data_dir() == isolated_data_dir
    assert isolated_data_dir.is_dir()
    assert exports_dir() == isolated_data_dir / "exports"
