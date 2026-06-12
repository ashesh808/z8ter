"""Tests for the use_email() builder step."""

from __future__ import annotations

import pytest

from z8ter.builders.app_builder import AppBuilder
from z8ter.email import EmailService, InMemoryEmailProvider


def test_use_email_with_explicit_provider() -> None:
    provider = InMemoryEmailProvider()
    builder = AppBuilder()
    builder.use_config()
    builder.use_email(provider=provider, default_from="noreply@example.com")
    app = builder.build(debug=True)

    service = app.starlette_app.state.email
    assert isinstance(service, EmailService)
    assert service.provider is provider
    assert service.default_from == "noreply@example.com"
    assert app.starlette_app.state.services["email"] is service


def test_use_email_defaults_to_console_provider() -> None:
    from z8ter.email import ConsoleEmailProvider

    builder = AppBuilder()
    builder.use_config()
    builder.use_email()
    app = builder.build(debug=True)
    assert isinstance(
        app.starlette_app.state.email.provider, ConsoleEmailProvider
    )


def test_use_email_smtp_requires_host(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    builder = AppBuilder()
    builder.use_config()
    builder.use_email()
    with pytest.raises(TypeError, match="SMTP_HOST"):
        builder.build(debug=True)


def test_use_email_smtp_from_config(monkeypatch) -> None:
    from z8ter.email import SMTPEmailProvider

    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USE_SSL", "true")
    monkeypatch.setenv("EMAIL_FROM", "noreply@example.com")
    builder = AppBuilder()
    builder.use_config()
    builder.use_email()
    app = builder.build(debug=True)

    service = app.starlette_app.state.email
    provider = service.provider
    assert isinstance(provider, SMTPEmailProvider)
    assert provider.host == "smtp.example.com"
    assert provider.port == 465
    assert provider.use_ssl is True
    assert service.default_from == "noreply@example.com"


def test_use_email_unknown_provider_rejected(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "carrier-pigeon")
    builder = AppBuilder()
    builder.use_config()
    builder.use_email()
    with pytest.raises(ValueError, match="unknown EMAIL_PROVIDER"):
        builder.build(debug=True)
