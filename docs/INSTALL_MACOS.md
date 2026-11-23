# Installation sous macOS (Intel et Apple Silicon)

Commandes à saisir dans Terminal (Applications > Utilitaires > Terminal).

## 1. Python

```bash
python3 --version
```

Une version 3.10 à 3.14 doit s'afficher. Le `python3` fourni par les outils de développement Apple peut être plus ancien. Installer une version récente avec Homebrew ou depuis https://www.python.org/downloads/macos/ :

```bash
brew install python@3.13
```

## 2. Récupération du projet

```bash
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
```

Au premier appel, macOS propose d'installer les outils de ligne de commande qui fournissent `git`.

## 3. Environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Dépendances et navigateur

```bash
python -m pip install --upgrade pip
python -m pip install .
hellowork-mcp --install-browser
```

Playwright télécharge la version de Chromium adaptée au processeur (arm64 sur Apple Silicon, x64 sur Intel) dans `~/Library/Caches/ms-playwright`.

## 5. Vérification

```bash
hellowork-mcp --check
which hellowork-mcp
```

## 6. Client MCP

Voir [MCP_CLIENTS.md](MCP_CLIENTS.md). Exemple pour Claude Desktop, fichier `~/Library/Application Support/Claude/claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "/Users/vous/hellowork-mcp/.venv/bin/hellowork-mcp"
    }
  }
}
```

Lors de la première connexion, macOS peut demander l'autorisation d'ouvrir « Chromium » : l'accepter.

## Mise à jour

```bash
cd hellowork-mcp
git pull
source .venv/bin/activate
python -m pip install .
hellowork-mcp --install-browser
```

## Désinstallation

Supprimer le dossier du projet et, pour effacer les données, `~/Library/Application Support/hellowork-mcp`.
