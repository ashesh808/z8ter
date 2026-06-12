"""Built-in email providers for Z8ter.

Providers implement the `EmailProvider` contract from
`z8ter.email.contracts`:

- `ConsoleEmailProvider`: logs messages — the development default.
- `InMemoryEmailProvider`: records messages in an outbox list — for tests.
- `SMTPEmailProvider`: delivers via SMTP using the standard library.

Security notes:
- `ConsoleEmailProvider` logs subjects and recipients but truncates bodies,
  since bodies often contain password-reset or verification tokens.
- `SMTPEmailProvider` defaults to STARTTLS. Only disable TLS for local
  development servers (e.g., Mailpit/MailHog on localhost).
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage as StdlibEmailMessage

from z8ter.email.contracts import EmailMessage

logger = logging.getLogger("z8ter.email")

# Maximum body characters echoed to the console log (bodies may hold tokens).
_CONSOLE_BODY_PREVIEW = 2000


class ConsoleEmailProvider:
    """Log messages instead of delivering them (development default).

    Useful while building flows (registration, password reset) before any
    real email infrastructure exists. Messages are logged at INFO level.

    Example:
        provider = ConsoleEmailProvider()
        provider.send(EmailMessage(to=["a@b.c"], subject="Hi", text="Hello"))

    """

    def send(self, message: EmailMessage) -> None:
        """Log the message to the `z8ter.email` logger.

        Args:
            message: Message to "deliver".

        """
        preview = message.text[:_CONSOLE_BODY_PREVIEW]
        logger.info(
            "Email (console provider) from=%s to=%s subject=%r\n%s",
            message.from_email,
            ", ".join(message.to),
            message.subject,
            preview,
        )


class InMemoryEmailProvider:
    """Record messages in an in-memory outbox (testing).

    Attributes:
        outbox: All messages passed to `send`, in order.

    Example:
        provider = InMemoryEmailProvider()
        service = EmailService(provider, default_from="noreply@example.com")
        ...
        assert provider.outbox[0].subject == "Verify your email"

    """

    def __init__(self) -> None:
        """Initialize an empty outbox."""
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        """Append the message to the outbox.

        Args:
            message: Message to record.

        """
        self.outbox.append(message)

    def clear(self) -> None:
        """Empty the outbox (e.g., between test cases)."""
        self.outbox.clear()


class SMTPEmailProvider:
    """Deliver messages over SMTP using the standard library.

    Supports STARTTLS (default), implicit SSL, and optional authentication.
    A new connection is opened per `send` call — simple and safe for the
    low volumes a web app sends inline. For bulk email, use a queue and a
    dedicated delivery service.

    Args:
        host: SMTP server hostname.
        port: SMTP server port (587 STARTTLS, 465 SSL, 25/1025 plain).
        username: Optional username for SMTP AUTH.
        password: Optional password for SMTP AUTH.
        use_tls: Upgrade the connection with STARTTLS (default: True).
        use_ssl: Use implicit SSL from the start (mutually exclusive with
            `use_tls`; takes precedence when both are set).
        timeout: Socket timeout in seconds.

    Example:
        provider = SMTPEmailProvider(
            host="smtp.example.com",
            port=587,
            username="apikey",
            password="...",
        )

    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: float = 10.0,
    ) -> None:
        """Store connection settings; no connection is made until `send`."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout

    def _build_mime(self, message: EmailMessage) -> StdlibEmailMessage:
        """Convert a Z8ter `EmailMessage` into a stdlib MIME message."""
        mime = StdlibEmailMessage()
        mime["From"] = message.from_email or ""
        mime["To"] = ", ".join(message.to)
        mime["Subject"] = message.subject
        if message.cc:
            mime["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            mime["Reply-To"] = message.reply_to
        for key, value in message.headers.items():
            mime[key] = value
        mime.set_content(message.text)
        if message.html:
            mime.add_alternative(message.html, subtype="html")
        return mime

    def send(self, message: EmailMessage) -> None:
        """Deliver the message via SMTP.

        Args:
            message: Message to deliver. `from_email` must be set.

        Raises:
            smtplib.SMTPException: On any SMTP-level delivery failure.
            OSError: On connection-level failures (DNS, refused, timeout).

        """
        mime = self._build_mime(message)
        recipients = message.all_recipients()

        if self.use_ssl:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout
            )
        else:
            smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

        try:
            if self.use_tls and not self.use_ssl:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(
                mime,
                from_addr=message.from_email,
                to_addrs=recipients,
            )
            logger.info(
                "Email sent via SMTP to=%s subject=%r",
                ", ".join(message.to),
                message.subject,
            )
        finally:
            try:
                smtp.quit()
            except smtplib.SMTPException:
                # Connection already torn down; delivery result stands.
                pass
