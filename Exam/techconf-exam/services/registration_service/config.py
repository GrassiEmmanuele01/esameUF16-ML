"""Configurazione del registration-service.

Dichiara sia ``USER_SERVICE_URL`` sia ``EVENT_SERVICE_URL`` per la verifica dei
riferimenti verso le due dipendenze di servizio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_NAME = "registration-service"

DEFAULT_PORT = 5003
DEFAULT_STORAGE_BACKEND = "memory"
DEFAULT_DATA_DIR = "./data"
DEFAULT_USER_SERVICE_URL = "http://localhost:5001"
DEFAULT_EVENT_SERVICE_URL = "http://localhost:5002"

_VALID_BACKENDS = frozenset({"memory", "json", "sqlite"})


@dataclass(frozen=True)
class Config:
    """Configurazione immutabile del servizio."""

    port: int = DEFAULT_PORT
    storage_backend: str = DEFAULT_STORAGE_BACKEND
    data_dir: str = DEFAULT_DATA_DIR
    user_service_url: str = DEFAULT_USER_SERVICE_URL
    event_service_url: str = DEFAULT_EVENT_SERVICE_URL

    def __post_init__(self) -> None:
        if self.storage_backend not in _VALID_BACKENDS:
            raise ValueError(
                f"STORAGE_BACKEND non valido: {self.storage_backend!r}. "
                f"Valori ammessi: {sorted(_VALID_BACKENDS)}"
            )


def load_config(env: dict[str, str] | None = None) -> Config:
    """Costruisce la :class:`Config` a partire dall'ambiente (default ``os.environ``)."""
    source = os.environ if env is None else env

    raw_port = source.get("PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        raise ValueError(f"PORT non valido: {raw_port!r}") from None

    storage_backend = source.get("STORAGE_BACKEND", DEFAULT_STORAGE_BACKEND).strip().lower()
    data_dir = source.get("DATA_DIR", DEFAULT_DATA_DIR)
    user_service_url = source.get("USER_SERVICE_URL", DEFAULT_USER_SERVICE_URL).rstrip("/")
    event_service_url = source.get("EVENT_SERVICE_URL", DEFAULT_EVENT_SERVICE_URL).rstrip("/")

    return Config(
        port=port,
        storage_backend=storage_backend,
        data_dir=data_dir,
        user_service_url=user_service_url,
        event_service_url=event_service_url,
    )
