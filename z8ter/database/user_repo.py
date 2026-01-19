"""SQLite-based user repository.

Implements user storage with SQLite persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from z8ter.database.connection import Database


class SQLiteUserRepo:
    """SQLite-backed user repository.

    Provides user CRUD operations with SQLite persistence.

    Args:
        db: Database instance

    Example:
        db = Database()
        repo = SQLiteUserRepo(db)
        user = repo.create_user(
            email="user@example.com",
            password_hash="hashed-password",
            name="John Doe",
        )
    """

    def __init__(self, db: Database) -> None:
        """Initialize user repository.

        Args:
            db: Database instance
        """
        self._db = db

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None = None,
    ) -> dict:
        """Create a new user.

        Args:
            email: User email (must be unique)
            password_hash: Pre-hashed password (use z8ter.auth.crypto)
            name: User display name (optional)

        Returns:
            Created user as dict

        Raises:
            sqlite3.IntegrityError: If email already exists
        """
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        self._db.execute(
            """
            INSERT INTO users (id, email, password_hash, name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, email.lower(), password_hash, name, now, now),
        )

        return {
            "id": user_id,
            "email": email.lower(),
            "name": name,
            "is_active": True,
            "is_verified": False,
            "created_at": now,
        }

    def get_user_by_id(self, user_id: str) -> dict | None:
        """Fetch user by ID.

        Args:
            user_id: User identifier

        Returns:
            User dict or None if not found
        """
        row = self._db.fetchone(
            """
            SELECT id, email, name, is_active, is_verified, created_at
            FROM users WHERE id = ?
            """,
            (user_id,),
        )
        if not row:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "is_active": bool(row["is_active"]),
            "is_verified": bool(row["is_verified"]),
            "created_at": row["created_at"],
        }

    def get_user_by_email(self, email: str) -> dict | None:
        """Fetch user by email address.

        Args:
            email: User email

        Returns:
            User dict (including password_hash) or None if not found
        """
        row = self._db.fetchone(
            """
            SELECT id, email, password_hash, name, is_active, is_verified, created_at
            FROM users WHERE email = ?
            """,
            (email.lower(),),
        )
        if not row:
            return None

        return {
            "id": row["id"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "name": row["name"],
            "is_active": bool(row["is_active"]),
            "is_verified": bool(row["is_verified"]),
            "created_at": row["created_at"],
        }

    def email_exists(self, email: str) -> bool:
        """Check if email is already registered.

        Args:
            email: Email to check

        Returns:
            True if email exists, False otherwise
        """
        row = self._db.fetchone(
            "SELECT 1 FROM users WHERE email = ?",
            (email.lower(),),
        )
        return row is not None

    def update_user(
        self,
        user_id: str,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        is_verified: bool | None = None,
    ) -> bool:
        """Update user fields.

        Args:
            user_id: User identifier
            name: New display name
            is_active: Account active status
            is_verified: Email verification status

        Returns:
            True if user was updated, False if not found
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
        if is_verified is not None:
            updates.append("is_verified = ?")
            params.append(1 if is_verified else 0)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(user_id)

        with self._db.connection() as conn:
            cursor = conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            return cursor.rowcount > 0

    def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user password.

        Args:
            user_id: User identifier
            password_hash: New hashed password

        Returns:
            True if password was updated, False if user not found
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._db.connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, now, user_id),
            )
            return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """Delete a user and their sessions.

        Args:
            user_id: User identifier

        Returns:
            True if user was deleted, False if not found
        """
        with self._db.connection() as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    def list_users(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False,
    ) -> list[dict]:
        """List users with pagination.

        Args:
            limit: Maximum users to return
            offset: Number of users to skip
            active_only: Only return active users

        Returns:
            List of user dicts
        """
        query = """
            SELECT id, email, name, is_active, is_verified, created_at
            FROM users
        """
        params: list = []

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._db.fetchall(query, tuple(params))
        return [
            {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "is_active": bool(row["is_active"]),
                "is_verified": bool(row["is_verified"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def count_users(self, active_only: bool = False) -> int:
        """Count total users.

        Args:
            active_only: Only count active users

        Returns:
            Number of users
        """
        query = "SELECT COUNT(*) as count FROM users"
        if active_only:
            query += " WHERE is_active = 1"

        row = self._db.fetchone(query)
        return row["count"] if row else 0
