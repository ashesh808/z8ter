"""Z8ter authentication package.

This package exposes the minimal public API for Z8ter's authentication layer:
session management, middleware that attaches the current user to requests, and
route guards for common auth flows.

Public modules:
- `contracts`: Protocols for pluggable repositories (`SessionRepo`, `UserRepo`).
- `crypto`: Password hashing helpers (`hash_password`, `verify_password`,
  `needs_rehash`) using Argon2id.
- `session`: High-level session management (`SessionManager`).
- `middleware`: Starlette middleware that resolves `request.state.user`.
- `guards`: Decorators for protecting routes (`login_required`,
  `skip_if_authenticated`).
- `tokens`: Signed, time-limited tokens for password reset and email
  verification (`TokenManager`).

Design notes:
- Storage is fully pluggable via `SessionRepo` and `UserRepo` implementations.
- Session IDs are random, opaque strings; repositories must hash at rest.
- The middleware relies on `request.state.user` for downstream access.
- Guards assume a `config` service providing `LOGIN_PATH` and `APP_PATH`.

Security:
- Always set auth cookies with `HttpOnly`, `Secure`, and `SameSite` flags.
- Validate any `?next=` redirect targets to avoid open-redirect attacks.
"""

from .contracts import SessionRepo, UserRepo
from .crypto import hash_password, needs_rehash, verify_password
from .guards import login_required, skip_if_authenticated
from .middleware import AuthSessionMiddleware
from .sessions import SessionManager
from .tokens import TokenManager

__all__ = [
    "SessionRepo",
    "UserRepo",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "SessionManager",
    "AuthSessionMiddleware",
    "login_required",
    "skip_if_authenticated",
    "TokenManager",
]
