"""Unit test dei casi d'uso RegistrationService con directory fittizie.

Copre REQ-REG-B01..B08 usando ``MemoryRegistrationRepository`` e i fake del conftest.
"""

from __future__ import annotations

import pytest

from common import ValidationError
from conftest import FakeEventDirectory, FakeUserDirectory

from registration_service.domain.directories import EventInfo
from registration_service.domain.errors import (
    AlreadyRegistered,
    DependencyUnavailable,
    EventFull,
    EventNotOpen,
    InvalidStatusTransition,
    NotFound,
    ReferenceNotFound,
)
from registration_service.domain.models import RegistrationStatus
from registration_service.domain.service import RegistrationService
from registration_service.infrastructure.repositories import (
    MemoryRegistrationRepository,
)

_USER = "11111111-1111-4111-8111-111111111111"
_USER2 = "22222222-2222-4222-8222-222222222222"
_EVENT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _service(*, capacity=10, price=149.0, status="published", user_known=True, users_unavailable=False, events_unavailable=False):
    repo = MemoryRegistrationRepository()
    known = {_USER, _USER2} if user_known else set()
    users = FakeUserDirectory(known, unavailable=users_unavailable)
    events = FakeEventDirectory(
        {_EVENT: EventInfo(status=status, capacity=capacity, price=price)},
        unavailable=events_unavailable,
    )
    return RegistrationService(repo, users, events), repo


def _payload(user_id=_USER, event_id=_EVENT):
    return {"user_id": user_id, "event_id": event_id}


# --------------------------------- create ---------------------------------- #
def test_create_confirmed_amount_from_event_price():
    svc, _ = _service(price=149.0)
    reg = svc.create_registration(_payload())
    assert reg.status is RegistrationStatus.CONFIRMED
    assert reg.amount == 149.0  # REQ-REG-B06
    assert reg.created_at == reg.updated_at


def test_create_unknown_user_reference_not_found():
    svc, _ = _service(user_known=False)  # REQ-REG-B01
    with pytest.raises(ReferenceNotFound):
        svc.create_registration(_payload())


def test_create_unknown_event_reference_not_found():
    svc, _ = _service()  # REQ-REG-B02
    with pytest.raises(ReferenceNotFound):
        svc.create_registration(_payload(event_id="ffffffff-ffff-4fff-8fff-ffffffffffff"))


def test_create_event_not_published_event_not_open():
    svc, _ = _service(status="draft")  # REQ-REG-B03
    with pytest.raises(EventNotOpen):
        svc.create_registration(_payload())


def test_create_double_registration_conflict():
    svc, _ = _service()  # REQ-REG-B04
    svc.create_registration(_payload())
    with pytest.raises(AlreadyRegistered):
        svc.create_registration(_payload())


def test_create_event_full_conflict():
    svc, _ = _service(capacity=1)  # REQ-REG-B05
    svc.create_registration(_payload(user_id=_USER))
    with pytest.raises(EventFull):
        svc.create_registration(_payload(user_id=_USER2))


def test_create_dependency_unavailable_user():
    svc, _ = _service(users_unavailable=True)
    with pytest.raises(DependencyUnavailable):
        svc.create_registration(_payload())


def test_create_dependency_unavailable_event():
    svc, _ = _service(events_unavailable=True)
    with pytest.raises(DependencyUnavailable):
        svc.create_registration(_payload())


def test_create_invalid_payload():
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.create_registration({"user_id": "not-a-uuid", "event_id": _EVENT})
    with pytest.raises(ValidationError):
        svc.create_registration({"user_id": _USER})  # event_id mancante


# --------------------------- transitions / cancel -------------------------- #
def test_cancel_frees_seat_and_allows_new_registration():
    svc, _ = _service(capacity=1)
    reg = svc.create_registration(_payload(user_id=_USER))
    # Capienza piena: seconda iscrizione bloccata.
    with pytest.raises(EventFull):
        svc.create_registration(_payload(user_id=_USER2))
    # Cancellazione libera il posto (REQ-REG-B05 + B07).
    cancelled = svc.update_status(reg.id, {"status": "cancelled"})
    assert cancelled.status is RegistrationStatus.CANCELLED
    again = svc.create_registration(_payload(user_id=_USER2))
    assert again.status is RegistrationStatus.CONFIRMED


def test_cancelled_to_confirmed_invalid():
    svc, _ = _service()  # REQ-REG-B07
    reg = svc.create_registration(_payload())
    svc.update_status(reg.id, {"status": "cancelled"})
    with pytest.raises(InvalidStatusTransition):
        svc.update_status(reg.id, {"status": "confirmed"})


def test_update_status_noop_same_state():
    svc, _ = _service()
    reg = svc.create_registration(_payload())
    same = svc.update_status(reg.id, {"status": "confirmed"})
    assert same.status is RegistrationStatus.CONFIRMED


def test_update_missing_not_found():
    svc, _ = _service()
    with pytest.raises(NotFound):
        svc.update_status("missing", {"status": "cancelled"})


# --------------------------------- get/delete ------------------------------ #
def test_get_missing_not_found():
    svc, _ = _service()
    with pytest.raises(NotFound):
        svc.get_registration("missing")


def test_delete_then_not_found():
    svc, _ = _service()
    reg = svc.create_registration(_payload())
    svc.delete_registration(reg.id)
    with pytest.raises(NotFound):
        svc.delete_registration(reg.id)


# --------------------------------- stats ----------------------------------- #
def test_stats_capacity_confirmed_available():
    svc, _ = _service(capacity=5)
    svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    stats = svc.stats(_EVENT)  # REQ-REG-B08
    assert stats == {"event_id": _EVENT, "capacity": 5, "confirmed": 2, "available": 3}


def test_stats_unknown_event_not_found():
    svc, _ = _service()
    with pytest.raises(NotFound):
        svc.stats("ffffffff-ffff-4fff-8fff-ffffffffffff")


def test_stats_invalid_event_id_validation_error():
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.stats(None)


def test_list_filters():
    svc, _ = _service()
    svc.create_registration(_payload(user_id=_USER))
    items, total = svc.list_registrations(event_id=_EVENT)
    assert total == 1
    items, total = svc.list_registrations(status="confirmed")
    assert total == 1
