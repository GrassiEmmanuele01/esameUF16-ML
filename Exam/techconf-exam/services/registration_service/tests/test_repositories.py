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


def test_list_second_page_offset(repo):
    # created_at crescente -> ordinamento deterministico id-1..id-5
    for i in range(1, 6):
        repo.add(_make(i=i))
    page1, total1 = repo.list(page=1, page_size=2)
    page2, total2 = repo.list(page=2, page_size=2)
    page3, total3 = repo.list(page=3, page_size=2)
    assert total1 == total2 == total3 == 5
    assert [r.id for r in page1] == ["id-1", "id-2"]
    assert [r.id for r in page2] == ["id-3", "id-4"]
    assert [r.id for r in page3] == ["id-5"]


def test_list_page_beyond_range_empty(repo):
    repo.add(_make(i=1))
    repo.add(_make(i=2))
    items, total = repo.list(page=10, page_size=20)
    assert total == 2 and items == []


def test_list_default_pagination(repo):
    repo.add(_make(i=1))
    items, total = repo.list()
    assert total == 1 and len(items) == 1


def test_cancel_frees_slot(repo):
    # confirmed -> cancelled deve liberare il posto (REQ-REG-B05) e
    # rimuovere l'iscrizione dalla ricerca della coppia confermata (REQ-REG-B04).
    repo.add(_make(i=1, user_id="u1", status=RegistrationStatus.CONFIRMED))
    assert repo.count_confirmed(_EVENT) == 1
    assert repo.find_confirmed("u1", _EVENT) is not None

    repo.update(repo.get("id-1").with_updates(status=RegistrationStatus.CANCELLED))
    assert repo.count_confirmed(_EVENT) == 0
    assert repo.find_confirmed("u1", _EVENT) is None


def test_persistence_json(tmp_path):
    path = tmp_path / "r.json"
    JsonRegistrationRepository(path).add(_make(i=5))
    assert JsonRegistrationRepository(path).get("id-5") is not None


def test_persistence_sqlite(tmp_path):
    path = tmp_path / "r.db"
    SqliteRegistrationRepository(path).add(_make(i=6))
    assert SqliteRegistrationRepository(path).get("id-6") is not None


def test_json_update_persists_across_instances(tmp_path):
    path = tmp_path / "r.json"
    JsonRegistrationRepository(path).add(_make(i=7, status=RegistrationStatus.CONFIRMED))
    JsonRegistrationRepository(path).update(
        JsonRegistrationRepository(path).get("id-7").with_updates(
            status=RegistrationStatus.CANCELLED
        )
    )
    assert JsonRegistrationRepository(path).get("id-7").status is RegistrationStatus.CANCELLED
    assert JsonRegistrationRepository(path).count_confirmed(_EVENT) == 0


def test_sqlite_update_persists_across_instances(tmp_path):
    path = tmp_path / "r.db"
    SqliteRegistrationRepository(path).add(_make(i=8, status=RegistrationStatus.CONFIRMED))
    SqliteRegistrationRepository(path).update(
        SqliteRegistrationRepository(path).get("id-8").with_updates(
            status=RegistrationStatus.CANCELLED
        )
    )
    assert SqliteRegistrationRepository(path).get("id-8").status is RegistrationStatus.CANCELLED
    assert SqliteRegistrationRepository(path).count_confirmed(_EVENT) == 0


def test_json_delete_persists_across_instances(tmp_path):
    path = tmp_path / "r.json"
    JsonRegistrationRepository(path).add(_make(i=9))
    assert JsonRegistrationRepository(path).delete("id-9") is True
    assert JsonRegistrationRepository(path).get("id-9") is None


def test_sqlite_delete_persists_across_instances(tmp_path):
    path = tmp_path / "r.db"
    SqliteRegistrationRepository(path).add(_make(i=10))
    assert SqliteRegistrationRepository(path).delete("id-10") is True
    assert SqliteRegistrationRepository(path).get("id-10") is None
