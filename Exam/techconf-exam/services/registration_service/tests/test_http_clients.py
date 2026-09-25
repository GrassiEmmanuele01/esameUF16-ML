"""Unit test dei client HTTP verso user-service ed event-service (responses)."""

from __future__ import annotations

import pytest
import requests
import responses

from registration_service.domain.errors import DependencyUnavailable
from registration_service.infrastructure.events_http import HttpEventDirectory
from registration_service.infrastructure.users_http import HttpUserDirectory

_USER_BASE = "http://user-service.local"
_EVENT_BASE = "http://event-service.local"
_UID = "11111111-1111-4111-8111-111111111111"
_EID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_USER_URL = f"{_USER_BASE}/api/v1/users/{_UID}"
_EVENT_URL = f"{_EVENT_BASE}/api/v1/events/{_EID}"


# ------------------------------ UserDirectory ------------------------------ #
@responses.activate
def test_user_exists_true_on_200():
    responses.add(responses.GET, _USER_URL, json={"id": _UID, "role": "attendee"}, status=200)
    assert HttpUserDirectory(_USER_BASE).exists(_UID) is True


@responses.activate
def test_user_false_on_404():
    responses.add(responses.GET, _USER_URL, json={"error": {}}, status=404)
    assert HttpUserDirectory(_USER_BASE).exists(_UID) is False


@responses.activate
def test_user_5xx_raises():
    responses.add(responses.GET, _USER_URL, json={"error": {}}, status=500)
    with pytest.raises(DependencyUnavailable):
        HttpUserDirectory(_USER_BASE).exists(_UID)


@responses.activate
def test_user_connection_error_raises():
    responses.add(responses.GET, _USER_URL, body=requests.exceptions.ConnectionError("refused"))
    with pytest.raises(DependencyUnavailable):
        HttpUserDirectory(_USER_BASE).exists(_UID)


@responses.activate
def test_user_timeout_raises():
    # Timeout esplicito (2s) -> RequestException -> DependencyUnavailable.
    responses.add(responses.GET, _USER_URL, body=requests.exceptions.ConnectTimeout("timeout"))
    with pytest.raises(DependencyUnavailable):
        HttpUserDirectory(_USER_BASE).exists(_UID)


@responses.activate
def test_user_unexpected_status_raises():
    # Esiti diversi da 200/404 sono trattati come indisponibilità.
    responses.add(responses.GET, _USER_URL, json={"error": {}}, status=418)
    with pytest.raises(DependencyUnavailable):
        HttpUserDirectory(_USER_BASE).exists(_UID)


@responses.activate
def test_user_calls_expected_url():
    # REQ-REG-B01: verifica GET {USER_SERVICE_URL}/api/v1/users/{id}.
    responses.add(responses.GET, _USER_URL, json={"role": "attendee"}, status=200)
    HttpUserDirectory(_USER_BASE).exists(_UID)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.method == "GET"
    assert responses.calls[0].request.url == _USER_URL


@responses.activate
def test_user_uses_2s_timeout():
    responses.add(responses.GET, _USER_URL, json={"role": "attendee"}, status=200)
    HttpUserDirectory(_USER_BASE).exists(_UID)
    assert responses.calls[0].request.req_kwargs.get("timeout") == 2.0


# ------------------------------ EventDirectory ----------------------------- #
@responses.activate
def test_event_get_returns_event_info():
    responses.add(
        responses.GET,
        _EVENT_URL,
        json={"id": _EID, "status": "published", "capacity": 100, "price": 149.0},
        status=200,
    )
    info = HttpEventDirectory(_EVENT_BASE).get(_EID)
    assert info is not None
    # REQ-REG-B02/B03/B06: status, capacity e price estratti (e tipizzati) dal body.
    assert info.status == "published"
    assert info.capacity == 100 and isinstance(info.capacity, int)
    assert info.price == 149.0 and isinstance(info.price, float)


@responses.activate
def test_event_none_on_404():
    responses.add(responses.GET, _EVENT_URL, json={"error": {}}, status=404)
    assert HttpEventDirectory(_EVENT_BASE).get(_EID) is None


@responses.activate
def test_event_5xx_raises():
    responses.add(responses.GET, _EVENT_URL, json={"error": {}}, status=502)
    with pytest.raises(DependencyUnavailable):
        HttpEventDirectory(_EVENT_BASE).get(_EID)


@responses.activate
def test_event_timeout_raises():
    responses.add(responses.GET, _EVENT_URL, body=requests.exceptions.ConnectTimeout("timeout"))
    with pytest.raises(DependencyUnavailable):
        HttpEventDirectory(_EVENT_BASE).get(_EID)


@responses.activate
def test_event_connection_error_raises():
    responses.add(responses.GET, _EVENT_URL, body=requests.exceptions.ConnectionError("refused"))
    with pytest.raises(DependencyUnavailable):
        HttpEventDirectory(_EVENT_BASE).get(_EID)


@responses.activate
def test_event_calls_expected_url():
    # REQ-REG-B02: verifica GET {EVENT_SERVICE_URL}/api/v1/events/{id}.
    responses.add(
        responses.GET,
        _EVENT_URL,
        json={"status": "published", "capacity": 10, "price": 0},
        status=200,
    )
    HttpEventDirectory(_EVENT_BASE).get(_EID)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.method == "GET"
    assert responses.calls[0].request.url == _EVENT_URL


@responses.activate
def test_event_bad_body_raises():
    # Body senza i campi attesi -> trattato come indisponibilità.
    responses.add(responses.GET, _EVENT_URL, json={"unexpected": True}, status=200)
    with pytest.raises(DependencyUnavailable):
        HttpEventDirectory(_EVENT_BASE).get(_EID)


@responses.activate
def test_event_uses_2s_timeout():
    responses.add(
        responses.GET,
        _EVENT_URL,
        json={"status": "published", "capacity": 10, "price": 0},
        status=200,
    )
    HttpEventDirectory(_EVENT_BASE).get(_EID)
    assert responses.calls[0].request.req_kwargs.get("timeout") == 2.0
