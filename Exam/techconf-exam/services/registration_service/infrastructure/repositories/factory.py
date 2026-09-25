"""Factory per la selezione del backend di persistenza delle iscrizioni."""

from __future__ import annotations

from pathlib import Path

from ...config import Config
from ...domain.repository import RegistrationRepository
from .json_repository import JsonRegistrationRepository
from .memory_repository import MemoryRegistrationRepository
from .sqlite_repository import SqliteRegistrationRepository

_JSON_FILENAME = "registrations.json"
_SQLITE_FILENAME = "registrations.db"


def build_repository(config: Config) -> RegistrationRepository:
    """Restituisce il repository concreto per il backend configurato."""
    backend = config.storage_backend
    if backend == "memory":
        return MemoryRegistrationRepository()

    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if backend == "json":
        return JsonRegistrationRepository(data_dir / _JSON_FILENAME)
    if backend == "sqlite":
        return SqliteRegistrationRepository(data_dir / _SQLITE_FILENAME)

    raise ValueError(f"STORAGE_BACKEND non supportato: {backend!r}")
