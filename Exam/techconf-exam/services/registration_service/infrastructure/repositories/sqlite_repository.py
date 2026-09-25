"""Implementazione su SQLite di :class:`RegistrationRepository`."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ...domain.models import Registration, RegistrationStatus
from ...domain.repository import RegistrationRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    amount      REAL NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_reg_event ON registrations(event_id, status);
CREATE INDEX IF NOT EXISTS ix_reg_user_event ON registrations(user_id, event_id, status);
"""

_CONFIRMED = RegistrationStatus.CONFIRMED.value


class SqliteRegistrationRepository(RegistrationRepository):
    """Repository iscrizioni con persistenza su SQLite."""

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
    def _row_to_registration(row: sqlite3.Row) -> Registration:
        return Registration(
            id=row["id"],
            user_id=row["user_id"],
            event_id=row["event_id"],
            amount=row["amount"],
            status=RegistrationStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add(self, registration: Registration) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO registrations "
                "(id, user_id, event_id, amount, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    registration.id,
                    registration.user_id,
                    registration.event_id,
                    registration.amount,
                    registration.status.value,
                    registration.created_at,
                    registration.updated_at,
                ),
            )

    def get(self, registration_id: str) -> Registration | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM registrations WHERE id = ?", (registration_id,)
            ).fetchone()
        return self._row_to_registration(row) if row is not None else None

    def update(self, registration: Registration) -> None:
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM registrations WHERE id = ?", (registration.id,)
            ).fetchone()
            if exists is None:
                raise KeyError(registration.id)
            conn.execute(
                "UPDATE registrations SET "
                "user_id = ?, event_id = ?, amount = ?, status = ?, "
                "created_at = ?, updated_at = ? WHERE id = ?",
                (
                    registration.user_id,
                    registration.event_id,
                    registration.amount,
                    registration.status.value,
                    registration.created_at,
                    registration.updated_at,
                    registration.id,
                ),
            )

    def delete(self, registration_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM registrations WHERE id = ?", (registration_id,)
            )
            return cur.rowcount > 0

    def list(
        self,
        *,
        user_id: str | None = None,
        event_id: str | None = None,
        status: RegistrationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Registration], int]:
        clauses: list[str] = []
        params: list[object] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if event_id is not None:
            clauses.append("event_id = ?")
            params.append(event_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM registrations{where}", params
            ).fetchone()["n"]
            rows = conn.execute(
                f"SELECT * FROM registrations{where} ORDER BY created_at LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [self._row_to_registration(r) for r in rows], int(total)

    def count_confirmed(self, event_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM registrations WHERE event_id = ? AND status = ?",
                (event_id, _CONFIRMED),
            ).fetchone()
        return int(row["n"])

    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM registrations WHERE user_id = ? AND event_id = ? AND status = ?",
                (user_id, event_id, _CONFIRMED),
            ).fetchone()
        return self._row_to_registration(row) if row is not None else None
