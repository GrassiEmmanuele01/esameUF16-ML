"""Client HTTP verso l'event-service (implementazione della porta EventDirectory).

Traduce gli esiti della chiamata HTTP nelle semantiche di dominio
(REQ-REG-B02/B03/B06):
  * ``200`` -> :class:`EventInfo` (``status``, ``capacity``, ``price``) dal body.
  * ``404`` -> ``None`` (l'evento non esiste; il chiamante lo tradurrà in
    ``REFERENCE_NOT_FOUND`` / 422 oppure ``NOT_FOUND`` per ``/stats``).
  * connessione rifiutata, timeout (2s) o risposta ``5xx`` -> ``DependencyUnavailable``
    (503), coerente con Requirement 14.
"""

from __future__ import annotations

import requests

from ..domain.directories import EventDirectory, EventInfo
from ..domain.errors import DependencyUnavailable

# Timeout esplicito di 2 secondi su tutte le chiamate (standard di piattaforma).
_TIMEOUT_SECONDS = 2.0

_DEPENDENCY = "event-service"


class HttpEventDirectory(EventDirectory):
    """Implementazione di :class:`EventDirectory` basata su ``requests``.

    Interroga l'event-service per recuperare le informazioni di un evento
    necessarie alle regole di business (stato, capienza, prezzo).
    """

    def __init__(self, base_url: str, *, timeout: float = _TIMEOUT_SECONDS) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get(self, event_id: str) -> EventInfo | None:
        url = f"{self._base_url}/api/v1/events/{event_id}"
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            # Connessione rifiutata / timeout / errore di rete -> 503.
            raise DependencyUnavailable(_DEPENDENCY) from exc

        if resp.status_code == 404:
            return None
        if resp.status_code >= 500:
            raise DependencyUnavailable(_DEPENDENCY)
        if resp.status_code != 200:
            # Qualsiasi altro esito inatteso è trattato come indisponibilità.
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
            # Body 200 privo dei campi attesi -> dipendenza non affidabile.
            raise DependencyUnavailable(_DEPENDENCY) from exc
