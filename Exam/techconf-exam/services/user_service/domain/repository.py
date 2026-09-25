"""Interfaccia astratta di persistenza per lo user-service.

``UserRepository`` definisce il contratto che le implementazioni concrete
(Memory, JSON, SQLite) devono rispettare. Il dominio dipende esclusivamente da
questa astrazione; il backend concreto è iniettato dal composition root.

Convenzioni:
  * ``find_by_email`` riceve un'email già normalizzata (minuscolo) e realizza il
    confronto di univocità case-insensitive (REQ-USR-B01 / REQ-USR-B02).
  * ``list`` applica i filtri opzionali e restituisce la tupla
    ``(items, total)`` dove ``total`` è il conteggio degli elementi che
    soddisfano i filtri PRIMA della paginazione (REQ-USR-B03).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Role, User


class UserRepository(ABC):
    """Contratto di persistenza per gli utenti."""

    @abstractmethod
    def add(self, user: User) -> None:
        """Persiste un nuovo utente."""
        raise NotImplementedError

    @abstractmethod
    def get(self, user_id: str) -> User | None:
        """Restituisce l'utente con l'id indicato, o ``None`` se assente."""
        raise NotImplementedError

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        """Restituisce l'utente con l'email normalizzata indicata, o ``None``.

        ``email`` deve essere già normalizzata (minuscolo).
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, user: User) -> None:
        """Aggiorna un utente esistente (identificato dal suo ``id``)."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Elimina l'utente indicato. Restituisce ``True`` se esisteva."""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        *,
        role: Role | None = None,
        email: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        """Elenca gli utenti applicando i filtri opzionali e la paginazione.

        Il filtro ``email`` è case-insensitive (email normalizzata). Restituisce
        ``(items, total)`` con ``total`` calcolato sull'insieme filtrato prima
        della paginazione.
        """
        raise NotImplementedError
