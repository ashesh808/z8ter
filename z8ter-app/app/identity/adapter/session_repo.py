from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional


class InMemorySessionRepo:
    """In-memory session repository with secure session ID storage.

    Security:
        - Session IDs are hashed using HMAC-SHA256 before storage
        - Plaintext session IDs are never persisted
        - A secret key is required for hashing

    Args:
        secret_key: Server-side secret for HMAC hashing. Required.
    """

    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValueError("secret_key is required for session security")
        self._secret_key = secret_key
        self._sessions: dict[str, dict] = {}

    def _hash_sid(self, sid_plain: str) -> str:
        """Hash a session ID using HMAC-SHA256.

        Args:
            sid_plain: Plaintext session ID

        Returns:
            Hexadecimal hash of the session ID
        """
        return hmac.new(
            self._secret_key.encode(),
            sid_plain.encode(),
            hashlib.sha256,
        ).hexdigest()

    def insert(
        self,
        *,
        sid_plain: str,
        user_id: str,
        expires_at: datetime,
        remember: bool,
        ip: Optional[str],
        user_agent: Optional[str],
        rotated_from_sid: Optional[str] = None,
    ) -> None:
        """Insert a new session, storing only the hashed session ID."""
        hashed_sid = self._hash_sid(sid_plain)

        # Revoke old session if rotating
        if rotated_from_sid:
            self.revoke(sid_plain=rotated_from_sid)

        self._sessions[hashed_sid] = {
            "user_id": user_id,
            "expires_at": expires_at,
            "remember": remember,
            "ip": ip,
            "user_agent": user_agent,
            "revoked_at": None,
        }

    def revoke(self, *, sid_plain: str) -> bool:
        """Revoke a session by its plaintext ID."""
        hashed_sid = self._hash_sid(sid_plain)
        session = self._sessions.get(hashed_sid)
        if not session:
            return False
        if session["revoked_at"] is not None:
            return False
        session["revoked_at"] = datetime.now(timezone.utc)
        return True

    def get_user_id(self, sid_plain: str) -> Optional[str]:
        """Get user ID for a valid session."""
        hashed_sid = self._hash_sid(sid_plain)
        session = self._sessions.get(hashed_sid)
        if not session:
            return None
        if session["revoked_at"] is not None:
            return None
        if session["expires_at"] <= datetime.now(timezone.utc):
            return None
        return session["user_id"]

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all active sessions for a given user.

        Used when a user changes their password or logs out of all sessions.

        Args:
            user_id: The user identifier whose sessions should be revoked

        Returns:
            Number of sessions that were revoked
        """
        now = datetime.now(timezone.utc)
        revoked_count = 0

        for session in self._sessions.values():
            if session["user_id"] == user_id and session["revoked_at"] is None:
                session["revoked_at"] = now
                revoked_count += 1

        return revoked_count

    def cleanup_expired(self) -> int:
        """Remove expired and revoked sessions from memory.

        This prevents unbounded memory growth in long-running applications.
        Should be called periodically (e.g., via a background task or cron job).

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc)
        to_remove = []

        for hashed_sid, session in self._sessions.items():
            # Remove if expired or revoked
            is_expired = session["expires_at"] <= now
            is_revoked = session["revoked_at"] is not None
            if is_expired or is_revoked:
                to_remove.append(hashed_sid)

        for hashed_sid in to_remove:
            del self._sessions[hashed_sid]

        return len(to_remove)

    def active_session_count(self) -> int:
        """Return the count of active (non-expired, non-revoked) sessions.

        Useful for monitoring and debugging.

        Returns:
            Number of currently active sessions
        """
        now = datetime.now(timezone.utc)
        count = 0

        for session in self._sessions.values():
            is_active = (
                session["expires_at"] > now and session["revoked_at"] is None
            )
            if is_active:
                count += 1

        return count
