"""Tests for z8ter.security.validators module."""

from z8ter.security.validators import validate_email, validate_password


def test_validate_email_accepts_valid_emails():
    result = validate_email("user@example.com")
    assert result.valid is True
    assert result.error is None


def test_validate_email_rejects_empty():
    result = validate_email("")
    assert result.valid is False
    assert result.error == "Email is required"


def test_validate_email_rejects_invalid_format():
    result = validate_email("not-an-email")
    assert result.valid is False
    assert result.error == "Invalid email format"


def test_validate_email_rejects_too_long():
    long_email = "a" * 250 + "@example.com"
    result = validate_email(long_email)
    assert result.valid is False
    assert "at most 254" in result.error


def test_validate_password_accepts_valid_password():
    result = validate_password("securepassword123")
    assert result.valid is True
    assert result.error is None


def test_validate_password_rejects_empty():
    result = validate_password("")
    assert result.valid is False
    assert result.error == "Password is required"


def test_validate_password_rejects_short():
    result = validate_password("short")
    assert result.valid is False
    assert "at least 8 characters" in result.error


def test_validate_password_respects_custom_min_length():
    result = validate_password("abc123", min_length=10)
    assert result.valid is False
    assert "at least 10 characters" in result.error


def test_validate_password_complexity_requirements():
    # Test uppercase requirement
    result = validate_password("alllowercase", require_uppercase=True)
    assert result.valid is False
    assert "uppercase" in result.error

    result = validate_password("HasUppercase", require_uppercase=True)
    assert result.valid is True

    # Test digit requirement
    result = validate_password("nodigitshere", require_digit=True)
    assert result.valid is False
    assert "digit" in result.error

    result = validate_password("hasdigit1", require_digit=True)
    assert result.valid is True
