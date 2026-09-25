"""Client HTTP verso lo user-service (implementazione della porta UserDirectory).

Traduce gli esiti della chiamata HTTP nelle semantiche di dominio (REQ-REG-B01):
  * ``200`` -> ``True`` (l'utente esiste).
  * ``404`` -> ``False`` (l'utente non esiste; il chiamante lo tradurrà in
    ``REFERENCE_NOT_FOUND`` / 422).
  * connessione rifiutata, timeout (2s) o risposta ``5xx`` -> ``DependencyUnavailable``
    (503), coerente con Requirement 14.
"""

from __future__ import annotations

import requests

from ..domain.directories import UserDirectory
from ..domain.errors import DependencyUnavailable

# Timeout esplicito di 2 secondi su tutte le chiamate (standard di piattaforma).
_TIMEOUT_SECONDS = 2.0

_DEPENDENCY = "user-service"


class HttpUserDirectory(UserDirectory):
    """Implementazione di :class:`UserDirectory` basata su ``requests``.

    Interroga lo user-service per verificare l'esistenza di un utente.
    """

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def exists(self, user_id: str) -> bool:
        url = f"{self._base_url}/api/v1/users/{user_id}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            # Connessione rifiutata / timeout / errore di rete -> 503.
            raise DependencyUnavailable(_DEPENDENCY) from exc

        if resp.status_code == 404:
            return False
        if resp.status_code == 200:
            return True
        # 5xx o qualsiasi altro esito inatteso è trattato come indisponibilità.
        raise DependencyUnavailable(_DEPENDENCY)
