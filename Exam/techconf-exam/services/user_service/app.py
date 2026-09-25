"""Composition root dello user-service.

Collega i layer concreti (configurazione, persistenza, casi d'uso, HTTP) e avvia
l'applicazione Flask. Il servizio ascolta sulla porta indicata da ``PORT``.

Avvio (dalla directory del servizio):

    python -m app
"""

from __future__ import annotations

import os
import sys

# Rende importabile packages/common quando il servizio è avviato standalone
# (es. `python -m app`) dalla propria working directory.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _extra in (os.path.join(_REPO_ROOT, "packages"), os.path.join(_REPO_ROOT, "services")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

from flask import Flask

try:  # Import assoluto quando eseguito come package (`python -m user_service.app`).
    from user_service.config import Config, load_config
    from user_service.entrypoints.http import (
        create_user_blueprint,
        register_error_handlers,
    )
    from user_service.domain.service import UserService
    from user_service.infrastructure.repositories import build_repository
except ImportError:  # Esecuzione come modulo top-level (`python -m app`).
    from config import Config, load_config  # type: ignore[no-redef]
    from entrypoints.http import (  # type: ignore[no-redef]
        create_user_blueprint,
        register_error_handlers,
    )
    from domain.service import UserService  # type: ignore[no-redef]
    from infrastructure.repositories import build_repository  # type: ignore[no-redef]


def create_app(config: Config | None = None) -> Flask:
    """Application factory: costruisce e configura l'app Flask."""
    config = config or load_config()

    repository = build_repository(config)
    service = UserService(repository)

    app = Flask(__name__)
    app.config["USER_SERVICE_CONFIG"] = config
    app.register_blueprint(create_user_blueprint(service))
    register_error_handlers(app)
    return app


def main() -> None:
    config = load_config()
    app = create_app(config)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
