# Contribuer

## Mise en place

```bash
git clone https://github.com/ATSU-ADJOTO007/hellowork-mcp.git
cd hellowork-mcp
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Avant chaque commit

```bash
python -m ruff check src tests scripts
python -m pytest
python scripts/check_dashes.py
python scripts/check_sensitive_files.py
```

La CI exécute les mêmes commandes sur Windows, macOS et Linux.

## Organisation du code

| Fichier | Rôle |
| --- | --- |
| `src/hellowork_mcp/server.py` | Déclaration des outils MCP |
| `src/hellowork_mcp/search.py` | Requêtes HTTP, URL de recherche, pagination |
| `src/hellowork_mcp/parsing.py` | Sélecteurs HTML et lecture du JSON-LD |
| `src/hellowork_mcp/scoring.py` | Barème du score sur 100 |
| `src/hellowork_mcp/filters.py` | Normalisation et mots-clés |
| `src/hellowork_mcp/applications.py` | Contrôles avant candidature et jetons |
| `src/hellowork_mcp/browser.py` | Playwright : connexion, session, formulaire de candidature |
| `src/hellowork_mcp/redirects.py` | Classement et registre des liens externes |
| `src/hellowork_mcp/history.py` | Historique et statuts |
| `src/hellowork_mcp/exports.py` | CSV et Markdown |
| `src/hellowork_mcp/config.py` | Configuration validée |
| `src/hellowork_mcp/storage.py` | Écritures JSON atomiques |
| `src/hellowork_mcp/paths.py` | Dossiers de données par système |

## Règles

- Tests avec des données fictives uniquement (`tests/fixtures/`). Aucune donnée personnelle réelle, aucun cookie.
- Un test qui contacte hellowork.com porte le marqueur `@pytest.mark.live`.
- Pas de `except` qui avale une erreur sans la tracer ni la remonter.
- Documentation en français, sans tiret cadratin ni demi-cadratin (contrôlé par `scripts/check_dashes.py`).
- Si Hellowork modifie ses pages, mettre à jour `parsing.py` et les fixtures correspondantes dans le même commit.
- L'icône se régénère avec `python scripts/make_icon.py`.

## Publier une version

1. Mettre à jour la version dans `pyproject.toml` et `src/hellowork_mcp/__init__.py`.
2. Compléter `CHANGELOG.md`.
3. `git tag v1.x.y` puis `git push origin main --tags`.
4. Créer la release GitHub à partir du tag, avec la section du changelog comme notes.
