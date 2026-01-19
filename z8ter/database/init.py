"""Database initialization and schema management.

Creates required tables for Z8ter applications:
- users: User accounts
- sessions: Authentication sessions
- migrations: Schema version tracking
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from z8ter.database.connection import Database

logger = logging.getLogger("z8ter.database")

# Schema version for migrations
SCHEMA_VERSION = 1

# Table definitions
TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            is_active INTEGER DEFAULT 1,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            sid_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            remember INTEGER DEFAULT 0,
            ip TEXT,
            user_agent TEXT,
            revoked_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """,
    "migrations": """
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """,
}

# Indexes for performance
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
]


def init_database(db: Database | None = None, url: str | None = None) -> Database:
    """Initialize database with required tables.

    Creates all tables and indexes if they don't exist.

    Args:
        db: Existing Database instance (optional)
        url: Database URL (optional, uses default if not provided)

    Returns:
        Database: Initialized database instance

    Example:
        from z8ter.database import init_database

        # Use default SQLite database
        db = init_database()

        # Or with custom URL
        db = init_database(url="sqlite:///custom.db")
    """
    if db is None:
        db = Database(url)

    logger.info("Initializing database at %s", db.path)

    with db.connection() as conn:
        # Create tables
        for table_name, ddl in TABLES.items():
            logger.debug("Creating table: %s", table_name)
            conn.execute(ddl)

        # Create indexes
        for index_ddl in INDEXES:
            conn.execute(index_ddl)

        # Record schema version
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO migrations (version, applied_at)
            VALUES (?, ?)
            """,
            (SCHEMA_VERSION, now),
        )

    logger.info("Database initialized successfully")
    return db


def get_schema_version(db: Database) -> int:
    """Get current schema version.

    Args:
        db: Database instance

    Returns:
        Current schema version number, or 0 if not initialized
    """
    try:
        row = db.fetchone("SELECT MAX(version) as version FROM migrations")
        return row["version"] if row and row["version"] else 0
    except Exception:
        return 0


def reset_database(db: Database) -> None:
    """Drop all tables and reinitialize.

    WARNING: This deletes all data!

    Args:
        db: Database instance
    """
    logger.warning("Resetting database - all data will be deleted!")

    with db.connection() as conn:
        # Drop tables in reverse dependency order
        conn.execute("DROP TABLE IF EXISTS sessions")
        conn.execute("DROP TABLE IF EXISTS users")
        conn.execute("DROP TABLE IF EXISTS migrations")

    # Reinitialize
    init_database(db)
