import uuid
from typing import Optional

from z8ter.auth.crypto import hash_password


class ManageUsers:
    """Use cases for user management."""

    def __init__(self, user_repo) -> None:
        self.user_repo = user_repo

    async def create_user(self, email: str, pwd: str) -> str:
        """Create a user and return its user_id.

        Args:
            email: User's email address
            pwd: User's plaintext password (will be hashed)

        Returns:
            The generated UUID user_id

        Security:
            - Passwords are hashed using Argon2id before storage
            - User IDs are random UUIDs, not derived from PII
        """
        user_id = str(uuid.uuid4())
        self.user_repo.add_user(
            user_id,
            {
                "id": user_id,
                "email": email.lower(),
                "pwd_hash": hash_password(pwd),
            },
        )
        return user_id

    async def get_user_email(self, email: str) -> Optional[dict]:
        """Fetch user record by email.

        Args:
            email: Email address to look up (case-insensitive)

        Returns:
            User dictionary if found, None otherwise
        """
        return self.user_repo.get_user_by_email(email.lower())

    async def email_exists(self, email: str) -> bool:
        """Check if an email is already registered.

        Args:
            email: Email address to check (case-insensitive)

        Returns:
            True if email exists, False otherwise
        """
        return self.user_repo.email_exists(email.lower())
