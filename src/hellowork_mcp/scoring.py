"""Score de correspondance sur 100 entre une offre et la configuration.

Le score est déterministe et explicable. L'agent IA peut l'utiliser tel quel ou l'ajuster
après lecture de la description complète.

Barème (total 100) :
- intitulé du poste : 25
- mots-clés obligatoires : 25
- type de contrat : 15
- localisation : 15
- salaire : 10
- télétravail : 10

Un critère non configuré rapporte la totalité de ses points. Une information absente de l'offre
rapporte la moitié des points et produit un point de vigilance. Un mot-clé interdit ramène le score à 0.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .config import Config
from .filters import contains_keyword, match_keywords, normalize
from .models import Offer

Decision = Literal["relevant", "review", "not_relevant", "already_processed"]

DECISION_LABELS = {
    "relevant": "offre pertinente",
    "review": "offre à examiner",
    "not_relevant": "offre non pertinente",
    "already_processed": "offre déjà traitée",
}

WEIGHTS = {"title": 25, "keywords": 25, "contract": 15, "location": 15, "salary": 10, "remote": 10}


class ScoreResult(BaseModel):
    offer_id: str
    score: int = Field(ge=0, le=100)
    decision: Decision
    decision_label: str
    justification: str
    satisfied: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    breakdown: dict[str, float] = Field(default_factory=dict)
    excluded_keywords_found: list[str] = Field(default_factory=list)


def _offer_text(offer: Offer) -> str:
    return "\n".join([offer.title, offer.company or "", offer.description, " ".join(offer.skills)])


def score_offer(offer: Offer, config: Config, already_processed: bool = False) -> ScoreResult:
    satisfied: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    points: dict[str, float] = {}
    text = _offer_text(offer)

    # Intitulé
    w = WEIGHTS["title"]
    if not config.job_titles:
        points["title"] = w
    else:
        best = 0.0
        best_title = None
        title_words = set(normalize(offer.title).replace("/", " ").replace("-", " ").split())
        for wanted in config.job_titles:
            if contains_keyword(offer.title, wanted):
                best, best_title = 1.0, wanted
                break
            wanted_words = [x for x in normalize(wanted).split() if len(x) > 2]
            if wanted_words:
                ratio = sum(1 for x in wanted_words if x in title_words) / len(wanted_words)
                if ratio > best:
                    best, best_title = ratio, wanted
        points["title"] = round(w * best, 1)
        if best == 1.0:
            satisfied.append(f"Intitulé correspondant à « {best_title} »")
        elif best > 0:
            satisfied.append(f"Intitulé proche de « {best_title} » ({int(best * 100)} % des mots)")
        else:
            missing.append("Intitulé sans rapport avec les postes recherchés")

    # Mots-clés obligatoires
    w = WEIGHTS["keywords"]
    if not config.required_keywords:
        points["keywords"] = w
    else:
        found, absent = match_keywords(text, config.required_keywords)
        points["keywords"] = round(w * len(found) / len(config.required_keywords), 1)
        if found:
            satisfied.append("Mots-clés présents : " + ", ".join(found))
        if absent:
            missing.append("Mots-clés absents : " + ", ".join(absent))

    # Contrat
    w = WEIGHTS["contract"]
    if not config.contract_types:
        points["contract"] = w
    elif not offer.contract:
        points["contract"] = w / 2
        warnings.append("Type de contrat non identifié")
    elif any(normalize(c) == normalize(offer.contract) for c in config.contract_types):
        points["contract"] = w
        satisfied.append(f"Contrat {offer.contract}")
    else:
        points["contract"] = 0
        missing.append(f"Contrat {offer.contract} hors critères ({', '.join(config.contract_types)})")

    # Localisation
    w = WEIGHTS["location"]
    if not config.locations:
        points["location"] = w
    else:
        place = " ".join(filter(None, [offer.location, offer.region, offer.postal_code]))
        if not place:
            points["location"] = w / 2
            warnings.append("Localisation non précisée")
        else:
            hit = next(
                (
                    loc
                    for loc in config.locations
                    if contains_keyword(place, loc)
                    or (loc.isdigit() and offer.postal_code and offer.postal_code.startswith(loc))
                ),
                None,
            )
            if hit or offer.remote == "full":
                points["location"] = w
                satisfied.append(f"Localisation {place}" + ("" if hit else " (télétravail complet)"))
            else:
                points["location"] = 0
                missing.append(f"Localisation {place} hors zones recherchées")

    # Salaire
    w = WEIGHTS["salary"]
    annual = offer.salary.annual_min() if offer.salary else None
    if config.min_salary is None:
        points["salary"] = w
    elif annual is None:
        points["salary"] = w / 2
        warnings.append("Salaire non communiqué")
    elif annual >= config.min_salary:
        points["salary"] = w
        satisfied.append(f"Salaire estimé {int(annual)} €/an, au moins {config.min_salary} €")
    else:
        points["salary"] = 0
        missing.append(f"Salaire estimé {int(annual)} €/an, sous le minimum de {config.min_salary} €")

    # Télétravail
    w = WEIGHTS["remote"]
    pref = config.remote_preference
    if pref == "any":
        points["remote"] = w
    elif offer.remote is None:
        points["remote"] = w / 2
        warnings.append("Politique de télétravail non précisée")
    else:
        ok = {
            "remote": offer.remote == "full",
            "hybrid": offer.remote in {"partial", "full"},
            "onsite": offer.remote in {"none", "partial"},
        }[pref]
        points["remote"] = w if ok else 0
        (satisfied if ok else missing).append(f"Télétravail : {offer.remote} (préférence {pref})")

    score = int(round(sum(points.values())))

    excluded_found, _ = match_keywords(text, config.excluded_keywords)
    if excluded_found:
        score = 0
        missing.append("Mots-clés interdits présents : " + ", ".join(excluded_found))

    if offer.external_apply_url or offer.direct_apply is False:
        warnings.append("Candidature sur un site externe")
    if not offer.description:
        warnings.append("Description vide ou non extraite")
    if not offer.available:
        warnings.append("Offre indisponible")
        score = 0

    if already_processed:
        decision: Decision = "already_processed"
    elif excluded_found or score < config.thresholds.review:
        decision = "not_relevant"
    elif score >= config.thresholds.relevant:
        decision = "relevant"
    else:
        decision = "review"

    justification = (
        f"Score {score}/100 ({DECISION_LABELS[decision]}). "
        f"{len(satisfied)} critère(s) satisfait(s), {len(missing)} manquant(s), {len(warnings)} point(s) de vigilance. "
        f"Seuils : pertinente à partir de {config.thresholds.relevant}, à examiner à partir de {config.thresholds.review}."
    )
    return ScoreResult(
        offer_id=offer.offer_id,
        score=max(0, min(100, score)),
        decision=decision,
        decision_label=DECISION_LABELS[decision],
        justification=justification,
        satisfied=satisfied,
        missing=missing,
        warnings=warnings,
        breakdown=points,
        excluded_keywords_found=excluded_found,
    )
