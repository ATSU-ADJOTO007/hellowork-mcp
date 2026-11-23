# Installation de Hellowork MCP sous Windows, en une commande PowerShell :
#   irm https://raw.githubusercontent.com/ATSU-ADJOTO007/hellowork-mcp/main/install.ps1 | iex
#
# Étapes : uv (gestionnaire Python d'Astral, sans droits administrateur), Hellowork MCP,
# navigateur Chromium, puis ajout automatique dans Claude Desktop (et Claude Code s'il est installé).
# Aucune donnée personnelle n'est demandée ni envoyée.

& {
    # Pas de "Stop" : sous PowerShell 5.1, la progression qu'uv écrit sur stderr deviendrait une erreur fatale.
    # Chaque étape vérifie plutôt le code de sortie avec Check.
    $ErrorActionPreference = "Continue"
    $source = if ($env:HELLOWORK_MCP_SOURCE) { $env:HELLOWORK_MCP_SOURCE } else {
        "https://github.com/ATSU-ADJOTO007/hellowork-mcp/archive/refs/heads/main.zip"
    }

    function Step($n, $text) { Write-Host "`n[$n/4] $text" -ForegroundColor Cyan }
    function Check($what) {
        if ($LASTEXITCODE -ne 0) { throw "Échec : $what (code $LASTEXITCODE). Relancez la commande ou consultez docs/TROUBLESHOOTING.md." }
    }

    Step 1 "Outil d'installation uv"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    uv --version; Check "installation de uv"

    Step 2 "Hellowork MCP (Python est téléchargé automatiquement si besoin)"
    uv tool install --force --python 3.12 $source; Check "installation de Hellowork MCP"
    $bin = (uv tool dir --bin).Trim()
    $exe = Join-Path $bin "hellowork-mcp.exe"
    if (-not (Test-Path $exe)) { throw "Commande introuvable : $exe" }

    Step 3 "Navigateur Chromium (environ 150 Mo, quelques minutes)"
    & $exe --install-browser; Check "téléchargement de Chromium"

    Step 4 "Ajout dans Claude Desktop"
    & $exe --setup-claude; Check "configuration de Claude Desktop"

    Write-Host "`nInstallation terminée." -ForegroundColor Green
    Write-Host "Quittez complètement Claude Desktop (clic droit sur son icône près de l'horloge > Quitter), puis relancez-le."
    Write-Host "Essayez ensuite : « Cherche des offres de développeur Python à Lyon sur Hellowork »."
}
