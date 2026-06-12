"""Async email service for Z8ter.

`EmailService` wraps a synchronous `EmailProvider` and exposes async send
methods that offload delivery to a threadpool, so request handlers never
block on SMTP handshakes or HTTP calls.

It also supports rendering message bodies from the application's Jinja
templates (the same environment used for pages), so transactional emails
live alongside the rest of your templates:

    templates/
      emails/
        welcome.html
        welcome.txt

Usage:
    from z8ter.email import EmailService, SMTPEmailProvider

    service = EmailService(
        SMTPEmailProvider(host="smtp.example.com", port=587),
        default_from="noreply@example.com",
    )
    await service.send_email(
        to="user@example.com",
        subject="Welcome!",
        text="Thanks for signing up.",
    )
"""

from __future__ import annotations

import asyncio
import logging

from z8ter.email.contracts import EmailMessage, EmailProvider

logger = logging.getLogger("z8ter.email")


class EmailService:
    """High-level async email sender.

    Args:
        provider: Transport implementation (`EmailProvider`).
        default_from: Sender address applied when a message has none.

    Notes:
        - Delivery runs in the default executor (`run_in_executor`), matching
          how Z8ter offloads other blocking repositories.
        - Provider exceptions propagate to the caller; decide per-flow
          whether a failed email should fail the request (verification)
          or be swallowed and logged (marketing).

    """

    def __init__(
        self,
        provider: EmailProvider,
        *,
        default_from: str | None = None,
    ) -> None:
        """Bind a provider and an optional default sender address."""
        self.provider = provider
        self.default_from = default_from

    async def send(self, message: EmailMessage) -> None:
        """Send a prepared `EmailMessage` without blocking the event loop.

        Args:
            message: Message to deliver. If `from_email` is unset, the
                service default is applied.

        Raises:
            ValueError: If no sender address can be resolved.

        """
        if message.from_email is None:
            message.from_email = self.default_from
        if not message.from_email:
            raise ValueError(
                "Z8ter: email message has no sender. Set from_email on the "
                "message or default_from on the EmailService (EMAIL_FROM)."
            )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.provider.send, message)

    async def send_email(
        self,
        *,
        to: str | list[str],
        subject: str,
        text: str,
        html: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Build and send a message in one call.

        Args:
            to: Single recipient or list of recipients.
            subject: Subject line.
            text: Plaintext body.
            html: Optional HTML body.
            from_email: Optional sender override.
            reply_to: Optional Reply-To address.

        """
        recipients = [to] if isinstance(to, str) else list(to)
        await self.send(
            EmailMessage(
                to=recipients,
                subject=subject,
                text=text,
                html=html,
                from_email=from_email,
                reply_to=reply_to,
            )
        )

    async def send_template(
        self,
        *,
        to: str | list[str],
        subject: str,
        template: str,
        context: dict | None = None,
        text_template: str | None = None,
        from_email: str | None = None,
    ) -> None:
        """Render Jinja templates from the app's template dir and send.

        Args:
            to: Single recipient or list of recipients.
            subject: Subject line.
            template: Template name for the HTML body
                (e.g., "emails/welcome.html").
            context: Variables passed to the template(s).
            text_template: Optional template name for the plaintext body.
                If omitted, a crude text fallback is derived by stripping
                tags from the rendered HTML.
            from_email: Optional sender override.

        Notes:
            - Uses `z8ter.get_templates()`, the same cached environment as
              page rendering, so `url_for` and friends are available when
              the app was built with templating.

        """
        import z8ter

        env = z8ter.get_templates().env
        ctx = context or {}
        html = env.get_template(template).render(**ctx)
        if text_template:
            text = env.get_template(text_template).render(**ctx)
        else:
            text = _strip_tags(html)
        await self.send_email(
            to=to,
            subject=subject,
            text=text,
            html=html,
            from_email=from_email,
        )


def _strip_tags(html: str) -> str:
    """Derive a rough plaintext fallback from an HTML body.

    This is intentionally simple (regex tag removal + whitespace collapse).
    Provide an explicit `text_template` for emails where the plaintext part
    matters.
    """
    import re

    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
