"""Unit test di HttpUserDirectory con le chiamate ``requests`` mockate.

Usa la libreria ``responses`` per simulare gli esiti dello user-service e
verificare la traduzione degli errori (404 -> None, connessione/5xx -> 503) e
il timeout esplicito di 2 secondi.
"""

from __future__ import annotations

import pytest
import responses

from event_service.domain.errors import DependencyUnavailable
from event_service.infrastructure.users_http import HttpUserDirectory

_BASE = "http://user-service.local"
_UID = "11111111-1111-4111-8111-111111111111"
_URL = f"{_BASE}/api/v1/users/{_UID}"


def _directory() -> HttpUserDirectory:
    return HttpUserDirectory(_BASE)


@responses.activate
def test_returns_role_on_200():
    responses.add(
        responses.GET,
        _URL,
        json={"id": _UID, "role": "organizer"},
        status=200,
    )
    assert _directory().get_role(_UID) == "organizer"


@responses.activate
def test_returns_none_on_404():
    # 404 -> None (il chiamante lo tradurrà in 422 REFERENCE_NOT_FOUND).
    responses.add(responses.GET, _URL, json={"error": {"code": "USER_NOT_FOUND"}}, status=404)
    assert _directory().get_role(_UID) is None


@responses.activate
def test_5xx_raises_dependency_unavailable():
    responses.add(responses.GET, _URL, json={"error": {}}, status=503)
    with pytest.raises(DependencyUnavailable):
        _directory().get_role(_UID)


@responses.activate
def test_connection_error_raises_dependency_unavailable():
    # Errore di connessione realistico (sottoclasse di RequestException).
    import requests

    responses.add(
        responses.GET,
        _URL,
        body=requests.exceptions.ConnectionError("connection refused"),
    )
    with pytest.raises(DependencyUnavailable):
        _directory().get_role(_UID)


@responses.activate
def test_timeout_raises_dependency_unavailable():
    import requests

    responses.add(
        responses.GET,
        _URL,
        body=requests.exceptions.ConnectTimeout("timed out"),
    )
    with pytest.raises(DependencyUnavailable):
        _directory().get_role(_UID)


@responses.activate
def test_uses_explicit_2s_timeout():
    responses.add(responses.GET, _URL, json={"role": "organizer"}, status=200)
    _directory().get_role(_UID)
    # Verifica che la chiamata sia stata effettuata con timeout=2s.
    assert len(responses.calls) == 1
    assert responses.calls[0].request.req_kwargs.get("timeout") == 2.0


@responses.activate
def test_calls_expected_user_service_url():
    # REQ-EVT-B01: la verifica interroga GET {BASE}/api/v1/users/{organizer_id}.
    responses.add(responses.GET, _URL, json={"role": "organizer"}, status=200)
    _directory().get_role(_UID)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == _URL


@responses.activate
def test_unexpected_status_raises_dependency_unavailable():
    # Esiti diversi da 200/404 (es. 4xx inatteso) sono trattati come indisponibilità.
    responses.add(responses.GET, _URL, json={"error": {}}, status=418)
    with pytest.raises(DependencyUnavailable):
        _directory().get_role(_UID)
