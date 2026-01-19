"""Password hashing utilities for Z8ter authentication.

This module wraps `argon2-cffi` with a fixed configuration tuned for general
web application security. It provides a stable API for password storage and
verification.

Rationale for choices:
- Argon2id (Type.ID) is recommended by OWASP and modern standards (resistant to
  both GPU/ASIC cracking and side-channel timing).
- Parameters (`time_cost=3`, `memory_cost=64MB`, `parallelism=2`) are chosen as
  a safe baseline for 2025 commodity servers. Adjust upward for stronger
  security if your infra can tolerate higher latency/CPU usage.

Public functions:
- `hash_password`: Derive a secure hash from a plaintext password.
- `verify_password`: Verify a plaintext against a stored hash.
- `needs_rehash`: Check if stored hash should be upgraded to new parameters.

Security notes:
- Hashes are salted automatically; do not provide your own salt.
- Always store the full Argon2 hash string in your DB (includes params & salt).
- Do not truncate or alter the hash string.
- `verify_password` should be used inside your login/authentication flow only.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

_PH = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(plain: str) -> str:
    """Derive a secure Argon2id hash for the given plaintext password.

    Args:
        plain: User-supplied plaintext password.

    Returns:
        Full Argon2 hash string, safe to persist (includes parameters, salt, hash).

    Notes:
        - Idempotent only with respect to the same password *and* same salt.
          Since salt is random, repeated calls with the same password yield
          different hashes.

    """
    return _PH.hash(plain)


def verify_password(hash_: str, plain: str) -> bool:
    """Verify a plaintext password against a stored Argon2 hash.

    Args:
        hash_: Full Argon2 hash string as persisted in DB.
        plain: User-supplied plaintext password.

    Returns:
        True if verification succeeds, False otherwise.

    Notes:
        - On expected failures (wrong password or malformed hash), returns False.
        - Verification is constant-time within Argon2 implementation, mitigating
          timing attacks.
        - Unexpected errors (e.g., MemoryError) are re-raised.

    """
    try:
        _PH.verify(hash_, plain)
        return True
    except VerifyMismatchError:
        # Password doesn't match - expected case
        return False
    except InvalidHashError:
        # Hash is malformed - treat as verification failure
        return False


def needs_rehash(hash_: str) -> bool:
    """Check whether a stored Argon2 hash should be recomputed.

    Args:
        hash_: Full Argon2 hash string as persisted in DB.

    Returns:
        True if the given hash was computed with weaker/old parameters compared
        to the current `_PH` configuration; False if up-to-date.

    Usage:
        - Call after successful `verify_password`. If True, transparently
          re-hash the password with current parameters and update DB.

    Example:
        if verify_password(stored, input):
            if needs_rehash(stored):
                db.update(user.id, hash_password(input))

    """
    return _PH.check_needs_rehash(hash_)
