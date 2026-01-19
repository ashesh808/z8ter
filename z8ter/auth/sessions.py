"""Session management for Z8ter.

This module provides a high-level API for creating, revoking, and managing
session cookies. It coordinates between the `SessionRepo` (persistent storage)
and HTTP responses.

Responsibilities:
- Generate secure random session IDs and persist them via `SessionRepo`.
- Attach session IDs as cookies (`z8_auth_sid`) to HTTP responses.
- Revoke sessions and clear cookies when logging out.
- Support "remember me" sessions with extended lifetimes.

Security notes:
- Session IDs (`sid`) are generated with `secrets.token_urlsafe`, providing
  cryptographically secure randomness.
- SessionRepo implementations must hash `sid` before storing.
- Cookies are set with `HttpOnly` and `Secure` flags by default.

Threading notes:
- Repository methods are called synchronously. If your repository implementation
  performs blocking I/O (e.g., database queries), consider using an async driver
  or wrapping calls in `run_in_executor`.
- The in-memory reference implementation is non-blocking and safe for async use.
"""

import asyncio
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial

from z8ter.auth.contracts import SessionRepo
from z8ter.responses import Response

# Thread pool for blocking repository operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="z8ter_session_")


class SessionManager:
    """High-level session management for authentication.

    This class acts as the glue between the repository (persistent storage) and
    HTTP responses. Use it inside login/logout flows to create or revoke sessions.
    """

    def __init__(self, session_repo: SessionRepo):
        """Initialize the session manager.

        Args:
            session_repo (SessionRepo): Repository implementation for persisting
                and revoking session records.

        """
        self.cookie_name = "z8_auth_sid"
        self.session_repo = session_repo

    async def start_session(
        self,
        user_id: str,
        *,
        remember: bool = False,
        ip: str | None = None,
        user_agent: str | None = None,
        ttl: int = 60 * 60 * 24 * 7,
    ) -> str:
        """Create and persist a new session for the given user.

        Args:
            user_id (str): The application-level user identifier.
            remember (bool, optional): If True, mark the session as "remember me"
                (longer-lived cookie). Defaults to False.
            ip (str | None, optional): Client IP at login time. Defaults to None.
            user_agent (str | None, optional): User agent string at login time.
                Defaults to None.
            ttl (int, optional): Session lifetime in seconds. Defaults to 7 days.

        Returns:
            str: The newly generated plaintext session ID (`sid`).

        Notes:
            - The returned `sid` should be attached to a cookie with
              `set_session_cookie`.
            - The session is persisted immediately via `SessionRepo`.
            - If the repository performs blocking I/O, the call is run in a
              thread pool to avoid blocking the event loop.

        """
        sid = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Run sync repository method in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            _executor,
            partial(
                self.session_repo.insert,
                sid_plain=sid,
                user_id=user_id,
                expires_at=expires_at,
                remember=remember,
                ip=ip,
                user_agent=user_agent,
            ),
        )
        return sid

    async def revoke_session(self, sid: str) -> bool:
        """Revoke an existing session.

        Args:
            sid (str): Plaintext session ID to revoke.

        Returns:
            bool: True if the session was found and revoked; False otherwise.

        Notes:
            - Idempotent: calling on a non-existent or already revoked session
              returns False.
            - If the repository performs blocking I/O, the call is run in a
              thread pool to avoid blocking the event loop.

        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor,
            partial(self.session_repo.revoke, sid_plain=sid),
        )

    async def set_session_cookie(
        self,
        resp: Response,
        sid: str,
        *,
        secure: bool = True,
        remember: bool = False,
        ttl: int = 60 * 60 * 24 * 7,
    ) -> None:
        """Attach the session cookie to an HTTP response.

        Args:
            resp (Response): The HTTP response to mutate.
            sid (str): The plaintext session ID to store in the cookie.
            secure (bool, optional): Whether to set the `Secure` flag (HTTPS-only).
                Defaults to True.
            remember (bool, optional): If True, set `max_age` to the TTL for a
                persistent cookie. Otherwise, cookie expires when browser closes.
                Defaults to False.
            ttl (int, optional): Session lifetime in seconds (used for max_age if
                remember=True). Defaults to 7 days.

        Notes:
            - Cookies are always set with `HttpOnly`, `SameSite=Lax`, and path="/".
            - Use `remember=True` for "remember me" functionality.

        """
        max_age = ttl if remember else None
        resp.set_cookie(
            key=self.cookie_name,
            value=sid,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
            max_age=max_age,
        )

    async def clear_session_cookie(self, resp: Response) -> None:
        """Remove the session cookie from an HTTP response.

        Args:
            resp (Response): The HTTP response to mutate.

        Notes:
            - This only clears the client cookie. To fully log out a user, call
              `revoke_session` as well.

        """
        resp.delete_cookie(self.cookie_name, path="/")
