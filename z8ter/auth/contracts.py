"""Auth contracts (lightweight protocols) for Z8ter.

This module defines the minimal interfaces an application must implement to plug
into Z8ter's authentication/session features. The framework depends only on these
protocols; you are free to back them with SQLite/Postgres/Redis/memory/etc.

Design goals:
- Keep the surface tiny and explicit (insert/revoke/lookup).
- Make expiry/validity decisions inside the repository, not the caller.
- Avoid leaking storage details (hashing, revocation tables) to the framework.

Security notes:
- `sid_plain` is the *plaintext* session identifier at the boundary. Implementors
  should NEVER persist `sid_plain` directly. Store a keyed hash (e.g., HMAC-SHA256
  with a server-side secret) or a slow hash (PBKDF2/argon2) depending on threat model.
- Treat `expires_at` as an absolute UTC timestamp (tz-aware) and enforce it on reads.
- Consider recording `ip` and `user_agent` for anomaly detection and session UX.
  Do not treat them as strong identity signals (users roam/proxy).

Error/behavior contracts:
- `insert(...)` should create a *new* active session record. If `rotated_from_sid`
  is provided, revoke the old session in a single atomic transaction when possible
  (rotation invariant: at most one active session lineage per cookie).
- `revoke(...)` should be idempotent — return True if a matching, currently-active
  session was revoked; False if it did not exist or was already revoked/expired.
- `get_user_id(...)` should return None for unknown, revoked, or *expired* sessions.

Performance:
- Lookups (`get_user_id`) are on the hot path. Index by hashed SID, and (optionally)
  keep a short-lived in-memory cache if your store is remote.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SessionRepo(Protocol):
    """Persistence contract for session lifecycle.

    Implementations are responsible for:
      - Persisting a *hashed* form of the plaintext SID (`sid_plain`).
      - Enforcing expiry and revocation on read.
      - (Optionally) recording basic telemetry for security/UX.

    All methods MUST be safe to call from async request handlers. If your storage
    client is blocking, offload to a threadpool or use an async driver.

    Notes on rotation:
      - When `rotated_from_sid` is provided to `insert`, revoke the referenced
        session atomically to prevent dual-active cookies during rotation.
    """

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
        """Create a new session record.

        Args:
            sid_plain: Plaintext session ID at the boundary. IMPLEMENTORS MUST hash
                before persisting (e.g., HMAC(secret, sid_plain)).
            user_id: Application-level user identifier to associate with the session.
            expires_at: Absolute expiry (UTC, tz-aware). Expired sessions are invalid.
            remember: True if the cookie was issued with a long-lived lifetime
                (“remember me”). Useful for analytics or separate expiry windows.
            ip: Best-effort client IP at issuance time (may be None/unreliable).
            user_agent: Best-effort user agent string at issuance time (optional).
            rotated_from_sid: If provided, revoke this prior session as part of an
                atomic rotation (prevents two valid cookies during renewal).

        Returns:
            None. Raise a storage-specific exception if insertion fails.

        Required behavior:
            - Must be idempotent only with respect to unique SID. A duplicate SID
              should raise an integrity error rather than silently overwrite.
            - If `rotated_from_sid` is provided and found active, revoke it atomically.

        Security:
            - Never persist `sid_plain` verbatim.
            - Consider salting/HMAC to avoid rainbow attacks if your DB leaks.

        """
        ...

    def revoke(self, *, sid_plain: str) -> bool:
        """Revoke an active session if it exists.

        Args:
            sid_plain: Plaintext SID presented by the client.

        Returns:
            True if an active session matching this SID was found and revoked.
            False if no active session existed (unknown, already revoked, or expired).

        Idempotency:
            - Repeated calls with the same SID after a successful revoke return False.

        """
        ...

    def get_user_id(self, sid_plain: str) -> str | None:
        """Resolve a valid session to a user id.

        Args:
            sid_plain: Plaintext SID presented by the client.

        Returns:
            The associated `user_id` if the session exists, is not revoked, and
            is not expired at the time of lookup; otherwise None.

        MUST:
            - Enforce expiry (`expires_at <= now`) by returning None.
            - Enforce revocation status by returning None.
            - Perform lookup by *hashed* SID (never use plaintext as a key at rest).

        """
        ...

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all active sessions for a given user.

        Used when a user changes their password or explicitly logs out of all
        sessions. This ensures that compromised sessions are invalidated.

        Args:
            user_id: The user identifier whose sessions should be revoked.

        Returns:
            The number of sessions that were revoked.

        Security:
            - This should be called when a user changes their password.
            - Consider also calling on account lockout or security incidents.
            - Implementation should be atomic if possible.

        """
        ...

    def cleanup_expired(self) -> int:
        """Remove expired and revoked sessions from storage.

        This is a maintenance method to prevent unbounded storage growth.
        Should be called periodically (e.g., via a background task or cron).

        Returns:
            The number of sessions removed.

        Implementation notes:
            - Safe to call frequently; should be idempotent.
            - For database-backed stores, consider batch deletion.
            - In-memory stores should call this to prevent memory leaks.

        """
        ...


class UserRepo(Protocol):
    """Read-only user lookup contract for auth flows.

    Minimal requirement so Z8ter can attach a user object to the request context.

    Method contracts:
      - `get_user_by_id(user_id)` returns a serializable mapping representing the user,
        or None if not found. The only strictly required field is a stable `"id"`.
        Common optional fields: `"email"`, `"name"`, `"avatar_url"`, `"roles"`.

    Security:
      - Do NOT include sensitive credentials or secrets (password hashes, MFA seeds).
      - If you include role/permission data, ensure it reflects current truth
        (stale caches can cause privilege drift).

    Performance:
      - This runs on most requests that need a user. Consider caching per-request
        or short-lived process caches keyed by user_id + version.
    """

    def get_user_by_id(self, user_id: str) -> dict | None:
        """Fetch a user model for the given identifier.

        Args:
            user_id: Stable application-level user identifier.

        Returns:
            A dict-like object with at least {"id": <user_id>} or None if missing.

        Shape guidance (non-binding):
            {
                "id": "u_123",
                "email": "user@example.com",
                "name": "Ada Lovelace",
                "roles": ["admin", "billing"],
                # …additional app-specific, non-sensitive fields
            }

        """
        ...
