"""Eccezioni di dominio specifiche del registration-service."""

from __future__ import annotations

from common import AppError, ConflictError, NotFoundError, ValidationError


class NotFound(NotFoundError):
    """Risorsa non trovata (404 NOT_FOUND)."""

    code = "NOT_FOUND"

    def __init__(self, message: str = "Risorsa non trovata", details=None) -> None:
        super().__init__(message, details=details)


class ReferenceNotFound(ValidationError):
    """Un riferimento (user_id o event_id) non esiste (422 REFERENCE_NOT_FOUND).

    REQ-REG-B01 / REQ-REG-B02.
    """

    code = "REFERENCE_NOT_FOUND"

    def __init__(self, reference: str = "reference", value: str | None = None) -> None:
        details = {"reference": reference}
        if value:
            details["value"] = value
        super().__init__(f"Riferimento inesistente: {reference}", details=details)


class EventNotOpen(ValidationError):
    """L'evento non è aperto alle iscrizioni (422 EVENT_NOT_OPEN). REQ-REG-B03."""

    code = "EVENT_NOT_OPEN"

    def __init__(self, event_id: str | None = None) -> None:
        details = {"event_id": event_id} if event_id else None
        super().__init__("L'evento non è pubblicato", details=details)


class AlreadyRegistered(ConflictError):
    """Iscrizione confermata già esistente (409 ALREADY_REGISTERED). REQ-REG-B04."""

    code = "ALREADY_REGISTERED"

    def __init__(self, user_id: str | None = None, event_id: str | None = None) -> None:
        details = None
        if user_id and event_id:
            details = {"user_id": user_id, "event_id": event_id}
        super().__init__("Utente già iscritto all'evento", details=details)


class EventFull(ConflictError):
    """Capienza dell'evento raggiunta (409 EVENT_FULL). REQ-REG-B05."""

    code = "EVENT_FULL"

    def __init__(self, event_id: str | None = None) -> None:
        details = {"event_id": event_id} if event_id else None
        super().__init__("Capienza dell'evento raggiunta", details=details)


class InvalidStatusTransition(ValidationError):
    """Transizione di stato non consentita (422 INVALID_STATUS_TRANSITION). REQ-REG-B07."""

    code = "INVALID_STATUS_TRANSITION"

    def __init__(self, from_status: str | None = None, to_status: str | None = None) -> None:
        details = None
        if from_status and to_status:
            details = {"from": from_status, "to": to_status}
        super().__init__("Transizione di stato non consentita", details=details)


class DependencyUnavailable(AppError):
    """Una dipendenza di servizio è irraggiungibile (503 DEPENDENCY_UNAVAILABLE)."""

    code = "DEPENDENCY_UNAVAILABLE"
    http_status = 503

    def __init__(self, dependency: str) -> None:
        super().__init__(
            f"Dipendenza non disponibile: {dependency}",
            details={"dependency": dependency},
        )
