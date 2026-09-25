"""Client HTTP verso lo user-service (implementazione di UserDirectory).

- ``200`` -> True (utente esistente).
- ``404`` -> False (utente inesistente; il chiamante lo tradurrà in 422).
- connessione/timeout (2s) o ``5xx`` -> ``DependencyUnavailable`` (503).
"""

from __future__ import annotations

import requests

from ..domain.directories import UserDirectory
from ..domain.errors import DependencyUnavailable

_TIMEOUT_SECONDS = 2.0
_DEPENDENCY = "user-service"


class HttpUserDirectory(UserDirectory):
    """Implementazione di :class:`UserDirectory` basata su ``requests``."""

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def exists(self, user_id: str) -> bool:
        url = f"{self._base_url}/api/v1/users/{user_id}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            raise DependencyUnavailable(_DEPENDENCY) from exc

        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        raise DependencyUnavailable(_DEPENDENCY)
