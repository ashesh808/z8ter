# Security

Z8ter ships a security baseline in `z8ter.security`. This page covers the
middleware, the account-protection utilities, and operational guidance
(secrets, `.env` files, dependency auditing).

## Middleware

Enable the full baseline through the builder:

```python
builder.use_csrf(exempt_paths=["/api/webhooks/"])
builder.use_rate_limiting(requests_per_minute=60)
builder.use_security_headers(enable_hsts=True)  # HTTPS-only deployments
```

- **CSRF** (`use_csrf`): validates a signed token on POST/PUT/DELETE/PATCH,
  submitted via the `csrf_token` form field or `X-CSRF-Token` header. The
  token is exposed to templates as `request.state.csrf_token`.
- **Rate limiting** (`use_rate_limiting`): per-IP request throttling with
  optional per-path rules (e.g., 5/min on `/login`). In-memory; use a
  Redis-based limiter for multi-instance deployments.
- **Security headers** (`use_security_headers`): CSP, HSTS,
  X-Frame-Options, Referrer-Policy, Permissions-Policy.

## Account lockout

`AccountLockout` protects individual accounts from password guessing —
complementary to rate limiting, which throttles a single source IP:

```python
from z8ter.security import AccountLockout

lockout = AccountLockout(max_attempts=5, lockout_seconds=900)

# In the login handler:
if lockout.is_locked(email):
    return error_response()        # indistinguishable from bad password

if verify_password(stored_hash, password):
    lockout.record_success(email)
else:
    lockout.record_failure(email, ip_address=client_ip)
    return error_response()
```

Lock events are emitted through the audit log (`ACCOUNT_LOCKED`). State is
in-memory and per-process; back it with a shared store for strict
guarantees across multiple workers. Schedule `lockout.cleanup()` as a
background task to bound memory.

## Password reset & email verification tokens

`TokenManager` (in `z8ter.auth.tokens`) mints stateless, signed,
time-limited tokens — no database table needed:

```python
from z8ter.auth.tokens import TokenManager

tokens = TokenManager(config("APP_SESSION_KEY"))

# Password reset (1 hour default)
token = tokens.generate_password_reset_token(user_id)
user_id = tokens.verify_password_reset_token(token)        # None if invalid

# Email verification (24 hours default)
token = tokens.generate_email_verification_token(user_id, email)
data = tokens.verify_email_verification_token(token)       # {"uid", "email"}
```

Tokens are signed, not encrypted — never embed secrets in payloads. After
a successful password reset, revoke the user's sessions:

```python
session_repo.revoke_all_for_user(user_id)
```

## Audit logging

```python
from z8ter.security import SecurityEvent, log_security_event

log_security_event(
    SecurityEvent.LOGIN_FAILURE,
    email=email,
    ip_address=client_ip,
    success=False,
)
```

Configure a handler for the `z8ter.security` logger to ship events to
your log aggregation / SIEM.

## Secrets and `.env` files

- **Never commit `.env` to version control.** Add it to `.gitignore`
  (scaffolded projects already do this) and verify with
  `git check-ignore .env`.
- **Generate strong keys**: `APP_SESSION_KEY` must be at least 32
  characters. Generate one with:

  ```bash
  python -c 'import secrets; print(secrets.token_hex(32))'
  ```

- **One key per environment.** Never reuse the production key in staging
  or development; rotating a key invalidates outstanding sessions, CSRF
  tokens, and reset/verification tokens signed with it.
- **Restrict file permissions** on servers: `chmod 600 .env`.
- **Prefer real environment variables** (or a secret manager) over `.env`
  files in production — container orchestrators and PaaS platforms
  provide these natively.
- Keep an `.env.example` with placeholder values in the repo so the
  required keys are documented without leaking secrets.

## Dependency auditing

The dev extra includes [pip-audit](https://pypi.org/project/pip-audit/).
Run it locally and in CI to catch known CVEs in dependencies:

```bash
pip install "z8ter[dev]"
pip-audit
```

A minimal GitHub Actions step:

```yaml
- name: Audit dependencies
  run: |
    pip install pip-audit
    pip-audit
```
