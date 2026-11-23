<p align="center"><img src="icon.png" alt="Hellowork MCP" width="96"></p>

# Hellowork MCP

Serveur [MCP](https://modelcontextprotocol.io) qui permet à un agent IA (Claude, Codex, Cursor, VS Code, Cline, Windsurf) de rechercher des offres sur [hellowork.com](https://www.hellowork.com), de les noter sur 100 selon vos critères, de suivre vos candidatures et de préparer l'envoi sous votre contrôle.

> Projet indépendant, non affilié à Hellowork. L'icône (monogramme « hw ») est une création du projet, distincte du logo déposé de Hellowork.

Version 1.1.0. Licence MIT. English summary at the end of this file.

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Prérequis et systèmes](#prérequis-et-systèmes)
- [Installation](#installation)
- [Configuration des clients MCP](#configuration-des-clients-mcp)
- [Ajouter par URL (connecteur HTTPS)](#ajouter-par-url-connecteur-https)
- [Utilisation](#utilisation)
- [Outils MCP](#outils-mcp)
- [Configuration des critères](#configuration-des-critères)
- [Stockage des données](#stockage-des-données)
- [Sécurité](#sécurité)
- [Tests](#tests)
- [Dépannage et FAQ](#dépannage-et-faq)
- [Contribution, licence, version](#contribution-licence-version)

## Fonctionnalités

- Recherche d'offres par mots-clés, poste, entreprise, ville, région, contrat et télétravail, avec pagination et suppression des doublons.
- Extraction structurée de chaque offre depuis le bloc JSON-LD `JobPosting` de Hellowork : titre, entreprise, lieu, contrat, salaire, télétravail, description, compétences, mode de candidature.
- Score sur 100 explicable (barème fixe, seuils configurables) avec justification, critères satisfaits, critères manquants, points de vigilance et décision : `relevant`, `review`, `not_relevant`, `already_processed`.
- Candidature protégée : contrôle des doublons, limite quotidienne, score minimum, mots-clés interdits, mode simulation actif par défaut et jeton de confirmation à usage unique lié au message validé.
- Détection des offres qui renvoient vers un autre site, classement (site d'annonce, site carrière, ATS, autre), registre sans doublon et ouverture contrôlée dans le navigateur.
- Historique horodaté de toutes les actions, écritures JSON atomiques et récupération des fichiers corrompus.
- Exports CSV (séparateur `;`, UTF-8 avec BOM pour Excel) et Markdown horodatés.
- Connexion manuelle dans une fenêtre Chromium, session conservée localement, détection d'expiration.
- Deux modes : stdio pour un client local, Streamable HTTP pour ajouter le serveur par URL HTTPS (connecteur personnalisé Claude), avec `Dockerfile` et blueprint Render.

## Prérequis et systèmes

| Élément | Version |
| --- | --- |
| Python | 3.10 à 3.14 |
| Navigateur | Chromium installé par Playwright (environ 150 Mo) |
| Systèmes | Windows 10 et 11, macOS (Intel et Apple Silicon), Linux (Ubuntu, Debian, Fedora...) |

Tests réellement exécutés pour la version 1.0.0 : Windows 11 avec Python 3.14 en local. La CI GitHub Actions exécute la suite sur `windows-latest`, `macos-latest` et `ubuntu-latest` avec Python 3.10, 3.12 et 3.13. La connexion et la candidature réelles demandent un compte Hellowork et ne sont pas couvertes par la CI.

## Installation

### Installation en une commande (recommandée)

Une seule ligne installe tout : Python (si besoin, sans droits administrateur), Hellowork MCP, le navigateur Chromium, puis ajoute le serveur dans Claude Desktop (et Claude Code s'il est installé).

**Windows** : ouvrir PowerShell (menu Démarrer > « PowerShell ») et coller :

```powershell
irm https://raw.githubusercontent.com/ATSU-ADJOTO007/hellowork-mcp/main/install.ps1 | iex
```

**macOS et Linux** : ouvrir Terminal et coller :

```bash
curl -LsSf https://raw.githubusercontent.com/ATSU-ADJOTO007/hellowork-mcp/main/install.sh | sh
```

Ensuite, quitter complètement Claude Desktop puis le relancer : les outils Hellowork apparaissent. Le script utilise [uv](https://docs.astral.sh/uv/) (Astral) pour gérer Python, conserve une copie de sauvegarde de `claude_desktop_config.json` avant de le modifier, et peut être relancé pour mettre à jour. Le code des scripts est lisible avant exécution : [install.ps1](install.ps1), [install.sh](install.sh).

Commandes utiles après installation : `hellowork-mcp --check` (diagnostic), `hellowork-mcp --setup-claude` (reconfigurer Claude Desktop), `uv tool uninstall hellowork-mcp` (désinstaller).

### Installation manuelle

Le guide détaillé par système se trouve dans [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md), [docs/INSTALL_MACOS.md](docs/INSTALL_MACOS.md) et [docs/INSTALL_LINUX.md](docs/INSTALL_LINUX.md).

### Windows (PowerShell)

```powershell
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
python -m playwright install chromium
hellowork-mcp --check
```

### macOS et Linux (Terminal)

```bash
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
python -m playwright install chromium
hellowork-mcp --check
```

Sous Linux, Chromium a besoin de bibliothèques système : `sudo .venv/bin/python -m playwright install-deps chromium` les installe sur Ubuntu et Debian.

`hellowork-mcp --check` affiche un rapport JSON. `"ok": true` signifie que le serveur, le dossier de données et Chromium sont prêts.

### Variante avec uv

Si [uv](https://docs.astral.sh/uv/) est installé, il crée l'environnement et la commande en une ligne :

```bash
uv tool install git+https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
hellowork-mcp --install-browser
hellowork-mcp --check
```

### Chemin de la commande

Les clients MCP ont besoin du chemin absolu de l'exécutable :

| Système | Chemin dans le dossier du projet |
| --- | --- |
| Windows | `C:\chemin\vers\hellowork-mcp\.venv\Scripts\hellowork-mcp.exe` |
| macOS, Linux | `/chemin/vers/hellowork-mcp/.venv/bin/hellowork-mcp` |

Pour l'obtenir : `(Get-Command hellowork-mcp).Source` sous PowerShell, `which hellowork-mcp` sous macOS et Linux (environnement activé).

## Configuration des clients MCP

Toutes les configurations, avec leurs emplacements et leurs vérifications, sont détaillées dans [docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md). Remplacer `CHEMIN` par le chemin obtenu ci-dessus.

### Claude Desktop

Fichier `claude_desktop_config.json` (Paramètres > Développeur > Modifier la configuration) :

- Windows : `%APPDATA%\Claude\claude_desktop_config.json`
- macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN/hellowork-mcp"
    }
  }
}
```

Sous Windows, doubler les barres obliques inverses : `"C:\\Users\\vous\\hellowork-mcp\\.venv\\Scripts\\hellowork-mcp.exe"`. Quitter complètement Claude Desktop (icône de la barre des tâches ou menu Claude > Quitter) puis le relancer. Les outils apparaissent dans le menu des connecteurs de la zone de saisie.

### Claude Code

```bash
claude mcp add --scope user hellowork -- CHEMIN/hellowork-mcp
claude mcp list
```

Dans une session, `/mcp` affiche l'état du serveur.

### OpenAI Codex

```bash
codex mcp add hellowork -- CHEMIN/hellowork-mcp
```

ou dans `~/.codex/config.toml` :

```toml
[mcp_servers.hellowork]
command = "CHEMIN/hellowork-mcp"
```

### Cursor

`~/.cursor/mcp.json` (global) ou `.cursor/mcp.json` (projet), même format `mcpServers` que Claude Desktop.

### VS Code

`.vscode/mcp.json` dans l'espace de travail, ou commande « MCP: Open User Configuration » :

```json
{
  "servers": {
    "hellowork": {
      "type": "stdio",
      "command": "CHEMIN/hellowork-mcp"
    }
  }
}
```

### Cline et Windsurf

Cline : panneau MCP Servers > Configure, fichier `cline_mcp_settings.json`. Windsurf : `~/.codeium/windsurf/mcp_config.json`. Les deux utilisent le format `mcpServers` de Claude Desktop.

## Ajouter par URL (connecteur HTTPS)

Pour ajouter Hellowork MCP dans Claude via Paramètres > Connecteurs > « Ajouter un connecteur personnalisé » (champs Nom et URL du serveur MCP), le serveur doit être joignable en HTTPS :

```bash
hellowork-mcp --transport http --host 0.0.0.0 --port 8000 --path /mcp-VOTRE-SECRET
```

Puis exposer ce port en HTTPS : tunnel `cloudflared tunnel --url http://localhost:8000` depuis votre PC, hébergement Render en un clic (`render.yaml`), ou Docker (`Dockerfile`). Dans Claude :

- Nom : `Hellowork`
- URL du serveur MCP : `https://votre-adresse/mcp-VOTRE-SECRET`

En mode HTTP, la recherche, l'analyse, le score, l'historique et la préparation de candidature fonctionnent. Les outils qui ouvrent un navigateur (connexion, envoi réel, ouverture de lien) sont désactivés car ils agiraient sur la machine du serveur. Le serveur n'a pas d'authentification : le chemin secret est la seule protection, ne partagez pas l'URL. Guide complet : [docs/REMOTE.md](docs/REMOTE.md).

## Utilisation

Exemples de demandes à l'agent :

- « Configure Hellowork MCP : je cherche un poste de développeur Python en CDI à Lyon ou en télétravail, 45 000 euros minimum, sans ESN. »
- « Cherche les 30 offres les plus récentes et analyse celles qui semblent pertinentes. »
- « Explique pourquoi l'offre 84561625 a obtenu 62/100. »
- « Prépare ma candidature pour l'offre 84561625 avec ce message : ... »
- « Liste les offres qui redirigent vers un ATS et exporte-les en CSV. »

Déroulé d'une candidature :

1. `check_session`, puis `hellowork_login` si la session a expiré. Une fenêtre Chromium s'ouvre sur la page de connexion Hellowork et vous vous connectez vous-même.
2. `prepare_application` vérifie les protections et renvoie un récapitulatif et un jeton valable 15 minutes.
3. L'agent vous montre le récapitulatif. Vous validez explicitement.
4. `submit_application` avec le jeton et `user_confirmed=true`. En mode simulation (par défaut), rien n'est envoyé et l'action est historisée comme `simulated`. Pour des envois réels : `update_config` avec `{"dry_run": false}`.

Si Hellowork demande une étape inconnue (CV, questions du recruteur), le serveur s'arrête, laisse la fenêtre ouverte et renvoie `manual_action_required`. Le champ `application_sent` n'est `true` que si Hellowork affiche une confirmation d'envoi.

## Outils MCP

| Outil | Rôle |
| --- | --- |
| `hellowork_status` | Version, dossier de données, mode simulation, compteurs du jour |
| `get_config`, `update_config` | Lire et modifier les critères (validation stricte) |
| `hellowork_login` | Ouvrir la page de connexion et attendre la connexion manuelle |
| `check_session` | Vérifier la validité de la session enregistrée |
| `clear_session` | Supprimer le profil navigateur local |
| `search_offers` | Rechercher des offres (critères explicites ou ceux de la configuration) |
| `get_offer` | Détail structuré d'une offre et contrôle des mots-clés |
| `analyze_offers` | Score sur 100 et décision pour 1 à 20 offres |
| `mark_offer` | Enregistrer une décision : `selected`, `rejected`, `manual_action_required` |
| `prepare_application` | Contrôles avant candidature et jeton de confirmation |
| `submit_application` | Envoi (ou simulation) après accord explicite |
| `record_external_redirect` | Enregistrer une offre qui renvoie vers un autre site |
| `open_external_redirect` | Ouvrir un lien externe enregistré, une seule fois par défaut |
| `list_redirects`, `classify_external_url` | Consulter et classer les liens externes |
| `get_history`, `list_tracked_offers` | Historique des événements et statut des offres |
| `export_data` | Export CSV ou Markdown des offres, événements ou redirections |

Chaque outil déclare un titre et les annotations MCP `readOnlyHint`, `destructiveHint`, `idempotentHint` et `openWorldHint` : les outils de lecture sont marqués en lecture seule, `submit_application` et `clear_session` comme destructifs.

Chaque réponse est un objet JSON. Les champs `application_sent`, `external_link_opened`, `human_validation_required`, `human_action` et `next_steps` indiquent ce qui a été fait et ce qui reste à faire. Les erreurs sont renvoyées comme erreurs d'outil MCP avec un message explicite.

## Configuration des critères

| Champ | Défaut | Description |
| --- | --- | --- |
| `job_titles` | `[]` | Postes recherchés |
| `required_keywords` | `[]` | Mots-clés obligatoires (insensibles aux accents) |
| `excluded_keywords` | `[]` | Mots-clés interdits : score ramené à 0 |
| `contract_types` | `[]` | CDI, CDD, Intérim, Stage, Alternance, Indépendant, Freelance... |
| `locations` | `[]` | Villes, régions ou numéros de département |
| `min_salary` | `null` | Salaire annuel brut minimum en euros |
| `remote_preference` | `any` | `any`, `remote`, `hybrid`, `onsite` |
| `min_score` | `60` | Score minimal pour autoriser une candidature |
| `thresholds` | `{"relevant": 70, "review": 50}` | Seuils de décision |
| `max_applications_per_day` | `10` | Limite quotidienne de candidatures réelles |
| `dry_run` | `true` | Mode simulation |
| `external_redirect_mode` | `record_only` | `record_only`, `open_in_browser`, `ignore` |
| `request_delay_seconds` | `1.5` | Pause entre deux requêtes vers Hellowork |
| `headless` | `true` | Navigateur invisible pour la vérification de session |

Barème du score : intitulé 25, mots-clés obligatoires 25, contrat 15, localisation 15, salaire 10, télétravail 10. Un critère non configuré rapporte tous ses points. Une information absente de l'offre en rapporte la moitié et ajoute un point de vigilance.

## Stockage des données

| Système | Dossier par défaut |
| --- | --- |
| Windows | `%LOCALAPPDATA%\hellowork-mcp` |
| macOS | `~/Library/Application Support/hellowork-mcp` |
| Linux | `$XDG_DATA_HOME/hellowork-mcp` ou `~/.local/share/hellowork-mcp` |

La variable d'environnement `HELLOWORK_MCP_DATA_DIR` remplace ce dossier. Contenu : `config.json`, `history.json`, `redirects.json`, `exports/`, `browser-profile/` (cookies de session). Un fichier JSON illisible est renommé en `*.corrupt-AAAAMMJJ-HHMMSS.json` et un fichier neuf est créé.

## Sécurité

- Aucun mot de passe n'est demandé, saisi ou stocké par le serveur. La connexion se fait à la main dans la fenêtre Chromium.
- Les CAPTCHA et contrôles de Hellowork ne sont jamais contournés.
- Les données restent sur votre machine. Le dépôt ignore `browser-profile/`, l'historique, la configuration et les exports.
- Aucune candidature réelle sans `dry_run=false`, jeton valide et `user_confirmed=true`. Le jeton est lié à l'offre et au texte exact du message.
- Seules les URL `http` et `https` déjà enregistrées peuvent être ouvertes. Les cellules CSV commençant par `=`, `+`, `-` ou `@` sont neutralisées.

Détails et signalement de vulnérabilité : [SECURITY.md](SECURITY.md). Données traitées et suppression : [PRIVACY.md](PRIVACY.md).

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests scripts
python scripts/check_dashes.py
python scripts/check_sensitive_files.py
```

Les tests utilisent des pages HTML fictives (`tests/fixtures/`) et un dossier de données temporaire. Le test qui contacte le vrai site est marqué `live` et ne s'exécute qu'avec `HELLOWORK_LIVE_TESTS=1`. La CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) lance ces contrôles à chaque push et pull request.

## Dépannage et FAQ

Voir [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). Cas fréquents :

- `Executable doesn't exist` : lancer `python -m playwright install chromium` avec le Python de l'environnement.
- Le serveur n'apparaît pas dans Claude Desktop : vérifier le chemin absolu, les `\\` sous Windows, puis quitter complètement l'application.
- `StructureChangedError` : Hellowork a modifié ses pages. Ouvrir une issue avec l'URL concernée.

**Le serveur peut-il postuler tout seul ?** Non. Chaque envoi réel exige votre accord pour l'offre concernée.

**Faut-il un compte Hellowork ?** Pas pour rechercher et analyser. Oui pour postuler.

**Mes données partent-elles ailleurs ?** Le serveur contacte uniquement hellowork.com, et les liens externes que vous choisissez d'ouvrir.

## Contribution, licence, version

- Contribution : [CONTRIBUTING.md](CONTRIBUTING.md)
- Historique des versions : [CHANGELOG.md](CHANGELOG.md)
- Licence : [MIT](LICENSE). Elle autorise la réutilisation et la modification, y compris commerciale, avec mention de l'auteur, ce qui convient à un outil personnel que d'autres candidats peuvent adapter.
- Dépôt : https://github.com/ATSU-ADJOTO007/hellowork-mcp

## English summary

Hellowork MCP is an unofficial Model Context Protocol server for the French job board hellowork.com. It searches offers, extracts structured data, computes an explainable 0 to 100 match score, tracks history, records external application redirects, exports CSV and Markdown, and submits applications only after explicit user confirmation (dry run by default). Install with `pip install .` then `python -m playwright install chromium`, and point your MCP client to the `hellowork-mcp` executable. See [docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md).
