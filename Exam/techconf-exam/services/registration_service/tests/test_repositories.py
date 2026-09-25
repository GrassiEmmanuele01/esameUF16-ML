"""Unit test parametrizzati sui tre backend di persistenza delle iscrizioni."""

from __future__ import annotations

import pytest

from registration_service.domain.models import Registration, RegistrationStatus
from registration_service.infrastructure.repositories import (
    JsonRegistrationRepository,
    MemoryRegistrationRepository,
    SqliteRegistrationRepository,
)

_EVENT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    backend = request.param
    if backend == "memory":
        return MemoryRegistrationRepository()
    if backend == "json":
        return JsonRegistrationRepository(tmp_path / "registrations.json")
    return SqliteRegistrationRepository(tmp_path / "registrations.db")


def _make(i=0, user_id=None, event_id=_EVENT, status=RegistrationStatus.CONFIRMED, amount=149.0):
    ts = f"2026-09-25T14:30:{i:02d}Z"
    return Registration(
        id=f"id-{i}",
        user_id=user_id or f"user-{i}",
        event_id=event_id,
        amount=amount,
        status=status,
        created_at=ts,
        updated_at=ts,
    )


def test_add_get(repo):
    repo.add(_make(i=1))
    got = repo.get("id-1")
    assert got is not None and got.amount == 149.0


def test_get_missing(repo):
    assert repo.get("nope") is None


def test_update(repo):
    repo.add(_make(i=2))
    repo.update(repo.get("id-2").with_updates(status=RegistrationStatus.CANCELLED))
    assert repo.get("id-2").status is RegistrationStatus.CANCELLED


def test_update_missing_keyerror(repo):
    with pytest.raises(KeyError):
        repo.update(_make(i=99))


def test_delete(repo):
    repo.add(_make(i=3))
    assert repo.delete("id-3") is True
    assert repo.delete("id-3") is False


def test_count_confirmed(repo):
    repo.add(_make(i=1, status=RegistrationStatus.CONFIRMED))
    repo.add(_make(i=2, status=RegistrationStatus.CONFIRMED))
    repo.add(_make(i=3, status=RegistrationStatus.CANCELLED))
    assert repo.count_confirmed(_EVENT) == 2
    assert repo.count_confirmed("other") == 0


def test_find_confirmed(repo):
    repo.add(_make(i=1, user_id="u1", status=RegistrationStatus.CONFIRMED))
    repo.add(_make(i=2, user_id="u2", status=RegistrationStatus.CANCELLED))
    assert repo.find_confirmed("u1", _EVENT) is not None
    # Un'iscrizione cancelled non conta come confermata (REQ-REG-B04).
    assert repo.find_confirmed("u2", _EVENT) is None
    assert repo.find_confirmed("u3", _EVENT) is None


def test_list_filters_and_total(repo):
    repo.add(_make(i=1, user_id="u1", status=RegistrationStatus.CONFIRMED))
    repo.add(_make(i=2, user_id="u2", status=RegistrationStatus.CANCELLED))
    repo.add(_make(i=3, user_id="u1", event_id="other", status=RegistrationStatus.CONFIRMED))

    _, total = repo.list(user_id="u1")
    assert total == 2
    _, total = repo.list(event_id=_EVENT)
    assert total == 2
    _, total = repo.list(status=RegistrationStatus.CONFIRMED)
    assert total == 2
    items, total = repo.list(event_id=_EVENT, status=RegistrationStatus.CONFIRMED, page=1, page_size=1)
    assert total == 1 and len(items) == 1


def test_persistence_json(tmp_path):
    path = tmp_path / "r.json"
    JsonRegistrationRepository(path).add(_make(i=5))
    assert JsonRegistrationRepository(path).get("id-5") is not None


def test_persistence_sqlite(tmp_path):
    path = tmp_path / "r.db"
    SqliteRegistrationRepository(path).add(_make(i=6))
    assert SqliteRegistrationRepository(path).get("id-6") is not None
