"""Mapping degli errori verso le risposte HTTP (struttura d'errore uniforme)."""

from __future__ import annotations

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

from common import AppError, MalformedJsonError, NotFoundError


def _error_response(code: str, message: str, status: int, details=None) -> Response:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    response = jsonify(body)
    response.status_code = status
    return response


def register_error_handlers(app: Flask) -> None:
    """Registra gli handler d'errore sull'app Flask."""

    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError) -> Response:
        return _error_response(exc.code, exc.message, exc.http_status, exc.details)

    @app.errorhandler(400)
    def _handle_bad_request(exc: HTTPException) -> Response:
        err = MalformedJsonError("Body JSON malformato")
        return _error_response(err.code, err.message, err.http_status)

    @app.errorhandler(404)
    def _handle_not_found(exc: HTTPException) -> Response:
        return _error_response(
            "RESOURCE_NOT_FOUND", "Risorsa non trovata", NotFoundError.http_status
        )

    @app.errorhandler(405)
    def _handle_method_not_allowed(exc: HTTPException) -> Response:
        return _error_response("METHOD_NOT_ALLOWED", "Metodo non consentito", 405)

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception) -> Response:
        if isinstance(exc, HTTPException):
            return exc  # type: ignore[return-value]
        return _error_response("INTERNAL_ERROR", "Errore interno del server", 500)
