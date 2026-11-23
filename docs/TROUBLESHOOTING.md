# Dépannage

Premier réflexe : `hellowork-mcp --check`. Le rapport JSON indique le dossier de données, l'état du serveur et la présence de Chromium.

## Installation

| Symptôme | Cause | Correction |
| --- | --- | --- |
| `python` ouvre le Microsoft Store | Alias Windows | Utiliser `py`, ou désactiver les alias d'exécution d'application |
| `Activate.ps1 cannot be loaded` | Stratégie d'exécution PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No matching distribution found for mcp` | Python trop ancien | Installer Python 3.10 ou plus récent |
| `hellowork-mcp` introuvable | Environnement non activé | Activer `.venv`, ou utiliser le chemin complet de l'exécutable |
| `error: externally-managed-environment` (Linux) | pip hors environnement virtuel | Créer et activer `.venv` avant `pip install` |

## Navigateur

| Symptôme | Correction |
| --- | --- |
| `Executable doesn't exist at ...ms-playwright...` | `hellowork-mcp --install-browser` avec la même installation que celle utilisée par le client MCP |
| `Host system is missing dependencies` (Linux) | `sudo .venv/bin/python -m playwright install-deps chromium` |
| `Le profil est déjà utilisé par une autre instance` | Deux clients MCP lancent le serveur en même temps. Fermer l'un des deux : le profil Chromium n'accepte qu'un processus |
| La fenêtre de connexion ne s'ouvre pas (Linux) | Session graphique absente : lancer le client depuis un bureau X11 ou Wayland |

## Client MCP

| Symptôme | Correction |
| --- | --- |
| Serveur absent dans Claude Desktop | Vérifier le JSON (virgules, `\\` sous Windows), le chemin absolu, puis quitter complètement l'application |
| `spawn ... ENOENT` dans les journaux | Le chemin `command` est faux : copier la sortie de `(Get-Command hellowork-mcp).Source` ou `which hellowork-mcp` |
| Outils visibles mais erreurs `ModuleNotFoundError` | Le client lance un autre Python : pointer vers l'exécutable `hellowork-mcp` du `.venv` |
| VS Code ne voit pas le serveur | La clé racine de `.vscode/mcp.json` est `servers`, pas `mcpServers` |
| Démarrage trop lent dans Codex | Ajouter `startup_timeout_sec = 20` dans la section `[mcp_servers.hellowork]` |

Journaux de Claude Desktop : `%APPDATA%\Claude\logs\` (Windows), `~/Library/Logs/Claude/` (macOS). Le serveur écrit ses propres messages sur la sortie d'erreur. Pour plus de détails, ajouter `"args": ["--log-level", "DEBUG"]` à la configuration.

## Hellowork

| Message | Signification |
| --- | --- |
| `StructureChangedError` | Les pages Hellowork ont changé. Les sélecteurs sont regroupés dans `src/hellowork_mcp/parsing.py`. Ouvrir une issue avec l'URL |
| `Hellowork a répondu 403` ou `429` | Trop de requêtes ou blocage temporaire. Augmenter `request_delay_seconds` (par exemple 4) et réessayer plus tard |
| `L'offre ... n'est plus disponible` | Offre expirée ou retirée |
| `login_required: true` | Session expirée : lancer `hellowork_login` |
| `manual_action_required` après `submit_application` | Hellowork demande une étape inconnue (CV, questionnaire). Terminer dans la fenêtre, puis vérifier « Mes candidatures » |

## Données

Un fichier `history.corrupt-20261123-101500.json` dans le dossier de données signifie que `history.json` était illisible. Le serveur l'a mis de côté et repart d'un historique vide. Le fichier mis de côté peut être réparé à la main puis renommé en `history.json`, serveur arrêté.

Pour repartir de zéro, arrêter le client MCP puis supprimer le dossier de données (voir README, section Stockage des données).
