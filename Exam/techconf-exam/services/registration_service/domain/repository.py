"""Interfaccia astratta di persistenza per il registration-service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Registration, RegistrationStatus


class RegistrationRepository(ABC):
    """Contratto di persistenza per le iscrizioni."""

    @abstractmethod
    def add(self, registration: Registration) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, registration_id: str) -> Registration | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, registration: Registration) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, registration_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        user_id: str | None = None,
        event_id: str | None = None,
        status: RegistrationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Registration], int]:
        """Elenca le iscrizioni filtrate e paginate. ``total`` prima della paginazione."""
        raise NotImplementedError

    @abstractmethod
    def count_confirmed(self, event_id: str) -> int:
        """Numero di iscrizioni ``confirmed`` per l'evento (REQ-REG-B05/B08)."""
        raise NotImplementedError

    @abstractmethod
    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        """Iscrizione ``confirmed`` esistente per la coppia (user, event), o None (REQ-REG-B04)."""
        raise NotImplementedError
