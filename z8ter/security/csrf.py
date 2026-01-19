"""CSRF protection middleware for Z8ter.

This module provides Cross-Site Request Forgery protection by:
1. Generating a unique CSRF token per session
2. Storing the token in a secure, HttpOnly cookie
3. Validating tokens on state-changing requests (POST, PUT, DELETE, PATCH)

The token is made available via request.state.csrf_token for template injection.

Security considerations:
- Token is stored in HttpOnly cookie with SameSite=Strict
- Token validation uses constant-time comparison
- Exempt paths can be configured for APIs using alternative auth (e.g., Bearer tokens)
"""

import hashlib
import hmac
import secrets
from typing import Callable, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Token settings
CSRF_COOKIE_NAME = "z8_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_TOKEN_LENGTH = 32


def _generate_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def _constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware.

    Validates CSRF tokens on state-changing HTTP methods (POST, PUT, DELETE, PATCH).
    The token can be provided either:
    - In the request body as 'csrf_token' field
    - In the X-CSRF-Token header

    Configuration:
        secret_key: Server-side secret for token signing
        exempt_paths: List of path prefixes to skip CSRF validation (e.g., /api/)
        cookie_secure: Whether to set Secure flag on cookie (default: True in prod)
        cookie_samesite: SameSite policy (default: "strict")

    Usage:
        app.add_middleware(
            CSRFMiddleware,
            secret_key="your-secret-key",
            exempt_paths=["/api/"],
        )
    """

    def __init__(
        self,
        app,
        secret_key: str,
        exempt_paths: Sequence[str] | None = None,
        cookie_secure: bool = True,
        cookie_samesite: str = "strict",
    ) -> None:
        super().__init__(app)
        self.secret_key = secret_key
        self.exempt_paths = list(exempt_paths or [])
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    def _sign_token(self, token: str) -> str:
        """Create HMAC signature for token verification."""
        return hmac.new(
            self.secret_key.encode(),
            token.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF validation."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Get or generate CSRF token
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)

        if csrf_cookie:
            # Verify existing token signature
            try:
                token, signature = csrf_cookie.rsplit(".", 1)
                if not _constant_time_compare(self._sign_token(token), signature):
                    csrf_cookie = None
            except ValueError:
                csrf_cookie = None

        if not csrf_cookie:
            # Generate new token with signature
            token = _generate_token()
            signature = self._sign_token(token)
            csrf_cookie = f"{token}.{signature}"

        # Extract the token (without signature) for request state
        csrf_token = csrf_cookie.rsplit(".", 1)[0]
        request.state.csrf_token = csrf_token

        # Validate on state-changing methods
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not self._is_exempt(request.url.path):
                # Get submitted token from form or header
                submitted_token = None

                # Check header first
                submitted_token = request.headers.get(CSRF_HEADER_NAME)

                # Check form field if not in header
                if not submitted_token:
                    content_type = request.headers.get("content-type", "")
                    if "application/x-www-form-urlencoded" in content_type:
                        try:
                            form = await request.form()
                            submitted_token = form.get(CSRF_FORM_FIELD)
                        except Exception:
                            pass
                    elif "multipart/form-data" in content_type:
                        try:
                            form = await request.form()
                            submitted_token = form.get(CSRF_FORM_FIELD)
                        except Exception:
                            pass

                # Validate token
                if not submitted_token or not _constant_time_compare(
                    csrf_token, str(submitted_token)
                ):
                    return JSONResponse(
                        {"ok": False, "error": {"message": "CSRF token validation failed"}},
                        status_code=403,
                    )

        # Process request
        response = await call_next(request)

        # Set CSRF cookie on response
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_cookie,
            httponly=True,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            max_age=60 * 60 * 24,  # 24 hours
            path="/",
        )

        return response
