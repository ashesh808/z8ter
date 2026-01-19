"""Database CLI commands for Z8ter.

Provides commands for database management:
  - init: Initialize database with tables
  - reset: Drop all tables and reinitialize (destructive)
  - status: Show database status and schema version
"""

from __future__ import annotations

import logging

from z8ter.database import Database, init_database
from z8ter.database.init import get_schema_version, reset_database

logger = logging.getLogger("z8ter.cli.database")


def db_init(url: str | None = None) -> None:
    """Initialize database with required tables.

    Args:
        url: Database URL (optional, uses DATABASE_URL env var or default)
    """
    db = init_database(url=url)
    print(f"Database initialized at: {db.path}")
    print(f"Schema version: {get_schema_version(db)}")


def db_reset(url: str | None = None, force: bool = False) -> None:
    """Reset database (drop all tables and reinitialize).

    WARNING: This deletes all data!

    Args:
        url: Database URL
        force: Skip confirmation prompt
    """
    db = Database(url)

    if not force:
        confirm = input(
            f"WARNING: This will delete ALL data in {db.path}. "
            "Type 'yes' to confirm: "
        )
        if confirm.lower() != "yes":
            print("Aborted.")
            return

    reset_database(db)
    print(f"Database reset at: {db.path}")


def db_status(url: str | None = None) -> None:
    """Show database status and schema version.

    Args:
        url: Database URL
    """
    db = Database(url)

    print(f"Database path: {db.path}")
    print(f"Schema version: {get_schema_version(db)}")

    # Try to get some stats
    try:
        from z8ter.database import SQLiteSessionRepo, SQLiteUserRepo

        user_repo = SQLiteUserRepo(db)
        print(f"Total users: {user_repo.count_users()}")
        print(f"Active users: {user_repo.count_users(active_only=True)}")
    except Exception:
        print("(Could not fetch user statistics)")
