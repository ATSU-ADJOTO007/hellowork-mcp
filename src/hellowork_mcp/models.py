"""Modèles de données partagés."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Salary(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None
    period: str | None = Field(default=None, description="YEAR, MONTH, DAY, HOUR")
    text: str | None = None

    def annual_min(self) -> float | None:
        """Salaire minimum ramené à l'année (estimation pour la comparaison avec la config)."""
        value = self.min if self.min is not None else self.max
        if value is None:
            return None
        factor = {"YEAR": 1, "MONTH": 12, "WEEK": 52, "DAY": 218, "HOUR": 1607}.get((self.period or "YEAR").upper(), 1)
        return value * factor


class OfferSummary(BaseModel):
    """Offre telle qu'affichée dans une page de résultats."""

    offer_id: str
    title: str
    company: str | None = None
    location: str | None = None
    contract: str | None = None
    tags: list[str] = Field(default_factory=list)
    url: str
    already_processed: bool = False
    status: str | None = None


class Offer(BaseModel):
    """Offre détaillée (page de l'offre)."""

    offer_id: str
    url: str
    title: str
    company: str | None = None
    location: str | None = None
    region: str | None = None
    postal_code: str | None = None
    contract: str | None = None
    employment_type: str | None = None
    remote: str | None = Field(default=None, description="full, partial, none ou None si inconnu")
    salary: Salary | None = None
    date_posted: str | None = None
    valid_through: str | None = None
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    direct_apply: bool | None = None
    external_apply_url: str | None = None
    available: bool = True
