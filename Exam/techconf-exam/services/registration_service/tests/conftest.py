"""Configurazione condivisa per gli unit test del registration-service.

Rende importabili ``packages/common``, ``services/`` e ``contracts/`` e fornisce
doppi in memoria delle porte ``UserDirectory`` ed ``EventDirectory``.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _sub in ("packages", "services", "contracts"):
    _path = os.path.join(_REPO_ROOT, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


from registration_service.domain.directories import (  # noqa: E402
    EventDirectory,
    EventInfo,
    UserDirectory,
)
from registration_service.domain.errors import DependencyUnavailable  # noqa: E402


class FakeUserDirectory(UserDirectory):
    """Doppio in memoria di UserDirectory.

    - ``known``: insieme di user_id esistenti.
    - ``unavailable=True``: simula lo user-service irraggiungibile.
    """

    def __init__(self, known=None, *, unavailable: bool = False) -> None:
        self.known = set(known or ())
        self.unavailable = unavailable

    def exists(self, user_id: str) -> bool:
        if self.unavailable:
            raise DependencyUnavailable("user-service")
        return user_id in self.known


class FakeEventDirectory(EventDirectory):
    """Doppio in memoria di EventDirectory.

    - ``events``: mappa event_id -> EventInfo.
    - ``unavailable=True``: simula l'event-service irraggiungibile.
    """

    def __init__(self, events=None, *, unavailable: bool = False) -> None:
        self.events = dict(events or {})
        self.unavailable = unavailable

    def get(self, event_id: str) -> EventInfo | None:
        if self.unavailable:
            raise DependencyUnavailable("event-service")
        return self.events.get(event_id)
