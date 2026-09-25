"""Utility di paginazione condivise.

Modello di paginazione di piattaforma:
  * ``page``: numero di pagina 1-based (default 1).
  * ``page_size``: elementi per pagina (default 20, range 1–100).
  * risposta con ``items``, ``page``, ``page_size`` e ``total`` (totale prima
    della paginazione, calcolato sull'insieme eventualmente filtrato).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Sequence, TypeVar

from .errors import ValidationError

T = TypeVar("T")

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    """Parametri di paginazione validati."""

    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class Page(Generic[T]):
    """Pagina di risultati serializzabile nella forma di piattaforma."""

    items: Sequence[T]
    page: int
    page_size: int
    total: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": list(self.items),
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
        }


def _coerce_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"'{field}' deve essere un intero", details={"field": field})
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        raise ValidationError(
            f"'{field}' deve essere un intero", details={"field": field}
        ) from None


def normalize_page_params(page: Any = None, page_size: Any = None) -> PageParams:
    """Valida e normalizza ``page``/``page_size`` applicando i default.

    Solleva :class:`ValidationError` se i valori sono fuori dai vincoli.
    """
    page_val = DEFAULT_PAGE if page is None or page == "" else _coerce_int(page, "page")
    size_val = (
        DEFAULT_PAGE_SIZE
        if page_size is None or page_size == ""
        else _coerce_int(page_size, "page_size")
    )

    if page_val < 1:
        raise ValidationError("'page' deve essere >= 1", details={"field": "page"})
    if not (MIN_PAGE_SIZE <= size_val <= MAX_PAGE_SIZE):
        raise ValidationError(
            f"'page_size' deve essere compreso tra {MIN_PAGE_SIZE} e {MAX_PAGE_SIZE}",
            details={"field": "page_size"},
        )
    return PageParams(page=page_val, page_size=size_val)


def paginate(items: Sequence[T], params: PageParams, total: int | None = None) -> Page[T]:
    """Applica la finestra di paginazione a ``items``.

    ``total`` di default è ``len(items)`` (utile quando ``items`` è già l'insieme
    filtrato completo); passarlo esplicitamente quando il conteggio è calcolato
    a monte (es. dal backend di persistenza).
    """
    computed_total = len(items) if total is None else total
    window = items[params.offset : params.offset + params.limit]
    return Page(items=window, page=params.page, page_size=params.page_size, total=computed_total)
