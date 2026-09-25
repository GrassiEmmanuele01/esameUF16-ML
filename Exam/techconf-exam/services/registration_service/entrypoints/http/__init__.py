"""Adapter HTTP: blueprint Flask, serializzazione e mapping degli errori."""

from __future__ import annotations

from .blueprint import create_registration_blueprint
from .errors import register_error_handlers

__all__ = ["create_registration_blueprint", "register_error_handlers"]
