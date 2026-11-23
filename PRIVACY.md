# Politique de confidentialité de Hellowork MCP

Dernière mise à jour : 23 novembre 2026. S'applique à la version 1.1.0 et suivantes.

Hellowork MCP est un logiciel open source (licence MIT) publié sur https://github.com/ATSU-ADJOTO007/hellowork-mcp. Il n'est pas affilié à Hellowork. Le développeur ne fait fonctionner aucun service central : chaque utilisateur exécute le serveur sur sa machine ou sur l'hébergement qu'il choisit, et il est seul responsable des données qui y sont conservées.

## Données traitées

| Donnée | Origine | Emplacement | Durée |
| --- | --- | --- | --- |
| Critères de recherche (postes, mots-clés, lieux, salaire, seuils) | saisis par l'utilisateur via `update_config` | `config.json` dans le dossier de données | jusqu'à suppression par l'utilisateur |
| Historique des offres (identifiant, titre, entreprise, URL, score, statut, date) | pages publiques hellowork.com | `history.json` | jusqu'à suppression, 20 000 événements au maximum |
| Liens de candidature externes | pages publiques hellowork.com | `redirects.json` | jusqu'à suppression |
| Fichiers d'export | demande de l'utilisateur | dossier `exports/` | jusqu'à suppression |
| Cookies de session Hellowork (mode local seulement) | connexion manuelle de l'utilisateur dans Chromium | `browser-profile/` | jusqu'à `clear_session` ou suppression du dossier |
| Message au recruteur | saisi par l'utilisateur | transmis à Hellowork uniquement lors d'un envoi réel validé, non conservé par le serveur | aucune conservation |

Le serveur ne collecte pas : mot de passe, conversation avec l'assistant, mémoire ou fichiers de Claude, données d'analyse d'usage, identifiant publicitaire. Il ne contient aucun traceur et n'envoie aucune télémétrie.

## Destinataires

- **hellowork.com** : requêtes de recherche et de lecture d'offres, et, en mode local avec accord explicite, le formulaire de candidature.
- **Sites externes** : uniquement lorsque l'utilisateur demande l'ouverture d'un lien de candidature enregistré (`open_external_redirect`), dans son propre navigateur.
- **Hébergeur choisi par l'utilisateur** : en mode HTTP, les fichiers ci-dessus sont stockés sur la machine de l'hébergeur (par exemple Render), selon sa propre politique.

Aucune donnée n'est vendue, partagée ni transmise au développeur du projet.

## Mode HTTP (connecteur par URL)

En mode HTTP, le serveur n'a pas de comptes utilisateurs : toutes les personnes qui connaissent l'URL partagent la même configuration et le même historique. Un serveur par personne et un chemin d'URL secret sont donc requis (voir `docs/REMOTE.md`). Les outils de connexion et d'envoi réel y sont désactivés : aucun cookie Hellowork n'est stocké sur un serveur distant par défaut.

## Vos droits et la suppression des données

Toutes les données sont dans le dossier de données de votre installation :

- Windows : `%LOCALAPPDATA%\hellowork-mcp`
- macOS : `~/Library/Application Support/hellowork-mcp`
- Linux : `~/.local/share/hellowork-mcp`
- Docker et Render : volume `/data`

Supprimer ce dossier efface l'ensemble des données. L'outil `clear_session` supprime seulement la session navigateur. Pour les données détenues par Hellowork (compte, candidatures envoyées), s'adresser à Hellowork selon sa propre politique de confidentialité.

## Contact

Questions et demandes : https://github.com/ATSU-ADJOTO007/hellowork-mcp/issues. Signalement de faille : onglet Security du dépôt (voir `SECURITY.md`).
