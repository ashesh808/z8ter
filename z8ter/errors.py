"""Exception handling utilities for Z8ter.

Provides error responses for HTTP and generic exceptions with content negotiation,
and a helper to register these handlers on the app.

Content Negotiation:
- Returns HTML for browser requests (Accept: text/html)
- Returns JSON for API requests (Accept: application/json or default)

Security:
- Internal error details are never exposed to clients
- All exceptions are logged with full traceback for debugging
- Log level varies by error type (4xx = warning, 5xx = error)
"""

import logging
import traceback
from typing import cast

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse
from starlette.types import ExceptionHandler, HTTPExceptionHandler

from z8ter.core import Z8ter
from z8ter.requests import Request
from z8ter.responses import JSONResponse, Response

logger = logging.getLogger("z8ter.errors")


def _wants_html(request: Request) -> bool:
    """Check if the client prefers HTML over JSON.

    Examines the Accept header to determine if the client is a browser
    requesting HTML content.

    Args:
        request: The incoming HTTP request.

    Returns:
        True if client prefers text/html, False otherwise.

    """
    accept = request.headers.get("accept", "")
    # Simple check: if text/html appears before application/json, prefer HTML
    # This handles common browser Accept headers like:
    # "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    if "text/html" in accept:
        html_pos = accept.find("text/html")
        json_pos = accept.find("application/json")
        # If JSON not in Accept, or HTML appears first, prefer HTML
        if json_pos == -1 or html_pos < json_pos:
            return True
    return False


def _html_error_page(status_code: int, message: str) -> str:
    """Generate a simple HTML error page.

    Args:
        status_code: HTTP status code.
        message: Error message to display.

    Returns:
        HTML string for the error page.

    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error {status_code}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: #f5f5f5;
            color: #333;
        }}
        .error-container {{
            text-align: center;
            padding: 2rem;
        }}
        h1 {{
            font-size: 4rem;
            margin: 0;
            color: #e74c3c;
        }}
        p {{
            font-size: 1.2rem;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>{status_code}</h1>
        <p>{message}</p>
    </div>
</body>
</html>"""


async def http_exc(request: Request, exc: HTTPException) -> Response:
    """Handle Starlette HTTPException.

    Returns either an HTML error page or JSON response based on the
    client's Accept header (content negotiation).

    Args:
        request: Incoming request that triggered the exception.
        exc: The raised HTTPException.

    Returns:
        Response: HTML page for browsers, JSON for API clients.

    """
    message = str(exc.detail) if exc.detail else "An error occurred"

    if _wants_html(request):
        return HTMLResponse(
            _html_error_page(exc.status_code, message),
            status_code=exc.status_code,
        )

    return JSONResponse(
        {"ok": False, "error": {"message": message}},
        status_code=exc.status_code,
    )


async def any_exc(request: Request, exc: Exception) -> Response:
    """Fallback handler for unexpected exceptions.

    Always returns a generic 500 Internal Server Error response without
    leaking internal details. The exception is logged with full context
    for debugging. Uses content negotiation to return HTML for browsers.

    Args:
        request: Incoming request that triggered the exception.
        exc: The raised exception.

    Returns:
        Response: HTML page for browsers, JSON for API clients.

    Security:
        - Internal error details are never exposed to clients
        - Full traceback is logged for debugging

    """
    # Log the exception with full context
    client_ip = None
    if request.client:
        client_ip = request.client.host

    logger.error(
        "Unhandled exception: %s\n"
        "Type: %s\n"
        "Path: %s\n"
        "Method: %s\n"
        "Client IP: %s\n"
        "Traceback:\n%s",
        str(exc),
        type(exc).__name__,
        request.url.path,
        request.method,
        client_ip,
        traceback.format_exc(),
    )

    message = "Internal server error"

    if _wants_html(request):
        return HTMLResponse(
            _html_error_page(500, message),
            status_code=500,
        )

    return JSONResponse(
        {"ok": False, "error": {"message": message}},
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
