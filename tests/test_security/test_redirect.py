"""Tests for z8ter.security.redirect module."""

from z8ter.security.redirect import get_safe_redirect_url, is_safe_redirect_url


class TestIsSafeRedirectUrl:
    def test_relative_url_is_safe(self):
        assert is_safe_redirect_url("/dashboard") is True
        assert is_safe_redirect_url("/app/settings") is True
        assert is_safe_redirect_url("/") is True

    def test_relative_url_with_query_is_safe(self):
        assert is_safe_redirect_url("/login?next=/home") is True

    def test_absolute_url_without_allowed_hosts_is_unsafe(self):
        assert is_safe_redirect_url("https://evil.com/steal") is False
        assert is_safe_redirect_url("http://attacker.com") is False

    def test_absolute_url_with_allowed_hosts_is_safe(self):
        allowed = {"example.com", "myapp.com"}
        assert is_safe_redirect_url("https://example.com/page", allowed) is True
        assert is_safe_redirect_url("https://myapp.com/dashboard", allowed) is True
        assert is_safe_redirect_url("https://evil.com/steal", allowed) is False

    def test_protocol_relative_url_is_unsafe(self):
        assert is_safe_redirect_url("//evil.com") is False
        assert is_safe_redirect_url("//evil.com/path") is False

    def test_empty_url_is_unsafe(self):
        assert is_safe_redirect_url("") is False
        assert is_safe_redirect_url(None) is False

    def test_url_with_credentials_is_unsafe(self):
        assert is_safe_redirect_url("https://user:pass@evil.com") is False


class TestGetSafeRedirectUrl:
    def test_returns_valid_url(self):
        assert get_safe_redirect_url("/dashboard") == "/dashboard"

    def test_returns_fallback_for_invalid_url(self):
        assert get_safe_redirect_url("https://evil.com") == "/"
        assert get_safe_redirect_url("https://evil.com", fallback="/home") == "/home"

    def test_returns_fallback_for_none(self):
        assert get_safe_redirect_url(None) == "/"
        assert get_safe_redirect_url(None, fallback="/app") == "/app"
