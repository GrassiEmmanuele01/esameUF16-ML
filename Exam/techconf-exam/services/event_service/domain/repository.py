"""Interfaccia astratta di persistenza per l'event-service."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Event, EventStatus


class EventRepository(ABC):
    """Contratto di persistenza per gli eventi."""

    @abstractmethod
    def add(self, event: Event) -> None:
        """Persiste un nuovo evento."""
        raise NotImplementedError

    @abstractmethod
    def get(self, event_id: str) -> Event | None:
        """Restituisce l'evento con l'id indicato, o ``None`` se assente."""
        raise NotImplementedError

    @abstractmethod
    def update(self, event: Event) -> None:
        """Aggiorna un evento esistente (identificato dal suo ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, event_id: str) -> bool:
        """Elimina l'evento indicato. Restituisce ``True`` se esisteva."""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        status: EventStatus | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        """Elenca gli eventi applicando i filtri opzionali e la paginazione.

        Restituisce ``(items, total)`` con ``total`` calcolato sull'insieme
        filtrato prima della paginazione.
        """
        raise NotImplementedError
