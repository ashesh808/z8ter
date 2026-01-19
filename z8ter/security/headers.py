"""Security headers middleware for Z8ter.

This module adds essential security headers to all HTTP responses to protect
against common web vulnerabilities.

Headers added:
- X-Content-Type-Options: nosniff - Prevents MIME sniffing
- X-Frame-Options: DENY - Prevents clickjacking
- X-XSS-Protection: 1; mode=block - Legacy XSS filter (browser support varies)
- Referrer-Policy: strict-origin-when-cross-origin - Controls referrer leakage
- Strict-Transport-Security: max-age=... - HTTPS enforcement (optional)
- Content-Security-Policy: ... - XSS prevention (optional, customizable)

Security considerations:
- HSTS should only be enabled in production with proper HTTPS
- CSP requires careful tuning to avoid breaking legitimate functionality
- Test thoroughly after enabling strict policies
"""

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware.

    Adds security headers to all responses.

    Configuration:
        enable_hsts: Enable Strict-Transport-Security header (default: False)
        hsts_max_age: HSTS max-age in seconds (default: 31536000 = 1 year)
        hsts_include_subdomains: Include subdomains in HSTS (default: True)
        content_security_policy: Custom CSP policy string (default: None)
        x_frame_options: X-Frame-Options value (default: "DENY")
        referrer_policy: Referrer-Policy value (default: "strict-origin-when-cross-origin")

    Usage:
        # Basic security headers
        app.add_middleware(SecurityHeadersMiddleware)

        # With HSTS for production
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_hsts=True,
        )

        # With custom CSP
        app.add_middleware(
            SecurityHeadersMiddleware,
            content_security_policy="default-src 'self'; script-src 'self';",
        )
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = False,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        content_security_policy: str | None = None,
        x_frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: str | None = None,
    ) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.content_security_policy = content_security_policy
        self.x_frame_options = x_frame_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

        # Pre-compute static headers
        self._static_headers: dict[str, str] = {
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
        }

        if x_frame_options:
            self._static_headers["X-Frame-Options"] = x_frame_options

        if referrer_policy:
            self._static_headers["Referrer-Policy"] = referrer_policy

        if permissions_policy:
            self._static_headers["Permissions-Policy"] = permissions_policy

        if enable_hsts:
            hsts_value = f"max-age={hsts_max_age}"
            if hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            self._static_headers["Strict-Transport-Security"] = hsts_value

        if content_security_policy:
            self._static_headers["Content-Security-Policy"] = content_security_policy

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response = await call_next(request)

        # Add security headers
        for header, value in self._static_headers.items():
            response.headers[header] = value

        return response
