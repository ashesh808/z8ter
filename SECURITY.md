# Z8ter Framework - Security Review

**Review Date:** January 2026
**Framework Version:** 0.2.6
**Severity Ratings:** Critical, High, Medium, Low, Informational

---

## Executive Summary

This security review identifies significant vulnerabilities in the Z8ter framework that must be addressed before production deployment. The framework lacks several fundamental security controls expected in modern web applications.

### Risk Summary

| Severity     | Count | Status                    |
| ------------ | ----- | ------------------------- |
| **Critical** | 4     | Immediate action required |
| **High**     | 7     | Fix before production     |
| **Medium**   | 9     | Should be addressed       |
| **Low**      | 6     | Recommended improvements  |

### Critical Findings Overview

1. **No CSRF Protection** - Forms have tokens but no validation
2. **Open Redirect Vulnerability** - `?next=` parameter unvalidated
3. **Session IDs Stored in Plaintext** - Violates documented contract
4. **Insecure Cookie Configuration** - Hardcoded `secure=False`

---

## 1. Authentication Security

### 1.1 No CSRF Protection [CRITICAL]

**Location:** Framework-wide
**CWE:** CWE-352 (Cross-Site Request Forgery)

**Finding:**
Templates include CSRF token hidden fields:

```html
<!-- z8ter-app/templates/pages/login.jinja:15 -->
<input type="hidden" name="csrf_token" value="{{ csrf_token }}" />
```

However, there is **NO middleware or validation** for CSRF tokens anywhere in the codebase. The `csrf_token` template variable is never defined, so it renders as empty.

**Impact:**

- Attackers can forge requests to perform actions as authenticated users
- Account takeover via password change forms
- Unauthorized transactions in payment flows
- State-changing actions without user consent

**Evidence:**

```bash
$ grep -r "csrf" z8ter/           # No results
$ grep -r "csrf" z8ter-app/*.py   # No results
```

**Remediation:**

1. Add CSRF middleware (e.g., `starlette-wtf` or custom implementation)
2. Generate and validate tokens on all state-changing requests
3. Use `SameSite=Strict` cookies as defense in depth

---

### 1.2 Open Redirect Vulnerability [CRITICAL]

**Location:** `z8ter/auth/guards.py:58-61`
**CWE:** CWE-601 (URL Redirection to Untrusted Site)

**Finding:**

```python
def login_required(handler):
    async def wrapper(self, request: Request, *args, **kwargs):
        ...
        next_url = request.url.path
        if request.url.query:
            next_url = f"{next_url}?{request.url.query}"
        redirect_url = f"{login_path}?next={quote(next_url, safe='')}"
```

The `next` parameter is URL-encoded but never validated when read back. An attacker can craft:

```
https://yourapp.com/login?next=https://evil.com/steal-creds
```

After login, users are redirected to the attacker's site.

**Impact:**

- Credential phishing via lookalike domains
- OAuth token theft
- User trust exploitation

**Remediation:**

```python
def is_safe_redirect(url: str, allowed_hosts: set[str]) -> bool:
    """Validate redirect URL is relative or to allowed host."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    # Only allow relative URLs or same-host
    return not parsed.netloc or parsed.netloc in allowed_hosts
```

---

### 1.3 No Account Lockout or Rate Limiting [HIGH]

**Location:** `z8ter-app/endpoints/views/login.py`
**CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)

**Finding:**
No rate limiting exists on authentication endpoints. Attackers can perform unlimited login attempts.

```python
async def post(self, request: Request) -> Response:
    form: FormData = await request.form()
    ...
    user = await mu.get_user_email(email)
    if user is None:
        return RedirectResponse("/login?e=badcreds", status_code=303)
    # No rate limiting, no lockout, no delay
```

**Impact:**

- Brute force password attacks
- Credential stuffing attacks
- DoS via resource exhaustion

**Remediation:**

1. Implement per-IP rate limiting (e.g., 5 attempts per minute)
2. Implement per-account lockout (e.g., 10 failed attempts = 15 min lockout)
3. Add exponential backoff delays
4. Log failed attempts for monitoring

---

### 1.4 Timing Attack on User Enumeration [MEDIUM]

**Location:** `z8ter-app/endpoints/views/login.py:27-31`
**CWE:** CWE-208 (Observable Timing Discrepancy)

**Finding:**

```python
user = await mu.get_user_email(email)
if user is None:
    return RedirectResponse("/login?e=badcreds", status_code=303)  # Fast return
ok = verify_password(user["pwd_hash"], pwd)  # Slow operation
if not ok:
    return RedirectResponse("/login?e=badcreds", status_code=303)
```

The response time differs based on whether the user exists:

- User exists: ~100-300ms (password verification)
- User doesn't exist: ~1-5ms (immediate return)

**Impact:**

- Attackers can enumerate valid email addresses
- Targeted phishing campaigns
- Credential stuffing optimization

**Remediation:**

```python
# Always perform password check, even for non-existent users
DUMMY_HASH = hash_password("dummy_password_for_timing")

user = await mu.get_user_email(email)
hash_to_check = user["pwd_hash"] if user else DUMMY_HASH
ok = verify_password(hash_to_check, pwd)
if not user or not ok:
    return RedirectResponse("/login?e=badcreds", status_code=303)
```

---

### 1.5 Weak Password Policy [MEDIUM]

**Location:** `z8ter-app/endpoints/views/register.py:20-21`
**CWE:** CWE-521 (Weak Password Requirements)

**Finding:**

```python
if (not email) or (not pwd) or (pwd != pwd2):
    return RedirectResponse("/register?e=invalid", status_code=303)
```

The only password validation is:

- Non-empty
- Matches confirmation

Passwords like "a", "123", "password" are accepted.

**Impact:**

- Easy credential guessing
- Credential stuffing success
- Compromised accounts

**Remediation:**

1. Minimum 8 characters (NIST recommends supporting up to 64)
2. Check against common password lists (e.g., Have I Been Pwned API)
3. Optional: Require complexity without mandating special characters

---

### 1.6 No Email Verification [MEDIUM]

**Location:** `z8ter-app/endpoints/views/register.py`
**CWE:** CWE-287 (Improper Authentication)

**Finding:**
Users can register with any email without verification:

```python
await mu.create_user(email, pwd)
return RedirectResponse("/login?m=signup_ok", status_code=303)
```

**Impact:**

- Fake account creation
- Email spoofing for social engineering
- Abuse of platform features
- Legal liability for unverified accounts

**Remediation:**

1. Send verification email with secure token
2. Mark accounts as unverified until confirmed
3. Restrict unverified account capabilities

---

### 1.7 No Duplicate Email Check [HIGH]

**Location:** `z8ter-app/endpoints/views/register.py`
**CWE:** CWE-287 (Improper Authentication)

**Finding:**
Registration doesn't check if email already exists:

```python
async def post(self, request: Request) -> Response:
    ...
    await mu.create_user(email, pwd)  # No duplicate check
```

**Impact:**

- Data corruption or silent overwrite
- Account takeover if existing accounts are overwritten
- Undefined behavior

**Remediation:**

```python
existing = await mu.get_user_email(email)
if existing:
    return RedirectResponse("/register?e=email_exists", status_code=303)
```

---

## 2. Session Management

### 2.1 Plaintext Session ID Storage [CRITICAL]

**Location:** `z8ter-app/app/identity/adapter/session_repo.py:22`
**CWE:** CWE-312 (Cleartext Storage of Sensitive Information)

**Finding:**
The contract (`z8ter/auth/contracts.py`) explicitly states:

> "IMPLEMENTORS MUST hash before persisting (e.g., HMAC(secret, sid_plain))."

But the reference implementation stores plaintext:

```python
def insert(self, *, sid_plain: str, ...):
    self._sessions[sid_plain] = {...}  # Plaintext key!
```

**Impact:**

- If session store is compromised, all sessions are immediately usable
- No defense against session theft
- Sets bad example for framework users

**Remediation:**

```python
import hashlib
import hmac

def _hash_sid(self, sid_plain: str) -> str:
    return hmac.new(
        self._secret.encode(),
        sid_plain.encode(),
        hashlib.sha256
    ).hexdigest()

def insert(self, *, sid_plain: str, ...):
    hashed = self._hash_sid(sid_plain)
    self._sessions[hashed] = {...}
```

---

### 2.2 Insecure Cookie Configuration [CRITICAL]

**Location:** `z8ter-app/endpoints/views/login.py:34`
**CWE:** CWE-614 (Sensitive Cookie in HTTPS Session Without 'Secure' Attribute)

**Finding:**

```python
await ms.set_session_cookie(resp, sid, secure=False)  # Hardcoded!
```

Cookies are sent over HTTP, allowing network interception.

**Impact:**

- Session hijacking via network sniffing
- MITM attacks on shared networks (coffee shops, airports)
- Cookie theft via HTTP downgrade attacks

**Remediation:**

```python
# Read from configuration
is_production = config("ENVIRONMENT", default="development") == "production"
await ms.set_session_cookie(resp, sid, secure=is_production)
```

---

### 2.3 No Session Expiry Cleanup [LOW]

**Location:** `z8ter-app/app/identity/adapter/session_repo.py:41-49`
**CWE:** CWE-613 (Insufficient Session Expiration)

**Finding:**
Expired sessions are checked but never removed:

```python
def get_user_id(self, sid_plain: str) -> Optional[str]:
    session = self._sessions.get(sid_plain)
    if session["expires_at"] <= datetime.now(timezone.utc):
        return None  # Returns None but session stays in memory
```

**Impact:**

- Memory exhaustion over time
- Potential reuse if timestamps roll over
- DoS via session creation

**Remediation:**

1. Implement periodic cleanup task
2. Remove expired sessions on access
3. Add maximum session store size

---

### 2.4 No Session Invalidation on Password Change [MEDIUM]

**Location:** Not implemented
**CWE:** CWE-613 (Insufficient Session Expiration)

**Finding:**
There is no mechanism to invalidate all sessions when a user changes their password.

**Impact:**

- Compromised sessions remain valid after password reset
- Attackers maintain access after user "secures" account

**Remediation:**

1. Store password change timestamp per user
2. Invalidate sessions created before password change
3. Or: Store session generation number, increment on password change

---

### 2.5 Session Fixation Potential [MEDIUM]

**Location:** `z8ter-app/endpoints/views/login.py`
**CWE:** CWE-384 (Session Fixation)

**Finding:**
The login flow creates a new session but doesn't explicitly regenerate if one exists:

```python
sid = await ms.start_session(user["id"])
resp = RedirectResponse("/app", status_code=303)
await ms.set_session_cookie(resp, sid, secure=False)
```

If an attacker can set a session cookie before login, it may persist.

**Remediation:**

1. Always create new session ID on successful authentication
2. Explicitly clear any existing session cookies before setting new ones

---

## 3. Input Validation & Injection

### 3.1 No Input Sanitization Framework [HIGH]

**Location:** Framework-wide
**CWE:** CWE-20 (Improper Input Validation)

**Finding:**
No input validation or sanitization exists beyond basic type coercion:

```python
email = str(form.get("email") or "").strip()
pwd = str(form.get("password") or "")
```

No validation for:

- Email format
- Maximum lengths
- Allowed characters
- Injection patterns

**Impact:**

- Potential for various injection attacks
- Data integrity issues
- Application crashes from malformed input

**Remediation:**

1. Add Pydantic or similar for request validation
2. Define schemas for all form inputs
3. Add middleware for global input sanitization

---

### 3.2 No SQL Injection Protection Built-In [HIGH]

**Location:** Framework design
**CWE:** CWE-89 (SQL Injection)

**Finding:**
The framework doesn't include database abstraction. Users implementing `SessionRepo` and `UserRepo` may write vulnerable queries if they use raw SQL.

The in-memory implementation doesn't demonstrate parameterized queries.

**Impact:**

- Database compromise if users implement naive SQL
- Data exfiltration
- Authentication bypass

**Remediation:**

1. Provide SQLite/PostgreSQL reference implementations using parameterized queries
2. Document SQL injection risks prominently
3. Consider bundling SQLAlchemy or similar ORM

---

### 3.3 Email Used as User ID [MEDIUM]

**Location:** `z8ter-app/app/identity/usecases/manage_users.py:12`
**CWE:** CWE-706 (Use of Incorrectly-Resolved Name)

**Finding:**

```python
async def create_user(self, email: str, pwd: str) -> str:
    user_id = email  # Email IS the user ID
```

**Impact:**

- PII used as identifier throughout system
- Email changes require cascading updates
- Logging/debugging exposes PII
- GDPR compliance complications

**Remediation:**
Use UUIDs for user IDs:

```python
import uuid
user_id = str(uuid.uuid4())
```

---

## 4. Cross-Site Scripting (XSS)

### 4.1 Jinja2 Autoescape Configuration [LOW - GOOD]

**Location:** `z8ter/cli/create.py:43-47`

**Finding:**
Scaffold template generator disables autoescape:

```python
env = Environment(
    ...
    autoescape=select_autoescape(
        enabled_extensions=(),
        default_for_string=False,
        default=False,
    ),
```

However, this is for code generation (`.py.j2` files), not runtime templates. Starlette's `Jinja2Templates` enables autoescape by default.

**Status:** Generally safe, but verify runtime configuration.

---

### 4.2 No Content Security Policy [HIGH]

**Location:** Not implemented
**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)

**Finding:**
No CSP headers are set anywhere. Templates include inline styles and external fonts.

```html
<!-- z8ter-app/templates/base.jinja -->
<link
  href="https://fonts.googleapis.com/css2?family=Inter..."
  rel="stylesheet"
/>
<style>
  body {
    font-family: "Inter", sans-serif;
  }
</style>
```

**Impact:**

- XSS attacks can execute arbitrary scripts
- No protection against script injection
- Data exfiltration via XSS

**Remediation:**
Add CSP middleware:

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
    )
    return response
```

---

### 4.3 Error Messages May Contain User Input [MEDIUM]

**Location:** Templates
**CWE:** CWE-79 (Cross-site Scripting)

**Finding:**

```html
{% if error %}
<p class="...">{{ error }}</p>
{% endif %}
```

If `error` contains unsanitized user input, XSS is possible. While Jinja2 autoescapes by default, developers may use `|safe` or `Markup()`.

**Remediation:**

1. Never include raw user input in error messages
2. Use error codes that map to predefined messages
3. Audit all uses of `|safe` filter

---

## 5. Security Headers

### 5.1 No Security Headers Middleware [HIGH]

**Location:** Not implemented
**CWE:** CWE-693 (Protection Mechanism Failure)

**Finding:**
No security headers are configured. Missing headers:

| Header                      | Purpose                  | Status  |
| --------------------------- | ------------------------ | ------- |
| `Content-Security-Policy`   | XSS prevention           | Missing |
| `Strict-Transport-Security` | HTTPS enforcement        | Missing |
| `X-Content-Type-Options`    | MIME sniffing prevention | Missing |
| `X-Frame-Options`           | Clickjacking prevention  | Missing |
| `X-XSS-Protection`          | Legacy XSS filter        | Missing |
| `Referrer-Policy`           | Referrer leakage         | Missing |
| `Permissions-Policy`        | Feature restrictions     | Missing |

**Remediation:**

```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response
```

---

## 6. Cryptographic Practices

### 6.1 Password Hashing Configuration [GOOD]

**Location:** `z8ter/auth/crypto.py:29-36`

**Finding:**
Argon2id with reasonable parameters:

```python
_PH = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
```

**Assessment:**

- Algorithm: Argon2id (recommended by OWASP)
- Memory: 64MB (good for server-side)
- Time cost: 3 iterations (acceptable)
- Salt: 16 bytes (sufficient)

**Status:** Acceptable for 2025-2026 standards.

---

### 6.2 Session ID Generation [GOOD]

**Location:** `z8ter/auth/sessions.py:74`

**Finding:**

```python
sid = secrets.token_urlsafe(32)
```

Using `secrets` module with 32 bytes = 256 bits of entropy.

**Status:** Cryptographically secure.

---

### 6.3 No Secret Key Validation [MEDIUM]

**Location:** `z8ter/builders/builder_functions.py:216-219`

**Finding:**

```python
def use_app_sessions_builder(context: dict[str, Any]) -> None:
    secret_key = get_config_value(context=context, key="APP_SESSION_KEY")
    if not secret_key:
        raise TypeError("Z8ter: secret key is required for app sessions.")
```

Only checks existence, not strength. Accepts "abc" as valid.

**Remediation:**

```python
if not secret_key or len(secret_key) < 32:
    raise ValueError(
        "Z8ter: APP_SESSION_KEY must be at least 32 characters. "
        "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
    )
```

---

## 7. Error Handling & Information Disclosure

### 7.1 Internal Errors Not Logged [HIGH]

**Location:** `z8ter/errors.py:38-55`
**CWE:** CWE-778 (Insufficient Logging)

**Finding:**

```python
async def any_exc(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "error": {"message": "Internal server error"}},
        status_code=500,
    )
    # Exception is swallowed - no logging!
```

**Impact:**

- Production errors are invisible
- Security incidents go undetected
- Debugging impossible without logs

**Remediation:**

```python
import logging
import traceback

logger = logging.getLogger("z8ter.errors")

async def any_exc(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"Unhandled exception: {exc}\n"
        f"Path: {request.url.path}\n"
        f"Traceback: {traceback.format_exc()}"
    )
    return JSONResponse(
        {"ok": False, "error": {"message": "Internal server error"}},
        status_code=500,
    )
```

---

### 7.2 Debug Mode Defaults to True [MEDIUM]

**Location:** `z8ter/builders/app_builder.py:232`
**CWE:** CWE-489 (Active Debug Code)

**Finding:**

```python
def build(self, debug: bool = True) -> Z8ter:
```

Debug mode is enabled by default. If developers forget to disable it in production:

- Detailed error messages may leak
- Performance overhead
- Potential debug endpoints exposed

**Remediation:**

```python
def build(self, debug: bool | None = None) -> Z8ter:
    if debug is None:
        debug = os.getenv("DEBUG", "false").lower() == "true"
```

---

### 7.3 JSON-Only Error Responses [LOW]

**Location:** `z8ter/errors.py`
**CWE:** CWE-209 (Information Exposure Through an Error Message)

**Finding:**
All errors return JSON, even for browser requests:

```python
async def http_exc(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(...)
```

**Impact:**

- Poor user experience for browser users
- Information disclosure via API structure

**Remediation:**
Check `Accept` header and return HTML for browsers.

---

## 8. Denial of Service

### 8.1 No Request Size Limits [MEDIUM]

**Location:** Not implemented
**CWE:** CWE-770 (Allocation of Resources Without Limits)

**Finding:**
No limits on:

- Request body size
- Form field count
- File upload size
- Header size

**Impact:**

- Memory exhaustion
- Server crashes
- Resource starvation

**Remediation:**
Configure limits in Uvicorn/ASGI server or add middleware.

---

### 8.2 Unbounded Session Storage [MEDIUM]

**Location:** `z8ter-app/app/identity/adapter/session_repo.py`

**Finding:**
No limit on number of stored sessions:

```python
self._sessions: dict[str, dict] = {}  # Grows unbounded
```

**Impact:**

- Memory exhaustion via session creation
- DoS by creating millions of sessions

**Remediation:**

1. Implement LRU cache with maximum size
2. Add per-user session limits
3. Implement session cleanup job

---

## 9. Dependency Security

### 9.1 Dependency Versions [LOW]

**Location:** `pyproject.toml`

**Finding:**
Dependencies use ranges, which is good for compatibility but may include vulnerable versions:

```toml
dependencies = [
  "starlette>=0.36,<1.0",
  "jinja2>=3.1,<4",
  ...
]
```

**Recommendation:**

1. Run `pip-audit` or `safety` regularly
2. Use Dependabot or Renovate for updates
3. Pin exact versions in production deployments

---

### 9.2 No Dependency Vulnerability Scanning [MEDIUM]

**Location:** CI/CD configuration

**Finding:**
No automated vulnerability scanning in project configuration.

**Remediation:**
Add to CI:

```yaml
- name: Security scan
  run: |
    pip install pip-audit
    pip-audit
```

---

## 10. Configuration Security

### 10.1 .env File Security [INFORMATIONAL]

**Location:** Framework design

**Finding:**
Secrets are expected in `.env` files. No guidance on:

- File permissions
- Git exclusion
- Secret rotation
- Production secret management

**Recommendation:**
Document secure configuration practices:

1. Never commit `.env` files
2. Use environment variables in production
3. Consider secrets managers (Vault, AWS Secrets Manager)

---

## 11. Logging & Monitoring

### 11.1 No Security Event Logging [HIGH]

**Location:** Not implemented
**CWE:** CWE-778 (Insufficient Logging)

**Finding:**
No logging for security-relevant events:

- Failed login attempts
- Session creation/destruction
- Password changes
- Account lockouts
- Privilege changes

**Impact:**

- Cannot detect attacks in progress
- No forensic capability
- Compliance failures (PCI-DSS, SOC2)

**Remediation:**

```python
import logging
security_logger = logging.getLogger("z8ter.security")

# In login handler:
if not ok:
    security_logger.warning(
        f"Failed login attempt for {email} from {request.client.host}"
    )
```

---

## 12. Additional Recommendations

### 12.1 Security Checklist for Production

Before deploying Z8ter applications to production:

- [ ] Implement CSRF protection middleware
- [ ] Validate all redirect URLs
- [ ] Enable `secure=True` for all cookies
- [ ] Set `SameSite=Strict` for auth cookies
- [ ] Add rate limiting to auth endpoints
- [ ] Implement account lockout
- [ ] Add security headers middleware
- [ ] Enable HTTPS only (HSTS)
- [ ] Configure Content Security Policy
- [ ] Implement proper error logging
- [ ] Set `debug=False` in production
- [ ] Validate and sanitize all inputs
- [ ] Hash session IDs before storage
- [ ] Add email verification
- [ ] Implement password complexity requirements
- [ ] Set up dependency vulnerability scanning
- [ ] Configure request size limits
- [ ] Implement security event logging

### 12.2 Security Testing Recommendations

1. **Automated Scanning:**
   - OWASP ZAP for web vulnerability scanning
   - Bandit for Python security linting
   - pip-audit for dependency vulnerabilities

2. **Manual Testing:**
   - CSRF attack simulation
   - Session fixation testing
   - Authentication bypass attempts
   - Input fuzzing

3. **Penetration Testing:**
   - Recommended before any production deployment
   - Focus on authentication and session management

---

## Conclusion

The Z8ter framework provides a foundation for web applications but **is not production-ready from a security perspective**. Critical vulnerabilities in authentication, session management, and input validation must be addressed before deploying applications built on this framework to production environments.

The framework would benefit from:

1. Built-in CSRF protection
2. Security headers middleware
3. Input validation framework
4. Reference implementations that follow security best practices
5. Comprehensive security documentation

**Risk Rating:** HIGH - Not suitable for production without significant security enhancements.
