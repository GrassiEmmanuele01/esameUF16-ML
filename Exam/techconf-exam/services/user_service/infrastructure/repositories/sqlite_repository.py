"""Implementazione su SQLite di :class:`UserRepository`.

Persistenza relazionale tramite il modulo ``sqlite3`` della standard library,
su un file di database in ``DATA_DIR``. L'univocità case-insensitive
(REQ-USR-B01) è imposta a livello di storage da un indice UNIQUE sull'email
normalizzata; l'email è sempre memorizzata in minuscolo (REQ-USR-B02) grazie
all'invariante dell'entità ``User``.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from common import ConflictError

from ...domain.models import Role, User, normalize_email
from ...domain.repository import UserRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT NOT NULL,
    company     TEXT,
    role        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email ON users(email);
"""


class SqliteUserRepository(UserRepository):
    """Repository utenti con persistenza su SQLite."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(self._path)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Apre una connessione, la commit-ta su successo e la chiude sempre.

        Chiudere esplicitamente la connessione evita di lasciare handle aperti
        sul file di database (rilevante soprattutto su Windows).
        """
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
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            company=row["company"],
            role=Role(row["role"]),
        )

    def add(self, user: User) -> None:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO users "
                    "(id, first_name, last_name, email, company, role, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user.id,
                        user.first_name,
                        user.last_name,
                        user.email,
                        user.company,
                        user.role.value,
                        user.created_at,
                        user.updated_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                # Distingue il conflitto sull'email dalla PK.
                if "email" in str(exc).lower():
                    raise ConflictError(
                        "Email già registrata", code="EMAIL_ALREADY_EXISTS"
                    ) from exc
                raise ConflictError(
                    "Utente già esistente", code="EMAIL_ALREADY_EXISTS"
                ) from exc

    def get(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return self._row_to_user(row) if row is not None else None

    def find_by_email(self, email: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (normalize_email(email),)
            ).fetchone()
        return self._row_to_user(row) if row is not None else None

    def update(self, user: User) -> None:
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE id = ?", (user.id,)
            ).fetchone()
            if exists is None:
                raise KeyError(user.id)
            try:
                conn.execute(
                    "UPDATE users SET "
                    "first_name = ?, last_name = ?, email = ?, company = ?, "
                    "role = ?, created_at = ?, updated_at = ? "
                    "WHERE id = ?",
                    (
                        user.first_name,
                        user.last_name,
                        user.email,
                        user.company,
                        user.role.value,
                        user.created_at,
                        user.updated_at,
                        user.id,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(
                    "Email già registrata", code="EMAIL_ALREADY_EXISTS"
                ) from exc

    def delete(self, user_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cur.rowcount > 0

    def list(
        self,
        *,
        role: Role | None = None,
        email: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        clauses: list[str] = []
        params: list[object] = []
        if role is not None:
            clauses.append("role = ?")
            params.append(role.value)
        if email:
            clauses.append("email = ?")
            params.append(normalize_email(email))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        offset = (page - 1) * page_size
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM users{where}", params
            ).fetchone()["n"]
            rows = conn.execute(
                f"SELECT * FROM users{where} ORDER BY created_at LIMIT ? OFFSET ?",
                (*params, page_size, offset),
            ).fetchall()
        return [self._row_to_user(r) for r in rows], int(total)
