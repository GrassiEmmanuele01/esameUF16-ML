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
        """Verifica l'esistenza di un utente (REQ-REG-B01).

        - Ritorna ``True`` se l'utente esiste (user-service risponde 200).
        - Ritorna ``False`` se l'utente non esiste (user-service risponde 404).
        - Solleva :class:`registration_service.domain.errors.DependencyUnavailable`
          se lo user-service è irraggiungibile (connessione/timeout) o 5xx.
        """
        raise NotImplementedError


class EventDirectory(ABC):
    """Porta per recuperare le informazioni di un evento."""

    @abstractmethod
    def get(self, event_id: str) -> EventInfo | None:
        """Recupera le informazioni di un evento (REQ-REG-B02/B03/B05/B06).

        - Ritorna :class:`EventInfo` (``status``, ``capacity``, ``price``) se
          l'evento esiste (event-service risponde 200).
        - Ritorna ``None`` se l'evento non esiste (event-service risponde 404).
        - Solleva :class:`registration_service.domain.errors.DependencyUnavailable`
          se l'event-service è irraggiungibile (connessione/timeout) o 5xx.
        """
        raise NotImplementedError
