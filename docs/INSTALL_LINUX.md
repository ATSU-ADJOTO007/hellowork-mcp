# Installation sous Linux

Testé sur la CI avec Ubuntu (`ubuntu-latest`). Les commandes des autres distributions sont données à titre d'équivalence.

## 1. Python, venv et Git

Ubuntu et Debian :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Fedora :

```bash
sudo dnf install -y python3 python3-pip git
```

Arch Linux :

```bash
sudo pacman -S --needed python python-pip git
```

Vérifier : `python3 --version` doit afficher 3.10 à 3.14.

## 2. Projet et environnement virtuel

```bash
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

## 3. Chromium et bibliothèques système

```bash
hellowork-mcp --install-browser
sudo .venv/bin/python -m playwright install-deps chromium
```

`install-deps` installe les bibliothèques requises par Chromium et ne fonctionne qu'avec `apt` (Ubuntu, Debian). Sur Fedora ou Arch, si Chromium ne démarre pas, l'erreur Playwright indique la bibliothèque manquante à installer avec le gestionnaire de paquets.

La connexion manuelle (`hellowork_login`) ouvre une fenêtre : elle exige une session graphique (X11 ou Wayland). Sur un serveur sans écran, la recherche et l'analyse fonctionnent, la connexion non.

## 4. Vérification

```bash
hellowork-mcp --check
which hellowork-mcp
```

## 5. Client MCP

Claude Desktop n'existe pas sous Linux. Utiliser Claude Code, Codex, Cursor, VS Code, Cline ou Windsurf : voir [MCP_CLIENTS.md](MCP_CLIENTS.md).

```bash
claude mcp add --scope user hellowork -- "$(which hellowork-mcp)"
```

## Données

Dossier par défaut : `$XDG_DATA_HOME/hellowork-mcp`, ou `~/.local/share/hellowork-mcp` si `XDG_DATA_HOME` n'est pas défini.

## Mise à jour

```bash
cd hellowork-mcp && git pull
source .venv/bin/activate
python -m pip install .
hellowork-mcp --install-browser
```
