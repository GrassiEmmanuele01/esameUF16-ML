"""Implementazione su file JSON di :class:`RegistrationRepository` (scrittura atomica)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ...domain.models import Registration, RegistrationStatus
from ...domain.repository import RegistrationRepository


def _record_to_registration(record: dict[str, Any]) -> Registration:
    return Registration(
        id=record["id"],
        user_id=record["user_id"],
        event_id=record["event_id"],
        amount=record["amount"],
        status=RegistrationStatus(record["status"]),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


class JsonRegistrationRepository(RegistrationRepository):
    """Repository iscrizioni con persistenza su file JSON."""

    def __init__(self, file_path: str | os.PathLike[str]) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all({})

    def _read_all(self) -> dict[str, Registration]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return {
            rec["id"]: _record_to_registration(rec)
            for rec in data.get("registrations", [])
        }

    def _write_all(self, registrations: dict[str, Registration]) -> None:
        payload = {"registrations": [r.to_dict() for r in registrations.values()]}
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

    def add(self, registration: Registration) -> None:
        registrations = self._read_all()
        registrations[registration.id] = registration
        self._write_all(registrations)

    def get(self, registration_id: str) -> Registration | None:
        return self._read_all().get(registration_id)

    def update(self, registration: Registration) -> None:
        registrations = self._read_all()
        if registration.id not in registrations:
            raise KeyError(registration.id)
        registrations[registration.id] = registration
        self._write_all(registrations)

    def delete(self, registration_id: str) -> bool:
        registrations = self._read_all()
        if registration_id not in registrations:
            return False
        del registrations[registration_id]
        self._write_all(registrations)
        return True

    def list(
        self,
        *,
        user_id: str | None = None,
        event_id: str | None = None,
        status: RegistrationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Registration], int]:
        registrations = self._read_all()

        def _matches(r: Registration) -> bool:
            if user_id is not None and r.user_id != user_id:
                return False
            if event_id is not None and r.event_id != event_id:
                return False
            if status is not None and r.status != status:
                return False
            return True

        filtered = [r for r in registrations.values() if _matches(r)]
        filtered.sort(key=lambda r: r.created_at)
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset : offset + page_size], total

    def count_confirmed(self, event_id: str) -> int:
        return sum(
            1
            for r in self._read_all().values()
            if r.event_id == event_id and r.status is RegistrationStatus.CONFIRMED
        )

    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        for r in self._read_all().values():
            if (
                r.user_id == user_id
                and r.event_id == event_id
                and r.status is RegistrationStatus.CONFIRMED
            ):
                return r
        return None
