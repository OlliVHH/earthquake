"""Shared API error types and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# Human: Raise this from handlers/services for predictable, user-safe HTTP error responses.
# Agent: HTTP status_code + error.code/message; CALLS to_response(); failure modes: uncaught AppError still handled by register_exception_handlers.
class AppError(Exception):
    """Application error with HTTP status and safe client message."""

    # Human: Attach machine-readable code, client message, and HTTP status for the handler.
    # Agent: WRITES self.code, self.message, self.status_code; failure modes: generic 400 if status_code omitted.
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    # Human: Serialize to the canonical `{ "error": { "code", "message" } }` envelope.
    # Agent: RETURNS JSONResponse; HTTP status from self.status_code; aligned with frontend getErrorMessage.
    def to_response(self) -> JSONResponse:
        """Serialize to canonical error JSON envelope."""
        return JSONResponse(
            status_code=self.status_code,
            content={"error": {"code": self.code, "message": self.message}},
        )


# Human: Register global handlers so all routes return consistent JSON on failure.
# Agent: WRITES app.exception_handler for AppError and Exception; CALLS logger.exception on 500; failure modes: stack traces never leak to clients.
def register_exception_handlers(app: FastAPI) -> None:
    """Wire AppError and unexpected exceptions to JSON responses."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )
