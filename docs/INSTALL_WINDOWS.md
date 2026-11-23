# Installation sous Windows 10 et 11

Commandes à saisir dans PowerShell (menu Démarrer > « PowerShell »).

## 1. Python

```powershell
py --version
```

Une version 3.10 à 3.14 doit s'afficher. Sinon, installer Python depuis https://www.python.org/downloads/windows/ en cochant « Add python.exe to PATH », ou :

```powershell
winget install Python.Python.3.13
```

Si `python` ouvre le Microsoft Store, désactiver les alias dans Paramètres > Applications > Paramètres avancés des applications > Alias d'exécution d'application (lignes `python.exe` et `python3.exe`).

## 2. Git et récupération du projet

```powershell
winget install Git.Git
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
```

Sans Git : bouton Code > Download ZIP sur GitHub, puis extraire l'archive.

## 3. Environnement virtuel

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell refuse l'exécution du script (`running scripts is disabled on this system`) :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Le préfixe `(.venv)` apparaît devant l'invite une fois l'environnement actif.

## 4. Dépendances et navigateur

```powershell
python -m pip install --upgrade pip
python -m pip install .
hellowork-mcp --install-browser
```

`hellowork-mcp --install-browser` équivaut à `python -m playwright install chromium`. Chromium est placé dans `%LOCALAPPDATA%\ms-playwright`.

## 5. Vérification

```powershell
hellowork-mcp --check
(Get-Command hellowork-mcp).Source
```

La seconde commande donne le chemin à copier dans la configuration du client MCP, par exemple `C:\Users\vous\hellowork-mcp\.venv\Scripts\hellowork-mcp.exe`.

## 6. Client MCP

Voir [MCP_CLIENTS.md](MCP_CLIENTS.md). Exemple pour Claude Desktop, fichier `%APPDATA%\Claude\claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "hellowork": {
      "command": "C:\\Users\\vous\\hellowork-mcp\\.venv\\Scripts\\hellowork-mcp.exe"
    }
  }
}
```

## Mise à jour

```powershell
cd hellowork-mcp
git pull
.venv\Scripts\Activate.ps1
python -m pip install .
hellowork-mcp --install-browser
```

Redémarrer ensuite le client MCP.

## Désinstallation

Supprimer le dossier du projet, puis le dossier de données `%LOCALAPPDATA%\hellowork-mcp` si vous voulez effacer l'historique et la session.
