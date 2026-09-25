"""Blueprint Flask dello user-service.

Espone le rotte REST su ``/api/v1/users`` e l'health check su ``/health``.
Il blueprint non contiene logica di business: adatta HTTP ai casi d'uso di
:class:`UserService` e serializza le risposte secondo il contratto.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from common import MalformedJsonError, normalize_page_params

from ...config import SERVICE_NAME
from ...domain.service import UserService

_BASE = "/api/v1/users"


def _parse_json_body() -> Any:
    """Restituisce il body JSON o solleva :class:`MalformedJsonError` (400)."""
    if not request.data:
        raise MalformedJsonError("Body JSON mancante o vuoto")
    body = request.get_json(silent=True)
    if body is None:
        raise MalformedJsonError("Body JSON malformato")
    return body


def _user_response(user, status: int, *, location: str | None = None) -> Response:
    response = jsonify(user.to_dict())
    response.status_code = status
    if location is not None:
        response.headers["Location"] = location
    return response


def create_user_blueprint(service: UserService) -> Blueprint:
    """Crea il blueprint collegato al ``service`` iniettato."""
    bp = Blueprint("users", __name__)

    @bp.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok", "service": SERVICE_NAME})

    @bp.post(_BASE)
    def create_user() -> Response:
        body = _parse_json_body()
        user = service.create_user(body)
        location = f"{_BASE}/{user.id}"
        return _user_response(user, 201, location=location)

    @bp.get(_BASE)
    def list_users() -> Response:
        params = normalize_page_params(
            request.args.get("page"), request.args.get("page_size")
        )
        role = request.args.get("role")
        email = request.args.get("email")
        items, total = service.list_users(
            role=role, email=email, page=params.page, page_size=params.page_size
        )
        body = {
            "items": [u.to_dict() for u in items],
            "page": params.page,
            "page_size": params.page_size,
            "total": total,
        }
        return jsonify(body)

    @bp.get(f"{_BASE}/<user_id>")
    def get_user(user_id: str) -> Response:
        user = service.get_user(user_id)
        return _user_response(user, 200)

    @bp.put(f"{_BASE}/<user_id>")
    def replace_user(user_id: str) -> Response:
        body = _parse_json_body()
        user = service.replace_user(user_id, body)
        return _user_response(user, 200)

    @bp.patch(f"{_BASE}/<user_id>")
    def update_user(user_id: str) -> Response:
        body = _parse_json_body()
        user = service.update_user(user_id, body)
        return _user_response(user, 200)

    @bp.delete(f"{_BASE}/<user_id>")
    def delete_user(user_id: str) -> Response:
        service.delete_user(user_id)
        return Response(status=204)

    return bp
