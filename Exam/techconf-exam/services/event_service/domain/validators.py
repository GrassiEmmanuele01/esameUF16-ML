"""Validazione dei payload evento (regole di schema e coerenza date).

I vincoli derivano dagli schemi ``EventCreate``/``EventUpdate`` del contratto
(``additionalProperties: false``). La coerenza ``end_date >= start_date``
(REQ-EVT-B03) è verificata a parte, combinando in PATCH i valori nuovi con
quelli persistiti.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping

from common import ValidationError

from .models import EventStatus

_ALLOWED_FIELDS = {
    "title",
    "description",
    "organizer_id",
    "venue",
    "city",
    "start_date",
    "end_date",
    "capacity",
    "price",
    "status",
}
_REQUIRED_ON_CREATE = (
    "title",
    "organizer_id",
    "venue",
    "city",
    "start_date",
    "end_date",
    "capacity",
    "price",
)

_TITLE_MIN, _TITLE_MAX = 3, 120
_DESCRIPTION_MAX = 2000
_VENUE_MAX = 100
_CITY_MAX = 60
_CAPACITY_MIN, _CAPACITY_MAX = 1, 10000

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fail(message: str, field: str) -> None:
    raise ValidationError(message, details={"field": field})


def _reject_unknown_fields(payload: Mapping[str, Any]) -> None:
    unknown = set(payload) - _ALLOWED_FIELDS
    if unknown:
        _fail(f"Campi non ammessi: {sorted(unknown)}", field=sorted(unknown)[0])


def _validate_str(value: Any, field: str, *, min_len: int = 0, max_len: int | None = None) -> str:
    if not isinstance(value, str):
        _fail(f"'{field}' deve essere una stringa", field)
    if len(value) < min_len:
        _fail(f"'{field}' deve avere almeno {min_len} caratteri", field)
    if max_len is not None and len(value) > max_len:
        _fail(f"'{field}' deve avere al più {max_len} caratteri", field)
    return value


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        _fail(f"'{field}' deve essere una data ISO (YYYY-MM-DD)", field)
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail(f"'{field}' non è una data valida", field)
        raise  # pragma: no cover


def _validate_capacity(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail("'capacity' deve essere un intero", "capacity")
    if not (_CAPACITY_MIN <= value <= _CAPACITY_MAX):
        _fail(
            f"'capacity' deve essere compreso tra {_CAPACITY_MIN} e {_CAPACITY_MAX}",
            "capacity",
        )
    return value


def _validate_price(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("'price' deve essere un numero", "price")
    if value < 0:
        _fail("'price' deve essere >= 0", "price")
    return float(value)


def _validate_description(value: Any) -> str | None:
    if value is None:
        return None
    return _validate_str(value, "description", max_len=_DESCRIPTION_MAX)


def _validate_status(value: Any) -> EventStatus:
    try:
        return EventStatus(value)
    except ValueError:
        _fail(f"'status' deve essere uno tra {[s.value for s in EventStatus]}", "status")
        raise  # pragma: no cover


def _validate_common(payload: Mapping[str, Any], result: dict[str, Any]) -> None:
    """Valida i campi presenti in ``payload`` scrivendoli in ``result``."""
    if "title" in payload:
        result["title"] = _validate_str(
            payload["title"], "title", min_len=_TITLE_MIN, max_len=_TITLE_MAX
        )
    if "description" in payload:
        result["description"] = _validate_description(payload["description"])
    if "organizer_id" in payload:
        result["organizer_id"] = _validate_str(payload["organizer_id"], "organizer_id", min_len=1)
    if "venue" in payload:
        result["venue"] = _validate_str(payload["venue"], "venue", min_len=1, max_len=_VENUE_MAX)
    if "city" in payload:
        result["city"] = _validate_str(payload["city"], "city", min_len=1, max_len=_CITY_MAX)
    if "start_date" in payload:
        _parse_date(payload["start_date"], "start_date")
        result["start_date"] = payload["start_date"]
    if "end_date" in payload:
        _parse_date(payload["end_date"], "end_date")
        result["end_date"] = payload["end_date"]
    if "capacity" in payload:
        result["capacity"] = _validate_capacity(payload["capacity"])
    if "price" in payload:
        result["price"] = _validate_price(payload["price"])
    if "status" in payload:
        result["status"] = _validate_status(payload["status"])


def check_date_coherence(start_date: str, end_date: str) -> None:
    """Verifica REQ-EVT-B03: ``end_date >= start_date``."""
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if end < start:
        raise ValidationError(
            "'end_date' non può precedere 'start_date'",
            details={"field": "end_date"},
        )


def validate_create(payload: Any) -> dict[str, Any]:
    """Valida un payload di creazione e verifica la coerenza delle date."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Il body deve essere un oggetto JSON")
    _reject_unknown_fields(payload)

    for field in _REQUIRED_ON_CREATE:
        if field not in payload or payload[field] is None:
            _fail(f"'{field}' è obbligatorio", field)

    result: dict[str, Any] = {}
    _validate_common(payload, result)
    result.setdefault("description", None)
    result.setdefault("status", EventStatus.default())

    check_date_coherence(result["start_date"], result["end_date"])
    return result


def validate_update(payload: Any, *, partial: bool) -> dict[str, Any]:
    """Valida un payload di aggiornamento.

    ``partial=True`` (PATCH) valida solo i campi presenti; ``partial=False``
    (PUT) applica gli stessi vincoli obbligatori della creazione.
    """
    if not partial:
        return validate_create(payload)

    if not isinstance(payload, Mapping):
        raise ValidationError("Il body deve essere un oggetto JSON")
    _reject_unknown_fields(payload)

    result: dict[str, Any] = {}
    _validate_common(payload, result)
    return result
