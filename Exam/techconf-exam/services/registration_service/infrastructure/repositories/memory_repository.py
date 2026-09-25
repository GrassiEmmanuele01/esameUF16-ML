"""Implementazione in memoria di :class:`RegistrationRepository`."""

from __future__ import annotations

from dataclasses import replace

from ...domain.models import Registration, RegistrationStatus
from ...domain.repository import RegistrationRepository


class MemoryRegistrationRepository(RegistrationRepository):
    """Repository iscrizioni con storage in memoria (dict per id)."""

    def __init__(self) -> None:
        self._by_id: dict[str, Registration] = {}

    def add(self, registration: Registration) -> None:
        self._by_id[registration.id] = replace(registration)

    def get(self, registration_id: str) -> Registration | None:
        found = self._by_id.get(registration_id)
        return replace(found) if found is not None else None

    def update(self, registration: Registration) -> None:
        if registration.id not in self._by_id:
            raise KeyError(registration.id)
        self._by_id[registration.id] = replace(registration)

    def delete(self, registration_id: str) -> bool:
        return self._by_id.pop(registration_id, None) is not None

    def list(
        self,
        *,
        user_id: str | None = None,
        event_id: str | None = None,
        status: RegistrationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Registration], int]:
        def _matches(r: Registration) -> bool:
            if user_id is not None and r.user_id != user_id:
                return False
            if event_id is not None and r.event_id != event_id:
                return False
            if status is not None and r.status != status:
                return False
            return True

        filtered = [replace(r) for r in self._by_id.values() if _matches(r)]
        filtered.sort(key=lambda r: r.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total

    def count_confirmed(self, event_id: str) -> int:
        return sum(
            1
            for r in self._by_id.values()
            if r.event_id == event_id and r.status is RegistrationStatus.CONFIRMED
        )

    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        for r in self._by_id.values():
            if (
                r.user_id == user_id
                and r.event_id == event_id
                and r.status is RegistrationStatus.CONFIRMED
            ):
                return replace(r)
        return None
