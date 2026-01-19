"""Z8ter database module.

Provides SQLite-based persistence with simple configuration:
- Default: sqlite:///data/app.db
- Configure via DATABASE_URL environment variable

Exports:
- Database: Connection manager
- SQLiteSessionRepo: Session storage implementation
- SQLiteUserRepo: User storage implementation
- init_database: Initialize tables
"""

from z8ter.database.connection import Database
from z8ter.database.session_repo import SQLiteSessionRepo
from z8ter.database.user_repo import SQLiteUserRepo
from z8ter.database.init import init_database

__all__ = [
    "Database",
    "SQLiteSessionRepo",
    "SQLiteUserRepo",
    "init_database",
]
