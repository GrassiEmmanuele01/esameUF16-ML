"""Implementazione in memoria di :class:`UserRepository`.

Store basato su ``dict`` con un indice ausiliario sull'email normalizzata per
garantire l'univocità case-insensitive (REQ-USR-B01) in tempo costante. Utile
per test e sviluppo rapido; nessuna persistenza tra riavvii.
"""

from __future__ import annotations

from dataclasses import replace

from common import ConflictError

from ...domain.models import Role, User, normalize_email
from ...domain.repository import UserRepository


class MemoryUserRepository(UserRepository):
    """Repository utenti con storage in memoria."""

    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        # Indice email normalizzata -> id, per univocità case-insensitive.
        self._email_index: dict[str, str] = {}

    def add(self, user: User) -> None:
        key = user.email_key
        if key in self._email_index:
            raise ConflictError(
                "Email già registrata", code="EMAIL_ALREADY_EXISTS"
            )
        stored = replace(user)
        self._by_id[stored.id] = stored
        self._email_index[key] = stored.id

    def get(self, user_id: str) -> User | None:
        found = self._by_id.get(user_id)
        return replace(found) if found is not None else None

    def find_by_email(self, email: str) -> User | None:
        user_id = self._email_index.get(normalize_email(email))
        if user_id is None:
            return None
        found = self._by_id.get(user_id)
        return replace(found) if found is not None else None

    def update(self, user: User) -> None:
        existing = self._by_id.get(user.id)
        if existing is None:
            raise KeyError(user.id)

        new_key = user.email_key
        owner = self._email_index.get(new_key)
        if owner is not None and owner != user.id:
            raise ConflictError(
                "Email già registrata", code="EMAIL_ALREADY_EXISTS"
            )

        # Riallinea l'indice email se l'utente ha cambiato indirizzo.
        old_key = existing.email_key
        if old_key != new_key:
            self._email_index.pop(old_key, None)
        self._email_index[new_key] = user.id
        self._by_id[user.id] = replace(user)

    def delete(self, user_id: str) -> bool:
        existing = self._by_id.pop(user_id, None)
        if existing is None:
            return False
        self._email_index.pop(existing.email_key, None)
        return True

    def list(
        self,
        *,
        role: Role | None = None,
        email: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        email_filter = normalize_email(email) if email else None

        def _matches(u: User) -> bool:
            if role is not None and u.role != role:
                return False
            if email_filter is not None and u.email != email_filter:
                return False
            return True

        filtered = [replace(u) for u in self._by_id.values() if _matches(u)]
        # Ordinamento deterministico per stabilità della paginazione.
        filtered.sort(key=lambda u: u.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        window = filtered[offset : offset + page_size]
        return window, total
