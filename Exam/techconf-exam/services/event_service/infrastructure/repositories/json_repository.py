"""Implementazione su file JSON di :class:`EventRepository` (scrittura atomica)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ...domain.models import Event, EventStatus
from ...domain.repository import EventRepository


def _record_to_event(record: dict[str, Any]) -> Event:
    return Event(
        id=record["id"],
        title=record["title"],
        description=record.get("description"),
        organizer_id=record["organizer_id"],
        venue=record["venue"],
        city=record["city"],
        start_date=record["start_date"],
        end_date=record["end_date"],
        capacity=record["capacity"],
        price=record["price"],
        status=EventStatus(record.get("status", EventStatus.default().value)),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


class JsonEventRepository(EventRepository):
    """Repository eventi con persistenza su file JSON."""

    def __init__(self, file_path: str | os.PathLike[str]) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all({})

    def _read_all(self) -> dict[str, Event]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return {rec["id"]: _record_to_event(rec) for rec in data.get("events", [])}

    def _write_all(self, events: dict[str, Event]) -> None:
        payload = {"events": [e.to_dict() for e in events.values()]}
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._path.parent), prefix=self._path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self._path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    def add(self, event: Event) -> None:
        events = self._read_all()
        events[event.id] = event
        self._write_all(events)

    def get(self, event_id: str) -> Event | None:
        return self._read_all().get(event_id)

    def update(self, event: Event) -> None:
        events = self._read_all()
        if event.id not in events:
            raise KeyError(event.id)
        events[event.id] = event
        self._write_all(events)

    def delete(self, event_id: str) -> bool:
        events = self._read_all()
        if event_id not in events:
            return False
        del events[event_id]
        self._write_all(events)
        return True

    def list(
        self,
        *,
        status: EventStatus | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        events = self._read_all()
        city_filter = city.casefold() if city else None

        def _matches(e: Event) -> bool:
            if status is not None and e.status != status:
                return False
            if city_filter is not None and e.city.casefold() != city_filter:
                return False
            return True

        filtered = [e for e in events.values() if _matches(e)]
        filtered.sort(key=lambda e: e.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total
