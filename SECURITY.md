# Sécurité

## Versions prises en charge

| Version | Correctifs de sécurité |
| --- | --- |
| 1.1.x | oui |
| 1.0.x | non |

## Signaler une vulnérabilité

Utiliser l'onglet Security > Report a vulnerability du dépôt GitHub (signalement privé). Ne pas ouvrir d'issue publique pour une faille. Joindre la version, le système, les étapes de reproduction et l'impact. Ne jamais joindre de cookies, de profil navigateur ni d'historique de candidatures réel.

## Modèle de sécurité

- **Identifiants** : le serveur ne demande, ne saisit et ne stocke aucun mot de passe. La connexion se fait à la main dans Chromium. Seuls les cookies de session restent dans `browser-profile/`, dans le dossier de données de l'utilisateur.
- **Protections du site** : aucun contournement de CAPTCHA, de double authentification ou de limitation de débit. Une pause de 1,5 seconde minimum sépare deux requêtes.
- **Candidatures** : un envoi réel exige `dry_run=false`, un jeton de confirmation de 15 minutes à usage unique lié à l'offre et au texte exact du message, et `user_confirmed=true`. Les contrôles (doublon, limite quotidienne, score, mots-clés interdits) sont refaits au moment de l'envoi.
- **Liens externes** : seules les URL `http` et `https` enregistrées au préalable peuvent être ouvertes, une seule fois sauf demande explicite (`force=true`). Les schémas `file:`, `javascript:` et autres sont refusés.
- **Paramètres** : les identifiants d'offre sont limités à des chiffres avant toute construction d'URL. Les paramètres de recherche sont encodés avec `urllib.parse.urlencode`. La configuration est validée par pydantic et les champs inconnus sont refusés.
- **Exports** : les cellules CSV qui commencent par `=`, `+`, `-` ou `@` sont préfixées d'une apostrophe pour empêcher l'exécution de formules dans Excel.
- **Fichiers** : écriture atomique (fichier temporaire puis `os.replace`). Aucune donnée personnelle n'est envoyée ailleurs que vers hellowork.com.
- **Dépôt** : `.gitignore` exclut sessions, historiques, configuration et exports. `scripts/check_sensitive_files.py` vérifie en CI qu'aucun fichier sensible ou jeton n'est suivi par Git.

## Risques connus

- En mode HTTP (connecteur par URL), le serveur n'a pas d'authentification : toute personne qui connaît l'URL accède à la configuration et à l'historique. Utiliser un chemin secret long (`--path`) et un serveur par personne. Les outils qui pilotent un navigateur y sont désactivés par défaut.

- Le profil Chromium local donne accès au compte Hellowork à toute personne qui peut lire votre dossier utilisateur. Utiliser `clear_session` sur un poste partagé.
- Un agent IA mal configuré pourrait appeler `submit_application` avec `user_confirmed=true` sans vous avoir consulté. Garder `dry_run=true` tant que le client n'impose pas une validation des appels d'outils, et ne pas mettre `submit_application` en approbation automatique.
- L'automatisation d'un site tiers peut être limitée par ses conditions d'utilisation. L'utilisateur reste responsable de son usage.
