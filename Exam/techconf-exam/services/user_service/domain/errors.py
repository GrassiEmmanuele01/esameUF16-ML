"""Eccezioni di dominio specifiche dello user-service.

Estendono gli errori standard di piattaforma con i ``code`` previsti dal
contratto dello user-service.
"""

from __future__ import annotations

from common import ConflictError, NotFoundError


class UserNotFound(NotFoundError):
    """L'utente richiesto non esiste (404 USER_NOT_FOUND)."""

    code = "USER_NOT_FOUND"

    def __init__(self, user_id: str | None = None) -> None:
        message = "Utente non trovato"
        details = {"id": user_id} if user_id else None
        super().__init__(message, details=details)


class EmailAlreadyExists(ConflictError):
    """L'email è già associata a un altro utente (409 EMAIL_ALREADY_EXISTS)."""

    code = "EMAIL_ALREADY_EXISTS"

    def __init__(self, email: str | None = None) -> None:
        message = "Email già registrata"
        details = {"email": email} if email else None
        super().__init__(message, details=details)
