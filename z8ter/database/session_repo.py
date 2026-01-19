"""SQLite-based session repository.

Implements the SessionRepo protocol with SQLite persistence.
Session IDs are hashed before storage for security.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from z8ter.database.connection import Database


class SQLiteSessionRepo:
    """SQLite-backed session repository.

    Security:
        - Session IDs are hashed using HMAC-SHA256 before storage
        - Plaintext session IDs are never persisted
        - Expired and revoked sessions are excluded from lookups

    Args:
        db: Database instance
        secret_key: Server-side secret for HMAC hashing

    Example:
        db = Database()
        repo = SQLiteSessionRepo(db, secret_key="your-secret-key")
        repo.insert(
            sid_plain="session-id",
            user_id="user-123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            remember=True,
            ip="127.0.0.1",
            user_agent="Mozilla/5.0",
        )
    """

    def __init__(self, db: Database, secret_key: str) -> None:
        """Initialize session repository.

        Args:
            db: Database instance
            secret_key: Server-side secret for HMAC hashing (required)

        Raises:
            ValueError: If secret_key is empty
        """
        if not secret_key:
            raise ValueError("secret_key is required for session security")
        self._db = db
        self._secret_key = secret_key

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
        ip: str | None,
        user_agent: str | None,
        rotated_from_sid: str | None = None,
    ) -> None:
        """Insert a new session, storing only the hashed session ID.

        Args:
            sid_plain: Plaintext session ID (will be hashed)
            user_id: User identifier
            expires_at: Session expiration time (UTC)
            remember: Whether this is a "remember me" session
            ip: Client IP address
            user_agent: Client user agent string
            rotated_from_sid: Previous session ID to revoke (for rotation)
        """
        hashed_sid = self._hash_sid(sid_plain)
        now = datetime.now(timezone.utc).isoformat()

        # Revoke old session if rotating
        if rotated_from_sid:
            self.revoke(sid_plain=rotated_from_sid)

        self._db.execute(
            """
            INSERT INTO sessions (sid_hash, user_id, expires_at, remember, ip, user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hashed_sid,
                user_id,
                expires_at.isoformat(),
                1 if remember else 0,
                ip,
                user_agent,
                now,
            ),
        )

    def revoke(self, *, sid_plain: str) -> bool:
        """Revoke a session by its plaintext ID.

        Args:
            sid_plain: Plaintext session ID

        Returns:
            True if session was found and revoked, False otherwise
        """
        hashed_sid = self._hash_sid(sid_plain)
        now = datetime.now(timezone.utc).isoformat()

        with self._db.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE sid_hash = ? AND revoked_at IS NULL
                """,
                (now, hashed_sid),
            )
            return cursor.rowcount > 0

    def get_user_id(self, sid_plain: str) -> str | None:
        """Get user ID for a valid session.

        Args:
            sid_plain: Plaintext session ID

        Returns:
            User ID if session is valid, None otherwise
        """
        hashed_sid = self._hash_sid(sid_plain)
        now = datetime.now(timezone.utc).isoformat()

        row = self._db.fetchone(
            """
            SELECT user_id FROM sessions
            WHERE sid_hash = ?
              AND revoked_at IS NULL
              AND expires_at > ?
            """,
            (hashed_sid, now),
        )
        return row["user_id"] if row else None

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all active sessions for a user.

        Used when a user changes their password or logs out everywhere.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions revoked
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._db.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (now, user_id),
            )
            return cursor.rowcount

    def cleanup_expired(self) -> int:
        """Remove expired and revoked sessions from storage.

        Should be called periodically to prevent table bloat.

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._db.connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM sessions
                WHERE revoked_at IS NOT NULL OR expires_at <= ?
                """,
                (now,),
            )
            return cursor.rowcount

    def active_session_count(self) -> int:
        """Return count of active sessions.

        Returns:
            Number of currently active sessions
        """
        now = datetime.now(timezone.utc).isoformat()

        row = self._db.fetchone(
            """
            SELECT COUNT(*) as count FROM sessions
            WHERE revoked_at IS NULL AND expires_at > ?
            """,
            (now,),
        )
        return row["count"] if row else 0
