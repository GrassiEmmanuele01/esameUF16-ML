"""Composition root del registration-service.

Collega configurazione, persistenza, client verso user/event-service, casi d'uso
e HTTP, e avvia Flask sulla porta ``PORT``.

Avvio (dalla directory del servizio):

    python -m app
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _extra in (os.path.join(_REPO_ROOT, "packages"), os.path.join(_REPO_ROOT, "services")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

from flask import Flask

try:  # Import assoluto quando eseguito come package.
    from registration_service.config import Config, load_config
    from registration_service.domain.service import RegistrationService
    from registration_service.entrypoints.http import (
        create_registration_blueprint,
        register_error_handlers,
    )
    from registration_service.infrastructure.events_http import HttpEventDirectory
    from registration_service.infrastructure.repositories import build_repository
    from registration_service.infrastructure.users_http import HttpUserDirectory
except ImportError:  # Esecuzione come modulo top-level (`python -m app`).
    from config import Config, load_config  # type: ignore[no-redef]
    from domain.service import RegistrationService  # type: ignore[no-redef]
    from entrypoints.http import (  # type: ignore[no-redef]
        create_registration_blueprint,
        register_error_handlers,
    )
    from infrastructure.events_http import HttpEventDirectory  # type: ignore[no-redef]
    from infrastructure.repositories import build_repository  # type: ignore[no-redef]
    from infrastructure.users_http import HttpUserDirectory  # type: ignore[no-redef]


def create_app(config: Config | None = None) -> Flask:
    """Application factory: costruisce e configura l'app Flask."""
    config = config or load_config()

    repository = build_repository(config)
    users = HttpUserDirectory(config.user_service_url)
    events = HttpEventDirectory(config.event_service_url)
    service = RegistrationService(repository, users, events)

    app = Flask(__name__)
    app.config["REGISTRATION_SERVICE_CONFIG"] = config
    app.register_blueprint(create_registration_blueprint(service))
    register_error_handlers(app)
    return app


def main() -> None:
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
