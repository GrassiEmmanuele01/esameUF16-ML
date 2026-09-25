"""Configurazione dello user-service.

La configurazione è letta dall'ambiente. Nessun valore critico è hardcoded al
di fuori di un default di fallback per lo sviluppo locale.

Variabili:
  * ``PORT``            porta di ascolto (default 5001).
  * ``STORAGE_BACKEND`` backend di persistenza: memory | json | sqlite (default memory).
  * ``DATA_DIR``        directory dei file per i backend json/sqlite (default ./data).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_NAME = "user-service"

DEFAULT_PORT = 5001
DEFAULT_STORAGE_BACKEND = "memory"
DEFAULT_DATA_DIR = "./data"

_VALID_BACKENDS = frozenset({"memory", "json", "sqlite"})


@dataclass(frozen=True)
class Config:
    """Configurazione immutabile del servizio."""

    port: int = DEFAULT_PORT
    storage_backend: str = DEFAULT_STORAGE_BACKEND
    data_dir: str = DEFAULT_DATA_DIR

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

    return Config(port=port, storage_backend=storage_backend, data_dir=data_dir)
