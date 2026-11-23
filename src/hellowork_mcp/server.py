"""Serveur MCP Hellowork : déclaration des outils."""

from __future__ import annotations

import base64
import logging
import webbrowser
from importlib import resources
from typing import Annotated, Any, Literal

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import Icon
from pydantic import Field

from . import __version__
from .applications import ConfirmationStore, run_guards
from .browser import BrowserSession, BrowserUnavailableError
from .config import Config, ConfigError, load_config, update_config
from .exports import (
    EVENT_COLUMNS,
    HISTORY_COLUMNS,
    REDIRECT_COLUMNS,
    export_csv,
    export_markdown,
)
from .filters import match_keywords
from .history import EVENT_LABELS, History
from .models import Offer
from .parsing import OfferUnavailableError, StructureChangedError, offer_url
from .paths import browser_profile_dir, data_dir
from .redirects import CATEGORY_LABELS, RedirectRegistry, classify_url, is_safe_external_url
from .scoring import score_offer
from .search import HelloworkClient, HelloworkHTTPError

log = logging.getLogger(__name__)

INSTRUCTIONS = """Serveur MCP non officiel pour la recherche d'emploi sur Hellowork (hellowork.com).

Déroulé conseillé :
1. hellowork_status puis get_config pour connaître les critères. Les compléter avec update_config.
2. search_offers pour lister des offres, puis analyze_offers pour obtenir un score sur 100 et une décision.
3. Lire la description, ajuster l'avis si besoin, puis mark_offer (selected ou rejected).
4. Pour postuler : check_session (ou hellowork_login), prepare_application, montrer le récapitulatif à
   l'utilisateur, obtenir son accord explicite, puis submit_application avec le jeton reçu.
5. Offres externes : record_external_redirect, puis open_external_redirect uniquement si l'utilisateur le demande.

Règles : ne jamais inventer d'information sur le candidat, ne jamais envoyer de candidature sans accord
explicite de l'utilisateur pour l'offre concernée. Le mode simulation (dry_run) est actif par défaut."""


def _icons() -> list[Icon] | None:
    try:
        png = resources.files("hellowork_mcp").joinpath("assets/icon.png").read_bytes()
    except (FileNotFoundError, OSError):
        log.warning("Icône introuvable dans le paquet : le serveur démarre sans icône")
        return None
    icons = [Icon(src="data:image/png;base64," + base64.b64encode(png).decode("ascii"), mime_type="image/png", sizes=["256x256"])]
    try:
        svg = resources.files("hellowork_mcp").joinpath("assets/icon.svg").read_bytes()
        icons.append(Icon(src="data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii"), mime_type="image/svg+xml", sizes=["any"]))
    except (FileNotFoundError, OSError):
        pass  # le PNG suffit
    return icons


mcp = MCPServer(
    name="hellowork",
    title="Hellowork MCP",
    description="Recherche, analyse et suivi des offres d'emploi Hellowork (projet non officiel).",
    instructions=INSTRUCTIONS,
    version=__version__,
    icons=_icons(),
    website_url="https://github.com/ATSU-ADJOTO007/hellowork-mcp",
)
_browser = BrowserSession()
_confirmations = ConfirmationStore()

# Mode HTTP : le serveur tourne sur une autre machine que celle de l'utilisateur (hébergeur, tunnel).
# Les outils qui ouvrent Chromium ou le navigateur par défaut agiraient sur cette machine distante :
# ils sont refusés, sauf activation explicite pour un serveur personnel (--enable-browser).
_http_mode = False
_browser_allowed = True


@mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def healthz(request):  # sonde de disponibilité des hébergeurs (Render, Docker)
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "version": __version__})


def configure_http_mode(enable_browser: bool = False) -> None:
    global _http_mode, _browser_allowed
    _http_mode = True
    _browser_allowed = enable_browser


def _require_local_browser(action: str) -> None:
    if not _browser_allowed:
        raise ToolError(
            f"{action} n'est pas disponible quand le serveur est utilisé par URL (mode HTTP) : la fenêtre s'ouvrirait "
            "sur la machine qui héberge le serveur. Utiliser l'installation locale (stdio) pour cette action, "
            "ou lancer le serveur personnel avec --enable-browser."
        )


def _config() -> Config:
    try:
        return load_config()
    except ConfigError as exc:
        raise ToolError(str(exc)) from exc


def _client(config: Config) -> HelloworkClient:
    return HelloworkClient(delay_seconds=config.request_delay_seconds)


def _fetch_offer(offer_id: str, config: Config) -> Offer:
    try:
        offer_url(offer_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    client = _client(config)
    try:
        return client.get_offer(offer_id)
    finally:
        client.close()


def _offer_payload(offer: Offer, config: Config) -> dict[str, Any]:
    text = "\n".join([offer.title, offer.description, " ".join(offer.skills)])
    req_found, req_missing = match_keywords(text, config.required_keywords)
    excl_found, _ = match_keywords(text, config.excluded_keywords)
    data = offer.model_dump(mode="json")
    data["keyword_check"] = {
        "required_found": req_found,
        "required_missing": req_missing,
        "excluded_found": excl_found,
    }
    return data


async def _run(func, *args):
    """Exécute une fonction bloquante (HTTP, disque) hors de la boucle asyncio."""
    try:
        return await anyio.to_thread.run_sync(func, *args)
    except (HelloworkHTTPError, StructureChangedError) as exc:
        raise ToolError(str(exc)) from exc


# ---------------------------------------------------------------- état et configuration


@mcp.tool()
def hellowork_status() -> dict[str, Any]:
    """État du serveur : version, dossier de données, mode simulation, candidatures du jour et critères actifs."""
    config = _config()
    history = History()
    return {
        "version": __version__,
        "data_dir": str(data_dir()),
        "dry_run": config.dry_run,
        "applications_today": history.applications_on(),
        "max_applications_per_day": config.max_applications_per_day,
        "min_score": config.min_score,
        "thresholds": config.thresholds.model_dump(),
        "criteria_configured": bool(config.job_titles or config.required_keywords or config.locations),
        "offers_tracked": len(history.offers()),
        "transport": "http" if _http_mode else "stdio",
        "browser_tools_enabled": _browser_allowed,
        "redirects_recorded": len(RedirectRegistry().all()),
    }


@mcp.tool()
def get_config() -> dict[str, Any]:
    """Retourne la configuration complète (critères de recherche, seuils, protections)."""
    return {"config": _config().model_dump(mode="json"), "fields": _config_field_docs()}


def _config_field_docs() -> dict[str, str]:
    return {name: (field.description or "") for name, field in Config.model_fields.items()}


@mcp.tool(name="update_config")
def update_config_tool(
    changes: Annotated[
        dict[str, Any],
        Field(
            description=(
                "Champs à modifier, par exemple {\"job_titles\": [\"Développeur Python\"], \"locations\": [\"Lyon\"], "
                "\"min_salary\": 40000, \"dry_run\": true}. thresholds accepte {\"relevant\": 70, \"review\": 50}."
            )
        ),
    ],
) -> dict[str, Any]:
    """Modifie et enregistre la configuration. Les valeurs sont validées et les champs inconnus refusés."""
    try:
        config = update_config(changes)
    except ConfigError as exc:
        raise ToolError(f"Configuration refusée : {exc}") from exc
    return {"ok": True, "updated_fields": sorted(changes), "config": config.model_dump(mode="json")}


# ---------------------------------------------------------------- session


@mcp.tool()
async def hellowork_login(
    timeout_seconds: Annotated[int, Field(ge=30, le=900, description="Durée d'attente de la connexion manuelle")] = 300,
) -> dict[str, Any]:
    """Ouvre une fenêtre Chromium sur la page de connexion Hellowork et attend que l'utilisateur se connecte
    lui-même. Aucun identifiant n'est saisi ni stocké par le serveur. La session est conservée localement."""
    try:
        _require_local_browser("La connexion Hellowork")
        result = await _browser.login(timeout_seconds)
    except BrowserUnavailableError as exc:
        raise ToolError(str(exc)) from exc
    result["human_action"] = None if result["logged_in"] else "Se connecter dans la fenêtre ouverte puis relancer l'outil."
    return result


@mcp.tool()
async def check_session() -> dict[str, Any]:
    """Vérifie si la session Hellowork enregistrée est toujours valide. login_required=true indique qu'il faut
    lancer hellowork_login."""
    try:
        _require_local_browser("La vérification de session")
        return await _browser.check_session(headless=_config().headless)
    except BrowserUnavailableError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
async def clear_session() -> dict[str, Any]:
    """Supprime le profil navigateur local (cookies et session Hellowork). Une nouvelle connexion sera nécessaire."""
    import shutil

    _require_local_browser("La suppression de session")

    await _browser.close()
    profile = browser_profile_dir()
    shutil.rmtree(profile, ignore_errors=False)
    return {"ok": True, "removed": str(profile), "login_required": True}


# ---------------------------------------------------------------- recherche et analyse


@mcp.tool()
async def search_offers(
    keywords: Annotated[str, Field(description="Mots-clés, poste ou entreprise. Vide : postes de la configuration")] = "",
    location: Annotated[str, Field(description="Ville, département ou région. Vide : lieux de la configuration")] = "",
    contracts: Annotated[
        list[str] | None,
        Field(description="Types de contrat : CDI, CDD, Intérim, Stage, Alternance, Indépendant, Freelance..."),
    ] = None,
    remote: Annotated[
        list[Literal["full", "partial", "occasional", "none"]] | None, Field(description="Filtre télétravail")
    ] = None,
    max_results: Annotated[int, Field(ge=1, le=150, description="Nombre maximum d'offres retournées")] = 30,
    sort: Annotated[Literal["relevance", "date"], Field(description="Tri des résultats")] = "relevance",
    include_processed: Annotated[bool, Field(description="Inclure les offres déjà traitées")] = True,
) -> dict[str, Any]:
    """Recherche des offres sur Hellowork. Sans mots-clés ni lieu, utilise les postes, lieux et contrats de la
    configuration. Les doublons sont supprimés et chaque offre indique si elle a déjà été traitée."""
    config = _config()
    queries: list[tuple[str, str]] = []
    keyword_list = [keywords] if keywords.strip() else (config.job_titles or [""])
    location_list = [location] if location.strip() else (config.locations or [""])
    for kw in keyword_list:
        for loc in location_list:
            queries.append((kw, loc))
    if queries == [("", "")]:
        raise ToolError("Aucun critère : fournir keywords ou location, ou renseigner job_titles/locations avec update_config.")
    contract_filter = contracts if contracts is not None else config.contract_types
    history = History()

    def work() -> dict[str, Any]:
        client = _client(config)
        offers: dict[str, Any] = {}
        totals: list[dict[str, Any]] = []
        per_query = max(1, max_results // len(queries)) if len(queries) > 1 else max_results
        try:
            for kw, loc in queries:
                try:
                    found, total, urls = client.search(kw, loc, contract_filter, remote, per_query, sort)
                except ValueError as exc:
                    raise ToolError(str(exc)) from exc
                totals.append({"keywords": kw, "location": loc, "announced_total": total, "returned": len(found), "urls": urls})
                for offer in found:
                    if offer.offer_id in offers:
                        continue
                    record = history.offer(offer.offer_id)
                    offer.already_processed = history.is_processed(offer.offer_id)
                    offer.status = record.get("status") if record else None
                    if not record:
                        history.record("detected", offer.offer_id, title=offer.title, company=offer.company, url=offer.url)
                    offers[offer.offer_id] = offer
        finally:
            client.close()
        items = [o.model_dump(mode="json") for o in offers.values() if include_processed or not o.already_processed]
        return {
            "count": len(items),
            "queries": totals,
            "offers": items[:max_results],
            "next_steps": "analyze_offers avec les offer_id retenus pour obtenir score et décision.",
        }

    return await _run(work)


@mcp.tool()
async def get_offer(
    offer_id: Annotated[str, Field(description="Identifiant numérique de l'offre, ex. 84561625")],
) -> dict[str, Any]:
    """Retourne le détail structuré d'une offre : titre, entreprise, lieu, contrat, salaire, télétravail,
    description, compétences, lien de candidature externe et contrôle des mots-clés."""
    config = _config()
    try:
        offer = await _run(_fetch_offer, offer_id, config)
    except OfferUnavailableError as exc:
        return {"offer_id": offer_id, "available": False, "error": str(exc)}
    return _offer_payload(offer, config)


@mcp.tool()
async def analyze_offers(
    offer_ids: Annotated[list[str], Field(min_length=1, max_length=20, description="1 à 20 identifiants d'offre")],
    include_description: Annotated[bool, Field(description="Inclure la description complète de chaque offre")] = False,
) -> dict[str, Any]:
    """Analyse chaque offre et calcule un score sur 100 avec justification, critères satisfaits et manquants,
    points de vigilance et décision proposée (relevant, review, not_relevant, already_processed)."""
    config = _config()
    history = History()

    def work() -> dict[str, Any]:
        results = []
        client = _client(config)
        try:
            for offer_id in dict.fromkeys(offer_ids):
                try:
                    offer_url(offer_id)
                    offer = client.get_offer(offer_id)
                except ValueError as exc:
                    results.append({"offer_id": offer_id, "error": str(exc)})
                    continue
                except OfferUnavailableError as exc:
                    history.record("error", offer_id, details=str(exc))
                    results.append({"offer_id": offer_id, "available": False, "error": str(exc)})
                    continue
                score = score_offer(offer, config, already_processed=history.is_processed(offer_id))
                history.record(
                    "analyzed", offer_id, title=offer.title, company=offer.company, url=offer.url, score=score.score,
                    details=score.decision_label,
                )
                payload = _offer_payload(offer, config)
                if not include_description:
                    payload["description"] = payload["description"][:600] + ("..." if len(payload["description"]) > 600 else "")
                results.append({"offer": payload, "analysis": score.model_dump(mode="json")})
        finally:
            client.close()
        summary = {d: 0 for d in ("relevant", "review", "not_relevant", "already_processed")}
        for r in results:
            if "analysis" in r:
                summary[r["analysis"]["decision"]] += 1
        return {"summary": summary, "results": results}

    return await _run(work)


@mcp.tool()
def mark_offer(
    offer_id: Annotated[str, Field(description="Identifiant de l'offre")],
    status: Annotated[Literal["selected", "rejected", "manual_action_required"], Field(description="Nouveau statut")],
    note: Annotated[str | None, Field(description="Justification ou commentaire")] = None,
    title: Annotated[str | None, Field(description="Titre (si l'offre n'est pas encore dans l'historique)")] = None,
    company: Annotated[str | None, Field(description="Entreprise")] = None,
) -> dict[str, Any]:
    """Enregistre la décision prise sur une offre (retenue, rejetée ou action manuelle nécessaire)."""
    try:
        url = offer_url(offer_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    entry = History().record(status, offer_id, title=title, company=company, url=url, details=note)
    return {"ok": True, "event": entry}


# ---------------------------------------------------------------- candidatures


@mcp.tool()
async def prepare_application(
    offer_id: Annotated[str, Field(description="Identifiant de l'offre")],
    message: Annotated[
        str | None,
        Field(max_length=2900, description="Message au recruteur rédigé avec l'utilisateur. Aucune information inventée."),
    ] = None,
) -> dict[str, Any]:
    """Vérifie les protections (doublon, limite quotidienne, score minimum, mots-clés interdits, offre externe)
    et prépare un récapitulatif. Retourne un jeton de confirmation valable 15 minutes, à transmettre à
    submit_application uniquement après accord explicite de l'utilisateur sur ce récapitulatif."""
    config = _config()
    history = History()
    try:
        offer = await _run(_fetch_offer, offer_id, config)
    except OfferUnavailableError as exc:
        history.record("error", offer_id, details=str(exc))
        raise ToolError(str(exc)) from exc
    score = score_offer(offer, config)
    guards = run_guards(offer, score, config, history)
    result: dict[str, Any] = {
        "offer": {"offer_id": offer.offer_id, "title": offer.title, "company": offer.company, "location": offer.location, "url": offer.url},
        "score": score.score,
        "decision": score.decision,
        "checks": guards.checks,
        "allowed": guards.allowed,
        "dry_run": config.dry_run,
        "message_to_send": message,
        "application_sent": False,
    }
    if not guards.allowed:
        result["human_validation_required"] = False
        result["next_steps"] = "Candidature bloquée par les contrôles ci-dessus."
        if offer.external_apply_url or offer.direct_apply is False:
            result["next_steps"] += " Offre externe : utiliser record_external_redirect."
        return result
    token, ttl = _confirmations.issue(offer.offer_id, message)
    result.update(
        {
            "confirmation_token": token,
            "token_expires_in_seconds": ttl,
            "human_validation_required": True,
            "next_steps": (
                "Montrer ce récapitulatif à l'utilisateur et obtenir son accord explicite pour cette offre, "
                "puis appeler submit_application avec le même offer_id, le même message et confirmation_token."
                + (" Mode simulation actif : aucune candidature réelle ne sera envoyée." if config.dry_run else "")
            ),
        }
    )
    return result


@mcp.tool()
async def submit_application(
    offer_id: Annotated[str, Field(description="Identifiant de l'offre")],
    confirmation_token: Annotated[str, Field(description="Jeton reçu de prepare_application")],
    user_confirmed: Annotated[
        bool, Field(description="true seulement si l'utilisateur a explicitement validé l'envoi de cette candidature")
    ],
    message: Annotated[str | None, Field(max_length=2900, description="Exactement le message validé")] = None,
) -> dict[str, Any]:
    """Envoie la candidature validée par l'utilisateur. En mode simulation (dry_run), rien n'est envoyé et
    l'action est enregistrée comme simulation. application_sent indique si une candidature est réellement partie."""
    if not user_confirmed:
        raise ToolError("user_confirmed=false : demander l'accord explicite de l'utilisateur avant l'envoi.")
    ok, reason = _confirmations.consume(confirmation_token, offer_id, message)
    if not ok:
        raise ToolError(reason)
    config = _config()
    history = History()
    try:
        offer = await _run(_fetch_offer, offer_id, config)
    except OfferUnavailableError as exc:
        history.record("error", offer_id, details=str(exc))
        raise ToolError(str(exc)) from exc
    score = score_offer(offer, config)
    guards = run_guards(offer, score, config, history)
    if not guards.allowed:
        return {"application_sent": False, "allowed": False, "checks": guards.checks}

    common = {"title": offer.title, "company": offer.company, "url": offer.url, "score": score.score}
    if config.dry_run or not _browser_allowed:
        history.record("simulated", offer_id, details="Mode simulation : rien n'a été envoyé", **common)
        return {
            "application_sent": False,
            "dry_run": True,
            "status": "simulated",
            "details": "Simulation enregistrée. Pour envoyer réellement : update_config({\"dry_run\": false})."
            if _browser_allowed
            else "Simulation enregistrée. En mode HTTP, l'envoi réel exige l'installation locale (stdio) : "
            "la candidature se termine dans une fenêtre Chromium sur votre machine.",
        }
    try:
        outcome = await _browser.apply(offer.url, message, headless=False)
    except BrowserUnavailableError as exc:
        history.record("error", offer_id, details=str(exc), **common)
        raise ToolError(str(exc)) from exc
    except Exception as exc:  # erreur Playwright inattendue : tracée puis remontée
        history.record("error", offer_id, details=repr(exc), **common)
        raise ToolError(f"Erreur pendant la candidature : {exc}") from exc
    history.record(outcome.status, offer_id, details=outcome.details, **common)
    return {
        "application_sent": outcome.status == "applied",
        "status": outcome.status,
        "details": outcome.details,
        "page_url": outcome.final_url,
        "human_action": None if outcome.status == "applied" else "Vérifier la fenêtre du navigateur et terminer à la main.",
    }


# ---------------------------------------------------------------- redirections externes


@mcp.tool()
async def record_external_redirect(
    offer_id: Annotated[str, Field(description="Identifiant de l'offre Hellowork")],
    external_url: Annotated[str | None, Field(description="URL externe. Vide : détectée depuis la page de l'offre")] = None,
) -> dict[str, Any]:
    """Enregistre une offre qui renvoie vers un autre site (site d'annonce, site carrière, ATS, autre).
    Une même URL n'est enregistrée qu'une fois. N'ouvre rien dans le navigateur."""
    config = _config()
    try:
        offer = await _run(_fetch_offer, offer_id, config)
    except OfferUnavailableError as exc:
        raise ToolError(str(exc)) from exc
    target = external_url or offer.external_apply_url
    if not target:
        return {
            "recorded": False,
            "external_link_opened": False,
            "details": "Aucun lien externe trouvé sur la page de l'offre : la candidature semble se faire sur Hellowork.",
        }
    try:
        entry, created = RedirectRegistry().record(
            offer_id=offer.offer_id, title=offer.title, company=offer.company, hellowork_url=offer.url, external_url=target
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    if created:
        History().record(
            "external_redirect", offer.offer_id, title=offer.title, company=offer.company, url=offer.url,
            details=f"{entry['category_label']} : {target}",
        )
    return {
        "recorded": True,
        "already_known": not created,
        "entry": entry,
        "external_link_opened": False,
        "next_steps": "open_external_redirect pour ouvrir le lien si l'utilisateur le souhaite."
        if config.external_redirect_mode != "ignore"
        else None,
    }


@mcp.tool()
def open_external_redirect(
    external_url: Annotated[str, Field(description="URL externe déjà enregistrée par record_external_redirect")],
    force: Annotated[bool, Field(description="Rouvrir même si le lien a déjà été ouvert")] = False,
) -> dict[str, Any]:
    """Ouvre un lien externe enregistré dans le navigateur par défaut de l'utilisateur. Un lien déjà ouvert
    n'est pas rouvert sauf si force=true."""
    _require_local_browser("L'ouverture d'un lien dans le navigateur")
    if not is_safe_external_url(external_url):
        raise ToolError("Seules les URL http et https sont acceptées.")
    registry = RedirectRegistry()
    entry = registry.find(external_url)
    if entry is None:
        raise ToolError("URL inconnue : l'enregistrer d'abord avec record_external_redirect.")
    if entry.get("opened_in_browser") and not force:
        return {"external_link_opened": False, "already_opened_at": entry.get("opened_at"), "entry": entry}
    opened = webbrowser.open(entry["external_url"], new=2)
    if opened:
        entry = registry.mark_opened(external_url)
    return {
        "external_link_opened": bool(opened),
        "entry": entry,
        "details": None if opened else "Aucun navigateur par défaut n'a pu être lancé.",
    }


@mcp.tool()
def list_redirects(
    category: Annotated[
        Literal["job_board", "company_careers", "ats", "other"] | None, Field(description="Filtrer par catégorie")
    ] = None,
    only_unopened: Annotated[bool, Field(description="Seulement les liens jamais ouverts")] = False,
) -> dict[str, Any]:
    """Liste les redirections externes enregistrées."""
    entries = RedirectRegistry().all()
    if category:
        entries = [e for e in entries if e.get("category") == category]
    if only_unopened:
        entries = [e for e in entries if not e.get("opened_in_browser")]
    return {"count": len(entries), "categories": CATEGORY_LABELS, "redirects": entries}


@mcp.tool()
def classify_external_url(url: Annotated[str, Field(description="URL à classer")]) -> dict[str, Any]:
    """Classe une URL : job_board (site d'annonce), company_careers (site carrière), ats ou other."""
    if not is_safe_external_url(url):
        raise ToolError("URL http ou https attendue.")
    category = classify_url(url)
    return {"url": url, "category": category, "category_label": CATEGORY_LABELS[category]}


# ---------------------------------------------------------------- historique et exports


@mcp.tool()
def get_history(
    limit: Annotated[int, Field(ge=1, le=1000, description="Nombre d'événements")] = 50,
    event: Annotated[str | None, Field(description="Filtrer par type : " + ", ".join(EVENT_LABELS))] = None,
    offer_id: Annotated[str | None, Field(description="Filtrer par offre")] = None,
) -> dict[str, Any]:
    """Derniers événements enregistrés (détection, analyse, rejet, sélection, simulation, envoi, redirection, erreur)."""
    if event and event not in EVENT_LABELS:
        raise ToolError(f"Type inconnu : {event}. Valeurs : {', '.join(EVENT_LABELS)}")
    events = History().events(limit, event, offer_id)
    return {"count": len(events), "events": events}


@mcp.tool()
def list_tracked_offers(
    status: Annotated[str | None, Field(description="Filtrer par statut : " + ", ".join(EVENT_LABELS))] = None,
    limit: Annotated[int, Field(ge=1, le=1000)] = 100,
) -> dict[str, Any]:
    """Offres connues avec leur dernier statut."""
    offers = History().offers(status)
    return {"count": len(offers), "offers": offers[:limit]}


@mcp.tool()
def export_data(
    dataset: Annotated[Literal["offers", "events", "redirects"], Field(description="Données à exporter")] = "offers",
    format: Annotated[Literal["csv", "markdown"], Field(description="csv (Excel, séparateur ;) ou markdown")] = "csv",
) -> dict[str, Any]:
    """Exporte les offres suivies, les événements ou les redirections dans un fichier horodaté du dossier exports."""
    history = History()
    if dataset == "offers":
        rows, columns, title = history.offers(), HISTORY_COLUMNS, "Offres suivies Hellowork"
    elif dataset == "events":
        rows, columns, title = history.events(limit=0), EVENT_COLUMNS, "Historique Hellowork MCP"
    else:
        rows, columns, title = RedirectRegistry().all(), REDIRECT_COLUMNS, "Redirections externes Hellowork"
    name = f"hellowork-{dataset}"
    path = export_csv(rows, columns, name) if format == "csv" else export_markdown(rows, columns, name, title)
    result: dict[str, Any] = {"ok": True, "path": str(path), "rows": len(rows), "format": format}
    if _http_mode:
        # Le fichier est écrit sur le serveur distant : le contenu est renvoyé pour que l'utilisateur le récupère.
        result["content"] = path.read_text(encoding="utf-8-sig" if format == "csv" else "utf-8")
    return result
