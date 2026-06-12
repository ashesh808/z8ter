"""Tests for z8ter.auth.tokens.TokenManager."""

from __future__ import annotations

import pytest

from z8ter.auth.tokens import TokenManager

SECRET = "unit-test-secret-key-0123456789abcdef0123456789"


@pytest.fixture()
def manager() -> TokenManager:
    return TokenManager(SECRET)


def test_short_secret_key_rejected() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        TokenManager("too-short")


def test_empty_secret_key_rejected() -> None:
    with pytest.raises(ValueError):
        TokenManager("")


def test_password_reset_roundtrip(manager: TokenManager) -> None:
    token = manager.generate_password_reset_token("u_123")
    assert manager.verify_password_reset_token(token) == "u_123"


def test_password_reset_token_tampering(manager: TokenManager) -> None:
    token = manager.generate_password_reset_token("u_123")
    assert manager.verify_password_reset_token(token + "x") is None
    assert manager.verify_password_reset_token("garbage") is None


def test_password_reset_token_expiry(manager: TokenManager) -> None:
    token = manager.generate_password_reset_token("u_123")
    assert manager.verify_password_reset_token(token, max_age=-1) is None


def test_reset_token_rejected_as_verification_token(
    manager: TokenManager,
) -> None:
    token = manager.generate_password_reset_token("u_123")
    assert manager.verify_email_verification_token(token) is None


def test_email_verification_roundtrip(manager: TokenManager) -> None:
    token = manager.generate_email_verification_token("u_1", "User@Example.com")
    data = manager.verify_email_verification_token(token)
    assert data == {"uid": "u_1", "email": "user@example.com"}


def test_verification_token_rejected_as_reset_token(
    manager: TokenManager,
) -> None:
    token = manager.generate_email_verification_token("u_1", "a@b.c")
    assert manager.verify_password_reset_token(token) is None


def test_tokens_from_different_secrets_rejected(manager: TokenManager) -> None:
    other = TokenManager("another-secret-key-0123456789abcdef012345")
    token = other.generate_password_reset_token("u_123")
    assert manager.verify_password_reset_token(token) is None


def test_generic_purpose_roundtrip(manager: TokenManager) -> None:
    token = manager.generate("unsubscribe", {"list": "news", "uid": "u_9"})
    data = manager.verify("unsubscribe", token, max_age=3600)
    assert data == {"list": "news", "uid": "u_9"}
    # Different purpose must not verify
    assert manager.verify("other", token, max_age=3600) is None
