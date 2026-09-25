"""Implementazioni concrete di :class:`RegistrationRepository` + factory."""

from __future__ import annotations

from .factory import build_repository
from .json_repository import JsonRegistrationRepository
from .memory_repository import MemoryRegistrationRepository
from .sqlite_repository import SqliteRegistrationRepository

__all__ = [
    "MemoryRegistrationRepository",
    "JsonRegistrationRepository",
    "SqliteRegistrationRepository",
    "build_repository",
]
