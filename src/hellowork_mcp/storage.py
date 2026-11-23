"""Lecture et écriture JSON protégées contre la corruption.

- écriture atomique : fichier temporaire dans le même dossier, fsync, puis os.replace
- verrou par fichier (threading) pour sérialiser les écritures du processus
- fichier illisible : il est renommé en *.corrupt-<horodatage>.json et la valeur par défaut est utilisée
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()


def lock_for(path: Path) -> threading.RLock:
    key = str(Path(path).resolve())
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.RLock()
        return _locks[key]


def read_json(path: Path, default_factory: Callable[[], Any]) -> Any:
    path = Path(path)
    with lock_for(path):
        if not path.exists():
            return default_factory()
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
            os.replace(path, backup)
            log.error("Fichier JSON corrompu %s (%s). Copie conservée dans %s", path, exc, backup)
            return default_factory()


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock_for(path):
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise


def update_json(path: Path, default_factory: Callable[[], Any], mutate: Callable[[Any], Any]) -> Any:
    """Lit, modifie et réécrit le fichier sous le même verrou. Retourne la valeur de `mutate`."""
    with lock_for(path):
        data = read_json(path, default_factory)
        result = mutate(data)
        write_json(path, data)
        return result
