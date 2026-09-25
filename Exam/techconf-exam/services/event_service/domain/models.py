"""Entità e value object del dominio event.

Contiene l'entità ``Event``, l'enum ``EventStatus`` e le regole delle
transizioni di stato consentite (REQ-EVT-B04), senza dipendenze da HTTP o
persistenza.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class EventStatus(str, Enum):
    """Stato del ciclo di vita di un evento."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

    @classmethod
    def default(cls) -> "EventStatus":
        return cls.DRAFT


# Transizioni consentite (REQ-EVT-B04). Uno stato assente o vuoto = terminale.
_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DRAFT: frozenset({EventStatus.PUBLISHED, EventStatus.CANCELLED}),
    EventStatus.PUBLISHED: frozenset({EventStatus.CANCELLED}),
    EventStatus.CANCELLED: frozenset(),
}


def can_transition(from_status: EventStatus, to_status: EventStatus) -> bool:
    """True se la transizione è consentita. La transizione verso lo stesso stato
    (no-op) è sempre valida."""
    if from_status == to_status:
        return True
    return to_status in _ALLOWED_TRANSITIONS.get(from_status, frozenset())


@dataclass
class Event:
    """Entità evento. ``id``, ``created_at`` e ``updated_at`` sono lato server."""

    id: str
    title: str
    organizer_id: str
    venue: str
    city: str
    start_date: str
    end_date: str
    capacity: int
    price: float
    created_at: str
    updated_at: str
    description: str | None = None
    status: EventStatus = field(default_factory=EventStatus.default)

    def __post_init__(self) -> None:
        if not isinstance(self.status, EventStatus):
            self.status = EventStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        """Serializza l'entità nella forma dello schema ``Event`` del contratto."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "organizer_id": self.organizer_id,
            "venue": self.venue,
            "city": self.city,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "capacity": self.capacity,
            "price": self.price,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def with_updates(self, **changes: Any) -> "Event":
        """Restituisce una copia dell'entità con i campi indicati aggiornati."""
        if "status" in changes and changes["status"] is not None:
            changes["status"] = EventStatus(changes["status"])
        return replace(self, **changes)
