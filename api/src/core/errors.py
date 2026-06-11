"""Error payloads and exception handlers.

Two shapes are used, matching the OpenAPI spec:
* ``AuthError``  ({error, error_description, correlationId}) for /auth/* routes.
* ``Error``      ({code, error, message, correlationId, details}) elsewhere.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error rendered as the standard Error payload."""

    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        error: str | None = None,
        http_status: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error = error or self.error_code
        if http_status is not None:
            self.http_status = http_status
        self.details = details


class NotFoundError(AppError):
    http_status = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ForbiddenError(AppError):
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class ConflictError(AppError):
    http_status = status.HTTP_409_CONFLICT
    error_code = "conflict"


class NotImplementedYetError(AppError):
    """A scaffolded endpoint whose behaviour is delivered in a later step.

    Step 2 wires up every route, its validation and its persistence schema, but
    the e-invoice generation (step 3) and validation (step 4) are not built yet.
    Those routes raise this and surface a clear ``501`` rather than pretending
    to succeed.
    """

    http_status = status.HTTP_501_NOT_IMPLEMENTED
    error_code = "not_implemented"


class AuthError(Exception):
    """OAuth-style error rendered as the AuthError payload."""

    def __init__(
        self,
        error: str,
        *,
        description: str | None = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(description or error)
        self.error = error
        self.description = description
        self.http_status = http_status


def _correlation_id() -> str:
    return str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _auth_error( # pyright: ignore[reportUnusedFunction]
        _: Request,
        exc: AuthError
    ) -> JSONResponse:
        body = {"error": exc.error, "correlationId": _correlation_id()}
        if exc.description:
            body["error_description"] = exc.description
        return JSONResponse(status_code=exc.http_status, content=body)

    @app.exception_handler(AppError)
    async def _app_error( # pyright: ignore[reportUnusedFunction]
        _: Request,
        exc: AppError
    ) -> JSONResponse:
        body: dict[str, Any] = {
            "code": exc.http_status,
            "error": exc.error,
            "message": exc.message,
            "correlationId": _correlation_id(),
        }
        if exc.details:
            body["details"] = exc.details
        return JSONResponse(status_code=exc.http_status, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation_error( # pyright: ignore[reportUnusedFunction]
        _: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error": "validation_error",
                "message": "Request validation failed",
                "correlationId": _correlation_id(),
                "details": {"errors": exc.errors()},
            },
        )
