"""Implementazione su file JSON di :class:`UserRepository`.

Persiste lo stato completo su un file ``.json`` in ``DATA_DIR`` tramite il
modulo ``json`` della standard library. Le scritture sono atomiche (file
temporaneo + ``os.replace``) per evitare corruzione in caso di interruzione.

L'email è sempre memorizzata in minuscolo (REQ-USR-B02) grazie all'invariante
dell'entità ``User``; l'univocità case-insensitive (REQ-USR-B01) è verificata
sul valore normalizzato.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from common import ConflictError

from ...domain.models import Role, User, normalize_email
from ...domain.repository import UserRepository


def _user_to_record(user: User) -> dict[str, Any]:
    return user.to_dict()


def _record_to_user(record: dict[str, Any]) -> User:
    return User(
        id=record["id"],
        first_name=record["first_name"],
        last_name=record["last_name"],
        email=record["email"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        company=record.get("company"),
        role=Role(record.get("role", Role.default().value)),
    )


class JsonUserRepository(UserRepository):
    """Repository utenti con persistenza su file JSON."""

    def __init__(self, file_path: str | os.PathLike[str]) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all({})

    # ---------------------------- I/O di basso livello --------------------- #

    def _read_all(self) -> dict[str, User]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return {rec["id"]: _record_to_user(rec) for rec in data.get("users", [])}

    def _write_all(self, users: dict[str, User]) -> None:
        payload = {"users": [_user_to_record(u) for u in users.values()]}
        # Scrittura atomica: file temporaneo nella stessa dir + replace.
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
            # Pulisce il temporaneo in caso di errore prima del replace.
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    @staticmethod
    def _email_index(users: dict[str, User]) -> dict[str, str]:
        return {u.email_key: uid for uid, u in users.items()}

    # ------------------------------- API --------------------------------- #

    def add(self, user: User) -> None:
        users = self._read_all()
        if user.email_key in self._email_index(users):
            raise ConflictError("Email già registrata", code="EMAIL_ALREADY_EXISTS")
        users[user.id] = user
        self._write_all(users)

    def get(self, user_id: str) -> User | None:
        return self._read_all().get(user_id)

    def find_by_email(self, email: str) -> User | None:
        users = self._read_all()
        uid = self._email_index(users).get(normalize_email(email))
        return users.get(uid) if uid is not None else None

    def update(self, user: User) -> None:
        users = self._read_all()
        if user.id not in users:
            raise KeyError(user.id)
        owner = self._email_index(users).get(user.email_key)
        if owner is not None and owner != user.id:
            raise ConflictError("Email già registrata", code="EMAIL_ALREADY_EXISTS")
        users[user.id] = user
        self._write_all(users)

    def delete(self, user_id: str) -> bool:
        users = self._read_all()
        if user_id not in users:
            return False
        del users[user_id]
        self._write_all(users)
        return True

    def list(
        self,
        *,
        role: Role | None = None,
        email: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        users = self._read_all()
        email_filter = normalize_email(email) if email else None

        def _matches(u: User) -> bool:
            if role is not None and u.role != role:
                return False
            if email_filter is not None and u.email != email_filter:
                return False
            return True

        filtered = [u for u in users.values() if _matches(u)]
        filtered.sort(key=lambda u: u.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total
