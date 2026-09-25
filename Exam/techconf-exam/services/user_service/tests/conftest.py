"""Configurazione condivisa per gli unit test dello user-service.

Rende importabili i package del repository (``packages/common``, ``services/`` e
``contracts/``) aggiungendoli a ``sys.path``.
"""

from __future__ import annotations

import os
import sys

# --------------------------------------------------------------------------- #
# Import path: repo_root/packages, repo_root/services, repo_root/contracts
# --------------------------------------------------------------------------- #
_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _sub in ("packages", "services", "contracts"):
    _path = os.path.join(_REPO_ROOT, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
