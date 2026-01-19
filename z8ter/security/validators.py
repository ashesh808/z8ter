"""Input validation utilities for Z8ter.

This module provides validation functions for common input types:
- Email addresses
- Passwords (with configurable policies)

Security considerations:
- Input validation is the first line of defense against injection attacks
- Always validate on the server side, even if client-side validation exists
- Use specific error messages to help legitimate users while not revealing system details
"""

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        valid: Whether the input passed validation
        error: Error message if validation failed (None if valid)
    """

    valid: bool
    error: str | None = None


# Email regex - covers most common cases without being overly strict
# Based on HTML5 spec for email validation
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def validate_email(
    email: str,
    max_length: int = 254,
) -> ValidationResult:
    """Validate an email address.

    Checks:
    - Non-empty
    - Valid format (RFC 5322 simplified)
    - Maximum length (default: 254 per RFC 5321)

    Args:
        email: Email address to validate
        max_length: Maximum allowed length (default: 254)

    Returns:
        ValidationResult with valid=True if email is valid, or error message.

    Examples:
        >>> validate_email("user@example.com")
        ValidationResult(valid=True, error=None)
        >>> validate_email("")
        ValidationResult(valid=False, error="Email is required")
        >>> validate_email("invalid")
        ValidationResult(valid=False, error="Invalid email format")
    """
    if not email or not email.strip():
        return ValidationResult(valid=False, error="Email is required")

    email = email.strip()

    if len(email) > max_length:
        return ValidationResult(
            valid=False,
            error=f"Email must be at most {max_length} characters",
        )

    if not EMAIL_REGEX.match(email):
        return ValidationResult(valid=False, error="Invalid email format")

    return ValidationResult(valid=True)


def validate_password(
    password: str,
    min_length: int = 8,
    max_length: int = 128,
    require_uppercase: bool = False,
    require_lowercase: bool = False,
    require_digit: bool = False,
    require_special: bool = False,
) -> ValidationResult:
    """Validate a password against configurable policy.

    Default policy (NIST 800-63B inspired):
    - Minimum 8 characters
    - Maximum 128 characters
    - No complexity requirements by default (research shows these don't help)

    Args:
        password: Password to validate
        min_length: Minimum required length (default: 8)
        max_length: Maximum allowed length (default: 128)
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_digit: Require at least one digit
        require_special: Require at least one special character

    Returns:
        ValidationResult with valid=True if password meets policy, or error message.

    Examples:
        >>> validate_password("secure123")
        ValidationResult(valid=True, error=None)
        >>> validate_password("short")
        ValidationResult(valid=False, error="Password must be at least 8 characters")
    """
    if not password:
        return ValidationResult(valid=False, error="Password is required")

    if len(password) < min_length:
        return ValidationResult(
            valid=False,
            error=f"Password must be at least {min_length} characters",
        )

    if len(password) > max_length:
        return ValidationResult(
            valid=False,
            error=f"Password must be at most {max_length} characters",
        )

    if require_uppercase and not any(c.isupper() for c in password):
        return ValidationResult(
            valid=False,
            error="Password must contain at least one uppercase letter",
        )

    if require_lowercase and not any(c.islower() for c in password):
        return ValidationResult(
            valid=False,
            error="Password must contain at least one lowercase letter",
        )

    if require_digit and not any(c.isdigit() for c in password):
        return ValidationResult(
            valid=False,
            error="Password must contain at least one digit",
        )

    if require_special:
        special_chars = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~")
        if not any(c in special_chars for c in password):
            return ValidationResult(
                valid=False,
                error="Password must contain at least one special character",
            )

    return ValidationResult(valid=True)
