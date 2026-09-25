"""Composition root dell'event-service.

Collega configurazione, persistenza, client verso lo user-service, casi d'uso e
HTTP, e avvia Flask sulla porta ``PORT``.

Avvio (dalla directory del servizio):

    python -m app
"""

from __future__ import annotations

import os
import sys

# Rende importabile packages/common e services/ quando avviato standalone.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _extra in (os.path.join(_REPO_ROOT, "packages"), os.path.join(_REPO_ROOT, "services")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

from flask import Flask

try:  # Import assoluto quando eseguito come package.
    from event_service.config import Config, load_config
    from event_service.domain.service import EventService
    from event_service.entrypoints.http import (
        create_event_blueprint,
        register_error_handlers,
    )
    from event_service.infrastructure.repositories import build_repository
    from event_service.infrastructure.users_http import HttpUserDirectory
except ImportError:  # Esecuzione come modulo top-level (`python -m app`).
    from config import Config, load_config  # type: ignore[no-redef]
    from domain.service import EventService  # type: ignore[no-redef]
    from entrypoints.http import (  # type: ignore[no-redef]
        create_event_blueprint,
        register_error_handlers,
    )
    from infrastructure.repositories import build_repository  # type: ignore[no-redef]
    from infrastructure.users_http import HttpUserDirectory  # type: ignore[no-redef]


def create_app(config: Config | None = None) -> Flask:
    """Application factory: costruisce e configura l'app Flask."""
    config = config or load_config()

    repository = build_repository(config)
    users = HttpUserDirectory(config.user_service_url)
    service = EventService(repository, users)

    app = Flask(__name__)
    app.config["EVENT_SERVICE_CONFIG"] = config
    app.register_blueprint(create_event_blueprint(service))
    register_error_handlers(app)
    return app


def main() -> None:
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
