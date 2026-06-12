# Email

Z8ter ships transactional email support with pluggable providers
(`z8ter.email`). Handlers send through an async `EmailService` that never
blocks the event loop.

## Enabling email

```python
builder = AppBuilder()
builder.use_config(".env")
builder.use_email()  # provider resolved from config
app = builder.build()
```

Configuration via `.env`:

```bash
EMAIL_PROVIDER=console        # console (default) or smtp
EMAIL_FROM=noreply@example.com

# Required when EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=secret
SMTP_USE_TLS=true             # STARTTLS (default)
SMTP_USE_SSL=false            # implicit SSL (e.g., port 465)
```

The `console` provider logs messages instead of delivering them — ideal
while developing flows like registration or password reset.

You can also pass a provider explicitly (any object with a
`send(message)` method satisfies the `EmailProvider` contract):

```python
from z8ter.email import SMTPEmailProvider

builder.use_email(
    provider=SMTPEmailProvider(host="smtp.example.com", port=587),
    default_from="noreply@example.com",
)
```

## Sending email

The service is available at `request.app.state.email`:

```python
class Register(View):
    async def post(self, request):
        email = request.app.state.email
        await email.send_email(
            to="user@example.com",
            subject="Welcome!",
            text="Thanks for signing up.",
            html="<p>Thanks for signing up.</p>",
        )
```

## Template-based email

Email bodies can be rendered from the same Jinja template directory as
your pages:

```
templates/
  emails/
    welcome.html
    welcome.txt
```

```python
await email.send_template(
    to=user["email"],
    subject="Welcome!",
    template="emails/welcome.html",
    text_template="emails/welcome.txt",   # optional; derived from HTML if omitted
    context={"name": user["name"]},
)
```

## Verification and password-reset emails

Combine the email service with `TokenManager` (see
[Authentication](authentication.md)) to implement email verification and
password reset:

```python
from z8ter.auth.tokens import TokenManager

tokens = TokenManager(config("APP_SESSION_KEY"))
token = tokens.generate_email_verification_token(user["id"], user["email"])
await email.send_email(
    to=user["email"],
    subject="Verify your email",
    text=f"Click to verify: https://example.com/verify?token={token}",
)
```

## Testing

Use the in-memory provider and assert on its outbox:

```python
from z8ter.email import InMemoryEmailProvider

provider = InMemoryEmailProvider()
builder.use_email(provider=provider, default_from="noreply@test")
...
assert provider.outbox[0].subject == "Verify your email"
```
