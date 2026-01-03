"""Exception handling utilities for Z8ter.

Provides JSON-formatted error responses for HTTP and generic exceptions,
and a helper to register these handlers on the app.
"""

from typing import cast

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.types import ExceptionHandler, HTTPExceptionHandler

from z8ter.core import Z8ter
from z8ter.requests import Request
from z8ter.responses import JSONResponse


async def http_exc(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle Starlette HTTPException.

    Returns a structured JSON error response, preserving the exception's
    status code and detail message.

    Args:
        request: Incoming request that triggered the exception.
        exc: The raised HTTPException.

    Returns:
        JSONResponse: {"ok": False, "error": {"message": <exc.detail>}}

    """
    return JSONResponse(
        {"ok": False, "error": {"message": exc.detail}},
        status_code=exc.status_code,
    )


async def any_exc(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected exceptions.

    Always returns a generic 500 Internal Server Error response without
    leaking internal details.

    Args:
        request: Incoming request that triggered the exception.
        exc: The raised exception.

    Returns:
        JSONResponse: {"ok": False, "error": {"message": "Internal server error"}}

    """
    return JSONResponse(
        {"ok": False, "error": {"message": "Internal server error"}},
        status_code=500,
    )


def register_exception_handlers(app: Z8ter) -> None:
    """Attach default exception handlers to a Z8ter app.

    Registers:
        - HTTPException -> http_exc
        - Exception     -> any_exc

    Args:
        app: The Z8ter application (or its wrapped Starlette app).

    """
    target = cast(Starlette, getattr(app, "starlette_app", app))
    target.add_exception_handler(HTTPException, cast(HTTPExceptionHandler, http_exc))
    target.add_exception_handler(Exception, cast(ExceptionHandler, any_exc))
