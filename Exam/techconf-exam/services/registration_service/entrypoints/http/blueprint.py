"""Blueprint Flask del registration-service.

Rotte REST su ``/api/v1/registrations`` (incluso ``/stats``) e ``/health``.
``PUT`` sul singolo elemento non è consentito (405). La rotta ``/stats`` è
registrata prima di ``/<id>`` per non essere interpretata come un id.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, abort, jsonify, request

from common import MalformedJsonError, normalize_page_params

from ...config import SERVICE_NAME
from ...domain.service import RegistrationService

_BASE = "/api/v1/registrations"


def _parse_json_body() -> Any:
    if not request.data:
        raise MalformedJsonError("Body JSON mancante o vuoto")
    body = request.get_json(silent=True)
    if body is None:
        raise MalformedJsonError("Body JSON malformato")
    return body


def _registration_response(reg, status: int, *, location: str | None = None) -> Response:
    response = jsonify(reg.to_dict())
    response.status_code = status
    if location is not None:
        response.headers["Location"] = location
    return response


def create_registration_blueprint(service: RegistrationService) -> Blueprint:
    """Crea il blueprint collegato al ``service`` iniettato."""
    bp = Blueprint("registrations", __name__)

    @bp.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok", "service": SERVICE_NAME})

    @bp.post(_BASE)
    def create_registration() -> Response:
        body = _parse_json_body()
        reg = service.create_registration(body)
        return _registration_response(reg, 201, location=f"{_BASE}/{reg.id}")

    @bp.get(_BASE)
    def list_registrations() -> Response:
        params = normalize_page_params(
            request.args.get("page"), request.args.get("page_size")
        )
        items, total = service.list_registrations(
            user_id=request.args.get("user_id"),
            event_id=request.args.get("event_id"),
            status=request.args.get("status"),
            page=params.page,
            page_size=params.page_size,
        )
        return jsonify(
            {
                "items": [r.to_dict() for r in items],
                "page": params.page,
                "page_size": params.page_size,
                "total": total,
            }
        )

    # Registrata prima di /<id> per priorità di matching.
    @bp.get(f"{_BASE}/stats")
    def registration_stats() -> Response:
        stats = service.stats(request.args.get("event_id"))
        return jsonify(stats)

    @bp.get(f"{_BASE}/<registration_id>")
    def get_registration(registration_id: str) -> Response:
        return _registration_response(service.get_registration(registration_id), 200)

    @bp.patch(f"{_BASE}/<registration_id>")
    def update_registration(registration_id: str) -> Response:
        body = _parse_json_body()
        return _registration_response(service.update_status(registration_id, body), 200)

    @bp.put(f"{_BASE}/<registration_id>")
    def put_not_allowed(registration_id: str) -> Response:
        # REQ 5: PUT non consentito.
        abort(405)

    @bp.delete(f"{_BASE}/<registration_id>")
    def delete_registration(registration_id: str) -> Response:
        service.delete_registration(registration_id)
        return Response(status=204)

    return bp
