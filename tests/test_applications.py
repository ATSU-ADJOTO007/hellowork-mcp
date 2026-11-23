from __future__ import annotations

from hellowork_mcp import applications
from hellowork_mcp.applications import ConfirmationStore, run_guards
from hellowork_mcp.config import Config
from hellowork_mcp.history import History
from hellowork_mcp.scoring import score_offer
from tests.test_scoring_filters import make_offer


def checks(report) -> dict[str, bool]:
    return {c["check"]: c["ok"] for c in report.checks}


def test_guards_allow_good_offer():
    offer = make_offer()
    config = Config(min_score=60)
    report = run_guards(offer, score_offer(offer, config), config, History())
    assert report.allowed
    assert all(checks(report).values())


def test_guards_block_duplicates_limit_and_score():
    history = History()
    offer = make_offer()
    history.record("applied", offer.offer_id)
    history.record("applied", "999")
    config = Config(min_score=100, max_applications_per_day=2, excluded_keywords=["docker"])
    report = run_guards(offer, score_offer(offer, config), config, history)
    result = checks(report)
    assert not report.allowed
    assert result["doublon"] is False
    assert result["limite_quotidienne"] is False
    assert result["score_minimum"] is False
    assert result["mots_cles_interdits"] is False


def test_guards_block_external_offers():
    offer = make_offer(direct_apply=False, external_apply_url="https://jobs.lever.co/a/1")
    config = Config(min_score=0)
    report = run_guards(offer, score_offer(offer, config), config, History())
    assert checks(report)["candidature_hellowork"] is False


def test_confirmation_token_single_use_and_bound_to_message():
    store = ConfirmationStore()
    token, ttl = store.issue("1", "Bonjour")
    assert ttl == 900
    assert store.consume(token, "1", "Bonjour modifié")[0] is False
    assert store.consume(token, "2", "Bonjour")[0] is False
    assert store.consume(token, "1", "Bonjour")[0] is True
    assert store.consume(token, "1", "Bonjour")[0] is False  # usage unique


def test_confirmation_token_expires(monkeypatch):
    store = ConfirmationStore()
    token, _ = store.issue("1", None)
    real = applications.time.monotonic
    monkeypatch.setattr(applications.time, "monotonic", lambda: real() + 10_000)
    ok, reason = store.consume(token, "1", None)
    assert not ok and "expiré" in reason
