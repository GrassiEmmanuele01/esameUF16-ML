"""Errori standard di piattaforma.

Ogni errore espone un ``code`` in UPPER_SNAKE_CASE e un ``message`` leggibile,
coerente con la struttura d'errore uniforme:

    { "error": { "code": <UPPER_SNAKE>, "message": <string>, "details": {...} } }

Gli errori sono agnostici rispetto al trasporto HTTP: il mapping verso gli
status code avviene nel layer entrypoints di ciascun servizio.
"""

from __future__ import annotations

from typing import Any, Mapping


class AppError(Exception):
    """Errore applicativo di base con codice e messaggio strutturati."""

    #: Codice d'errore predefinito in UPPER_SNAKE_CASE.
    code: str = "INTERNAL_ERROR"
    #: Status HTTP suggerito per questo tipo di errore.
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details: dict[str, Any] = dict(details) if details else {}

    def to_dict(self) -> dict[str, Any]:
        """Serializza l'errore nella struttura uniforme di piattaforma."""
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AppError):
    """Il payload viola i vincoli di validazione (422)."""

    code = "VALIDATION_ERROR"
    http_status = 422


class MalformedJsonError(AppError):
    """Il body della richiesta non è JSON valido (400)."""

    code = "MALFORMED_JSON"
    http_status = 400


class NotFoundError(AppError):
    """La risorsa richiesta non esiste (404)."""

    code = "RESOURCE_NOT_FOUND"
    http_status = 404


class ConflictError(AppError):
    """La richiesta è in conflitto con lo stato corrente (409)."""

    code = "CONFLICT"
    http_status = 409
