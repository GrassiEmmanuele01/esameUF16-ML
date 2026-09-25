"""Casi d'uso del registration-service.

``RegistrationService`` orchestra le regole di business REQ-REG-B01..B08 e
dipende dalle porte ``RegistrationRepository``, ``UserDirectory`` ed
``EventDirectory``.
"""

from __future__ import annotations

from typing import Any

from common import iso_now, new_uuid

from .directories import EventDirectory, EventInfo, UserDirectory
from .errors import (
    AlreadyRegistered,
    EventFull,
    EventNotOpen,
    InvalidStatusTransition,
    NotFound,
    ReferenceNotFound,
)
from .models import Registration, RegistrationStatus, can_transition
from .repository import RegistrationRepository
from .validators import validate_create, validate_patch, validate_uuid_param

_PUBLISHED = "published"


class RegistrationService:
    """Servizio applicativo per la gestione delle iscrizioni."""

    def __init__(
        self,
        repository: RegistrationRepository,
        users: UserDirectory,
        events: EventDirectory,
    ) -> None:
        self._repo = repository
        self._users = users
        self._events = events

    # ------------------------------- create ------------------------------- #

    def create_registration(self, payload: Any) -> Registration:
        data = validate_create(payload)
        user_id = data["user_id"]
        event_id = data["event_id"]

        # REQ-REG-B01: l'utente deve esistere.
        if not self._users.exists(user_id):
            raise ReferenceNotFound("user_id", user_id)

        # REQ-REG-B02: l'evento deve esistere.
        event = self._events.get(event_id)
        if event is None:
            raise ReferenceNotFound("event_id", event_id)

        # REQ-REG-B03: l'evento deve essere published.
        if event.status != _PUBLISHED:
            raise EventNotOpen(event_id)

        # REQ-REG-B04: nessuna doppia iscrizione confermata.
        if self._repo.find_confirmed(user_id, event_id) is not None:
            raise AlreadyRegistered(user_id, event_id)

        # REQ-REG-B05: capienza non superata.
        if self._repo.count_confirmed(event_id) >= event.capacity:
            raise EventFull(event_id)

        # REQ-REG-B06: amount dal prezzo dell'evento.
        now = iso_now()
        registration = Registration(
            id=new_uuid(),
            user_id=user_id,
            event_id=event_id,
            amount=event.price,
            status=RegistrationStatus.CONFIRMED,
            created_at=now,
            updated_at=now,
        )
        self._repo.add(registration)
        return registration

    # -------------------------------- read -------------------------------- #

    def get_registration(self, registration_id: str) -> Registration:
        registration = self._repo.get(registration_id)
        if registration is None:
            raise NotFound("Iscrizione non trovata", details={"id": registration_id})
        return registration

    def list_registrations(
        self,
        *,
        user_id: str | None = None,
        event_id: str | None = None,
        status: Any = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Registration], int]:
        status_filter = self._coerce_status(status) if status else None
        return self._repo.list(
            user_id=user_id,
            event_id=event_id,
            status=status_filter,
            page=page,
            page_size=page_size,
        )

    # ------------------------------- update ------------------------------- #

    def update_status(self, registration_id: str, payload: Any) -> Registration:
        new_status = validate_patch(payload)
        existing = self._repo.get(registration_id)
        if existing is None:
            raise NotFound("Iscrizione non trovata", details={"id": registration_id})

        # REQ-REG-B07: transizione consentita (confirmed -> cancelled).
        if not can_transition(existing.status, new_status):
            raise InvalidStatusTransition(existing.status.value, new_status.value)

        if new_status == existing.status:
            return existing  # no-op

        updated = existing.with_updates(status=new_status, updated_at=iso_now())
        self._repo.update(updated)
        return updated

    # ------------------------------- delete ------------------------------- #

    def delete_registration(self, registration_id: str) -> None:
        if not self._repo.delete(registration_id):
            raise NotFound("Iscrizione non trovata", details={"id": registration_id})

    # -------------------------------- stats ------------------------------- #

    def stats(self, event_id_param: Any) -> dict[str, Any]:
        """REQ-REG-B08: statistiche di riempimento di un evento."""
        event_id = validate_uuid_param(event_id_param, "event_id")

        event = self._events.get(event_id)
        if event is None:
            raise NotFound("Evento non trovato", details={"event_id": event_id})

        confirmed = self._repo.count_confirmed(event_id)
        return {
            "event_id": event_id,
            "capacity": event.capacity,
            "confirmed": confirmed,
            "available": event.capacity - confirmed,
        }

    # ------------------------------- helpers ------------------------------ #

    @staticmethod
    def _coerce_status(status: Any) -> RegistrationStatus:
        from common import ValidationError

        if isinstance(status, RegistrationStatus):
            return status
        try:
            return RegistrationStatus(status)
        except ValueError:
            raise ValidationError(
                f"'status' deve essere uno tra {[s.value for s in RegistrationStatus]}",
                details={"field": "status"},
            ) from None
