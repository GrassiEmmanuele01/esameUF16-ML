"""Unit test dei casi d'uso EventService con un UserDirectory fittizio.

Copre le regole di business REQ-EVT-B01..B05, i default e i CRUD, usando un
``MemoryEventRepository`` e il ``FakeUserDirectory`` del conftest.
"""

from __future__ import annotations

import pytest

from common import ValidationError
from conftest import FakeUserDirectory

from event_service.domain.errors import (
    DependencyUnavailable,
    EventNotFound,
    InvalidOrganizer,
    InvalidStatusTransition,
    ReferenceNotFound,
)
from event_service.domain.models import EventStatus
from event_service.domain.service import EventService
from event_service.infrastructure.repositories import MemoryEventRepository


def _payload(organizer_id, **overrides):
    base = {
        "title": "PyConf 2026",
        "organizer_id": organizer_id,
        "venue": "Auditorium",
        "city": "Roma",
        "start_date": "2026-10-15",
        "end_date": "2026-10-16",
        "capacity": 100,
        "price": 149.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def service(fake_users):
    return EventService(MemoryEventRepository(), fake_users), fake_users


# -------------------------------- create ---------------------------------- #
def test_create_defaults_status_draft(service, organizer_id):
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    assert event.status is EventStatus.DRAFT
    assert event.description is None
    assert event.id and event.created_at == event.updated_at


def test_create_verifies_organizer_via_directory(service, organizer_id):
    svc, users = service
    svc.create_event(_payload(organizer_id))
    assert users.calls == [organizer_id]  # REQ-EVT-B01: verifica effettuata


def test_create_unknown_organizer_reference_not_found(fake_users, organizer_id):
    # REQ-EVT-B01: organizer_id non presente -> None -> ReferenceNotFound.
    svc = EventService(MemoryEventRepository(), fake_users)
    with pytest.raises(ReferenceNotFound):
        svc.create_event(_payload("00000000-0000-4000-8000-000000000000"))


def test_create_wrong_role_invalid_organizer():
    # REQ-EVT-B02: utente esiste ma non è organizer.
    attendee = "22222222-2222-4222-8222-222222222222"
    svc = EventService(MemoryEventRepository(), FakeUserDirectory({attendee: "attendee"}))
    with pytest.raises(InvalidOrganizer):
        svc.create_event(_payload(attendee))


def test_create_dependency_unavailable(organizer_id):
    # REQ-EVT-B05: user-service irraggiungibile -> DependencyUnavailable.
    svc = EventService(MemoryEventRepository(), FakeUserDirectory(unavailable=True))
    with pytest.raises(DependencyUnavailable):
        svc.create_event(_payload(organizer_id))


def test_create_end_before_start_validation_error(service, organizer_id):
    # REQ-EVT-B03.
    svc, _ = service
    with pytest.raises(ValidationError):
        svc.create_event(
            _payload(organizer_id, start_date="2026-10-16", end_date="2026-10-15")
        )


def test_create_same_day_is_valid(service, organizer_id):
    svc, _ = service
    event = svc.create_event(
        _payload(organizer_id, start_date="2026-10-15", end_date="2026-10-15")
    )
    assert event.start_date == event.end_date


def test_create_invalid_schema_validation_error(service, organizer_id):
    svc, _ = service
    with pytest.raises(ValidationError):
        svc.create_event(_payload(organizer_id, title="ab"))  # < 3 char
    with pytest.raises(ValidationError):
        svc.create_event(_payload(organizer_id, capacity=0))
    with pytest.raises(ValidationError):
        svc.create_event(_payload(organizer_id, price=-1))


# ---------------------------------- read ----------------------------------- #
def test_get_missing_raises(service):
    svc, _ = service
    with pytest.raises(EventNotFound):
        svc.get_event("missing")


def test_get_existing_returns_event(service, organizer_id):
    svc, _ = service
    created = svc.create_event(_payload(organizer_id))
    fetched = svc.get_event(created.id)
    assert fetched.id == created.id
    assert fetched.title == created.title


def test_list_filters_and_total(service, organizer_id):
    svc, _ = service
    e1 = svc.create_event(_payload(organizer_id, city="Roma"))
    svc.create_event(_payload(organizer_id, city="Milano"))
    svc.update_event(e1.id, {"status": "published"})

    items, total = svc.list_events(status="published", page=1, page_size=10)
    assert total == 1 and items[0].id == e1.id

    items, total = svc.list_events(city="roma", page=1, page_size=10)  # case-insensitive
    assert total == 1


# --------------------------- update / transitions -------------------------- #
def test_transition_draft_to_published_ok(service, organizer_id):
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    updated = svc.update_event(event.id, {"status": "published"})
    assert updated.status is EventStatus.PUBLISHED
    assert updated.created_at == event.created_at  # invariato


def test_transition_draft_to_cancelled_ok(service, organizer_id):
    # REQ-EVT-B04: draft -> cancelled consentita.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    updated = svc.update_event(event.id, {"status": "cancelled"})
    assert updated.status is EventStatus.CANCELLED


def test_transition_published_to_cancelled_ok(service, organizer_id):
    # REQ-EVT-B04: published -> cancelled consentita.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    svc.update_event(event.id, {"status": "published"})
    updated = svc.update_event(event.id, {"status": "cancelled"})
    assert updated.status is EventStatus.CANCELLED


def test_transition_published_to_draft_invalid(service, organizer_id):
    # REQ-EVT-B04.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    svc.update_event(event.id, {"status": "published"})
    with pytest.raises(InvalidStatusTransition):
        svc.update_event(event.id, {"status": "draft"})


def test_transition_from_cancelled_is_terminal(service, organizer_id):
    # REQ-EVT-B04: cancelled è stato terminale, ogni transizione è vietata.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    svc.update_event(event.id, {"status": "cancelled"})
    with pytest.raises(InvalidStatusTransition):
        svc.update_event(event.id, {"status": "published"})
    with pytest.raises(InvalidStatusTransition):
        svc.update_event(event.id, {"status": "draft"})


def test_transition_same_status_noop(service, organizer_id):
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    updated = svc.update_event(event.id, {"status": "draft"})
    assert updated.status is EventStatus.DRAFT


def test_update_missing_organizer_not_reverified(service, organizer_id):
    # Se organizer_id non cambia, non deve rieseguire la verifica.
    svc, users = service
    event = svc.create_event(_payload(organizer_id))
    users.calls.clear()
    svc.update_event(event.id, {"venue": "Nuovo Venue"})
    assert users.calls == []


def test_update_changed_organizer_reverified(service, organizer_id):
    svc, users = service
    event = svc.create_event(_payload(organizer_id))
    new_org = "33333333-3333-4333-8333-333333333333"
    users.roles[new_org] = "organizer"
    users.calls.clear()
    svc.update_event(event.id, {"organizer_id": new_org})
    assert users.calls == [new_org]  # REQ-EVT-B01/B02 rieseguiti


def test_update_changed_organizer_unknown_reference_not_found(service, organizer_id):
    # REQ-EVT-B01 sul path di update.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    with pytest.raises(ReferenceNotFound):
        svc.update_event(
            event.id, {"organizer_id": "00000000-0000-4000-8000-000000000000"}
        )


def test_update_changed_organizer_wrong_role_invalid_organizer(service, organizer_id):
    # REQ-EVT-B02 sul path di update.
    svc, users = service
    event = svc.create_event(_payload(organizer_id))
    attendee = "44444444-4444-4444-8444-444444444444"
    users.roles[attendee] = "attendee"
    with pytest.raises(InvalidOrganizer):
        svc.update_event(event.id, {"organizer_id": attendee})


def test_update_changed_organizer_dependency_unavailable(organizer_id):
    # REQ-EVT-B05 sul path di update: creo con directory disponibile, poi la
    # rendo irraggiungibile e cambio l'organizzatore.
    users = FakeUserDirectory({organizer_id: "organizer"})
    svc = EventService(MemoryEventRepository(), users)
    event = svc.create_event(_payload(organizer_id))
    users.unavailable = True
    with pytest.raises(DependencyUnavailable):
        svc.update_event(
            event.id, {"organizer_id": "55555555-5555-4555-8555-555555555555"}
        )


def test_update_patch_date_coherence_uses_persisted(service, organizer_id):
    # REQ-EVT-B03 in PATCH: end nuovo confrontato con start persistito.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id, start_date="2026-10-15", end_date="2026-10-20"))
    with pytest.raises(ValidationError):
        svc.update_event(event.id, {"end_date": "2026-10-10"})


def test_replace_missing_raises(service, organizer_id):
    svc, _ = service
    with pytest.raises(EventNotFound):
        svc.replace_event("missing", _payload(organizer_id))


def test_replace_updates_fields_and_touches_updated_at(service, organizer_id):
    # Requirement 3.1/3.3: replace aggiorna i campi, updated_at avanza,
    # id/created_at restano invariati.
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    replaced = svc.replace_event(
        event.id, _payload(organizer_id, title="PyConf Edizione 2027", city="Milano")
    )
    assert replaced.id == event.id
    assert replaced.created_at == event.created_at
    assert replaced.title == "PyConf Edizione 2027"
    assert replaced.city == "Milano"
    assert replaced.updated_at >= event.updated_at


def test_delete(service, organizer_id):
    svc, _ = service
    event = svc.create_event(_payload(organizer_id))
    svc.delete_event(event.id)
    with pytest.raises(EventNotFound):
        svc.delete_event(event.id)
