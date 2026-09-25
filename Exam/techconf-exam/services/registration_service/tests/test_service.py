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


# ------------------------ create: format & extra cases -------------------- #
def test_create_generates_uuid_v4_id_and_iso_utc_timestamps():
    """Requirement 1.2: id UUID v4 lato server, timestamp ISO 8601 UTC coincidenti."""
    import uuid

    svc, _ = _service()
    reg = svc.create_registration(_payload())
    # id è un UUID versione 4 generato lato server.
    parsed = uuid.UUID(reg.id)
    assert parsed.version == 4
    # created_at/updated_at coincidono e sono ISO 8601 UTC (suffisso Z).
    assert reg.created_at == reg.updated_at
    assert reg.created_at.endswith("Z")


def test_create_event_cancelled_event_not_open():
    """REQ-REG-B03: un evento 'cancelled' non consente iscrizioni."""
    svc, _ = _service(status="cancelled")
    with pytest.raises(EventNotOpen):
        svc.create_registration(_payload())


def test_create_extra_field_rejected():
    """Requirement 1.4: campi non ammessi -> VALIDATION_ERROR."""
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.create_registration({"user_id": _USER, "event_id": _EVENT, "amount": 10})


def test_create_dependency_unavailable_does_not_persist():
    """Requirement 14.2: in caso di dipendenza offline non viene creata l'iscrizione."""
    svc, repo = _service(events_unavailable=True)
    with pytest.raises(DependencyUnavailable):
        svc.create_registration(_payload())
    assert repo.count_confirmed(_EVENT) == 0


# ------------------------ B04.2: cancel then re-register ------------------- #
def test_new_registration_allowed_after_cancel_same_pair():
    """REQ-REG-B04.2: se l'unica iscrizione della coppia è cancelled, una nuova è consentita."""
    svc, _ = _service(capacity=10)  # nessuna pressione di capienza
    reg = svc.create_registration(_payload(user_id=_USER))
    svc.update_status(reg.id, {"status": "cancelled"})
    again = svc.create_registration(_payload(user_id=_USER))
    assert again.status is RegistrationStatus.CONFIRMED
    assert again.id != reg.id


# --------------------------------- get/delete ------------------------------ #
def test_get_returns_created_registration():
    """Requirement 2.1: get per id esistente restituisce l'iscrizione."""
    svc, _ = _service()
    reg = svc.create_registration(_payload())
    fetched = svc.get_registration(reg.id)
    assert fetched.id == reg.id
    assert fetched.user_id == _USER
    assert fetched.event_id == _EVENT


def test_delete_existing_returns_none():
    """Requirement 4.1: delete di un'iscrizione esistente non solleva e la rimuove."""
    svc, _ = _service()
    reg = svc.create_registration(_payload())
    assert svc.delete_registration(reg.id) is None
    with pytest.raises(NotFound):
        svc.get_registration(reg.id)


# ------------------------------- list / paging ----------------------------- #
def test_list_defaults_page_and_size():
    """Requirement 3.1/3.2: risposta paginata con default page=1, page_size=20."""
    svc, _ = _service()
    svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    items, total = svc.list_registrations()
    assert total == 2
    assert len(items) == 2


def test_list_pagination_total_before_slicing():
    """Requirement 3.4: total calcolato sull'insieme filtrato, prima della paginazione."""
    svc, _ = _service()
    svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    page1, total = svc.list_registrations(page=1, page_size=1)
    assert total == 2
    assert len(page1) == 1
    page2, total2 = svc.list_registrations(page=2, page_size=1)
    assert total2 == 2
    assert len(page2) == 1
    assert page1[0].id != page2[0].id


def test_list_combined_filters():
    """Requirement 3.3: i filtri user_id/event_id/status vengono combinati."""
    svc, _ = _service()
    reg = svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    items, total = svc.list_registrations(
        user_id=_USER, event_id=_EVENT, status="confirmed"
    )
    assert total == 1
    assert items[0].id == reg.id


def test_list_filter_by_status_cancelled():
    """Requirement 3.3: filtro per status cancelled."""
    svc, _ = _service()
    reg = svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    svc.update_status(reg.id, {"status": "cancelled"})
    items, total = svc.list_registrations(status="cancelled")
    assert total == 1
    assert items[0].id == reg.id


def test_list_invalid_status_validation_error():
    """Requirement 3.5: status fuori enum -> VALIDATION_ERROR."""
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.list_registrations(status="bogus")


# --------------------------------- stats ----------------------------------- #
def test_stats_reflects_freed_seat_after_cancel():
    """REQ-REG-B05.3 + B08: la cancellazione libera un posto riflesso in /stats."""
    svc, _ = _service(capacity=5)
    r1 = svc.create_registration(_payload(user_id=_USER))
    svc.create_registration(_payload(user_id=_USER2))
    assert svc.stats(_EVENT)["available"] == 3
    svc.update_status(r1.id, {"status": "cancelled"})
    stats = svc.stats(_EVENT)
    assert stats["confirmed"] == 1
    assert stats["available"] == 4


def test_stats_missing_event_id_validation_error():
    """Requirement 13.4: event_id assente/vuoto -> VALIDATION_ERROR."""
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.stats("")


def test_stats_malformed_event_id_validation_error():
    """Requirement 13.4: event_id non UUID -> VALIDATION_ERROR."""
    svc, _ = _service()
    with pytest.raises(ValidationError):
        svc.stats("not-a-uuid")
