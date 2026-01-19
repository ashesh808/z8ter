# Z8ter Framework - Issues Tracker

This document consolidates all identified issues from security reviews, code reviews, and feature gap analysis. Items are marked as completed or pending.

**Last Updated:** January 2026

---

## Summary

| Category              | Total | Completed | Pending |
| --------------------- | ----- | --------- | ------- |
| Security (Critical)   | 4     | 4         | 0       |
| Security (High)       | 7     | 7         | 0       |
| Security (Medium)     | 9     | 7         | 2       |
| Security (Low)        | 6     | 4         | 2       |
| Code Quality (High)   | 6     | 6         | 0       |
| Code Quality (Medium) | 15    | 15        | 0       |
| Code Quality (Low)    | 12    | 12        | 0       |
| Feature Gaps          | 12    | 5         | 7       |

---

## Security Issues

### Critical (All Completed)

- [x] **SEC-001: No CSRF Protection** - Forms had tokens but no validation
  - _Fixed:_ Created `z8ter/security/csrf.py` with CSRFMiddleware
  - _Builder:_ `app_builder.use_csrf()`

- [x] **SEC-002: Open Redirect Vulnerability** - `?next=` parameter unvalidated
  - _Fixed:_ Created `z8ter/security/redirect.py` with `is_safe_redirect_url()` and `get_safe_redirect_url()`
  - _Updated:_ `z8ter/auth/guards.py` to validate redirect URLs

- [x] **SEC-003: Session IDs Stored in Plaintext** - Violated documented contract
  - _Fixed:_ Updated `z8ter-app/app/identity/adapter/session_repo.py` with HMAC-SHA256 hashing
  - _Fixed:_ Created `z8ter/database/session_repo.py` with hashing built-in

- [x] **SEC-004: Insecure Cookie Configuration** - Hardcoded `secure=False`
  - _Fixed:_ Updated `z8ter-app/endpoints/views/login.py` to derive secure flag from request scheme

### High Priority (All Completed)

- [x] **SEC-005: No Rate Limiting on Auth** - Unlimited login attempts allowed
  - _Fixed:_ Created `z8ter/security/rate_limit.py` with RateLimitMiddleware
  - _Builder:_ `app_builder.use_rate_limiting()`

- [x] **SEC-006: No Duplicate Email Check** - Registration didn't check existing emails
  - _Fixed:_ Updated `z8ter-app/endpoints/views/register.py` with duplicate check
  - _Fixed:_ Added `email_exists()` to user repositories

- [x] **SEC-007: No Input Validation Framework** - No email/password validation
  - _Fixed:_ Created `z8ter/security/validators.py` with `validate_email()` and `validate_password()`

- [x] **SEC-008: No Security Headers** - Missing CSP, HSTS, X-Frame-Options
  - _Fixed:_ Created `z8ter/security/headers.py` with SecurityHeadersMiddleware
  - _Builder:_ `app_builder.use_security_headers()`

- [x] **SEC-009: Internal Errors Not Logged** - Exceptions swallowed silently
  - _Fixed:_ Updated `z8ter/errors.py` with comprehensive error logging including traceback

- [x] **SEC-010: No Security Event Logging** - Failed logins not tracked
  - _Fixed:_ Created `z8ter/security/audit.py` with `log_security_event()` and SecurityEvent enum

- [x] **SEC-011: No SQL Injection Protection** - No parameterized query examples
  - _Fixed:_ Created `z8ter/database/` module with parameterized queries throughout

### Medium Priority

- [x] **SEC-012: Timing Attack on User Enumeration** - Response time differs
  - _Fixed:_ Updated `z8ter-app/endpoints/views/login.py` with dummy hash verification

- [x] **SEC-013: Weak Password Policy** - Only checked non-empty
  - _Fixed:_ Added password validation with minimum 8 characters

- [x] **SEC-014: No Session Invalidation on Password Change** - Old sessions remained valid
  - _Fixed:_ Added `revoke_all_for_user()` to session repositories

- [x] **SEC-015: Session Fixation Potential** - Existing sessions not cleared on login
  - _Fixed:_ Updated login flow to revoke existing sessions

- [x] **SEC-016: Email Used as User ID** - PII used as identifier
  - _Fixed:_ Updated `z8ter-app/app/identity/usecases/manage_users.py` to use UUIDs

- [x] **SEC-017: No Secret Key Validation** - Accepted weak keys
  - _Fixed:_ Added 32-character minimum validation in `use_app_sessions_builder`

- [x] **SEC-018: Debug Mode Defaults to True** - Unsafe for production
  - _Fixed:_ Changed default to `False`, reads from `Z8TER_DEBUG` env var

- [ ] **SEC-019: No Email Verification** - Fake accounts can be created
  - _Status:_ Pending - Requires email infrastructure

- [ ] **SEC-020: No Dependency Vulnerability Scanning** - No automated CVE checks
  - _Status:_ Pending - Recommend adding pip-audit to CI

### Low Priority

- [x] **SEC-021: No Session Expiry Cleanup** - Expired sessions stayed in memory
  - _Fixed:_ Added `cleanup_expired()` to session repositories

- [x] **SEC-022: JSON-Only Error Responses** - Poor UX for browsers
  - _Fixed:_ Added content negotiation in `z8ter/errors.py` - returns HTML for browsers

- [x] **SEC-023: No Request Size Limits** - Potential DoS
  - _Fixed:_ Documented in deployment guide - configure in Uvicorn/nginx

- [x] **SEC-024: Unbounded Session Storage** - Memory exhaustion risk
  - _Fixed:_ Added `cleanup_expired()` and moved to SQLite by default

- [ ] **SEC-025: .env File Security Guidance** - No documentation
  - _Status:_ Pending - Add security documentation

- [ ] **SEC-026: Dependency Versions** - Using ranges, may include vulnerabilities
  - _Status:_ Informational - Monitor with Dependabot

---

## Code Quality Issues

### High Priority (All Completed)

- [x] **CODE-001: Async/Sync Mismatch in Sessions** - Methods declared async but called sync repos
  - _Fixed:_ Added `run_in_executor` in `z8ter/auth/sessions.py` and `middleware.py`

- [x] **CODE-002: Open Redirect in Guards** - `next` parameter not validated
  - _Fixed:_ Same as SEC-002

- [x] **CODE-003: Plaintext Session Storage** - Reference implementation violated contract
  - _Fixed:_ Same as SEC-003

- [x] **CODE-004: Insecure Cookie Hardcoding** - `secure=False` hardcoded
  - _Fixed:_ Same as SEC-004

- [x] **CODE-005: No Error Handling for Repo Failures** - Exceptions crashed requests
  - _Fixed:_ Added try/except with logging in `z8ter/auth/middleware.py`

- [x] **CODE-006: No Duplicate Email Check** - Registration could overwrite
  - _Fixed:_ Same as SEC-006

### Medium Priority (All Completed)

- [x] **CODE-007: Global Mutable State with Caching** - Race conditions possible
  - _Fixed:_ Changed to `threading.RLock()` in `z8ter/__init__.py`

- [x] **CODE-008: Silent Exception Swallowing in Crypto** - Caught all exceptions
  - _Fixed:_ Changed to catch specific `VerifyMismatchError` and `InvalidHashError`

- [x] **CODE-009: Empty Lifespan Handler** - Caught exceptions but did nothing
  - _Fixed:_ Added logging to lifespan handler

- [x] **CODE-010: Debug Mode Default** - Unsafe default
  - _Fixed:_ Same as SEC-018

- [x] **CODE-011: Context Mutation Side Effect** - Step kwargs leaked between steps
  - _Fixed:_ Updated context handling to isolate kwargs per step

- [x] **CODE-012: Unsafe Config Injection** - Direct attribute assignment
  - _Fixed:_ Changed to use `set_config()` method pattern only

- [x] **CODE-013: No Secret Key Strength Validation** - Accepted weak keys
  - _Fixed:_ Same as SEC-017

- [x] **CODE-014: Hardcoded App Factory Path** - Non-standard projects failed
  - _Fixed:_ Made configurable via `Z8TER_APP_FACTORY` env var

- [x] **CODE-015: Legacy Quirk Without Migration** - Trimmed "endpoints" prefix
  - _Fixed:_ Added documentation explaining the behavior

- [x] **CODE-016: Single Instance for All Routes** - State could leak between requests
  - _Fixed:_ Added prominent documentation warning

- [x] **CODE-017: Silent Content Loading Failure** - Missing content only logged warning
  - _Fixed:_ Fixed typo, added warning for multiple content files

- [x] **CODE-018: No Dev Server Fallback** - Pages failed if Vite not running
  - _Fixed:_ Added `VITE_ALWAYS_RELOAD_MANIFEST` option and better error messages

- [x] **CODE-019: Manifest Cache Issues** - mtime-based caching could fail
  - _Fixed:_ Added file size check for more reliable invalidation

- [x] **CODE-020: Direct Config State Mutation** - Relied on Starlette internals
  - _Fixed:_ Created `Z8terConfig` wrapper class

- [x] **CODE-021: JSON-Only Error Responses** - Bad UX for browsers
  - _Fixed:_ Same as SEC-022

### Low Priority (All Completed)

- [x] **CODE-022: Emoji in Logging** - May not render in all terminals
  - _Fixed:_ Removed emojis from logging messages

- [x] **CODE-023: Docstring Mismatch in core.py** - Wrong description for state property
  - _Fixed:_ Updated docstring

- [x] **CODE-024: Mode Not Used After Validation** - Stored but never used
  - _Fixed:_ Added `is_dev`, `is_prod`, `is_test` properties

- [x] **CODE-025: Variable Shadows Builtin** - `files` variable in create.py
  - _Fixed:_ Renamed to `file_mappings`

- [x] **CODE-026: Overwrites Without Warning** - Files silently overwritten
  - _Fixed:_ Added existence check with logging

- [x] **CODE-027: Simple Capitalize Fails for Multi-Word** - PascalCase incorrect
  - _Fixed:_ Added `_to_pascal_case()` function

- [x] **CODE-028: Unusual **init** Pattern in View** - Allowed invalid instances
  - _Fixed:_ Added documentation explaining testing use case

- [x] **CODE-029: Extra Parenthesis in Log Message** - Typo in helpers.py
  - _Fixed:_ Removed extra parenthesis

- [x] **CODE-030: Last Match Wins Silently** - Multiple content files not warned
  - _Fixed:_ Added warning when multiple content files found

- [x] **CODE-031: Starlette Deprecation Warnings** - Using deprecated patterns
  - _Fixed:_ Updated tests to use new Route API and cookie patterns

- [x] **CODE-032: TemplateResponse Deprecated Pattern** - Old parameter order
  - _Fixed:_ Updated `render()` to use new API

- [x] **CODE-033: Thread-Safety in Caching** - Potential race conditions
  - _Fixed:_ Added proper locking with RLock

---

## Feature Gaps

### Completed

- [x] **FEAT-001: No Database Integration** - Only in-memory repositories
  - _Fixed:_ Created `z8ter/database/` module with:
    - `Database` connection manager
    - `SQLiteSessionRepo` implementation
    - `SQLiteUserRepo` implementation
    - `init_database()` for table creation

- [x] **FEAT-002: No Dockerfile or Deployment Config** - Manual deployment required
  - _Fixed:_ Added to scaffold template:
    - `Dockerfile` (multi-stage production build)
    - `docker-compose.yml` (local development)
    - `.dockerignore`
    - Health check endpoint (`/health`)

- [x] **FEAT-003: No Security Baseline** - Missing middleware
  - _Fixed:_ Created `z8ter/security/` package with:
    - CSRF middleware
    - Rate limiting middleware
    - Security headers middleware
    - Input validators
    - Audit logging

- [x] **FEAT-004: CLI Lacks Database Commands** - No migration tools
  - _Fixed:_ Added CLI commands:
    - `z8 db init` - Initialize database
    - `z8 db status` - Show database info
    - `z8 db reset` - Reset database

- [x] **FEAT-005: Documentation Gaps** - README incomplete
  - _Fixed:_ Comprehensive README update with:
    - Database documentation
    - Security middleware documentation
    - Deployment guide
    - Configuration reference
    - CLI command reference

### Pending

- [ ] **FEAT-006: No Payment/Stripe Integration** - Empty billing module
  - _Status:_ Pending
  - _Needed:_
    - Stripe SDK integration
    - Webhook endpoint
    - Subscription management
    - Customer portal redirect

- [ ] **FEAT-007: No Email/Transactional Email Support** - No email functionality
  - _Status:_ Pending
  - _Needed:_
    - Email service abstraction
    - SMTP/SendGrid/Resend providers
    - Email templates (welcome, password reset, etc.)
    - Async sending

- [ ] **FEAT-008: Incomplete Authentication** - No OAuth or password recovery
  - _Status:_ Pending
  - _Needed:_
    - Google OAuth
    - Password reset flow
    - Email verification
    - Account lockout

- [ ] **FEAT-009: No Admin Portal** - No admin functionality
  - _Status:_ Pending
  - _Needed:_
    - Protected `/admin` routes
    - User management
    - Subscription management
    - Basic analytics

- [ ] **FEAT-010: Landing Page Needs SaaS Focus** - Generic template
  - _Status:_ Pending
  - _Needed:_
    - Pricing table component
    - Feature cards
    - Testimonials section
    - Legal page templates

- [ ] **FEAT-011: No Background Task Support** - No task queue
  - _Status:_ Pending
  - _Needed:_
    - Simple asyncio task system
    - Optional Celery/RQ integration
    - Scheduled tasks

- [ ] **FEAT-012: Testing Infrastructure Missing** - No test utilities
  - _Status:_ Pending
  - _Needed:_
    - Test client setup guide
    - Pytest fixtures
    - Mock services
    - Example tests in scaffold

---

## Files Created/Modified

### New Files Created

```
z8ter/security/
├── __init__.py
├── csrf.py
├── redirect.py
├── rate_limit.py
├── headers.py
├── validators.py
└── audit.py

z8ter/database/
├── __init__.py
├── connection.py
├── init.py
├── session_repo.py
└── user_repo.py

z8ter/cli/database.py

z8ter/scaffold/create_project_template/
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

### Modified Files

- `z8ter/__init__.py` - Thread-safe caching with RLock
- `z8ter/core.py` - Removed emojis, added mode properties
- `z8ter/errors.py` - Error logging, content negotiation
- `z8ter/config.py` - Z8terConfig wrapper class
- `z8ter/vite.py` - Cache invalidation improvements
- `z8ter/auth/sessions.py` - Async/sync handling
- `z8ter/auth/middleware.py` - Error handling, executor
- `z8ter/auth/guards.py` - Safe redirect validation
- `z8ter/auth/crypto.py` - Specific exception handling
- `z8ter/auth/contracts.py` - Added cleanup_expired, revoke_all_for_user
- `z8ter/builders/app_builder.py` - Health check, context fixes
- `z8ter/builders/builder_functions.py` - Security builders, health check
- `z8ter/endpoints/helpers.py` - TemplateResponse fix, content warnings
- `z8ter/endpoints/view.py` - CSRF token injection
- `z8ter/endpoints/api.py` - Documentation updates
- `z8ter/cli/main.py` - Database commands
- `z8ter/cli/create.py` - PascalCase, overwrite warnings
- `z8ter/cli/run_server.py` - Configurable factory
- `z8ter-app/` - Various security and code quality fixes
- `README.md` - Comprehensive documentation update
- Test files - Updated for deprecation warnings

---

## Version History

| Version | Date     | Changes                                                 |
| ------- | -------- | ------------------------------------------------------- |
| 0.2.6   | Jan 2026 | Security fixes, database integration, deployment config |

---

## Contributing

When working on issues:

1. Reference the issue ID (e.g., SEC-001, CODE-015, FEAT-006)
2. Update this document when completing an issue
3. Add tests for any security-related fixes
4. Update README if adding new features
