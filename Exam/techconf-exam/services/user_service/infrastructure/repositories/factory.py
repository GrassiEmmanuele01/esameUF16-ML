"""Factory per la selezione del backend di persistenza.

Costruisce l'implementazione concreta di :class:`UserRepository` a partire dalla
configurazione (``STORAGE_BACKEND``). Per i backend ``json``/``sqlite`` crea la
directory ``DATA_DIR`` se assente. Non introduce dipendenze esterne.
"""

from __future__ import annotations

from pathlib import Path

from ...config import Config
from ...domain.repository import UserRepository
from .json_repository import JsonUserRepository
from .memory_repository import MemoryUserRepository
from .sqlite_repository import SqliteUserRepository

_JSON_FILENAME = "users.json"
_SQLITE_FILENAME = "users.db"


def build_repository(config: Config) -> UserRepository:
    """Restituisce il repository concreto per il backend configurato.

    ``memory`` -> :class:`MemoryUserRepository`
    ``json``   -> :class:`JsonUserRepository`   (file in ``DATA_DIR``)
    ``sqlite`` -> :class:`SqliteUserRepository`  (db in ``DATA_DIR``)
    """
    backend = config.storage_backend
    if backend == "memory":
        return MemoryUserRepository()

    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if backend == "json":
        return JsonUserRepository(data_dir / _JSON_FILENAME)
    if backend == "sqlite":
        return SqliteUserRepository(data_dir / _SQLITE_FILENAME)

    # config.Config valida già il backend; questo ramo è una difesa aggiuntiva.
    raise ValueError(f"STORAGE_BACKEND non supportato: {backend!r}")
