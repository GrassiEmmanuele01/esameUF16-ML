"""Utility per date/orari in formato ISO 8601 con timezone UTC.

Tutte le date di piattaforma sono serializzate in UTC con suffisso ``Z``
(es. ``2026-09-25T14:30:00Z``).
"""

from __future__ import annotations

from datetime import datetime, timezone


def iso_now() -> str:
    """Istante corrente in ISO 8601 UTC con suffisso ``Z`` (precisione ai secondi)."""
    return to_iso(datetime.now(timezone.utc))


def to_iso(value: datetime) -> str:
    """Serializza un ``datetime`` in ISO 8601 UTC con suffisso ``Z``.

    Un ``datetime`` naive è interpretato come UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")
