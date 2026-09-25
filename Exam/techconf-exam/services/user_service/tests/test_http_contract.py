"""Unit test dell'entrypoint HTTP con validazione del contratto.

Ogni risposta è validata contro ``contracts/openapi/user-service.yaml`` tramite
``assert_matches_contract``. La suite è parametrizzata sui tre backend di
storage (memory/json/sqlite) usando ``tmp_path`` per quelli su file, così da
verificare che routing, status code e forma delle risposte siano conformi al
contratto indipendentemente dalla persistenza.
"""

from __future__ import annotations

import pytest

from validator import assert_matches_contract

from user_service.app import create_app
from user_service.config import Config


# --------------------------------------------------------------------------- #
# App + client parametrizzati sui backend
# --------------------------------------------------------------------------- #
@pytest.fixture(params=["memory", "json", "sqlite"])
def client(request, tmp_path):
    config = Config(
        port=5001,
        storage_backend=request.param,
        data_dir=str(tmp_path),
    )
    app = create_app(config)
    app.testing = True
    return app.test_client()


def _check(method: str, path: str, response) -> object:
    """Valida la risposta contro il contratto e restituisce il body JSON."""
    body = response.get_json(silent=True)
    assert_matches_contract(
        "user",
        method,
        path,
        {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "json": body,
        },
    )
    return body


def _create(client, **overrides):
    payload = {"first_name": "Mario", "last_name": "Rossi", "email": "mario@example.com"}
    payload.update(overrides)
    resp = client.post("/api/v1/users", json=payload)
    return resp, _check("POST", "/api/v1/users", resp)


# --------------------------------- health ---------------------------------- #
def test_health(client):
    resp = client.get("/health")
    body = _check("GET", "/health", resp)
    assert resp.status_code == 200
    assert body == {"status": "ok", "service": "user-service"}


# --------------------------------- create ---------------------------------- #
def test_create_returns_201_location_and_defaults(client):
    resp, body = _create(client, email="Mario@Example.COM")
    assert resp.status_code == 201
    assert resp.headers["Location"] == f"/api/v1/users/{body['id']}"
    assert body["email"] == "mario@example.com"  # REQ-USR-B02
    assert body["role"] == "attendee"            # default
    assert body["company"] is None               # default


def test_create_duplicate_email_conflict(client):
    _create(client, email="dup@example.com")
    resp, body = _create(client, email="DUP@EXAMPLE.COM")  # REQ-USR-B01
    assert resp.status_code == 409
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.parametrize(
    "payload",
    [
        {"first_name": "A", "last_name": "B"},                        # email mancante
        {"first_name": "A", "last_name": "B", "email": "bad"},        # email non valida
        {"first_name": "A" * 51, "last_name": "B", "email": "a@b.com"},  # nome troppo lungo
        {"first_name": "A", "last_name": "B", "email": "a@b.com", "role": "boss"},  # ruolo fuori enum
        {"first_name": "A", "last_name": "B", "email": "a@b.com", "extra": 1},      # campo non ammesso
    ],
)
def test_create_validation_errors(client, payload):
    resp = client.post("/api/v1/users", json=payload)
    body = _check("POST", "/api/v1/users", resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_malformed_json_returns_400(client):
    resp = client.post(
        "/api/v1/users", data="{not valid", content_type="application/json"
    )
    body = _check("POST", "/api/v1/users", resp)
    assert resp.status_code == 400
    assert body["error"]["code"] == "MALFORMED_JSON"


# ----------------------------------- get ----------------------------------- #
def test_get_existing(client):
    _, created = _create(client, email="get@example.com")
    path = f"/api/v1/users/{created['id']}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 200
    assert body["id"] == created["id"]


def test_get_missing_returns_404(client):
    path = "/api/v1/users/00000000-0000-4000-8000-000000000000"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 404
    assert body["error"]["code"] == "USER_NOT_FOUND"


# --------------------------------- update ---------------------------------- #
def test_patch_partial_update(client):
    _, created = _create(client, email="patch@example.com")
    path = f"/api/v1/users/{created['id']}"
    resp = client.patch(path, json={"company": "ACME"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 200
    assert body["company"] == "ACME"
    assert body["first_name"] == "Mario"  # invariato
    assert body["created_at"] == created["created_at"]  # invariato


def test_put_replace(client):
    _, created = _create(client, email="put@example.com")
    path = f"/api/v1/users/{created['id']}"
    resp = client.put(
        path,
        json={
            "first_name": "Luigi",
            "last_name": "Verdi",
            "email": "luigi@example.com",
            "role": "speaker",
        },
    )
    body = _check("PUT", path, resp)
    assert resp.status_code == 200
    assert body["first_name"] == "Luigi"
    assert body["role"] == "speaker"
    assert body["id"] == created["id"]


def test_update_missing_returns_404(client):
    path = "/api/v1/users/00000000-0000-4000-8000-000000000000"
    resp = client.patch(path, json={"company": "X"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 404
    assert body["error"]["code"] == "USER_NOT_FOUND"


def test_update_email_conflict_returns_409(client):
    _create(client, email="one@example.com")
    _, second = _create(client, email="two@example.com")
    path = f"/api/v1/users/{second['id']}"
    resp = client.patch(path, json={"email": "ONE@EXAMPLE.COM"})
    body = _check("PATCH", path, resp)
    assert resp.status_code == 409
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


# --------------------------------- delete ---------------------------------- #
def test_delete_204_then_404(client):
    _, created = _create(client, email="del@example.com")
    path = f"/api/v1/users/{created['id']}"
    resp = client.delete(path)
    _check("DELETE", path, resp)
    assert resp.status_code == 204
    assert resp.data == b""

    resp2 = client.delete(path)
    body = _check("DELETE", path, resp2)
    assert resp2.status_code == 404
    assert body["error"]["code"] == "USER_NOT_FOUND"


# ------------------------------ list / filters ----------------------------- #
def test_list_default_pagination(client):
    for i in range(3):
        _create(client, email=f"list{i}@example.com")
    resp = client.get("/api/v1/users")
    body = _check("GET", "/api/v1/users", resp)
    assert resp.status_code == 200
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 3


def test_list_filter_role(client):
    _create(client, email="a@example.com", role="organizer")
    _create(client, email="b@example.com", role="attendee")
    resp = client.get("/api/v1/users?role=organizer")
    body = _check("GET", "/api/v1/users?role=organizer", resp)
    assert body["total"] == 1
    assert body["items"][0]["role"] == "organizer"


def test_list_filter_email_case_insensitive(client):
    _create(client, email="findme@example.com")
    resp = client.get("/api/v1/users?email=FINDME@EXAMPLE.COM")
    body = _check("GET", "/api/v1/users?email=FINDME@EXAMPLE.COM", resp)
    assert body["total"] == 1


def test_list_total_before_pagination(client):
    for i in range(4):
        _create(client, email=f"p{i}@example.com", role="attendee")
    resp = client.get("/api/v1/users?page=1&page_size=2")
    body = _check("GET", "/api/v1/users?page=1&page_size=2", resp)
    assert body["total"] == 4
    assert len(body["items"]) == 2


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "page_size=0", "role=boss"])
def test_list_invalid_params_return_422(client, query):
    path = f"/api/v1/users?{query}"
    resp = client.get(path)
    body = _check("GET", path, resp)
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"
