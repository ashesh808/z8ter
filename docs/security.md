# Security

Z8ter provides security middleware and account-protection utilities in `z8ter.security`. Register the middleware your application needs: a bare `AppBuilder` does not enable a complete security configuration. The packaged starter explicitly enables basic security headers, but does not enable authentication, CSRF protection, or rate limiting.

## Z8ter 0.3.1 Compatibility

Z8ter 0.3.1 requires Starlette `>=1.6,<2`; the published 0.3.0 release required Starlette below 1. Remove stale Starlette 0.x pins when upgrading and review direct Starlette usage in your app. See [Getting Started](getting-started.md) for upgrade commands.

Version 0.3.1 also preserves form bodies after CSRF validation and bounds the memory used to replay them, as described below.

## Middleware

Set `APP_SESSION_KEY` to a strong secret, then configure your builder before calling `build()`:

```python
from z8ter.builders.app_builder import AppBuilder

builder = AppBuilder()
builder.use_config(".env")
builder.use_csrf()
builder.use_rate_limiting(requests_per_minute=60)
builder.use_security_headers()
app = builder.build()
```

### CSRF Protection

`use_csrf()` checks POST, PUT, DELETE, and PATCH requests for a token submitted through the `csrf_token` form field or `X-CSRF-Token` header. It compares the submitted value with the token in a signed cookie. The token is available as `request.state.csrf_token`, and `View.render()` exposes it as `csrf_token` in templates.

```jinja
<form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <button type="submit">Save</button>
</form>
```

Form-token requests are buffered so handlers can still read their fields and files, with an **8 MiB total body limit** enforced even without `Content-Length`. Larger bodies receive HTTP 413. Set another positive limit in your CSRF registration:

```python
builder.use_csrf(max_form_body_size=16 * 1024 * 1024)
```

Send the token in `X-CSRF-Token` for uploads that should stream without CSRF buffering. This skips only CSRF's form-body buffering limit; application and proxy body limits still apply, and a stricter application-wide limit is preserved. Invalid or missing tokens produce HTTP 403.

The CSRF cookie defaults to `HttpOnly`, `Secure`, and `SameSite=Strict`. For local development over plain HTTP, explicitly use `cookie_secure=False`; keep secure cookies enabled for HTTPS deployments. `exempt_paths` contains path prefixes, so exempt only endpoints that use another appropriate protection, such as a separately authenticated webhook.

### Rate Limiting

`use_rate_limiting()` throttles per client IP and returns HTTP 429 with `Retry-After` when a limit is exceeded. It supports a global per-minute limit, a burst allowance, and path-specific `RateLimitConfig` rules from `z8ter.security.rate_limit`.

Counters are in memory and separate in each process. Shared limits across workers require a shared limiter or an upstream service. The middleware reads forwarded-IP headers; ensure a trusted proxy replaces client-supplied forwarding headers before relying on those addresses.

### Security Headers

`use_security_headers()` adds `X-Content-Type-Options`, `X-Frame-Options`, the legacy `X-XSS-Protection` header, and `Referrer-Policy` by default. **HSTS is disabled by default**. `Content-Security-Policy` and `Permissions-Policy` are added only when you supply values.

Choose options in your single `use_security_headers(...)` registration. Enable `enable_hsts=True` only for an HTTPS deployment, and tailor `content_security_policy` and `permissions_policy` to the resources and browser features your application uses.

## Account Lockout

`AccountLockout` tracks failed attempts for an identifier, complementing the per-IP rate limiter. This synchronous helper illustrates where to record outcomes in a login flow:

```python
from z8ter.auth.crypto import verify_password
from z8ter.security import AccountLockout

lockout = AccountLockout(max_attempts=5, lockout_seconds=900)


def password_accepted(email, stored_hash, password, client_ip=None):
    if lockout.is_locked(email):
        return False
    if verify_password(stored_hash, password):
        lockout.record_success(email)
        return True
    lockout.record_failure(email, ip_address=client_ip)
    return False
```

Keep locked-account and bad-password responses indistinguishable. Lock events produce `ACCOUNT_LOCKED` audit events. State is in memory and per process; use a shared implementation when workers must share account limits. Call `lockout.cleanup()` periodically to remove stale state. `record_success()` does not clear an active lock; `reset()` is the explicit administrative reset.

## Password Reset and Email Verification Tokens

`TokenManager` mints signed, time-limited tokens. The following example reads a secret from the process environment:

```python
import os

from z8ter.auth.tokens import TokenManager

tokens = TokenManager(os.environ["APP_SESSION_KEY"])

reset_token = tokens.generate_password_reset_token("user-123")
user_id = tokens.verify_password_reset_token(reset_token)  # One-hour default

verification_token = tokens.generate_email_verification_token(
    "user-123", "ada@example.com"
)
data = tokens.verify_email_verification_token(verification_token)  # 24-hour default
```

Verification returns `None` for invalid or expired tokens. Tokens are signed, not encrypted, and **are not single-use**: verification does not record consumption or consult the user's current record. Implement consumption or version checks in your application when a reset link must become invalid after use. For email verification, also compare the returned address with the user's current address before marking it verified.

After a successful password reset, revoke the user's authentication sessions with `session_repo.revoke_all_for_user(user_id)`. Session revocation does not itself consume a reset token.

## Audit Logging

```python
from z8ter.security import SecurityEvent, log_security_event

log_security_event(
    SecurityEvent.LOGIN_FAILURE,
    email="ada@example.com",
    ip_address="127.0.0.1",
    success=False,
)
```

Configure handlers for the `z8ter.security` logger. Events include structured data in the log record's `security_data` attribute. Add application-specific events where needed; enabling one middleware does not automatically instrument every account flow. Keep passwords and tokens out of logs.

## Secrets and Environment Files

- Keep `.env` out of version control and verify with `git check-ignore .env`.
- Use an `APP_SESSION_KEY` of at least 32 characters. Generate one with `python -c 'import secrets; print(secrets.token_hex(32))'`.
- Use separate keys for each environment. Rotating a signing key invalidates application-session cookies, CSRF cookies, and tokens signed with that key. Revoke repository-backed authentication sessions separately when required.
- Restrict server-side `.env` permissions and prefer deployment environment variables or a secret manager in production.
- Document required settings in `.env.example` using placeholders.

## Dependency Auditing

The development extra includes `pip-audit`. In your active environment:

```bash
python -m pip install "z8ter[dev]>=0.3.1,<0.4"
python -m pip_audit
```

Audit the application's installed dependencies in CI as well as locally. See [Testing](testing.md) for the current test dependencies.
