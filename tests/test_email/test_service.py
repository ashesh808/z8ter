"""Tests for z8ter.email.service.EmailService."""

from __future__ import annotations

import asyncio

import pytest

import z8ter
from z8ter.email import EmailMessage, EmailService, InMemoryEmailProvider
from z8ter.email.service import _strip_tags


def test_send_applies_default_from() -> None:
    provider = InMemoryEmailProvider()
    service = EmailService(provider, default_from="noreply@example.com")
    asyncio.run(
        service.send_email(to="user@example.com", subject="Hi", text="Body")
    )
    assert provider.outbox[0].from_email == "noreply@example.com"
    assert provider.outbox[0].to == ["user@example.com"]


def test_send_without_sender_raises() -> None:
    service = EmailService(InMemoryEmailProvider())
    message = EmailMessage(to=["user@example.com"], subject="Hi", text="Body")
    with pytest.raises(ValueError, match="no sender"):
        asyncio.run(service.send(message))


def test_send_email_accepts_recipient_list() -> None:
    provider = InMemoryEmailProvider()
    service = EmailService(provider, default_from="noreply@example.com")
    asyncio.run(
        service.send_email(
            to=["a@example.com", "b@example.com"],
            subject="Hi",
            text="Body",
            html="<p>Body</p>",
        )
    )
    msg = provider.outbox[0]
    assert msg.to == ["a@example.com", "b@example.com"]
    assert msg.html == "<p>Body</p>"


def test_send_template_renders_jinja(tmp_path) -> None:
    emails_dir = tmp_path / "templates" / "emails"
    emails_dir.mkdir(parents=True)
    (emails_dir / "welcome.html").write_text(
        "<h1>Welcome {{ name }}</h1><p>Glad you joined.</p>"
    )
    z8ter.set_app_dir(tmp_path)  # conftest restores the previous app dir

    provider = InMemoryEmailProvider()
    service = EmailService(provider, default_from="noreply@example.com")
    asyncio.run(
        service.send_template(
            to="user@example.com",
            subject="Welcome",
            template="emails/welcome.html",
            context={"name": "Ada"},
        )
    )
    msg = provider.outbox[0]
    assert "<h1>Welcome Ada</h1>" in msg.html
    # Derived plaintext fallback has tags stripped
    assert "Welcome Ada" in msg.text
    assert "<h1>" not in msg.text


def test_strip_tags_removes_markup_and_scripts() -> None:
    html = "<style>p{}</style><p>Hello <b>world</b></p><script>x()</script>"
    assert _strip_tags(html) == "Hello world"
