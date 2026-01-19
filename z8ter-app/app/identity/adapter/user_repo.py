from __future__ import annotations

from typing import Optional


class InMemoryUserRepo:
    """In-memory user repository with email index.

    Stores users by their unique ID and maintains an email index
    for efficient email-based lookups.
    """

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}
        self._email_index: dict[str, str] = {}  # email -> user_id

    def add_user(self, user_id: str, user: dict) -> None:
        """Add a user to the repository.

        Args:
            user_id: Unique identifier for the user
            user: User data dictionary (must contain 'email' key)
        """
        self._users[user_id] = user
        # Update email index if email is provided
        if "email" in user:
            email = user["email"].lower()
            self._email_index[email] = user_id

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by their unique ID."""
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by their email address.

        Args:
            email: Email address to look up (case-insensitive)

        Returns:
            User dictionary if found, None otherwise
        """
        email = email.lower()
        user_id = self._email_index.get(email)
        if user_id:
            return self._users.get(user_id)
        return None

    def email_exists(self, email: str) -> bool:
        """Check if an email is already registered.

        Args:
            email: Email address to check (case-insensitive)

        Returns:
            True if email exists, False otherwise
        """
        return email.lower() in self._email_index
