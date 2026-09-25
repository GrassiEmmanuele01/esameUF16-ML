"""Client HTTP verso lo user-service (implementazione della porta UserDirectory).

Traduce gli esiti della chiamata HTTP nelle semantiche di dominio:
  * ``200`` -> ruolo dell'utente (dal body).
  * ``404`` -> ``None`` (l'utente non esiste; il chiamante lo tradurrà in
    ``REFERENCE_NOT_FOUND`` / 422).
  * connessione rifiutata, timeout (2s) o risposta ``5xx`` -> ``DependencyUnavailable``
    (503), coerente con REQ-EVT-B05.
"""

from __future__ import annotations

import requests

from ..domain.errors import DependencyUnavailable
from ..domain.users import UserDirectory

# Timeout esplicito di 2 secondi su tutte le chiamate (standard di piattaforma).
_TIMEOUT_SECONDS = 2.0


class HttpUserDirectory(UserDirectory):
    """Implementazione di :class:`UserDirectory` basata su ``requests``.

    Storicamente indicata come *UserServiceHTTPClient*: interroga lo
    user-service per recuperare il ruolo di un utente.
    """

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_role(self, user_id: str) -> str | None:
        url = f"{self._base_url}/api/v1/users/{user_id}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            # Connessione rifiutata / timeout / errore di rete -> 503.
            raise DependencyUnavailable("user-service") from exc

        if resp.status_code == 404:
            return None
        if resp.status_code >= 500:
            # Errore server della dipendenza -> 503.
            raise DependencyUnavailable("user-service")
        if resp.status_code != 200:
            # Qualsiasi altro esito inatteso è trattato come indisponibilità.
            raise DependencyUnavailable("user-service")

        try:
            body = resp.json()
        except ValueError as exc:
            raise DependencyUnavailable("user-service") from exc

        return body.get("role")
