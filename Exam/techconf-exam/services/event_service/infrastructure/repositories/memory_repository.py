"""Implementazione in memoria di :class:`EventRepository`."""

from __future__ import annotations

from dataclasses import replace

from ...domain.models import Event, EventStatus
from ...domain.repository import EventRepository


class MemoryEventRepository(EventRepository):
    """Repository eventi con storage in memoria (dict per id)."""

    def __init__(self) -> None:
        self._by_id: dict[str, Event] = {}

    def add(self, event: Event) -> None:
        self._by_id[event.id] = replace(event)

    def get(self, event_id: str) -> Event | None:
        found = self._by_id.get(event_id)
        return replace(found) if found is not None else None

    def update(self, event: Event) -> None:
        if event.id not in self._by_id:
            raise KeyError(event.id)
        self._by_id[event.id] = replace(event)

    def delete(self, event_id: str) -> bool:
        return self._by_id.pop(event_id, None) is not None

    def list(
        self,
        *,
        status: EventStatus | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        city_filter = city.casefold() if city else None

        def _matches(e: Event) -> bool:
            if status is not None and e.status != status:
                return False
            if city_filter is not None and e.city.casefold() != city_filter:
                return False
            return True

        filtered = [replace(e) for e in self._by_id.values() if _matches(e)]
        filtered.sort(key=lambda e: e.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total
