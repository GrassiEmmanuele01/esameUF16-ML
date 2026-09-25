"""Blueprint Flask dell'event-service.

Espone le rotte REST su ``/api/v1/events`` e l'health check su ``/health``.
Adatta HTTP ai casi d'uso di :class:`EventService`.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from common import MalformedJsonError, normalize_page_params

from ...config import SERVICE_NAME
from ...domain.service import EventService

_BASE = "/api/v1/events"


def _parse_json_body() -> Any:
    if not request.data:
        raise MalformedJsonError("Body JSON mancante o vuoto")
    body = request.get_json(silent=True)
    if body is None:
        raise MalformedJsonError("Body JSON malformato")
    return body


def _event_response(event, status: int, *, location: str | None = None) -> Response:
    response = jsonify(event.to_dict())
    response.status_code = status
    if location is not None:
        response.headers["Location"] = location
    return response


def create_event_blueprint(service: EventService) -> Blueprint:
    """Crea il blueprint collegato al ``service`` iniettato."""
    bp = Blueprint("events", __name__)

    @bp.get("/health")
    def health() -> Response:
        # REQ 11: non dipende dalla raggiungibilità dello user-service.
        return jsonify({"status": "ok", "service": SERVICE_NAME})

    @bp.post(_BASE)
    def create_event() -> Response:
        body = _parse_json_body()
        event = service.create_event(body)
        return _event_response(event, 201, location=f"{_BASE}/{event.id}")

    @bp.get(_BASE)
    def list_events() -> Response:
        params = normalize_page_params(
            request.args.get("page"), request.args.get("page_size")
        )
        status = request.args.get("status")
        city = request.args.get("city")
        items, total = service.list_events(
            status=status, city=city, page=params.page, page_size=params.page_size
        )
        return jsonify(
            {
                "items": [e.to_dict() for e in items],
                "page": params.page,
                "page_size": params.page_size,
                "total": total,
            }
        )

    @bp.get(f"{_BASE}/<event_id>")
    def get_event(event_id: str) -> Response:
        return _event_response(service.get_event(event_id), 200)

    @bp.put(f"{_BASE}/<event_id>")
    def replace_event(event_id: str) -> Response:
        body = _parse_json_body()
        return _event_response(service.replace_event(event_id, body), 200)

    @bp.patch(f"{_BASE}/<event_id>")
    def update_event(event_id: str) -> Response:
        body = _parse_json_body()
        return _event_response(service.update_event(event_id, body), 200)

    @bp.delete(f"{_BASE}/<event_id>")
    def delete_event(event_id: str) -> Response:
        service.delete_event(event_id)
        return Response(status=204)

    return bp
