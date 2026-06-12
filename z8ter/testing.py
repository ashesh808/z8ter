"""Testing utilities for Z8ter applications.

Drop-in fakes and helpers so app tests never need a database or mail
server:

- `InMemorySessionRepo`: full `SessionRepo` implementation (hashes SIDs,
  enforces expiry/revocation) backed by a dict.
- `InMemoryUserRepo`: full `UserRepo` implementation mirroring the
  `SQLiteUserRepo` surface (create/get/update/delete/list).
- `InMemoryEmailProvider`: re-exported from `z8ter.email` — assert on
  `provider.outbox` instead of sending real mail.
- `create_test_app()`: build a minimal Z8ter app with sane test defaults.

Example (pytest):

    from starlette.testclient import TestClient
    from z8ter.testing import InMemorySessionRepo, InMemoryUserRepo, create_test_app

    def test_login_flow():
        app = create_test_app(
            session_repo=InMemorySessionRepo(),
            user_repo=InMemoryUserRepo(),
        )
        client = TestClient(app.starlette_app)
        ...
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from z8ter.email.providers import InMemoryEmailProvider

__all__ = [
    "InMemorySessionRepo",
    "InMemoryUserRepo",
    "InMemoryEmailProvider",
    "create_test_app",
]


def _hash_sid(sid_plain: str) -> str:
    """Hash a plaintext SID for storage (honors the SessionRepo contract).

    SHA-256 is sufficient for tests; production stores should use a keyed
    hash (HMAC) as documented in `z8ter.auth.contracts`.
    """
    return hashlib.sha256(sid_plain.encode()).hexdigest()


@dataclass
class _SessionRecord:
    """Internal session row for `InMemorySessionRepo`."""

    user_id: str
    expires_at: datetime
    remember: bool
    ip: str | None
    user_agent: str | None
    revoked: bool = False


class InMemorySessionRepo:
    """Dict-backed `SessionRepo` for tests.

    Implements the full contract: SIDs are stored hashed, expiry and
    revocation are enforced on read, rotation revokes the prior session.

    Thread-safe so it also works under `TestClient`'s threadpool.
    """

    def __init__(self) -> None:
        """Initialize empty session storage."""
        self._sessions: dict[str, _SessionRecord] = {}
        self._lock = threading.Lock()

    def insert(
        self,
        *,
        sid_plain: str,
        user_id: str,
        expires_at: datetime,
        remember: bool,
        ip: str | None,
        user_agent: str | None,
        rotated_from_sid: str | None = None,
    ) -> None:
        """Create a session record; revoke the rotated-from session if given.

        Raises:
            ValueError: If the SID already exists (duplicate insert).

        """
        key = _hash_sid(sid_plain)
        with self._lock:
            if key in self._sessions:
                raise ValueError("Duplicate session id")
            if rotated_from_sid is not None:
                old = self._sessions.get(_hash_sid(rotated_from_sid))
                if old is not None:
                    old.revoked = True
            self._sessions[key] = _SessionRecord(
                user_id=user_id,
                expires_at=expires_at,
                remember=remember,
                ip=ip,
                user_agent=user_agent,
            )

    def revoke(self, *, sid_plain: str) -> bool:
        """Revoke an active session; return True if one was revoked."""
        key = _hash_sid(sid_plain)
        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._sessions.get(key)
            if record is None or record.revoked or record.expires_at <= now:
                return False
            record.revoked = True
            return True

    def get_user_id(self, sid_plain: str) -> str | None:
        """Resolve a valid (unexpired, unrevoked) session to its user id."""
        key = _hash_sid(sid_plain)
        now = datetime.now(timezone.utc)
        with self._lock:
            record = self._sessions.get(key)
            if record is None or record.revoked or record.expires_at <= now:
                return None
            return record.user_id

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke every active session belonging to a user."""
        now = datetime.now(timezone.utc)
        count = 0
        with self._lock:
            for record in self._sessions.values():
                if (
                    record.user_id == user_id
                    and not record.revoked
                    and record.expires_at > now
                ):
                    record.revoked = True
                    count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired and revoked sessions from storage."""
        now = datetime.now(timezone.utc)
        with self._lock:
            stale = [
                key
                for key, record in self._sessions.items()
                if record.revoked or record.expires_at <= now
            ]
            for key in stale:
                del self._sessions[key]
        return len(stale)

    def active_session_count(self) -> int:
        """Test helper: number of currently valid sessions."""
        now = datetime.now(timezone.utc)
        with self._lock:
            return sum(
                1
                for record in self._sessions.values()
                if not record.revoked and record.expires_at > now
            )


class InMemoryUserRepo:
    """Dict-backed `UserRepo` for tests, mirroring `SQLiteUserRepo`.

    Provides the same surface as the SQLite implementation (create_user,
    get_user_by_email, email_exists, update_password, ...) so application
    code can be exercised unchanged.
    """

    def __init__(self) -> None:
        """Initialize empty user storage."""
        self._users: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None = None,
    ) -> dict:
        """Create a user; raises ValueError on duplicate email."""
        with self._lock:
            if any(
                u["email"] == email.lower() for u in self._users.values()
            ):
                raise ValueError(f"Email already exists: {email}")
            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            self._users[user_id] = {
                "id": user_id,
                "email": email.lower(),
                "password_hash": password_hash,
                "name": name,
                "is_active": True,
                "is_verified": False,
                "created_at": now,
            }
        return self.get_user_by_id(user_id)  # type: ignore[return-value]

    def get_user_by_id(self, user_id: str) -> dict | None:
        """Fetch a user by id (without password hash)."""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return None
            public = dict(user)
        public.pop("password_hash", None)
        return public

    def get_user_by_email(self, email: str) -> dict | None:
        """Fetch a user by email (including password hash, as SQLite does)."""
        with self._lock:
            for user in self._users.values():
                if user["email"] == email.lower():
                    return dict(user)
        return None

    def email_exists(self, email: str) -> bool:
        """Return True if the email is already registered."""
        return self.get_user_by_email(email) is not None

    def update_user(
        self,
        user_id: str,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        is_verified: bool | None = None,
    ) -> bool:
        """Update user fields; return True if the user exists."""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            if name is not None:
                user["name"] = name
            if is_active is not None:
                user["is_active"] = is_active
            if is_verified is not None:
                user["is_verified"] = is_verified
            return True

    def update_password(self, user_id: str, password_hash: str) -> bool:
        """Replace a user's password hash; return True if user exists."""
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False
            user["password_hash"] = password_hash
            return True

    def delete_user(self, user_id: str) -> bool:
        """Delete a user; return True if one was removed."""
        with self._lock:
            return self._users.pop(user_id, None) is not None

    def list_users(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
    ) -> list[dict]:
        """List users (newest first) without password hashes."""
        with self._lock:
            users = list(self._users.values())
        if active_only:
            users = [u for u in users if u["is_active"]]
        users.sort(key=lambda u: u["created_at"], reverse=True)
        page = users[offset : offset + limit]
        return [
            {k: v for k, v in u.items() if k != "password_hash"}
            for u in page
        ]

    def count_users(self, active_only: bool = False) -> int:
        """Count users, optionally only active ones."""
        with self._lock:
            users = list(self._users.values())
        if active_only:
            return sum(1 for u in users if u["is_active"])
        return len(users)


def create_test_app(
    *,
    session_repo: object | None = None,
    user_repo: object | None = None,
    secret_key: str = "test-secret-key-0123456789abcdef0123456789",  # noqa: S107 - test fixture, not a credential
    use_errors: bool = True,
    debug: bool = True,
):
    """Build a minimal Z8ter app for tests.

    Args:
        session_repo: Optional `SessionRepo`; when provided together with
            `user_repo`, auth repos and authentication middleware are wired.
        user_repo: Optional `UserRepo` (see above).
        secret_key: App session secret (a fixed 40+ char test default).
        use_errors: Install the framework exception handlers.
        debug: Build the app in debug mode.

    Returns:
        A built `Z8ter` app. Wrap `app.starlette_app` in Starlette's
        `TestClient` to make requests.

    Notes:
        - Templating/Vite are NOT enabled (they require an app directory);
          point `z8ter.set_app_dir(...)` at a project and add
          `builder.use_templating()` yourself if a test needs pages.

    """
    from z8ter.builders.app_builder import AppBuilder

    builder = AppBuilder()
    builder.use_app_sessions(secret_key=secret_key)
    if use_errors:
        builder.use_errors()
    if session_repo is not None and user_repo is not None:
        builder.use_auth_repos(session_repo=session_repo, user_repo=user_repo)
        builder.use_authentication()
    return builder.build(debug=debug)
