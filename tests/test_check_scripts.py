from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts import check_dashes

EM = chr(0x2014)
EN = chr(0x2013)

ROOT = Path(__file__).resolve().parents[1]


def test_check_dashes_detects(tmp_path, capsys):
    bad = tmp_path / "doc.md"
    bad.write_text(f"Ligne correcte - ok\nLigne fautive {EM} ici\nEt {EN} là\n", encoding="utf-8")
    assert check_dashes.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "doc.md:2:15: tiret cadratin (U+2014)" in out
    assert "doc.md:3:4: tiret demi-cadratin (U+2013)" in out
    assert bad.read_text(encoding="utf-8").count(EM) == 1  # fichier non modifié


def test_check_dashes_clean(tmp_path):
    (tmp_path / "ok.md").write_text("Texte - propre\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG" + EM.encode())  # extension non contrôlée
    assert check_dashes.main([str(tmp_path)]) == 0


def test_check_dashes_skips_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "x.md").write_text(EM, encoding="utf-8")
    assert check_dashes.main([str(tmp_path)]) == 0


def test_repository_has_no_long_dashes():
    assert check_dashes.main([str(ROOT)]) == 0


def test_cli_entrypoint_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_dashes.py"), str(ROOT / "README.md")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
