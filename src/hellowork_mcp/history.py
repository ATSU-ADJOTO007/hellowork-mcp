"""Historique des actions et statut courant de chaque offre."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from .paths import data_dir
from .storage import read_json, update_json

EventType = Literal[
    "detected",
    "analyzed",
    "rejected",
    "selected",
    "simulated",
    "applied",
    "external_redirect",
    "error",
    "manual_action_required",
]

EVENT_LABELS = {
    "detected": "offre détectée",
    "analyzed": "offre analysée",
    "rejected": "offre rejetée",
    "selected": "offre retenue",
    "simulated": "simulation",
    "applied": "candidature envoyée",
    "external_redirect": "redirection externe",
    "error": "erreur",
    "manual_action_required": "action manuelle nécessaire",
}

# Statuts qui signifient qu'une offre a déjà été traitée par l'utilisateur ou l'agent.
PROCESSED_STATUSES = {"rejected", "selected", "simulated", "applied", "external_redirect"}

MAX_EVENTS = 20_000


def _empty() -> dict[str, Any]:
    return {"offers": {}, "events": []}


class History:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "history.json"

    def _read(self) -> dict[str, Any]:
        data = read_json(self.path, _empty)
        if not isinstance(data, dict):
            data = _empty()
        data.setdefault("offers", {})
        data.setdefault("events", [])
        return data

    def record(
        self,
        event: EventType,
        offer_id: str | None = None,
        *,
        title: str | None = None,
        company: str | None = None,
        url: str | None = None,
        score: int | None = None,
        details: str | None = None,
    ) -> dict[str, Any]:
        if event not in EVENT_LABELS:
            raise ValueError(f"Type d'événement inconnu : {event}")
        now = datetime.now().isoformat(timespec="seconds")
        entry = {
            "date": now,
            "event": event,
            "label": EVENT_LABELS[event],
            "offer_id": offer_id,
            "title": title,
            "company": company,
            "url": url,
            "score": score,
            "details": details,
        }

        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            data.setdefault("offers", {})
            data.setdefault("events", [])
            data["events"].append(entry)
            if len(data["events"]) > MAX_EVENTS:
                data["events"] = data["events"][-MAX_EVENTS:]
            if offer_id:
                offer = data["offers"].setdefault(offer_id, {"offer_id": offer_id, "first_seen": now})
                for key, value in (("title", title), ("company", company), ("url", url), ("score", score)):
                    if value is not None:
                        offer[key] = value
                # Les événements informatifs ne remplacent pas un statut de traitement.
                if event not in {"error", "detected", "analyzed"} or "status" not in offer:
                    offer["status"] = event
                    offer["status_label"] = EVENT_LABELS[event]
                offer["updated"] = now
            return entry

        return update_json(self.path, _empty, mutate)

    def offer(self, offer_id: str) -> dict[str, Any] | None:
        return self._read()["offers"].get(offer_id)

    def is_processed(self, offer_id: str) -> bool:
        offer = self.offer(offer_id)
        return bool(offer and offer.get("status") in PROCESSED_STATUSES)

    def has_applied(self, offer_id: str) -> bool:
        offer = self.offer(offer_id)
        if offer and offer.get("status") == "applied":
            return True
        return any(e["event"] == "applied" and e.get("offer_id") == offer_id for e in self._read()["events"])

    def applications_on(self, day: date | None = None) -> int:
        prefix = (day or date.today()).isoformat()
        return sum(1 for e in self._read()["events"] if e["event"] == "applied" and e["date"].startswith(prefix))

    def offers(self, status: str | None = None) -> list[dict[str, Any]]:
        items = list(self._read()["offers"].values())
        if status:
            items = [o for o in items if o.get("status") == status]
        return sorted(items, key=lambda o: o.get("updated", ""), reverse=True)

    def events(self, limit: int = 50, event: str | None = None, offer_id: str | None = None) -> list[dict[str, Any]]:
        items = self._read()["events"]
        if event:
            items = [e for e in items if e["event"] == event]
        if offer_id:
            items = [e for e in items if e.get("offer_id") == offer_id]
        return list(reversed(items[-limit:])) if limit > 0 else list(reversed(items))
