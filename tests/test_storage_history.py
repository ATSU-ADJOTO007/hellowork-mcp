from __future__ import annotations

import json
import threading
from datetime import date

import pytest

from hellowork_mcp.history import History
from hellowork_mcp.storage import read_json, update_json, write_json


def test_atomic_write_and_read(tmp_path):
    path = tmp_path / "a" / "data.json"
    write_json(path, {"é": [1, 2]})
    assert read_json(path, dict) == {"é": [1, 2]}
    assert not list(path.parent.glob("*.tmp"))


def test_corrupted_file_is_preserved(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{ pas du json", encoding="utf-8")
    assert read_json(path, list) == []
    backups = list(tmp_path.glob("history.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{ pas du json"


def test_concurrent_updates_are_serialized(tmp_path):
    path = tmp_path / "counter.json"

    def bump():
        for _ in range(50):
            update_json(path, lambda: {"n": 0}, lambda d: d.__setitem__("n", d["n"] + 1))

    threads = [threading.Thread(target=bump) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert json.loads(path.read_text(encoding="utf-8"))["n"] == 200


def test_history_status_and_duplicates():
    history = History()
    history.record("detected", "1", title="Poste A", company="Exemple")
    assert not history.is_processed("1")
    history.record("analyzed", "1", score=72)
    assert history.offer("1")["status"] == "detected"  # l'analyse ne remplace pas un statut existant
    assert history.offer("1")["score"] == 72
    history.record("selected", "1")
    assert history.is_processed("1")
    assert not history.has_applied("1")
    history.record("applied", "1")
    assert history.has_applied("1")
    history.record("error", "1", details="timeout")
    assert history.offer("1")["status"] == "applied"  # une erreur n'efface pas l'envoi


def test_history_daily_count_and_filters():
    history = History()
    history.record("applied", "1")
    history.record("applied", "2")
    history.record("simulated", "3")
    assert history.applications_on(date.today()) == 2
    assert history.applications_on(date(2000, 1, 1)) == 0
    assert [e["offer_id"] for e in history.events(event="applied")] == ["2", "1"]
    assert len(history.offers(status="simulated")) == 1


def test_history_rejects_unknown_event():
    with pytest.raises(ValueError):
        History().record("bidon", "1")
