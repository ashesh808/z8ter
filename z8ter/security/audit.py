"""Security event audit logging for Z8ter.

This module provides standardized security event logging for:
- Authentication events (login success/failure)
- Session management events
- Access control events
- Security policy violations

Security considerations:
- Log security events to enable detection and forensics
- Be careful not to log sensitive data (passwords, tokens)
- Use structured logging for easy parsing and analysis
- Consider log rotation and retention policies
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Security logger - configure handler in application
security_logger = logging.getLogger("z8ter.security")


class SecurityEvent(Enum):
    """Security event types for audit logging."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"

    # Session events
    SESSION_CREATED = "session_created"
    SESSION_REVOKED = "session_revoked"
    SESSION_EXPIRED = "session_expired"

    # Account events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_LOCKED = "account_locked"
    PASSWORD_CHANGED = "password_changed"

    # Security violations
    CSRF_VIOLATION = "csrf_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_REDIRECT = "invalid_redirect"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


def log_security_event(
    event: SecurityEvent,
    *,
    user_id: str | None = None,
    email: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    path: str | None = None,
    success: bool = True,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a security event.

    Creates a structured log entry for security-relevant events.
    Use this for authentication, authorization, and security policy events.

    Args:
        event: The type of security event
        user_id: User identifier (if known)
        email: User email (if applicable, for login attempts)
        ip_address: Client IP address
        user_agent: Client user agent string
        path: Request path (if applicable)
        success: Whether the event represents a successful action
        details: Additional event-specific details

    Examples:
        # Successful login
        log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id="u_123",
            email="user@example.com",
            ip_address="192.168.1.1",
        )

        # Failed login
        log_security_event(
            SecurityEvent.LOGIN_FAILURE,
            email="unknown@example.com",
            ip_address="192.168.1.1",
            success=False,
            details={"reason": "invalid_password"},
        )

    Security notes:
        - Never log passwords, tokens, or other secrets
        - Be mindful of PII in logs (GDPR, etc.)
        - Consider log aggregation and SIEM integration
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    log_data: dict[str, Any] = {
        "timestamp": timestamp,
        "event": event.value,
        "success": success,
    }

    if user_id:
        log_data["user_id"] = user_id
    if email:
        # Optionally mask email for privacy
        log_data["email"] = email
    if ip_address:
        log_data["ip_address"] = ip_address
    if user_agent:
        log_data["user_agent"] = user_agent
    if path:
        log_data["path"] = path
    if details:
        log_data["details"] = details

    # Format as structured log message
    message_parts = [f"event={event.value}"]
    if user_id:
        message_parts.append(f"user_id={user_id}")
    if email:
        message_parts.append(f"email={email}")
    if ip_address:
        message_parts.append(f"ip={ip_address}")
    if path:
        message_parts.append(f"path={path}")
    if not success:
        message_parts.append("success=false")
    if details:
        for key, value in details.items():
            message_parts.append(f"{key}={value}")

    message = " ".join(message_parts)

    # Log level based on event type and success
    if not success or event in (
        SecurityEvent.CSRF_VIOLATION,
        SecurityEvent.RATE_LIMIT_EXCEEDED,
        SecurityEvent.UNAUTHORIZED_ACCESS,
        SecurityEvent.ACCOUNT_LOCKED,
    ):
        security_logger.warning(message, extra={"security_data": log_data})
    elif event == SecurityEvent.LOGIN_FAILURE:
        security_logger.warning(message, extra={"security_data": log_data})
    else:
        security_logger.info(message, extra={"security_data": log_data})
