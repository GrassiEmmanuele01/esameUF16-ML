"""Eccezioni di dominio specifiche dell'event-service."""

from __future__ import annotations

from common import AppError, NotFoundError, ValidationError


class EventNotFound(NotFoundError):
    """L'evento richiesto non esiste (404 EVENT_NOT_FOUND)."""

    code = "EVENT_NOT_FOUND"

    def __init__(self, event_id: str | None = None) -> None:
        details = {"id": event_id} if event_id else None
        super().__init__("Evento non trovato", details=details)


class ReferenceNotFound(ValidationError):
    """L'organizer_id non corrisponde ad alcun utente (422 REFERENCE_NOT_FOUND).

    REQ-EVT-B01: lo user-service ha risposto 404 per l'organizer_id indicato.
    """

    code = "REFERENCE_NOT_FOUND"

    def __init__(self, organizer_id: str | None = None) -> None:
        details = {"organizer_id": organizer_id} if organizer_id else None
        super().__init__("organizer_id non esistente", details=details)


class InvalidOrganizer(ValidationError):
    """L'utente referenziato non ha ruolo organizer (422 INVALID_ORGANIZER).

    REQ-EVT-B02.
    """

    code = "INVALID_ORGANIZER"

    def __init__(self, organizer_id: str | None = None) -> None:
        details = {"organizer_id": organizer_id} if organizer_id else None
        super().__init__(
            "L'utente indicato non ha ruolo 'organizer'", details=details
        )


class InvalidStatusTransition(ValidationError):
    """Transizione di stato non consentita (422 INVALID_STATUS_TRANSITION).

    REQ-EVT-B04.
    """

    code = "INVALID_STATUS_TRANSITION"

    def __init__(self, from_status: str | None = None, to_status: str | None = None) -> None:
        details = None
        if from_status and to_status:
            details = {"from": from_status, "to": to_status}
        super().__init__(
            "Transizione di stato non consentita", details=details
        )


class DependencyUnavailable(AppError):
    """Una dipendenza di servizio è irraggiungibile (503 DEPENDENCY_UNAVAILABLE).

    REQ-EVT-B05: lo user-service non risponde (connessione/timeout) o restituisce 5xx.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    http_status = 503

    def __init__(self, dependency: str = "user-service") -> None:
        super().__init__(
            f"Dipendenza non disponibile: {dependency}",
            details={"dependency": dependency},
        )
