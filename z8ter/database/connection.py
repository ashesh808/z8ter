"""Database connection manager for Z8ter.

Provides a simple SQLite connection wrapper that:
- Creates database file and directories automatically
- Supports connection pooling for concurrent access
- Configures WAL mode for better concurrent performance
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse


class Database:
    """SQLite database connection manager.

    Thread-safe connection pool for SQLite databases.

    Args:
        url: Database URL (e.g., "sqlite:///data/app.db" or "sqlite:///:memory:")

    Example:
        db = Database("sqlite:///app.db")
        with db.connection() as conn:
            conn.execute("SELECT * FROM users")
    """

    def __init__(self, url: str | None = None) -> None:
        """Initialize database connection.

        Args:
            url: Database URL. Defaults to DATABASE_URL env var or sqlite:///data/app.db
        """
        self._url = url or os.getenv("DATABASE_URL", "sqlite:///data/app.db")
        self._db_path = self._parse_url(self._url)
        self._local = threading.local()
        self._ensure_directory()

    def _parse_url(self, url: str) -> str:
        """Parse database URL to extract file path.

        Args:
            url: Database URL (sqlite:///path/to/db.db)

        Returns:
            File path or ":memory:" for in-memory databases
        """
        if url == "sqlite:///:memory:" or url == ":memory:":
            return ":memory:"

        parsed = urlparse(url)
        if parsed.scheme != "sqlite":
            raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")

        # Handle sqlite:///path (absolute) and sqlite://./path (relative)
        path = parsed.path
        if path.startswith("//"):
            path = path[1:]  # Remove extra slash
        elif path.startswith("/"):
            pass  # Absolute path
        else:
            path = path  # Relative path

        return path or ":memory:"

    def _ensure_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0,
            )
            # Enable WAL mode for better concurrent performance
            conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")
            # Return rows as dictionaries
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection.

        Usage:
            with db.connection() as conn:
                conn.execute("SELECT * FROM users")

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            sqlite3.Cursor: Query cursor
        """
        with self.connection() as conn:
            return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

        Returns:
            sqlite3.Cursor: Query cursor
        """
        with self.connection() as conn:
            return conn.executemany(sql, params_list)

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute query and return single row.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Row or None if no results
        """
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute query and return all rows.

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of rows
        """
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @property
    def path(self) -> str:
        """Return the database file path."""
        return self._db_path
