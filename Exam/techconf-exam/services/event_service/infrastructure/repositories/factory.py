"""Factory per la selezione del backend di persistenza degli eventi."""

from __future__ import annotations

from pathlib import Path

from ...config import Config
from ...domain.repository import EventRepository
from .json_repository import JsonEventRepository
from .memory_repository import MemoryEventRepository
from .sqlite_repository import SqliteEventRepository

_JSON_FILENAME = "events.json"
_SQLITE_FILENAME = "events.db"


def build_repository(config: Config) -> EventRepository:
    """Restituisce il repository concreto per il backend configurato."""
    backend = config.storage_backend
    if backend == "memory":
        return MemoryEventRepository()

    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if backend == "json":
        return JsonEventRepository(data_dir / _JSON_FILENAME)
    if backend == "sqlite":
        return SqliteEventRepository(data_dir / _SQLITE_FILENAME)

    raise ValueError(f"STORAGE_BACKEND non supportato: {backend!r}")
