"""Z8ter security utilities.

This package provides security middleware and utilities for Z8ter applications:
- CSRF protection middleware
- Safe redirect URL validation
- Rate limiting middleware
- Security headers middleware
- Input validators
- Security event audit logging

Usage:
    from z8ter.security import (
        CSRFMiddleware,
        is_safe_redirect_url,
        get_safe_redirect_url,
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
        validate_email,
        validate_password,
        SecurityEvent,
        log_security_event,
    )
"""

from z8ter.security.audit import SecurityEvent, log_security_event
from z8ter.security.csrf import CSRFMiddleware
from z8ter.security.headers import SecurityHeadersMiddleware
from z8ter.security.rate_limit import RateLimitMiddleware
from z8ter.security.redirect import get_safe_redirect_url, is_safe_redirect_url
from z8ter.security.validators import validate_email, validate_password

__all__ = [
    "CSRFMiddleware",
    "is_safe_redirect_url",
    "get_safe_redirect_url",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "validate_email",
    "validate_password",
    "SecurityEvent",
    "log_security_event",
]
