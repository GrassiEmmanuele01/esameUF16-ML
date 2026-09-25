"""Configurazione condivisa per gli unit test dell'event-service.

Rende importabili ``packages/common``, ``services/`` e ``contracts/`` e fornisce
un doppio in memoria della porta :class:`UserDirectory`.
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _sub in ("packages", "services", "contracts"):
    _path = os.path.join(_REPO_ROOT, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
# Consente `from conftest import ...` nei moduli di test.
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


from event_service.domain.errors import DependencyUnavailable  # noqa: E402
from event_service.domain.users import UserDirectory  # noqa: E402


class FakeUserDirectory(UserDirectory):
    """Doppio in memoria della porta UserDirectory per i test di dominio.

    - ``roles``: mappa user_id -> ruolo (utente esistente).
    - ``unavailable=True``: simula lo user-service irraggiungibile (REQ-EVT-B05).
    """

    def __init__(self, roles: dict[str, str] | None = None, *, unavailable: bool = False) -> None:
        self.roles = dict(roles or {})
        self.unavailable = unavailable
        self.calls: list[str] = []

    def get_role(self, user_id: str) -> str | None:
        self.calls.append(user_id)
        if self.unavailable:
            raise DependencyUnavailable("user-service")
        return self.roles.get(user_id)


@pytest.fixture
def organizer_id() -> str:
    return "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def fake_users(organizer_id):
    """UserDirectory con un organizzatore valido preconfigurato."""
    return FakeUserDirectory({organizer_id: "organizer"})
