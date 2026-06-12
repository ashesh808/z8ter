"""Account lockout tracking for Z8ter.

Tracks failed login attempts per identifier (email, user id, or IP) and
locks the identifier after too many failures within a window. Complements
`RateLimitMiddleware`: rate limiting throttles a single source IP, while
lockout protects a single *account* from distributed guessing.

Usage in a login flow:

    lockout = AccountLockout(max_attempts=5, lockout_seconds=900)

    if lockout.is_locked(email):
        # Render "try again later"; do NOT reveal whether the account exists.
        ...
    if verify_password(stored_hash, password):
        lockout.record_success(email)
    else:
        locked_now = lockout.record_failure(email)

Security notes:
- Storage is in-memory and per-process. Behind multiple workers, each
  process tracks independently; for strict guarantees use a shared store
  (e.g., Redis) implementing the same methods.
- Lockout responses should be indistinguishable from bad-password responses
  to avoid user enumeration (SEC-012).
- `ACCOUNT_LOCKED` audit events are emitted via `z8ter.security.audit`.
"""

from __future__ import annotations

import threading
import time

from z8ter.security.audit import SecurityEvent, log_security_event

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LOCKOUT_SECONDS = 900  # 15 minutes
DEFAULT_WINDOW_SECONDS = 900  # failures older than this are forgotten


class AccountLockout:
    """Track failed attempts and lock identifiers after repeated failures.

    Args:
        max_attempts: Failures within the window that trigger a lock.
        lockout_seconds: How long a lock lasts once triggered.
        window_seconds: Sliding window in which failures are counted.

    Thread safety:
        All methods take an internal lock; safe to share across request
        handlers within one process.

    """

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        """Initialize empty tracking state."""
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # identifier -> list of failure timestamps (monotonic-ish epoch secs)
        self._failures: dict[str, list[float]] = {}
        # identifier -> epoch seconds when the lock expires
        self._locked_until: dict[str, float] = {}

    @staticmethod
    def _key(identifier: str) -> str:
        """Normalize identifiers (emails are case-insensitive)."""
        return identifier.strip().lower()

    def is_locked(self, identifier: str) -> bool:
        """Return True if the identifier is currently locked.

        Args:
            identifier: Account email, user id, or other stable key.

        """
        key = self._key(identifier)
        now = time.time()
        with self._lock:
            until = self._locked_until.get(key)
            if until is None:
                return False
            if until <= now:
                # Lock expired: clear it and the failure history.
                self._locked_until.pop(key, None)
                self._failures.pop(key, None)
                return False
            return True

    def record_failure(
        self,
        identifier: str,
        *,
        ip_address: str | None = None,
    ) -> bool:
        """Record a failed attempt; lock the identifier if over the limit.

        Args:
            identifier: Account email, user id, or other stable key.
            ip_address: Optional client IP for the audit log.

        Returns:
            True if this failure triggered (or extended) a lock.

        """
        key = self._key(identifier)
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            failures = [t for t in self._failures.get(key, []) if t > cutoff]
            failures.append(now)
            self._failures[key] = failures
            if len(failures) >= self.max_attempts:
                self._locked_until[key] = now + self.lockout_seconds
                locked = True
            else:
                locked = False
        if locked:
            log_security_event(
                SecurityEvent.ACCOUNT_LOCKED,
                email=identifier,
                ip_address=ip_address,
                success=False,
                details={
                    "failed_attempts": len(failures),
                    "lockout_seconds": self.lockout_seconds,
                },
            )
        return locked

    def record_success(self, identifier: str) -> None:
        """Clear failure history after a successful authentication.

        Args:
            identifier: Account email, user id, or other stable key.

        Notes:
            - Does NOT clear an active lock: a correct guess during a lock
              window must not unlock the account.

        """
        key = self._key(identifier)
        with self._lock:
            if key not in self._locked_until:
                self._failures.pop(key, None)

    def remaining_attempts(self, identifier: str) -> int:
        """Return how many failures remain before a lock triggers.

        Args:
            identifier: Account email, user id, or other stable key.

        Returns:
            0 when locked; otherwise max_attempts minus recent failures.

        """
        key = self._key(identifier)
        if self.is_locked(identifier):
            return 0
        cutoff = time.time() - self.window_seconds
        with self._lock:
            recent = [t for t in self._failures.get(key, []) if t > cutoff]
            return max(0, self.max_attempts - len(recent))

    def seconds_until_unlock(self, identifier: str) -> int:
        """Return seconds until an active lock expires (0 if not locked).

        Args:
            identifier: Account email, user id, or other stable key.

        """
        key = self._key(identifier)
        with self._lock:
            until = self._locked_until.get(key)
        if until is None:
            return 0
        return max(0, int(until - time.time()) + 1) if until > time.time() else 0

    def reset(self, identifier: str) -> None:
        """Administratively clear failures and any active lock.

        Args:
            identifier: Account email, user id, or other stable key.

        """
        key = self._key(identifier)
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def cleanup(self) -> int:
        """Drop expired locks and stale failure history.

        Suitable for periodic invocation from a background task to bound
        memory usage (mirrors `SessionRepo.cleanup_expired`).

        Returns:
            Number of identifiers whose state was removed.

        """
        now = time.time()
        cutoff = now - self.window_seconds
        removed = 0
        with self._lock:
            for key in [k for k, v in self._locked_until.items() if v <= now]:
                del self._locked_until[key]
                self._failures.pop(key, None)
                removed += 1
            for key in list(self._failures):
                recent = [t for t in self._failures[key] if t > cutoff]
                if recent:
                    self._failures[key] = recent
                elif key not in self._locked_until:
                    del self._failures[key]
                    removed += 1
        return removed
