"""Entità e value object del dominio user.

Contiene le regole di rappresentazione dell'entità ``User`` (default, forma
normalizzata dell'email) senza alcuna dipendenza da HTTP o dalla persistenza.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class Role(str, Enum):
    """Ruolo di un utente sulla piattaforma."""

    ATTENDEE = "attendee"
    SPEAKER = "speaker"
    ORGANIZER = "organizer"

    @classmethod
    def default(cls) -> "Role":
        return cls.ATTENDEE


def normalize_email(email: str) -> str:
    """Restituisce la forma normalizzata dell'email (minuscolo, senza spazi ai bordi).

    La normalizzazione è la base sia per la memorizzazione (REQ-USR-B02) sia per
    il confronto di univocità case-insensitive (REQ-USR-B01).
    """
    return email.strip().lower()


@dataclass
class User:
    """Entità utente.

    ``email`` è sempre memorizzata nella forma normalizzata in minuscolo.
    ``id``, ``created_at`` e ``updated_at`` sono valorizzati lato server.
    """

    id: str
    first_name: str
    last_name: str
    email: str
    created_at: str
    updated_at: str
    company: str | None = None
    role: Role = field(default_factory=Role.default)

    def __post_init__(self) -> None:
        # Garantisce l'invariante di normalizzazione dell'email sull'entità.
        self.email = normalize_email(self.email)
        if not isinstance(self.role, Role):
            self.role = Role(self.role)

    @property
    def email_key(self) -> str:
        """Chiave usata per il confronto di univocità (email già normalizzata)."""
        return self.email

    def to_dict(self) -> dict[str, Any]:
        """Serializza l'entità nella forma dello schema ``User`` del contratto."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "company": self.company,
            "role": self.role.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def with_updates(self, **changes: Any) -> "User":
        """Restituisce una copia dell'entità con i campi indicati aggiornati."""
        if "role" in changes and changes["role"] is not None:
            changes["role"] = Role(changes["role"])
        if "email" in changes and changes["email"] is not None:
            changes["email"] = normalize_email(changes["email"])
        return replace(self, **changes)
