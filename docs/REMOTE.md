# Ajouter Hellowork MCP par URL (connecteur personnalisé)

Claude (claude.ai, Claude Desktop, application mobile) accepte des connecteurs personnalisés définis par une URL HTTPS : Paramètres > Connecteurs > Ajouter un connecteur personnalisé, puis « Nom » et « URL du serveur MCP ». Hellowork MCP fournit ce mode avec le transport Streamable HTTP :

```bash
hellowork-mcp --transport http --host 0.0.0.0 --port 8000 --path /mcp-7f3a9c2e51b84d0f
```

Le serveur répond alors sur `http://<machine>:8000/mcp-7f3a9c2e51b84d0f`. Claude se connecte depuis les serveurs d'Anthropic : l'adresse doit être publique et en HTTPS. Une adresse `localhost` ne fonctionne pas dans un connecteur personnalisé.

## Ce qui change en mode HTTP

| Fonction | stdio (local) | HTTP (URL) |
| --- | --- | --- |
| Recherche, analyse, score, historique, redirections | oui | oui |
| `prepare_application` et simulation | oui | oui |
| Envoi réel d'une candidature | oui | non, simulation seulement |
| `hellowork_login`, `check_session`, `clear_session` | oui | non |
| `open_external_redirect` | oui | non (le lien reste dans la réponse) |
| `export_data` | fichier local | fichier sur le serveur et contenu renvoyé dans la réponse |

Les outils refusés ouvriraient une fenêtre sur la machine qui héberge le serveur, pas chez l'utilisateur. L'option `--enable-browser` (ou `HELLOWORK_MCP_ENABLE_BROWSER=1`) les réactive pour un serveur personnel qui tourne sur votre propre PC derrière un tunnel.

## Sécurité

Les connecteurs personnalisés de Claude ne transmettent pas de jeton fixe : le serveur n'a pas d'authentification. Toute personne qui connaît l'URL peut utiliser le serveur, lire et modifier sa configuration et son historique. Deux règles :

1. Choisir un chemin long et aléatoire avec `--path` (ou `HELLOWORK_MCP_PATH`). Exemple sous PowerShell : `"/mcp-" + [guid]::NewGuid().ToString("N")`. Sous macOS et Linux : `echo "/mcp-$(openssl rand -hex 16)"`. Les autres chemins renvoient 404.
2. Un serveur par personne. Ne pas partager l'URL : elle donne accès à vos critères et à votre historique.

## Option 1 : votre PC et un tunnel HTTPS

Le serveur tourne chez vous, un tunnel lui donne une adresse HTTPS publique. Avantage : `--enable-browser` est possible puisque la fenêtre s'ouvre sur votre propre écran.

1. Installer [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (Windows : `winget install Cloudflare.cloudflared`, macOS : `brew install cloudflared`).
2. Terminal 1 :
   ```bash
   hellowork-mcp --transport http --port 8000 --path /mcp-VOTRE-SECRET --enable-browser
   ```
3. Terminal 2 :
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
   cloudflared affiche une adresse du type `https://mots-aleatoires.trycloudflare.com`.
4. Dans Claude, URL du serveur MCP : `https://mots-aleatoires.trycloudflare.com/mcp-VOTRE-SECRET`.

L'adresse `trycloudflare.com` change à chaque lancement et le PC doit rester allumé. Un tunnel nommé Cloudflare donne une adresse fixe.

## Option 2 : hébergement Render (gratuit)

Le dépôt contient un `Dockerfile` et un `render.yaml`.

1. Créer un compte sur https://render.com et le relier à GitHub.
2. New > Blueprint, choisir le dépôt `hellowork-mcp` (ou votre fork).
3. Render demande la valeur de `HELLOWORK_MCP_PATH` : saisir votre chemin secret, par exemple `/mcp-7f3a9c2e51b84d0f`.
4. Après le déploiement, Render affiche l'adresse `https://hellowork-mcp-xxxx.onrender.com`. Vérifier `https://hellowork-mcp-xxxx.onrender.com/healthz` : la réponse est `{"status": "ok", ...}`.
5. Dans Claude, URL du serveur MCP : `https://hellowork-mcp-xxxx.onrender.com/mcp-7f3a9c2e51b84d0f`.

Limites du plan gratuit Render : le service s'endort après 15 minutes sans requête (premier appel lent, environ 30 secondes) et le disque n'est pas persistant, donc la configuration et l'historique sont perdus à chaque redéploiement. Un disque persistant monté sur `/data` (offre payante) les conserve.

## Option 3 : Docker sur votre serveur

```bash
docker build -t hellowork-mcp .
docker run -d --name hellowork-mcp -p 8000:8000 -v hellowork-data:/data \
  -e HELLOWORK_MCP_PATH=/mcp-VOTRE-SECRET \
  -e HELLOWORK_MCP_ALLOWED_HOSTS=mcp.votre-domaine.fr \
  hellowork-mcp
```

Placer un proxy HTTPS devant (Caddy, Nginx, Traefik). `HELLOWORK_MCP_ALLOWED_HOSTS` active le contrôle de l'en-tête `Host` pour votre domaine.

## Ajouter le connecteur dans Claude

1. Claude > Paramètres > Connecteurs > Ajouter un connecteur personnalisé.
2. Nom : `Hellowork`.
3. URL du serveur MCP : l'adresse HTTPS complète, chemin secret compris.
4. Valider, puis activer le connecteur dans une conversation (menu des outils de la zone de saisie).

Les connecteurs personnalisés sont disponibles selon votre offre Claude. Le connecteur ajouté sur claude.ai est aussi disponible dans Claude Desktop et l'application mobile du même compte.

## Variables d'environnement

| Variable | Équivalent CLI | Défaut |
| --- | --- | --- |
| `HELLOWORK_MCP_TRANSPORT` | `--transport` | `stdio` |
| `HELLOWORK_MCP_HOST` | `--host` | `127.0.0.1` |
| `PORT` ou `HELLOWORK_MCP_PORT` | `--port` | `8000` |
| `HELLOWORK_MCP_PATH` | `--path` | `/mcp` |
| `HELLOWORK_MCP_ALLOWED_HOSTS` | `--allowed-host` (répétable) | aucun |
| `HELLOWORK_MCP_ENABLE_BROWSER` | `--enable-browser` | désactivé |
| `HELLOWORK_MCP_DATA_DIR` | aucun | dossier par système |

`GET /healthz` renvoie l'état du serveur pour les sondes des hébergeurs.
