"""Validazione dei payload utente (regole di business, indipendenti da HTTP).

I vincoli derivano dagli schemi ``UserCreate``/``UserUpdate`` del contratto
(``additionalProperties: false``, lunghezze, formato email, enum ruolo).
Violazioni -> :class:`common.ValidationError` (mappata a 422).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from common import ValidationError

from .models import Role

# Campi ammessi in creazione/aggiornamento (allineati al contratto).
_ALLOWED_FIELDS = {"first_name", "last_name", "email", "company", "role"}
_REQUIRED_ON_CREATE = ("first_name", "last_name", "email")

# Email pratica: parte locale + dominio con almeno un punto.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_NAME_MIN, _NAME_MAX = 1, 50
_COMPANY_MAX = 100


def _fail(message: str, field: str) -> None:
    raise ValidationError(message, details={"field": field})


def _reject_unknown_fields(payload: Mapping[str, Any]) -> None:
    unknown = set(payload) - _ALLOWED_FIELDS
    if unknown:
        _fail(f"Campi non ammessi: {sorted(unknown)}", field=sorted(unknown)[0])


def _validate_name(value: Any, field: str) -> str:
    if not isinstance(value, str):
        _fail(f"'{field}' deve essere una stringa", field)
    if not (_NAME_MIN <= len(value) <= _NAME_MAX):
        _fail(f"'{field}' deve avere lunghezza {_NAME_MIN}-{_NAME_MAX}", field)
    return value


def _validate_email(value: Any) -> str:
    if not isinstance(value, str) or not _EMAIL_RE.match(value):
        _fail("'email' non è un indirizzo valido", "email")
    return value


def _validate_company(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail("'company' deve essere una stringa o null", "company")
    if len(value) > _COMPANY_MAX:
        _fail(f"'company' deve avere al più {_COMPANY_MAX} caratteri", "company")
    return value


def _validate_role(value: Any) -> Role:
    try:
        return Role(value)
    except ValueError:
        _fail(
            f"'role' deve essere uno tra {[r.value for r in Role]}", "role"
        )
        raise  # pragma: no cover - _fail solleva sempre


def validate_create(payload: Any) -> dict[str, Any]:
    """Valida un payload di creazione. Restituisce i campi normalizzati."""
    if not isinstance(payload, Mapping):
        raise ValidationError("Il body deve essere un oggetto JSON")
    _reject_unknown_fields(payload)

    for field in _REQUIRED_ON_CREATE:
        if field not in payload or payload[field] is None:
            _fail(f"'{field}' è obbligatorio", field)

    result: dict[str, Any] = {
        "first_name": _validate_name(payload["first_name"], "first_name"),
        "last_name": _validate_name(payload["last_name"], "last_name"),
        "email": _validate_email(payload["email"]),
        "company": _validate_company(payload.get("company")),
        "role": _validate_role(payload["role"]) if "role" in payload else Role.default(),
    }
    return result


def validate_update(payload: Any, *, partial: bool) -> dict[str, Any]:
    """Valida un payload di aggiornamento.

    ``partial=True`` (PATCH) valida solo i campi presenti; ``partial=False``
    (PUT) applica gli stessi vincoli obbligatori della creazione.
    """
    if partial:
        if not isinstance(payload, Mapping):
            raise ValidationError("Il body deve essere un oggetto JSON")
        _reject_unknown_fields(payload)

        result: dict[str, Any] = {}
        if "first_name" in payload:
            result["first_name"] = _validate_name(payload["first_name"], "first_name")
        if "last_name" in payload:
            result["last_name"] = _validate_name(payload["last_name"], "last_name")
        if "email" in payload:
            result["email"] = _validate_email(payload["email"])
        if "company" in payload:
            result["company"] = _validate_company(payload["company"])
        if "role" in payload:
            result["role"] = _validate_role(payload["role"])
        return result

    # PUT: sostituzione totale, stessi vincoli della creazione.
    return validate_create(payload)
