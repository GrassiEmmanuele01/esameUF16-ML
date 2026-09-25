"""Client HTTP verso l'event-service (implementazione di EventDirectory).

- ``200`` -> ``EventInfo(status, capacity, price)`` dal body.
- ``404`` -> ``None`` (evento inesistente).
- connessione/timeout (2s) o ``5xx`` -> ``DependencyUnavailable`` (503).
"""

from __future__ import annotations

import requests

from ..domain.directories import EventDirectory, EventInfo
from ..domain.errors import DependencyUnavailable

_TIMEOUT_SECONDS = 2.0
_DEPENDENCY = "event-service"


class HttpEventDirectory(EventDirectory):
    """Implementazione di :class:`EventDirectory` basata su ``requests``."""

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get(self, event_id: str) -> EventInfo | None:
        url = f"{self._base_url}/api/v1/events/{event_id}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            raise DependencyUnavailable(_DEPENDENCY) from exc

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise DependencyUnavailable(_DEPENDENCY)

        try:
            body = resp.json()
        except ValueError as exc:
            raise DependencyUnavailable(_DEPENDENCY) from exc

        try:
            return EventInfo(
                status=body["status"],
                capacity=int(body["capacity"]),
                price=float(body["price"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            # Body inatteso dalla dipendenza -> trattato come indisponibilità.
            raise DependencyUnavailable(_DEPENDENCY) from exc
