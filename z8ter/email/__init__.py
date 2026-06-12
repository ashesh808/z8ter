"""Z8ter email module.

Transactional email support with pluggable providers:
- `EmailMessage` / `EmailProvider`: minimal contracts.
- `ConsoleEmailProvider`: logs messages (development default).
- `InMemoryEmailProvider`: records messages in an outbox (tests).
- `SMTPEmailProvider`: stdlib SMTP delivery with STARTTLS/SSL.
- `EmailService`: async send + Jinja template rendering.

Enable via the app builder:

    builder.use_config()
    builder.use_email()   # provider resolved from EMAIL_PROVIDER config

Configuration (via .env):
    EMAIL_PROVIDER=console|smtp     (default: console)
    EMAIL_FROM=noreply@example.com
    SMTP_HOST=smtp.example.com
    SMTP_PORT=587
    SMTP_USERNAME=...
    SMTP_PASSWORD=...
    SMTP_USE_TLS=true
"""

from z8ter.email.contracts import EmailMessage, EmailProvider
from z8ter.email.providers import (
    ConsoleEmailProvider,
    InMemoryEmailProvider,
    SMTPEmailProvider,
)
from z8ter.email.service import EmailService

__all__ = [
    "EmailMessage",
    "EmailProvider",
    "ConsoleEmailProvider",
    "InMemoryEmailProvider",
    "SMTPEmailProvider",
    "EmailService",
]
