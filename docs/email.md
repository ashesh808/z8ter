# Email

Z8ter's `z8ter.email` module provides an asynchronous `EmailService` over synchronous delivery providers. Provider sends run in an executor thread. Awaiting a send still waits for delivery to finish, and provider errors propagate to the caller.

Email is optional; a new app does not enable it automatically.

## Enabling Email

```python
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")
builder.use_email()
app = builder.build()
```

`use_email()` requires `use_config()`, including when you pass an explicit provider. The service is published as `request.app.state.email` and in the `email` service entry.

Example environment settings:

```dotenv
EMAIL_PROVIDER=console
EMAIL_FROM=noreply@example.com

# Set EMAIL_PROVIDER=smtp to deliver through this server.
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=replace-with-your-username
SMTP_PASSWORD=replace-with-your-password
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

The default `console` provider logs a message preview through `z8ter.email` without delivering it. Previews can contain personal data or tokens; use it for development rather than production mail delivery.

For SMTP, `SMTP_HOST` is required. Port 587 and STARTTLS are the defaults. For implicit SSL, set `SMTP_USE_SSL=true`, `SMTP_USE_TLS=false`, and the appropriate port, commonly 465. The provider opens a connection for each send.

## Sending from a View

With email enabled, this example returns a response after the send completes:

```python
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Welcome(View):
    async def post(self, request: Request) -> JSONResponse:
        await request.app.state.email.send_email(
            to="ada@example.com",
            subject="Welcome!",
            text="Thanks for signing up.",
            html="<p>Thanks for signing up.</p>",
        )
        return JSONResponse({"ok": True})
```

Use your application's recipient and authorization rules when adapting this example. `send_email()` accepts one address or a list of addresses, plus optional `from_email` and `reply_to`. Set either `EMAIL_FROM`, `default_from` on the service, or a per-message sender; sending without a sender raises `ValueError`.

## Explicit Providers

A provider implements the synchronous `send(message: EmailMessage) -> None` contract. Raise an exception on delivery failure. Register an explicit provider before building the app:

```python
from z8ter.builders.app_builder import AppBuilder
from z8ter.email import SMTPEmailProvider

builder = AppBuilder()
builder.use_config()
builder.use_email(
    provider=SMTPEmailProvider(host="smtp.example.com", port=587),
    default_from="noreply@example.com",
)
app = builder.build()
```

Supply the credentials required by your SMTP server. `EmailMessage` also supports CC, BCC, extra headers, and a reply address; use `EmailService.send(message)` for a prepared message.

## Template-Based Email

Register `builder.use_templating()` before building when the app needs Jinja templates. Store email templates alongside page templates:

```text
templates/
  emails/
    welcome.html
    welcome.txt
```

Call the service from an async handler or helper:

```python
from z8ter.email import EmailService


async def send_welcome(email: EmailService, address: str, name: str) -> None:
    await email.send_template(
        to=address,
        subject="Welcome!",
        template="emails/welcome.html",
        text_template="emails/welcome.txt",
        context={"name": name},
    )
```

The HTML and text templates receive the supplied context. If `text_template` is omitted, the service derives a rough plain-text fallback by removing HTML tags. Template rendering happens synchronously before delivery is offloaded; provide an explicit text template when formatting matters.

## Verification and Password-Reset Emails

Combine `EmailService` with `TokenManager` and your own verification route:

```python
from urllib.parse import urlencode

from z8ter.auth.tokens import TokenManager
from z8ter.email import EmailService


async def send_verification(
    email: EmailService, secret_key: str, user_id: str, address: str
) -> None:
    tokens = TokenManager(secret_key)
    token = tokens.generate_email_verification_token(user_id, address)
    link = "https://example.com/verify?" + urlencode({"token": token})
    await email.send_email(
        to=address,
        subject="Verify your email",
        text=f"Open this link to verify your address: {link}",
    )
```

Replace the example domain with your application's address. Your route must validate the token and compare its email address with the current user record. Tokens are signed and expire, but are not consumed on verification; see [Security](security.md) for replay and password-reset considerations.

## Testing and Background Delivery

`InMemoryEmailProvider` records messages without external delivery:

```python
import asyncio

from z8ter.email import EmailService, InMemoryEmailProvider

provider = InMemoryEmailProvider()
email = EmailService(provider, default_from="noreply@example.com")
asyncio.run(email.send_email(
    to="ada@example.com",
    subject="Welcome!",
    text="Thanks for signing up.",
))
assert provider.outbox[0].subject == "Welcome!"
```

Use a [background task](background-tasks.md) when a request should not wait for a send. These tasks run in the application process and do not provide durable delivery; use a persistent job system for messages that must survive restarts.
