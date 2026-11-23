"""Refuse la publication de fichiers sensibles suivis par Git.

Vérifie la liste `git ls-files` : profils navigateur, cookies, historiques, exports, fichiers .env,
clés privées et motifs de jetons courants. Code de sortie 1 si un problème est trouvé.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_PATHS = [
    re.compile(p)
    for p in (
        r"(^|/)\.env($|\.)",
        r"(^|/)browser-profile/",
        r"(^|/)cookies?(\.json|\.txt|\.sqlite)?$",
        r"(^|/)history\.json$",
        r"(^|/)redirects\.json$",
        r"(^|/)config\.json$",
        r"(^|/)exports/",
        r"\.(pem|key|p12|pfx)$",
        r"(^|/)storage_state\.json$",
    )
]
FORBIDDEN_CONTENT = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "clé privée"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "jeton GitHub"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{40,}"), "jeton GitHub"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "clé d'API"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "clé AWS"),
]
ALLOWED = {"scripts/check_sensitive_files.py", "tests/test_check_scripts.py"}


def tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in result.stdout.decode("utf-8").split("\0") if p]


def main() -> int:
    try:
        files = tracked_files()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"git ls-files impossible : {exc}", file=sys.stderr)
        return 1
    problems = []
    for name in files:
        if name in ALLOWED:
            continue
        for pattern in FORBIDDEN_PATHS:
            if pattern.search(name):
                problems.append(f"{name}: fichier sensible suivi par Git ({pattern.pattern})")
        path = Path(name)
        if path.is_file() and path.stat().st_size < 2_000_000:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern, label in FORBIDDEN_CONTENT:
                if pattern.search(text):
                    problems.append(f"{name}: {label} détecté")
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"{len(files)} fichier(s) suivi(s) contrôlé(s), aucun fichier sensible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
