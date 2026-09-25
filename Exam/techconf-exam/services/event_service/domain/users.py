"""Porta di dominio verso lo user-service.

``UserDirectory`` astrae la verifica dell'organizzatore (REQ-EVT-B01/B02),
isolando il dominio dal trasporto HTTP. L'implementazione concreta vive in
``infrastructure/`` (client ``requests``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UserDirectory(ABC):
    """Contratto per interrogare lo user-service sull'organizzatore."""

    @abstractmethod
    def get_role(self, user_id: str) -> str | None:
        """Restituisce il ruolo dell'utente indicato.

        - Ritorna la stringa del ruolo (es. ``"organizer"``) se l'utente esiste.
        - Ritorna ``None`` se l'utente non esiste (user-service risponde 404).
        - Solleva :class:`event_service.domain.errors.DependencyUnavailable`
          se lo user-service è irraggiungibile (connessione/timeout) o 5xx.
        """
        raise NotImplementedError
