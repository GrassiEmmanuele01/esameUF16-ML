"""Entità e value object del dominio registration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class RegistrationStatus(str, Enum):
    """Stato di un'iscrizione."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    @classmethod
    def default(cls) -> "RegistrationStatus":
        return cls.CONFIRMED


# Transizioni consentite (REQ-REG-B07). ``cancelled`` è terminale.
_ALLOWED_TRANSITIONS: dict[RegistrationStatus, frozenset[RegistrationStatus]] = {
    RegistrationStatus.CONFIRMED: frozenset({RegistrationStatus.CANCELLED}),
    RegistrationStatus.CANCELLED: frozenset(),
}


def can_transition(from_status: RegistrationStatus, to_status: RegistrationStatus) -> bool:
    """True se la transizione è consentita. Stesso stato (no-op) = valido."""
    if from_status == to_status:
        return True
    return to_status in _ALLOWED_TRANSITIONS.get(from_status, frozenset())


@dataclass
class Registration:
    """Entità iscrizione. Campi generati lato server: id, amount, status, timestamp."""

    id: str
    user_id: str
    event_id: str
    amount: float
    created_at: str
    updated_at: str
    status: RegistrationStatus = field(default_factory=RegistrationStatus.default)

    def __post_init__(self) -> None:
        if not isinstance(self.status, RegistrationStatus):
            self.status = RegistrationStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        """Serializza l'entità nella forma dello schema ``Registration`` del contratto."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "amount": self.amount,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def with_updates(self, **changes: Any) -> "Registration":
        if "status" in changes and changes["status"] is not None:
            changes["status"] = RegistrationStatus(changes["status"])
        return replace(self, **changes)
