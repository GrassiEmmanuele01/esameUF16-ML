"""Porte di dominio verso le dipendenze di servizio (user-service, event-service).

Isolano il dominio dal trasporto HTTP. Le implementazioni concrete (client
``requests``) vivono in ``infrastructure/``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EventInfo:
    """Informazioni sull'evento necessarie alle regole di business.

    ``status`` (REQ-REG-B03), ``capacity`` (REQ-REG-B05), ``price`` (REQ-REG-B06).
    """

    status: str
    capacity: int
    price: float


class UserDirectory(ABC):
    """Porta per verificare l'esistenza di un utente."""

    @abstractmethod
    def exists(self, user_id: str) -> bool:
        """True se l'utente esiste, False se lo user-service risponde 404.

        Solleva ``DependencyUnavailable`` se lo user-service è irraggiungibile o 5xx.
        """
        raise NotImplementedError


class EventDirectory(ABC):
    """Porta per recuperare le informazioni di un evento."""

    @abstractmethod
    def get(self, event_id: str) -> EventInfo | None:
        """Restituisce :class:`EventInfo` se l'evento esiste, ``None`` su 404.

        Solleva ``DependencyUnavailable`` se l'event-service è irraggiungibile o 5xx.
        """
        raise NotImplementedError
