"""Unit test dell'entrypoint HTTP con validazione del contratto.

Costruisce un'app Flask iniettando un ``EventService`` con
``MemoryEventRepository`` e ``FakeUserDirectory`` (nessuna rete). Ogni risposta è
validata contro ``contracts/openapi/event-service.yaml`` con
``assert_matches_contract``.
"""

from __future__ import annotations

import pytest
from flask import Flask

from validator import assert_matches_contract
from conftest import FakeUserDirectory

from event_service.domain.service import EventService
from event_service.entrypoints.http import (
    create_event_blueprint,
    register_error_handlers,
)
from event_service.infrastructure.repositories import MemoryEventRepository

_ORG = "11111111-1111-4111-8111-111111111111"
_ATTENDEE = "22222222-2222-4222-8222-222222222222"


def _build_client(users: FakeUserDirectory):
    service = EventService(MemoryEventRepository(), users)
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(create_event_blueprint(service))
    register_error_handlers(app)
    return app.test_client()


@pytest.fixture
def users():
    return FakeUserDirectory({_ORG: "organizer", _ATTENDEE: "attendee"})


@pytest.fixture
def client(users):
    return _build_client(users)


def _check(method, path, resp):
    body = resp.get_json(silent=True)
    assert_matches_contract(
        "event",
        method,
        path,
        {"status_code": resp.status_code, "headers": dict(resp.headers), "json": body},
    )
    return body


def _payload(**overrides):
    base = {
        "title": "PyConf 2026",
        "organizer_id": _ORG,
        "venue": "Auditorium",
        "city": "Roma",
        "start_date": "2026-10-15",
        "end_date": "2026-10-16",
        "capacity": 100,
        "price": 149.0,
    }
    base.update(overrides)
    return base


def _create(client, **overrides):
    resp = client.post("/api/v1/events", json=_payload(**overrides))
    return resp, _check("POST", "/api/v1/events", resp)


# --------------------------------- health ---------------------------------- #
def test_health(client):
    resp = client.get("/health")
    body = _check("GET", "/health", resp)
    assert resp.status_code == 200
    assert body == {"status": "ok", "service": "event-service"}


# --------------------------------- create ---------------------------------- #
def test_create_201_location_and_default_status(client):
    resp, body = _create(client)
    assert resp.status_code == 201
    assert resp.headers["Location"] == f"/api/v1/events/{body['id']}"
    assert body["status"] == "draft"


def test_create_unknown_organizer_422_reference_not_found(client):
    resp = client.post("/api/v1/events", json=_payload(organizer_id="00000000-0000-4000-8000-000000000000"))
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "REFERENCE_NOT_FOUND"


def test_create_wrong_role_422_invalid_organizer(client):
    resp = client.post("/api/v1/events", json=_payload(organizer_id=_ATTENDEE))
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "INVALID_ORGANIZER"


def test_create_end_before_start_422_validation_error(client):
    resp = client.post(
        "/api/v1/events", json=_payload(start_date="2026-10-16", end_date="2026-10-15")
    )
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_schema_violation_422(client):
    resp = client.post("/api/v1/events", json=_payload(capacity=0))
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_malformed_json_400(client):
    resp = client.post("/api/v1/events", data="{bad", content_type="application/json")
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 400
    assert body["error"]["code"] == "MALFORMED_JSON"


def test_create_dependency_unavailable_503():
    client = _build_client(FakeUserDirectory(unavailable=True))
    resp = client.post("/api/v1/events", json=_payload())
    body = _check("POST", "/api/v1/events", resp)
    assert resp.status_code == 503
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


# ------------------------------- get / update ------------------------------ #
def test_get_and_404(client):
    _, created = _create(client)
    path = f"/api/v1/events/{created['id']}"
    resp = client.get(path)
    assert _check("GET", path, resp)["id"] == created["id"]

    missing = "/api/v1/events/00000000-0000-4000-8000-000000000000"
    resp = client.get(missing)
    body = _check("GET", missing, resp)
    assert resp.status_code == 404
    assert body["error"]["code"] == "EVENT_NOT_FOUND"


def test_patch_status_transition(client):
    _, created = _create(client)
    path = f"/api/v1/events/{created['id']}"
    resp = client.patch(path, json={"status": "published"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 200 and body["status"] == "published"

    resp = client.patch(path, json={"status": "draft"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_put_replace(client):
    _, created = _create(client)
    path = f"/api/v1/events/{created['id']}"
    resp = client.put(path, json=_payload(capacity=200))
    body = _check("PUT", path, resp)
    assert resp.status_code == 200 and body["capacity"] == 200


def test_delete_204_then_404(client):
    _, created = _create(client)
    path = f"/api/v1/events/{created['id']}"
    resp = client.delete(path)
    _check("DELETE", path, resp)
    assert resp.status_code == 204 and resp.data == b""
    resp = client.delete(path)
    body = _check("DELETE", path, resp)
    assert resp.status_code == 404 and body["error"]["code"] == "EVENT_NOT_FOUND"


# ------------------------------ list / filters ----------------------------- #
def test_list_pagination_and_filters(client):
    e1, b1 = _create(client, city="Roma")
    _create(client, city="Milano")
    client.patch(f"/api/v1/events/{b1['id']}", json={"status": "published"})

    path = "/api/v1/events?page=1&page_size=10&status=published&city=Roma"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 200
    assert body["page"] == 1 and body["page_size"] == 10
    assert all(e["status"] == "published" and e["city"] == "Roma" for e in body["items"])


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "status=boss"])
def test_list_invalid_params_422(client, query):
    path = f"/api/v1/events?{query}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"
