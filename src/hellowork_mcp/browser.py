"""Navigateur Playwright avec profil persistant local.

Le profil (cookies de session Hellowork) est stocké dans <dossier de données>/browser-profile.
Aucun mot de passe n'est saisi ni enregistré par ce programme : la connexion est faite à la main
par l'utilisateur dans la fenêtre ouverte. Les CAPTCHA et contrôles de sécurité ne sont jamais contournés.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Literal

from . import HELLOWORK_BASE_URL
from .paths import browser_profile_dir

log = logging.getLogger(__name__)

LOGIN_URL = f"{HELLOWORK_BASE_URL}/fr-fr/candidat/connexion-inscription.html#connexion"
ACCOUNT_URL = f"{HELLOWORK_BASE_URL}/fr-fr/candidat/mon-espace.html"

SUCCESS_MARKERS = (
    "candidature a bien été envoyée",
    "candidature a été envoyée",
    "votre candidature a bien été",
    "candidature envoyée",
    "merci pour votre candidature",
)


class BrowserUnavailableError(RuntimeError):
    pass


@dataclass
class ApplyOutcome:
    status: Literal["applied", "manual_action_required", "error"]
    details: str
    final_url: str | None = None


class BrowserSession:
    """Contexte Chromium persistant partagé par les outils du serveur."""

    def __init__(self) -> None:
        self._playwright = None
        self._context = None
        self._headless: bool | None = None
        self._lock = asyncio.Lock()

    async def _ensure(self, headless: bool):
        if self._context is not None and self._headless == headless:
            return self._context
        await self._close_context()
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # dépendance absente
            raise BrowserUnavailableError("Playwright n'est pas installé : pip install playwright") from exc
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(browser_profile_dir()),
                headless=headless,
                locale="fr-FR",
                viewport={"width": 1280, "height": 900},
            )
        except Exception as exc:
            message = str(exc)
            hint = ""
            if "Executable doesn't exist" in message or "playwright install" in message:
                hint = " Installer le navigateur : python -m playwright install chromium"
            elif "ProcessSingleton" in message or "already in use" in message or "lock" in message.lower():
                hint = " Le profil est déjà utilisé par une autre instance de hellowork-mcp : fermer l'autre client MCP."
            raise BrowserUnavailableError(f"Lancement de Chromium impossible : {message.splitlines()[0]}.{hint}") from exc
        self._headless = headless
        return self._context

    async def _close_context(self) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            finally:
                self._context = None
                self._headless = None

    async def close(self) -> None:
        async with self._lock:
            await self._close_context()
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    async def _is_logged_in(self, context) -> tuple[bool, str]:
        response = await context.request.get(ACCOUNT_URL, max_redirects=5, timeout=20_000)
        final_url = response.url
        logged = response.ok and "connexion" not in final_url and "/candidat/" in final_url
        return logged, final_url

    async def check_session(self, headless: bool = True) -> dict:
        async with self._lock:
            context = await self._ensure(headless if self._context is None else self._headless)
            logged, final_url = await self._is_logged_in(context)
            return {
                "logged_in": logged,
                "checked_url": ACCOUNT_URL,
                "final_url": final_url,
                "login_required": not logged,
            }

    async def login(self, timeout_seconds: int = 300) -> dict:
        """Ouvre une fenêtre visible sur la page de connexion et attend que l'utilisateur se connecte."""
        async with self._lock:
            context = await self._ensure(headless=False)
            logged, _ = await self._is_logged_in(context)
            if logged:
                return {"logged_in": True, "waited_seconds": 0, "message": "Session déjà active."}
            page = await context.new_page()
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            start = time.monotonic()
            while time.monotonic() - start < timeout_seconds:
                await asyncio.sleep(3)
                if page.is_closed():
                    break
                logged, _ = await self._is_logged_in(context)
                if logged:
                    await page.close()
                    return {
                        "logged_in": True,
                        "waited_seconds": int(time.monotonic() - start),
                        "message": "Connexion détectée. La session est conservée dans le profil local.",
                    }
            return {
                "logged_in": False,
                "waited_seconds": int(time.monotonic() - start),
                "message": "Connexion non détectée dans le délai imparti ou fenêtre fermée.",
            }

    async def apply(self, offer_url: str, message: str | None, headless: bool = False) -> ApplyOutcome:
        """Remplit et envoie le formulaire de candidature Hellowork de l'offre.

        Le formulaire est chargé dans le turbo-frame « offer-detail-step-frame ». Si une étape
        demande une information que le programme ne connaît pas (questions du recruteur, CV, CGU),
        la page reste ouverte et le statut manual_action_required est renvoyé.
        """
        async with self._lock:
            context = await self._ensure(headless=headless)
            logged, _ = await self._is_logged_in(context)
            if not logged:
                return ApplyOutcome("manual_action_required", "Session Hellowork absente : lancer hellowork_login.")
            page = await context.new_page()
            await page.goto(offer_url, wait_until="domcontentloaded")
            frame_form = page.locator("#offer-detail-step-frame form, turbo-frame#offer-detail-step-frame form")
            try:
                await page.locator("#postuler").scroll_into_view_if_needed(timeout=10_000)
                await frame_form.first.wait_for(state="visible", timeout=15_000)
            except Exception:
                return ApplyOutcome(
                    "manual_action_required",
                    "Formulaire de candidature Hellowork introuvable sur la page (offre externe ou structure modifiée).",
                    page.url,
                )
            form = frame_form.first

            cgu = form.locator('input[name="HasAcceptedCGU"]')
            if await cgu.count() and await cgu.first.is_visible() and not await cgu.first.is_checked():
                return ApplyOutcome(
                    "manual_action_required",
                    "Le formulaire demande d'accepter les CGU de création de compte : la session n'est pas reconnue. "
                    "Se connecter avec hellowork_login puis réessayer.",
                    page.url,
                )

            for name in ("Firstname", "LastName", "Email"):
                field = form.locator(f'input[name="{name}"]')
                if await field.count() and await field.first.is_visible() and not (await field.first.input_value()).strip():
                    return ApplyOutcome(
                        "manual_action_required",
                        f"Le champ {name} est vide. Compléter le profil Hellowork : le programme n'invente aucune information.",
                        page.url,
                    )

            if message:
                toggle = form.locator('input[name="cover-letter-collapse-funnel"]')
                if await toggle.count() and not await toggle.first.is_checked():
                    await toggle.first.check(force=True)
                letter = form.locator('textarea[name="MotivationLetter"]')
                if await letter.count():
                    await letter.first.fill(message[:2900])

            submit = form.locator('button[type="submit"], input[type="submit"]')
            if not await submit.count():
                return ApplyOutcome("manual_action_required", "Bouton d'envoi introuvable dans le formulaire.", page.url)
            await submit.first.click()

            for _ in range(20):
                await asyncio.sleep(1)
                body = (await page.locator("body").inner_text()).lower()
                if any(marker in body for marker in SUCCESS_MARKERS):
                    await page.close()
                    return ApplyOutcome("applied", "Confirmation d'envoi affichée par Hellowork.", offer_url)
            return ApplyOutcome(
                "manual_action_required",
                "Aucune confirmation d'envoi détectée après 20 secondes. Une étape supplémentaire est probablement "
                "demandée (CV, questions du recruteur). Terminer dans la fenêtre ouverte puis vérifier "
                "« Mes candidatures » sur Hellowork.",
                page.url,
            )
