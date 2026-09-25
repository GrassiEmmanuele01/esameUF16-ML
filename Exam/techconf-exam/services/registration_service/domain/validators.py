"""Validazione dei payload iscrizione (schema del contratto)."""

from __future__ import annotations

import re
from typing import Any, Mapping

from common import ValidationError

from .models import RegistrationStatus

_CREATE_ALLOWED = {"user_id", "event_id"}
_CREATE_REQUIRED = ("user_id", "event_id")
_PATCH_ALLOWED = {"status"}

# UUID v4-ish (accetta qualsiasi UUID ben formato).
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _fail(message: str, field: str) -> None:
    raise ValidationError(message, details={"field": field})


def _validate_uuid(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _UUID_RE.match(value):
        _fail(f"'{field}' deve essere un UUID valido", field)
    return value


def validate_create(payload: Any) -> dict[str, str]:
    """Valida un payload di creazione (user_id, event_id)."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Il body deve essere un oggetto JSON")
    unknown = set(payload) - _CREATE_ALLOWED
    if unknown:
        _fail(f"Campi non ammessi: {sorted(unknown)}", sorted(unknown)[0])
    for field in _CREATE_REQUIRED:
        if field not in payload or payload[field] is None:
            _fail(f"'{field}' è obbligatorio", field)
    return {
        "user_id": _validate_uuid(payload["user_id"], "user_id"),
        "event_id": _validate_uuid(payload["event_id"], "event_id"),
    }


def validate_patch(payload: Any) -> RegistrationStatus:
    """Valida un payload PATCH (status obbligatorio) e restituisce lo stato."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Il body deve essere un oggetto JSON")
    unknown = set(payload) - _PATCH_ALLOWED
    if unknown:
        _fail(f"Campi non ammessi: {sorted(unknown)}", sorted(unknown)[0])
    if "status" not in payload or payload["status"] is None:
        _fail("'status' è obbligatorio", "status")
    try:
        return RegistrationStatus(payload["status"])
    except ValueError:
        _fail(
            f"'status' deve essere uno tra {[s.value for s in RegistrationStatus]}",
            "status",
        )
        raise  # pragma: no cover


def validate_uuid_param(value: Any, field: str) -> str:
    """Valida un UUID passato come parametro di query (es. stats event_id)."""
    if value is None or value == "":
        _fail(f"'{field}' è obbligatorio", field)
    return _validate_uuid(value, field)
