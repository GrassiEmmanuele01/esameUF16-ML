"""Unit test dell'entrypoint HTTP con validazione del contratto.

Costruisce un'app Flask con ``RegistrationService`` iniettato (repository in
memoria + directory fittizie). Ogni risposta è validata contro
``contracts/openapi/registration-service.yaml`` con ``assert_matches_contract``.
"""

from __future__ import annotations

import pytest
from flask import Flask

from validator import assert_matches_contract
from conftest import FakeEventDirectory, FakeUserDirectory

from registration_service.domain.directories import EventInfo
from registration_service.domain.service import RegistrationService
from registration_service.entrypoints.http import (
    create_registration_blueprint,
    register_error_handlers,
)
from registration_service.infrastructure.repositories import (
    MemoryRegistrationRepository,
)

_USER = "11111111-1111-4111-8111-111111111111"
_USER2 = "22222222-2222-4222-8222-222222222222"
_EVENT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_UNKNOWN = "ffffffff-ffff-4fff-8fff-ffffffffffff"


def _build_client(*, capacity=10, price=149.0, status="published", users=None, events=None):
    repo = MemoryRegistrationRepository()
    users = users or FakeUserDirectory({_USER, _USER2})
    events = events or FakeEventDirectory(
        {_EVENT: EventInfo(status=status, capacity=capacity, price=price)}
    )
    service = RegistrationService(repo, users, events)
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(create_registration_blueprint(service))
    register_error_handlers(app)
    return app.test_client()


@pytest.fixture
def client():
    return _build_client()


def _check(method, path, resp):
    body = resp.get_json(silent=True)
    assert_matches_contract(
        "registration",
        method,
        path,
        {"status_code": resp.status_code, "headers": dict(resp.headers), "json": body},
    )
    return body


def _register(client, user_id=_USER, event_id=_EVENT):
    resp = client.post("/api/v1/registrations", json={"user_id": user_id, "event_id": event_id})
    return resp, _check("POST", "/api/v1/registrations", resp)


# --------------------------------- health ---------------------------------- #
def test_health(client):
    resp = client.get("/health")
    body = _check("GET", "/health", resp)
    assert resp.status_code == 200
    assert body == {"status": "ok", "service": "registration-service"}


# --------------------------------- create ---------------------------------- #
def test_create_201_confirmed_amount_location(client):
    resp, body = _register(client)
    assert resp.status_code == 201
    assert body["status"] == "confirmed"
    assert body["amount"] == 149.0
    assert resp.headers["Location"] == f"/api/v1/registrations/{body['id']}"


def test_create_unknown_user_422(client):
    resp = client.post("/api/v1/registrations", json={"user_id": _UNKNOWN, "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 422 and body["error"]["code"] == "REFERENCE_NOT_FOUND"


def test_create_unknown_event_422(client):
    resp = client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _UNKNOWN})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 422 and body["error"]["code"] == "REFERENCE_NOT_FOUND"


def test_create_event_not_open_422():
    client = _build_client(status="draft")
    resp = client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 422 and body["error"]["code"] == "EVENT_NOT_OPEN"


def test_create_double_registration_409(client):
    _register(client)
    resp = client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 409 and body["error"]["code"] == "ALREADY_REGISTERED"


def test_create_event_full_409():
    client = _build_client(capacity=1)
    client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _EVENT})
    resp = client.post("/api/v1/registrations", json={"user_id": _USER2, "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 409 and body["error"]["code"] == "EVENT_FULL"


def test_create_dependency_unavailable_503():
    client = _build_client(users=FakeUserDirectory(unavailable=True))
    resp = client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 503 and body["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


def test_create_malformed_json_400(client):
    resp = client.post("/api/v1/registrations", data="{bad", content_type="application/json")
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 400 and body["error"]["code"] == "MALFORMED_JSON"


def test_create_validation_error_422(client):
    resp = client.post("/api/v1/registrations", json={"user_id": "bad", "event_id": _EVENT})
    body = _check("POST", "/api/v1/registrations", resp)
    assert resp.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------ get / patch -------------------------------- #
def test_get_and_404(client):
    _, created = _register(client)
    path = f"/api/v1/registrations/{created['id']}"
    resp = client.get(path)
    assert _check("GET", path, resp)["id"] == created["id"]

    missing = f"/api/v1/registrations/{_UNKNOWN}"
    resp = client.get(missing)
    body = _check("GET", missing, resp)
    assert resp.status_code == 404 and body["error"]["code"] == "NOT_FOUND"


def test_patch_cancel_and_invalid_transition(client):
    _, created = _register(client)
    path = f"/api/v1/registrations/{created['id']}"
    resp = client.patch(path, json={"status": "cancelled"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 200 and body["status"] == "cancelled"

    resp = client.patch(path, json={"status": "confirmed"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 422 and body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_put_not_allowed_405(client):
    path = f"/api/v1/registrations/{_UNKNOWN}"
    resp = client.put(path)
    # Il contratto dichiara 405 per PUT.
    _check("PUT", path, resp)
    assert resp.status_code == 405


def test_delete_204_then_404(client):
    _, created = _register(client)
    path = f"/api/v1/registrations/{created['id']}"
    resp = client.delete(path)
    _check("DELETE", path, resp)
    assert resp.status_code == 204 and resp.data == b""
    resp = client.delete(path)
    body = _check("DELETE", path, resp)
    assert resp.status_code == 404 and body["error"]["code"] == "NOT_FOUND"


# --------------------------------- stats ----------------------------------- #
def test_stats_ok():
    client = _build_client(capacity=5)
    client.post("/api/v1/registrations", json={"user_id": _USER, "event_id": _EVENT})
    client.post("/api/v1/registrations", json={"user_id": _USER2, "event_id": _EVENT})
    path = f"/api/v1/registrations/stats?event_id={_EVENT}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 200
    assert body == {"event_id": _EVENT, "capacity": 5, "confirmed": 2, "available": 3}


def test_stats_unknown_event_404(client):
    path = f"/api/v1/registrations/stats?event_id={_UNKNOWN}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 404 and body["error"]["code"] == "NOT_FOUND"


def test_stats_invalid_event_id_422(client):
    path = "/api/v1/registrations/stats?event_id=not-a-uuid"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------ list / filters ----------------------------- #
def test_list_pagination_and_filters(client):
    _register(client, user_id=_USER)
    _register(client, user_id=_USER2)
    path = f"/api/v1/registrations?event_id={_EVENT}&status=confirmed&page=1&page_size=10"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 200
    assert body["page"] == 1 and body["page_size"] == 10 and body["total"] == 2


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "status=bogus"])
def test_list_invalid_params_422(client, query):
    path = f"/api/v1/registrations?{query}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR"
