"""Email contracts (lightweight protocols) for Z8ter.

This module defines the minimal interfaces for sending email from a Z8ter
application. The framework depends only on these contracts; you are free to
back them with SMTP, SendGrid, Resend, SES, or an in-memory outbox for tests.

Design goals:
- Keep the surface tiny and explicit (one `send` method).
- Providers are synchronous at the contract level; `EmailService` offloads
  blocking sends to a threadpool so async handlers never block.
- Message construction is a plain dataclass, easy to assert on in tests.

Security notes:
- Never log full message bodies in production (may contain reset tokens).
- Use TLS (STARTTLS or implicit SSL) for any real SMTP provider.
- Treat recipient addresses as PII when logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class EmailMessage:
    """A single outbound email message.

    Attributes:
        to: List of recipient addresses.
        subject: Message subject line.
        text: Plaintext body (always provide one; HTML is optional).
        html: Optional HTML body. When set, providers should send a
            multipart/alternative message with both parts.
        from_email: Sender address. If None, the `EmailService` default
            (EMAIL_FROM) is applied before the provider sees the message.
        reply_to: Optional Reply-To address.
        cc: Carbon-copy recipients.
        bcc: Blind carbon-copy recipients (never rendered in headers
            visible to other recipients).
        headers: Extra headers (e.g., {"X-Campaign": "welcome"}).

    """

    to: list[str]
    subject: str
    text: str
    html: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)

    def all_recipients(self) -> list[str]:
        """Return every envelope recipient (to + cc + bcc).

        Returns:
            Combined recipient list in to/cc/bcc order, duplicates preserved.

        """
        return [*self.to, *self.cc, *self.bcc]


class EmailProvider(Protocol):
    """Transport contract for delivering an `EmailMessage`.

    Implementations are responsible for:
      - Actually delivering the message (or queueing/recording it).
      - Raising a provider-specific exception on delivery failure so the
        caller can decide whether to retry or surface an error.

    Methods may block (SMTP handshakes, HTTP calls); `EmailService` runs
    providers in a threadpool, so implementations do not need to be async.
    """

    def send(self, message: EmailMessage) -> None:
        """Deliver a single message.

        Args:
            message: Fully-populated message. `from_email` is guaranteed to
                be set by the time a provider receives it.

        Returns:
            None. Raise on failure rather than returning a status code.

        """
        ...
