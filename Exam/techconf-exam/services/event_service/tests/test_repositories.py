"""Unit test parametrizzati sui tre backend di persistenza degli eventi."""

from __future__ import annotations

import pytest

from event_service.domain.models import Event, EventStatus
from event_service.infrastructure.repositories import (
    JsonEventRepository,
    MemoryEventRepository,
    SqliteEventRepository,
)


@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    backend = request.param
    if backend == "memory":
        return MemoryEventRepository()
    if backend == "json":
        return JsonEventRepository(tmp_path / "events.json")
    return SqliteEventRepository(tmp_path / "events.db")


def _make_event(i=0, city="Roma", status=EventStatus.DRAFT, uid=None):
    ts = f"2026-09-25T14:30:{i:02d}Z"
    return Event(
        id=uid or f"id-{i}",
        title=f"Event {i}",
        organizer_id="org-1",
        venue="Auditorium",
        city=city,
        start_date="2026-10-15",
        end_date="2026-10-16",
        capacity=100,
        price=149.0,
        status=status,
        created_at=ts,
        updated_at=ts,
        description=None,
    )


def test_add_get_roundtrip(repo):
    repo.add(_make_event(i=1))
    got = repo.get("id-1")
    assert got is not None and got.title == "Event 1"
    assert got.status is EventStatus.DRAFT


def test_get_missing_none(repo):
    assert repo.get("nope") is None


def test_update(repo):
    repo.add(_make_event(i=2))
    repo.update(repo.get("id-2").with_updates(venue="Palazzo"))
    assert repo.get("id-2").venue == "Palazzo"


def test_update_missing_keyerror(repo):
    with pytest.raises(KeyError):
        repo.update(_make_event(i=99, uid="missing"))


def test_delete(repo):
    repo.add(_make_event(i=3))
    assert repo.delete("id-3") is True
    assert repo.delete("id-3") is False


def _seed(repo):
    repo.add(_make_event(i=1, city="Roma", status=EventStatus.DRAFT))
    repo.add(_make_event(i=2, city="Roma", status=EventStatus.PUBLISHED))
    repo.add(_make_event(i=3, city="Milano", status=EventStatus.PUBLISHED))


def test_list_all(repo):
    _seed(repo)
    items, total = repo.list(page=1, page_size=20)
    assert total == 3 and len(items) == 3


def test_list_filter_status(repo):
    _seed(repo)
    items, total = repo.list(status=EventStatus.PUBLISHED, page=1, page_size=20)
    assert total == 2 and all(e.status is EventStatus.PUBLISHED for e in items)


def test_list_filter_city_case_insensitive(repo):
    _seed(repo)
    items, total = repo.list(city="ROMA", page=1, page_size=20)
    assert total == 2 and all(e.city == "Roma" for e in items)


def test_list_combined_filters(repo):
    _seed(repo)
    items, total = repo.list(status=EventStatus.PUBLISHED, city="Milano", page=1, page_size=20)
    assert total == 1 and items[0].id == "id-3"


def test_list_total_before_pagination(repo):
    _seed(repo)
    items, total = repo.list(status=EventStatus.PUBLISHED, page=1, page_size=1)
    assert total == 2 and len(items) == 1


def test_json_persistence_across_instances(tmp_path):
    path = tmp_path / "events.json"
    JsonEventRepository(path).add(_make_event(i=5))
    assert JsonEventRepository(path).get("id-5") is not None


def test_sqlite_persistence_across_instances(tmp_path):
    path = tmp_path / "events.db"
    SqliteEventRepository(path).add(_make_event(i=6))
    assert SqliteEventRepository(path).get("id-6") is not None


def test_list_second_page_offset(repo):
    # created_at crescente -> ordinamento deterministico id-1..id-5
    for i in range(1, 6):
        repo.add(_make_event(i=i))
    page1, total1 = repo.list(page=1, page_size=2)
    page2, total2 = repo.list(page=2, page_size=2)
    page3, total3 = repo.list(page=3, page_size=2)
    assert total1 == total2 == total3 == 5
    assert [e.id for e in page1] == ["id-1", "id-2"]
    assert [e.id for e in page2] == ["id-3", "id-4"]
    assert [e.id for e in page3] == ["id-5"]


def test_list_page_beyond_range_empty(repo):
    _seed(repo)
    items, total = repo.list(page=10, page_size=20)
    assert total == 3 and items == []


def test_json_update_persists_across_instances(tmp_path):
    path = tmp_path / "events.json"
    JsonEventRepository(path).add(_make_event(i=7))
    JsonEventRepository(path).update(
        JsonEventRepository(path).get("id-7").with_updates(venue="Nuovo")
    )
    assert JsonEventRepository(path).get("id-7").venue == "Nuovo"


def test_sqlite_update_persists_across_instances(tmp_path):
    path = tmp_path / "events.db"
    SqliteEventRepository(path).add(_make_event(i=8))
    SqliteEventRepository(path).update(
        SqliteEventRepository(path).get("id-8").with_updates(venue="Nuovo")
    )
    assert SqliteEventRepository(path).get("id-8").venue == "Nuovo"


def test_json_delete_persists_across_instances(tmp_path):
    path = tmp_path / "events.json"
    JsonEventRepository(path).add(_make_event(i=9))
    assert JsonEventRepository(path).delete("id-9") is True
    assert JsonEventRepository(path).get("id-9") is None


def test_sqlite_delete_persists_across_instances(tmp_path):
    path = tmp_path / "events.db"
    SqliteEventRepository(path).add(_make_event(i=10))
    assert SqliteEventRepository(path).delete("id-10") is True
    assert SqliteEventRepository(path).get("id-10") is None
