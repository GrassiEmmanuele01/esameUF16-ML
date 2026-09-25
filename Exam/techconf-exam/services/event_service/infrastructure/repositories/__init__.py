"""Implementazioni concrete di :class:`EventRepository` + factory."""

from __future__ import annotations

from .factory import build_repository
from .json_repository import JsonEventRepository
from .memory_repository import MemoryEventRepository
from .sqlite_repository import SqliteEventRepository

__all__ = [
    "MemoryEventRepository",
    "JsonEventRepository",
    "SqliteEventRepository",
    "build_repository",
]
