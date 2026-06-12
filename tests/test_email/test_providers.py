"""Tests for z8ter.email providers."""

from __future__ import annotations

import logging

from z8ter.email import (
    ConsoleEmailProvider,
    EmailMessage,
    InMemoryEmailProvider,
    SMTPEmailProvider,
)


def _msg(**overrides) -> EmailMessage:
    base = dict(
        to=["user@example.com"],
        subject="Hello",
        text="Plain body",
        from_email="noreply@example.com",
    )
    base.update(overrides)
    return EmailMessage(**base)


def test_console_provider_logs_message(caplog) -> None:
    provider = ConsoleEmailProvider()
    with caplog.at_level(logging.INFO, logger="z8ter.email"):
        provider.send(_msg())
    assert "user@example.com" in caplog.text
    assert "Hello" in caplog.text


def test_in_memory_provider_records_outbox() -> None:
    provider = InMemoryEmailProvider()
    provider.send(_msg(subject="One"))
    provider.send(_msg(subject="Two"))
    assert [m.subject for m in provider.outbox] == ["One", "Two"]
    provider.clear()
    assert provider.outbox == []


def test_all_recipients_combines_to_cc_bcc() -> None:
    msg = _msg(cc=["cc@example.com"], bcc=["bcc@example.com"])
    assert msg.all_recipients() == [
        "user@example.com",
        "cc@example.com",
        "bcc@example.com",
    ]


def test_smtp_provider_builds_multipart_mime() -> None:
    provider = SMTPEmailProvider(host="smtp.example.com", port=587)
    msg = _msg(
        html="<p>HTML body</p>",
        cc=["cc@example.com"],
        reply_to="reply@example.com",
        headers={"X-Test": "1"},
    )
    mime = provider._build_mime(msg)
    assert mime["From"] == "noreply@example.com"
    assert mime["To"] == "user@example.com"
    assert mime["Cc"] == "cc@example.com"
    assert mime["Reply-To"] == "reply@example.com"
    assert mime["X-Test"] == "1"
    # multipart/alternative with text + html parts
    parts = [p.get_content_type() for p in mime.iter_parts()]
    assert parts == ["text/plain", "text/html"]
    # Bcc must never appear in headers
    assert mime["Bcc"] is None


def test_smtp_provider_plaintext_only_mime() -> None:
    provider = SMTPEmailProvider(host="smtp.example.com")
    mime = provider._build_mime(_msg())
    assert mime.get_content_type() == "text/plain"
    assert "Plain body" in mime.get_content()
