"""Generazione di identificatori di piattaforma.

Gli ID delle risorse sono UUID v4 generati lato server.
"""

from __future__ import annotations

import uuid


def new_uuid() -> str:
    """Restituisce un nuovo UUID v4 in formato stringa."""
    return str(uuid.uuid4())
