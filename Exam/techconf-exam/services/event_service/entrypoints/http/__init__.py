"""Adapter HTTP: blueprint Flask, serializzazione e mapping degli errori."""

from __future__ import annotations

from .blueprint import create_event_blueprint
from .errors import register_error_handlers

__all__ = ["create_event_blueprint", "register_error_handlers"]
