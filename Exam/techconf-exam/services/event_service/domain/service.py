"""Casi d'uso dell'event-service.

``EventService`` orchestra le regole di business e dipende dalle porte
``EventRepository`` (persistenza) e ``UserDirectory`` (verifica organizzatore).
È agnostico rispetto a HTTP e al backend concreto.
"""

from __future__ import annotations

from typing import Any

from common import iso_now, new_uuid

from .errors import (
    EventNotFound,
    InvalidOrganizer,
    InvalidStatusTransition,
    ReferenceNotFound,
)
from .models import Event, EventStatus, can_transition
from .repository import EventRepository
from .users import UserDirectory
from .validators import check_date_coherence, validate_create, validate_update

_ORGANIZER_ROLE = "organizer"


class EventService:
    """Servizio applicativo per la gestione degli eventi."""

    def __init__(self, repository: EventRepository, users: UserDirectory) -> None:
        self._repo = repository
        self._users = users

    # ------------------------------- create ------------------------------- #

    def create_event(self, payload: Any) -> Event:
        data = validate_create(payload)

        # REQ-EVT-B01/B02/B05: verifica organizzatore (può sollevare
        # ReferenceNotFound / InvalidOrganizer / DependencyUnavailable).
        self._verify_organizer(data["organizer_id"])

        now = iso_now()
        event = Event(
            id=new_uuid(),
            title=data["title"],
            description=data["description"],
            organizer_id=data["organizer_id"],
            venue=data["venue"],
            city=data["city"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            capacity=data["capacity"],
            price=data["price"],
            status=data["status"],
            created_at=now,
            updated_at=now,
        )
        self._repo.add(event)
        return event

    # -------------------------------- read -------------------------------- #

    def get_event(self, event_id: str) -> Event:
        event = self._repo.get(event_id)
        if event is None:
            raise EventNotFound(event_id)
        return event

    def list_events(
        self,
        *,
        status: Any = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        status_filter = self._coerce_status(status) if status else None
        return self._repo.list(
            status=status_filter, city=city, page=page, page_size=page_size
        )

    # ------------------------------- update ------------------------------- #

    def replace_event(self, event_id: str, payload: Any) -> Event:
        return self._apply_update(event_id, payload, partial=False)

    def update_event(self, event_id: str, payload: Any) -> Event:
        return self._apply_update(event_id, payload, partial=True)

    def _apply_update(self, event_id: str, payload: Any, *, partial: bool) -> Event:
        existing = self._repo.get(event_id)
        if existing is None:
            raise EventNotFound(event_id)

        data = validate_update(payload, partial=partial)

        # REQ-EVT-B01/B02: ri-verifica l'organizzatore solo se cambia.
        if "organizer_id" in data and data["organizer_id"] != existing.organizer_id:
            self._verify_organizer(data["organizer_id"])

        # REQ-EVT-B03: coerenza date combinando nuovi valori e persistiti.
        new_start = data.get("start_date", existing.start_date)
        new_end = data.get("end_date", existing.end_date)
        check_date_coherence(new_start, new_end)

        # REQ-EVT-B04: controllo transizione se cambia lo stato.
        if "status" in data:
            new_status = data["status"]
            if not can_transition(existing.status, new_status):
                raise InvalidStatusTransition(
                    existing.status.value, new_status.value
                )

        updated = existing.with_updates(**data, updated_at=iso_now())
        self._repo.update(updated)
        return updated

    # ------------------------------- delete ------------------------------- #

    def delete_event(self, event_id: str) -> None:
        if not self._repo.delete(event_id):
            raise EventNotFound(event_id)

    # ------------------------------- helpers ------------------------------ #

    def _verify_organizer(self, organizer_id: str) -> None:
        """Verifica esistenza (REQ-EVT-B01) e ruolo (REQ-EVT-B02).

        Propaga :class:`DependencyUnavailable` (REQ-EVT-B05) sollevata dalla porta.
        """
        role = self._users.get_role(organizer_id)
        if role is None:
            raise ReferenceNotFound(organizer_id)
        if role != _ORGANIZER_ROLE:
            raise InvalidOrganizer(organizer_id)

    @staticmethod
    def _coerce_status(status: Any) -> EventStatus:
        from common import ValidationError

        if isinstance(status, EventStatus):
            return status
        try:
            return EventStatus(status)
        except ValueError:
            raise ValidationError(
                f"'status' deve essere uno tra {[s.value for s in EventStatus]}",
                details={"field": "status"},
            ) from None
