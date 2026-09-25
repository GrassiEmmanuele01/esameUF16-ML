"""Unit test parametrizzati sui tre backend di persistenza.

La stessa suite viene eseguita su ``MemoryUserRepository``,
``JsonUserRepository`` e ``SqliteUserRepository`` per garantire un comportamento
identico. I backend su file usano ``tmp_path`` (fixture di pytest).

Copre: round-trip CRUD, normalizzazione email in minuscolo (REQ-USR-B02),
univocità case-insensitive su add/update (REQ-USR-B01) e filtri/paginazione
con ``total`` calcolato prima della paginazione (REQ-USR-B03).
"""

from __future__ import annotations

import pytest

from common import ConflictError
from user_service.domain.models import Role, User
from user_service.infrastructure.repositories import (
    JsonUserRepository,
    MemoryUserRepository,
    SqliteUserRepository,
)


# --------------------------------------------------------------------------- #
# Fixture: un repository per ciascun backend
# --------------------------------------------------------------------------- #
@pytest.fixture(params=["memory", "json", "sqlite"])
def repo(request, tmp_path):
    backend = request.param
    if backend == "memory":
        return MemoryUserRepository()
    if backend == "json":
        return JsonUserRepository(tmp_path / "users.json")
    return SqliteUserRepository(tmp_path / "users.db")


def _make_user(email="a@b.com", role=Role.ATTENDEE, i=0, uid=None):
    ts = f"2026-09-25T14:30:{i:02d}Z"
    return User(
        id=uid or f"id-{i}",
        first_name="A",
        last_name="B",
        email=email,
        created_at=ts,
        updated_at=ts,
        role=role,
    )


# --------------------------------- CRUD ------------------------------------ #
def test_add_and_get_roundtrip(repo):
    user = _make_user(email="Mario@Example.com", i=1)
    repo.add(user)
    got = repo.get(user.id)
    assert got is not None
    assert got.id == user.id
    assert got.first_name == "A"


def test_get_missing_returns_none(repo):
    assert repo.get("does-not-exist") is None


def test_email_stored_lowercase(repo):
    # REQ-USR-B02: email memorizzata in minuscolo.
    repo.add(_make_user(email="MixedCase@EXAMPLE.CoM", i=2))
    got = repo.get("id-2")
    assert got.email == "mixedcase@example.com"


def test_update_changes_fields(repo):
    repo.add(_make_user(email="x@y.com", i=3))
    updated = repo.get("id-3").with_updates(first_name="Changed")
    repo.update(updated)
    assert repo.get("id-3").first_name == "Changed"


def test_update_missing_raises_keyerror(repo):
    with pytest.raises(KeyError):
        repo.update(_make_user(email="ghost@y.com", i=99, uid="missing"))


def test_delete_returns_true_then_false(repo):
    repo.add(_make_user(email="d@y.com", i=4))
    assert repo.delete("id-4") is True
    assert repo.delete("id-4") is False
    assert repo.get("id-4") is None


# ------------------------- uniqueness (case-insensitive) ------------------- #
def test_add_duplicate_email_case_insensitive_conflicts(repo):
    # REQ-USR-B01: univocità case-insensitive su add.
    repo.add(_make_user(email="dup@example.com", i=5))
    with pytest.raises(ConflictError) as exc:
        repo.add(_make_user(email="DUP@EXAMPLE.COM", i=6))
    assert exc.value.code == "EMAIL_ALREADY_EXISTS"


def test_find_by_email_is_case_insensitive(repo):
    repo.add(_make_user(email="findme@example.com", i=7))
    assert repo.find_by_email("FINDME@example.COM").id == "id-7"
    assert repo.find_by_email("nobody@example.com") is None


def test_update_to_others_email_conflicts(repo):
    repo.add(_make_user(email="first@example.com", i=8))
    repo.add(_make_user(email="second@example.com", i=9))
    clash = repo.get("id-9").with_updates(email="FIRST@example.com")
    with pytest.raises(ConflictError) as exc:
        repo.update(clash)
    assert exc.value.code == "EMAIL_ALREADY_EXISTS"


def test_update_own_email_case_variation_allowed(repo):
    repo.add(_make_user(email="self@example.com", i=10))
    same = repo.get("id-10").with_updates(email="SELF@Example.com", first_name="Z")
    repo.update(same)  # non deve sollevare
    got = repo.get("id-10")
    assert got.first_name == "Z"
    assert got.email == "self@example.com"


# ----------------------------- list / filters ----------------------------- #
def _seed_mixed(repo):
    repo.add(_make_user(email="att1@example.com", role=Role.ATTENDEE, i=11))
    repo.add(_make_user(email="att2@example.com", role=Role.ATTENDEE, i=12))
    repo.add(_make_user(email="spk@example.com", role=Role.SPEAKER, i=13))
    repo.add(_make_user(email="org@example.com", role=Role.ORGANIZER, i=14))


def test_list_no_filter_returns_all_with_total(repo):
    _seed_mixed(repo)
    items, total = repo.list(page=1, page_size=20)
    assert total == 4
    assert len(items) == 4


def test_list_filter_by_role(repo):
    _seed_mixed(repo)
    items, total = repo.list(role=Role.ATTENDEE, page=1, page_size=20)
    assert total == 2
    assert all(u.role == Role.ATTENDEE for u in items)


def test_list_filter_by_email_case_insensitive(repo):
    _seed_mixed(repo)
    items, total = repo.list(email="SPK@EXAMPLE.COM", page=1, page_size=20)
    assert total == 1
    assert items[0].email == "spk@example.com"


def test_list_total_counts_filtered_set_before_pagination(repo):
    # REQ-USR-B03: total = conteggio sull'insieme filtrato, non la pagina.
    _seed_mixed(repo)
    items, total = repo.list(role=Role.ATTENDEE, page=1, page_size=1)
    assert total == 2
    assert len(items) == 1


def test_list_pagination_window(repo):
    _seed_mixed(repo)
    page1, total1 = repo.list(page=1, page_size=2)
    page2, total2 = repo.list(page=2, page_size=2)
    assert total1 == total2 == 4
    assert len(page1) == 2 and len(page2) == 2
    ids = {u.id for u in page1} | {u.id for u in page2}
    assert len(ids) == 4  # pagine disgiunte


# --------------------------- persistence (file backends) ------------------- #
def test_json_persistence_across_instances(tmp_path):
    path = tmp_path / "persist.json"
    r1 = JsonUserRepository(path)
    r1.add(_make_user(email="persist@example.com", i=20))
    r2 = JsonUserRepository(path)
    assert r2.find_by_email("PERSIST@EXAMPLE.COM") is not None


def test_sqlite_persistence_across_instances(tmp_path):
    path = tmp_path / "persist.db"
    r1 = SqliteUserRepository(path)
    r1.add(_make_user(email="persist@example.com", i=21))
    r2 = SqliteUserRepository(path)
    assert r2.find_by_email("PERSIST@EXAMPLE.COM") is not None
