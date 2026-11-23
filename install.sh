#!/bin/sh
# Installation de Hellowork MCP sous macOS et Linux, en une commande :
#   curl -LsSf https://raw.githubusercontent.com/ATSU-ADJOTO007/hellowork-mcp/main/install.sh | sh
#
# Étapes : uv (gestionnaire Python d'Astral, sans sudo), Hellowork MCP, navigateur Chromium,
# puis ajout automatique dans Claude Desktop (et Claude Code s'il est installé).
set -eu

SOURCE="${HELLOWORK_MCP_SOURCE:-https://github.com/ATSU-ADJOTO007/hellowork-mcp/archive/refs/heads/main.zip}"

step() { printf '\n[%s/4] %s\n' "$1" "$2"; }

step 1 "Outil d'installation uv"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
    export PATH
fi
uv --version

step 2 "Hellowork MCP (Python est téléchargé automatiquement si besoin)"
uv tool install --force --python 3.12 "$SOURCE"
EXE="$(uv tool dir --bin)/hellowork-mcp"

step 3 "Navigateur Chromium (environ 150 Mo, quelques minutes)"
"$EXE" --install-browser
if [ "$(uname)" = "Linux" ]; then
    echo "Linux : si Chromium ne démarre pas, lancer : sudo \"$(uv tool dir)/hellowork-mcp/bin/python\" -m playwright install-deps chromium"
fi

step 4 "Ajout dans Claude Desktop"
"$EXE" --setup-claude

printf '\nInstallation terminée.\n'
echo "Quittez complètement Claude Desktop (Claude > Quitter Claude), puis relancez-le."
echo "Essayez ensuite : « Cherche des offres de développeur Python à Lyon sur Hellowork »."
