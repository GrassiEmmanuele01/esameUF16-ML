"""Adapter HTTP: blueprint Flask, serializzazione e mapping degli errori."""

from __future__ import annotations

from .blueprint import create_user_blueprint
from .errors import register_error_handlers

__all__ = ["create_user_blueprint", "register_error_handlers"]
