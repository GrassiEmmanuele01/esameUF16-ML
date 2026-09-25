"""Implementazioni concrete di :class:`UserRepository`.

Tre backend intercambiabili, tutti basati sulla sola standard library:
  * :class:`MemoryUserRepository` — store in memoria (dict).
  * :class:`JsonUserRepository`   — persistenza su file ``.json``.
  * :class:`SqliteUserRepository` — persistenza relazionale via ``sqlite3``.

Tutti garantiscono la memorizzazione dell'email in minuscolo (REQ-USR-B02) e
l'univocità case-insensitive (REQ-USR-B01).
"""

from __future__ import annotations

from .json_repository import JsonUserRepository
from .memory_repository import MemoryUserRepository
from .sqlite_repository import SqliteUserRepository

__all__ = [
    "MemoryUserRepository",
    "JsonUserRepository",
    "SqliteUserRepository",
]
