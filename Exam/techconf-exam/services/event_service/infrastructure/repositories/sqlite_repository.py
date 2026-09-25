"""Implementazione su SQLite di :class:`EventRepository`."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ...domain.models import Event, EventStatus
from ...domain.repository import EventRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    description  TEXT,
    organizer_id TEXT NOT NULL,
    venue        TEXT NOT NULL,
    city         TEXT NOT NULL,
    start_date   TEXT NOT NULL,
    end_date     TEXT NOT NULL,
    capacity     INTEGER NOT NULL,
    price        REAL NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
"""


class SqliteEventRepository(EventRepository):
    """Repository eventi con persistenza su SQLite."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(self._path)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            organizer_id=row["organizer_id"],
            venue=row["venue"],
            city=row["city"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            capacity=row["capacity"],
            price=row["price"],
            status=EventStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _insert_params(self, event: Event) -> tuple:
        return (
            event.id,
            event.title,
            event.description,
            event.organizer_id,
            event.venue,
            event.city,
            event.start_date,
            event.end_date,
            event.capacity,
            event.price,
            event.status.value,
            event.created_at,
            event.updated_at,
        )

    def add(self, event: Event) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events "
                "(id, title, description, organizer_id, venue, city, start_date, "
                "end_date, capacity, price, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._insert_params(event),
            )

    def get(self, event_id: str) -> Event | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            ).fetchone()
        return self._row_to_event(row) if row is not None else None

    def update(self, event: Event) -> None:
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM events WHERE id = ?", (event.id,)
            ).fetchone()
            if exists is None:
                raise KeyError(event.id)
            conn.execute(
                "UPDATE events SET "
                "title = ?, description = ?, organizer_id = ?, venue = ?, city = ?, "
                "start_date = ?, end_date = ?, capacity = ?, price = ?, status = ?, "
                "created_at = ?, updated_at = ? WHERE id = ?",
                (
                    event.title,
                    event.description,
                    event.organizer_id,
                    event.venue,
                    event.city,
                    event.start_date,
                    event.end_date,
                    event.capacity,
                    event.price,
                    event.status.value,
                    event.created_at,
                    event.updated_at,
                    event.id,
                ),
            )

    def delete(self, event_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cur.rowcount > 0

    def list(
        self,
        *,
        status: EventStatus | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if city:
            clauses.append("city = ? COLLATE NOCASE")
            params.append(city)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM events{where}", params
            ).fetchone()["n"]
            rows = conn.execute(
                f"SELECT * FROM events{where} ORDER BY created_at LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [self._row_to_event(r) for r in rows], int(total)
