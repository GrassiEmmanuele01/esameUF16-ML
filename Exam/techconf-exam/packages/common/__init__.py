"""Codice condiviso tra i servizi TechConf.

Espone utility trasversali (errori standard, paginazione, date ISO 8601 UTC,
generazione UUID v4) riutilizzabili da tutti i servizi, senza dipendere da
alcun servizio specifico.
"""

from __future__ import annotations

from .errors import (
    AppError,
    ConflictError,
    MalformedJsonError,
    NotFoundError,
    ValidationError,
)
from .ids import new_uuid
from .pagination import Page, PageParams, normalize_page_params, paginate
from .timeutils import iso_now, to_iso

__all__ = [
    "AppError",
    "ConflictError",
    "MalformedJsonError",
    "NotFoundError",
    "ValidationError",
    "new_uuid",
    "Page",
    "PageParams",
    "normalize_page_params",
    "paginate",
    "iso_now",
    "to_iso",
]
