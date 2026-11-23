"""Extraction des données depuis le HTML de Hellowork.

Les sélecteurs ont été relevés sur hellowork.com en novembre 2026 :
- résultats : <li data-id-storage-item-id="..."> contenant des éléments data-cy
  (offerTitle, localisationCard, contractCard, contractTag)
- offre : bloc JSON-LD schema.org JobPosting, complété par le HTML si besoin

Si la structure change, les fonctions lèvent StructureChangedError avec un message explicite
au lieu de renvoyer des données vides silencieusement.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import HELLOWORK_BASE_URL
from .filters import strip_html
from .models import Offer, OfferSummary, Salary

OFFER_URL_RE = re.compile(r"/emplois/(\d+)\.html")

EMPLOYMENT_TYPES = {
    "FULL_TIME": "Temps plein",
    "PART_TIME": "Temps partiel",
    "CONTRACTOR": "Indépendant",
    "TEMPORARY": "Temporaire",
    "INTERN": "Stage",
    "VOLUNTEER": "Bénévolat",
    "PER_DIEM": "À la journée",
    "OTHER": "Autre",
}

KNOWN_CONTRACTS = [
    "CDI",
    "CDD",
    "Intérim",
    "Stage",
    "Alternance",
    "Indépendant",
    "Freelance",
    "Franchise",
    "Fonctionnaire",
    "Associé",
]


class StructureChangedError(RuntimeError):
    """La page ne contient plus les éléments attendus."""


class OfferUnavailableError(RuntimeError):
    """L'offre n'existe plus ou a expiré."""


def offer_id_from_url(url: str) -> str | None:
    match = OFFER_URL_RE.search(url or "")
    return match.group(1) if match else None


def offer_url(offer_id: str) -> str:
    if not str(offer_id).isdigit():
        raise ValueError(f"Identifiant d'offre invalide : {offer_id!r} (chiffres attendus)")
    return f"{HELLOWORK_BASE_URL}/fr-fr/emplois/{offer_id}.html"


def _text(node) -> str | None:
    if node is None:
        return None
    value = " ".join(node.get_text(" ", strip=True).split())
    return value or None


def parse_search_results(html: str) -> tuple[list[OfferSummary], int | None]:
    """Retourne les offres de la page et le nombre total annoncé (si présent)."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li[data-id-storage-item-id]")
    results: list[OfferSummary] = []
    for item in items:
        link = item.select_one('a[data-cy="offerTitle"]') or item.select_one('a[href*="/emplois/"]')
        if link is None:
            continue
        href = urljoin(HELLOWORK_BASE_URL, link.get("href", ""))
        offer_id = item.get("data-id-storage-item-id") or offer_id_from_url(href)
        if not offer_id or any(r.offer_id == str(offer_id) for r in results):
            continue
        title_attr = link.get("title") or ""
        lines = [p for p in link.get_text("\n", strip=True).split("\n") if p.strip()]
        title = lines[0] if lines else title_attr.split(" - ")[0]
        company = lines[1] if len(lines) > 1 else None
        hidden_company = item.select_one('input[name="company"]')
        if not company and hidden_company is not None:
            company = hidden_company.get("value")
        tags = [t for t in (_text(n) for n in item.select('[data-cy="contractTag"]')) if t]
        results.append(
            OfferSummary(
                offer_id=str(offer_id),
                title=title,
                company=company,
                location=_text(item.select_one('[data-cy="localisationCard"]')),
                contract=_text(item.select_one('[data-cy="contractCard"]')),
                tags=tags,
                url=href.split("?")[0],
            )
        )

    total = None
    total_text = soup.find(string=re.compile(r"\d[\d\s \xa0]*\s+offres?\b"))
    if total_text:
        digits = re.sub(r"\D", "", re.search(r"\d[\d\s \xa0]*", str(total_text)).group(0))
        total = int(digits) if digits else None

    if not results and not _looks_like_empty_search(soup):
        raise StructureChangedError(
            "Aucune carte d'offre trouvée (sélecteur li[data-id-storage-item-id]). "
            "La structure de la page de recherche Hellowork a probablement changé."
        )
    return results, total


def _looks_like_empty_search(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return any(
        marker in text
        for marker in ("0 offre", "aucune offre", "aucun résultat", "pas d'offre", "nous n'avons trouvé aucune")
    )


def _find_job_posting(soup: BeautifulSoup) -> dict | None:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text() or ""
        if "JobPosting" not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                return candidate
    return None


def _salary_from_ld(ld: dict) -> Salary | None:
    base = ld.get("baseSalary")
    if not isinstance(base, dict):
        return None
    value = base.get("value")
    currency = base.get("currency") or ld.get("salaryCurrency")
    if isinstance(value, dict):
        return Salary(
            min=_num(value.get("minValue", value.get("value"))),
            max=_num(value.get("maxValue", value.get("value"))),
            currency=currency,
            period=value.get("unitText"),
        )
    if value is not None:
        amount = _num(value)
        return Salary(min=amount, max=amount, currency=currency)
    return None


def _num(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _contract_from_html(soup: BeautifulSoup, title: str) -> str | None:
    head = soup.title.get_text(" ", strip=True) if soup.title else ""
    for contract in KNOWN_CONTRACTS:
        if re.search(rf"\b{re.escape(contract)}\b", head, re.I):
            return contract
    for contract in KNOWN_CONTRACTS:
        if re.search(rf"\b{re.escape(contract)}\b", title, re.I):
            return contract
    return None


def _external_apply_url(soup: BeautifulSoup) -> str | None:
    """Repère un lien de candidature qui sort de hellowork.com."""
    selectors = [
        "#postuler a[href]",
        'a[data-cy*="apply" i][href]',
        'a[data-cy*="Apply"][href]',
        "a[href][target=_blank]",
    ]
    for selector in selectors:
        for link in soup.select(selector):
            href = link.get("href", "")
            label = (link.get_text(" ", strip=True) or "").lower()
            if not href.startswith("http"):
                continue
            host = urlparse(href).hostname or ""
            if host.endswith("hellowork.com"):
                continue
            if selector.startswith("#postuler") or "postuler" in label or "candidat" in label or "apply" in selector:
                return href
    return None


def parse_offer(html: str, url: str) -> Offer:
    soup = BeautifulSoup(html, "html.parser")
    offer_id = offer_id_from_url(url) or ""
    page_text = soup.get_text(" ", strip=True).lower()
    if not soup.select_one('[data-cy="jobTitle"]') and any(
        marker in page_text for marker in ("offre n'est plus disponible", "offre a expiré", "page introuvable", "erreur 404")
    ):
        raise OfferUnavailableError(f"L'offre {offer_id} n'est plus disponible ({url}).")

    ld = _find_job_posting(soup)
    if ld is None:
        title = _text(soup.select_one('[data-cy="jobTitle"]'))
        if not title:
            raise StructureChangedError(
                f"Ni JSON-LD JobPosting ni data-cy=jobTitle sur {url}. La structure de la page offre a changé "
                "ou la page n'est pas une offre."
            )
        return Offer(
            offer_id=offer_id,
            url=url,
            title=title,
            contract=_contract_from_html(soup, title),
            description=_text(soup.select_one("main")) or "",
            external_apply_url=_external_apply_url(soup),
        )

    org = ld.get("hiringOrganization") or {}
    location = ld.get("jobLocation") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    address = location.get("address", {}) if isinstance(location, dict) else {}
    title = str(ld.get("title") or _text(soup.select_one('[data-cy="jobTitle"]')) or "").strip()
    employment = ld.get("employmentType")
    if isinstance(employment, list):
        employment = employment[0] if employment else None
    skills = ld.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in re.split(r"[,;\n]", skills) if s.strip()]

    remote_flag = ld.get("jobLocationType")
    remote = None
    if remote_flag == "TELECOMMUTE":
        tag_text = page_text
        remote = "full" if "télétravail complet" in tag_text or "full remote" in tag_text else "partial"
    elif "télétravail partiel" in page_text:
        remote = "partial"
    elif "télétravail complet" in page_text:
        remote = "full"

    salary = _salary_from_ld(ld)
    salary_btn = _text(soup.select_one('[data-cy="salary-tag-button"]'))
    if salary_btn:
        salary = salary or Salary()
        salary.text = salary_btn

    description = strip_html(str(ld.get("description") or ""))
    for extra in ("qualifications", "experienceRequirements", "educationRequirements"):
        value = ld.get(extra)
        if isinstance(value, str) and value.strip():
            description += "\n" + strip_html(value)

    identifier = ld.get("identifier")
    if not offer_id and isinstance(identifier, dict) and identifier.get("value"):
        offer_id = str(identifier["value"])

    return Offer(
        offer_id=offer_id,
        url=url,
        title=title,
        company=org.get("name") if isinstance(org, dict) else None,
        location=address.get("addressLocality"),
        region=address.get("addressRegion"),
        postal_code=address.get("postalCode"),
        contract=_contract_from_html(soup, title),
        employment_type=EMPLOYMENT_TYPES.get(str(employment), employment) if employment else None,
        remote=remote,
        salary=salary,
        date_posted=ld.get("datePosted"),
        valid_through=ld.get("validThrough"),
        description=description.strip(),
        skills=[str(s) for s in skills],
        direct_apply=ld.get("directApply") if isinstance(ld.get("directApply"), bool) else None,
        external_apply_url=_external_apply_url(soup),
    )
