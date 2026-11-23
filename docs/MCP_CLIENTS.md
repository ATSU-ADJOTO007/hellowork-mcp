# Configuration des clients MCP

Hellowork MCP est un serveur MCP en transport `stdio`. Le client lance l'exécutable `hellowork-mcp` et dialogue avec lui sur l'entrée et la sortie standard. Il n'y a ni port ni clé d'API à configurer.

Formats relevés en novembre 2026 sur la documentation officielle de chaque client. Si un client change de format, sa documentation fait foi.

## Trouver le chemin de l'exécutable

| Installation | Windows | macOS et Linux |
| --- | --- | --- |
| Environnement virtuel du projet | `C:\Users\vous\hellowork-mcp\.venv\Scripts\hellowork-mcp.exe` | `/Users/vous/hellowork-mcp/.venv/bin/hellowork-mcp` |
| `uv tool install` | `C:\Users\vous\.local\bin\hellowork-mcp.exe` | `~/.local/bin/hellowork-mcp` |

Environnement activé, `(Get-Command hellowork-mcp).Source` (PowerShell) ou `which hellowork-mcp` (macOS, Linux) affiche le chemin exact. Dans les exemples ci-dessous, remplacer `CHEMIN_EXE` par ce chemin.

Dans un fichier JSON sous Windows, chaque `\` s'écrit `\\`, ou bien on utilise `/` : `"C:/Users/vous/hellowork-mcp/.venv/Scripts/hellowork-mcp.exe"` fonctionne aussi.

Variable facultative, commune à tous les clients : `HELLOWORK_MCP_DATA_DIR` pour changer le dossier de données. Exemple JSON : `"env": {"HELLOWORK_MCP_DATA_DIR": "D:/hellowork-data"}`.

## Claude (connecteur personnalisé par URL)

claude.ai, Claude Desktop et l'application mobile acceptent un connecteur ajouté par URL HTTPS : Paramètres > Connecteurs > Ajouter un connecteur personnalisé, Nom `Hellowork`, URL `https://votre-adresse/mcp-VOTRE-SECRET`. Le serveur doit tourner en mode HTTP et être exposé en HTTPS : voir [REMOTE.md](REMOTE.md).

## Claude Desktop

Fichier : Paramètres > Développeur > Modifier la configuration, ce qui ouvre `claude_desktop_config.json`.

- Windows : `%APPDATA%\Claude\claude_desktop_config.json`
- macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux : Claude Desktop n'a pas de version Linux officielle.

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN_EXE"
    }
  }
}
```

Si le fichier contient déjà d'autres serveurs, ajouter seulement l'entrée `"hellowork"` dans l'objet `mcpServers` existant.

Redémarrage : quitter complètement Claude Desktop (clic droit sur l'icône de la barre des tâches > Quitter sous Windows, Claude > Quitter Claude sous macOS) puis le relancer. Fermer la fenêtre ne suffit pas.

Vérification : l'icône des connecteurs de la zone de saisie liste « hellowork » et ses outils. En cas d'échec, les journaux se trouvent dans `%APPDATA%\Claude\logs\mcp-server-hellowork.log` (Windows) ou `~/Library/Logs/Claude/mcp-server-hellowork.log` (macOS).

## Claude Code

```bash
claude mcp add --scope user hellowork -- CHEMIN_EXE
```

- `--scope user` : disponible dans tous vos projets.
- `--scope project` : écrit un fichier `.mcp.json` à la racine du projet, partageable avec l'équipe.
- sans option : portée locale au projet courant.

Fichier `.mcp.json` équivalent :

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN_EXE",
      "args": []
    }
  }
}
```

Vérification : `claude mcp list` affiche `hellowork: ... - Connected`. Dans une session, la commande `/mcp` montre l'état et les outils.

## OpenAI Codex (CLI et extension)

```bash
codex mcp add hellowork -- CHEMIN_EXE
codex mcp list
```

Configuration manuelle dans `~/.codex/config.toml` (Windows : `%USERPROFILE%\.codex\config.toml`) :

```toml
[mcp_servers.hellowork]
command = "CHEMIN_EXE"
args = []
startup_timeout_sec = 20
```

Le fichier est partagé entre la CLI Codex et l'extension Codex pour VS Code. Dans une session, `/mcp` liste les serveurs actifs.

## Cursor

- Global : `~/.cursor/mcp.json` (Windows : `%USERPROFILE%\.cursor\mcp.json`)
- Projet : `.cursor/mcp.json` à la racine du projet

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN_EXE",
      "args": []
    }
  }
}
```

Vérification : Cursor Settings > MCP (ou Tools & Integrations) affiche « hellowork » avec un indicateur vert et la liste des outils. Après modification du fichier, désactiver puis réactiver le serveur ou redémarrer Cursor.

## VS Code (GitHub Copilot, mode agent)

Espace de travail : `.vscode/mcp.json`. Configuration utilisateur : palette de commandes > « MCP: Open User Configuration ». La clé racine est `servers` et non `mcpServers`.

```json
{
  "servers": {
    "hellowork": {
      "type": "stdio",
      "command": "CHEMIN_EXE",
      "args": []
    }
  }
}
```

Ajout en ligne de commande :

```bash
code --add-mcp "{\"name\":\"hellowork\",\"command\":\"CHEMIN_EXE\"}"
```

Vérification : palette > « MCP: List Servers », puis le bouton outils de la vue Chat en mode Agent.

## Cline

Panneau Cline > icône MCP Servers > onglet Installed (ou Configure) > « Configure MCP Servers ». Cela ouvre `cline_mcp_settings.json`.

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN_EXE",
      "args": [],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Laisser `autoApprove` vide : chaque appel d'outil est alors soumis à votre accord, ce qui convient à `submit_application`.

## Windsurf

Fichier `~/.codeium/windsurf/mcp_config.json` (Windows : `%USERPROFILE%\.codeium\windsurf\mcp_config.json`), accessible aussi par Windsurf Settings > Cascade > MCP Servers > View raw config.

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "CHEMIN_EXE",
      "args": []
    }
  }
}
```

Vérification : bouton Refresh du panneau MCP de Cascade, le serveur doit apparaître avec ses outils.

## Autres clients

Tout client MCP compatible `stdio` fonctionne avec la commande `CHEMIN_EXE` sans argument. Pour tester sans client, l'inspecteur officiel :

```bash
npx @modelcontextprotocol/inspector CHEMIN_EXE
```

## Icône

Le serveur déclare une icône PNG dans le champ `icons` de la spécification MCP, pris en charge par le SDK Python `mcp` installé. Les clients qui n'affichent pas encore les icônes ignorent ce champ sans erreur.

## Bundle MCPB

Le format MCPB (extension installable en un clic dans Claude Desktop) a été étudié et n'est pas proposé pour la version 1.0.0. Playwright embarque un pilote propre à chaque système et Chromium doit être téléchargé séparément (environ 150 Mo) : un bundle unique ne fonctionnerait pas sur les trois systèmes sans étape manuelle. L'installation par `pip` ou `uv tool install` reste la méthode prise en charge.
