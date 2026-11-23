# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [1.1.0] - 2026-11-23

### Ajouté

- Mode Streamable HTTP (`--transport http`, `--host`, `--port`, `--path`, `--allowed-host`) pour ajouter le serveur par URL HTTPS, par exemple comme connecteur personnalisé Claude.
- En mode HTTP, outils navigateur désactivés (connexion, session, envoi réel, ouverture de lien) sauf `--enable-browser`, et `export_data` renvoie le contenu du fichier.
- Route `GET /healthz`, `Dockerfile` et blueprint `render.yaml`.
- Guide `docs/REMOTE.md` (tunnel cloudflared, Render, Docker).
- Annotations MCP sur les 19 outils (titre, lecture seule, destructif, idempotent, monde ouvert).
- Politique de confidentialité `PRIVACY.md`.

### Modifié

- Nouvelle icône : monogramme « hw » noir et blanc au format carré, source vectorielle `icon.svg` déclarée en plus du PNG.

## [1.0.0] - 2026-11-23

Première version publique.

### Ajouté

- Serveur MCP `hellowork` (SDK Python `mcp`, transport stdio) avec 19 outils.
- Recherche d'offres par mots-clés, lieu, contrat et télétravail, avec pagination (30 offres par page, 10 pages maximum) et suppression des doublons.
- Extraction des offres à partir du JSON-LD `JobPosting` de Hellowork, avec repli sur le HTML et erreur explicite `StructureChangedError` si la page change.
- Score sur 100 (intitulé 25, mots-clés 25, contrat 15, lieu 15, salaire 10, télétravail 10) avec justification et décision.
- Configuration persistante validée : postes, mots-clés obligatoires et interdits, contrats, lieux, salaire minimum, télétravail, seuils, limite quotidienne, mode simulation.
- Candidature avec contrôles (doublon, limite quotidienne, score minimum, mots-clés interdits, offre externe), mode simulation par défaut et jeton de confirmation à usage unique.
- Connexion manuelle dans Chromium (Playwright), session persistante et vérification d'expiration.
- Registre des redirections externes avec classement (site d'annonce, site carrière, ATS, autre) et ouverture unique dans le navigateur par défaut.
- Historique des événements, écritures JSON atomiques et mise de côté des fichiers corrompus.
- Exports CSV compatibles Excel (`;`, UTF-8 avec BOM) et Markdown.
- Commandes `hellowork-mcp --check` et `hellowork-mcp --install-browser`.
- Scripts `check_dashes.py` et `check_sensitive_files.py`, workflow GitHub Actions sur Windows, macOS et Linux.
- Documentation d'installation par système et configuration de Claude Desktop, Claude Code, Codex, Cursor, VS Code, Cline et Windsurf.

### Limites connues

- Le formulaire de candidature Hellowork comporte plusieurs étapes. Lorsqu'une étape demande un CV ou répond à un questionnaire du recruteur, le serveur s'arrête et renvoie `manual_action_required`.
- Aucun bundle MCPB : Playwright et Chromium dépendent du système (voir docs/MCP_CLIENTS.md).
