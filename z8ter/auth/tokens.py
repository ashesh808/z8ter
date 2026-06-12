"""Signed, time-limited tokens for auth flows (password reset, verification).

`TokenManager` wraps `itsdangerous.URLSafeTimedSerializer` to mint and verify
single-purpose tokens that can be embedded in emailed links:

    manager = TokenManager(secret_key=config("APP_SESSION_KEY"))
    token = manager.generate_password_reset_token("u_123")
    # later, in the reset endpoint:
    user_id = manager.verify_password_reset_token(token)  # None if invalid

Design:
- Tokens are stateless: nothing is stored server-side. Verification checks
  the signature and age, so no database table or cleanup job is needed.
- Each purpose uses a distinct salt, so a verification token can never be
  replayed as a password-reset token (and vice versa).

Security notes:
- Tokens are signed, NOT encrypted — payloads (user id, email) are readable
  by anyone holding the token. Never embed secrets in the payload.
- Statelessness means a token cannot be revoked individually. Keep max ages
  short (reset: 1h default, verification: 24h default). For password reset,
  additionally compare against the user's `updated_at`/password timestamp if
  you need "invalidate on use" semantics.
- Reuses the app secret key; rotating it invalidates all outstanding tokens.
"""

from __future__ import annotations

from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Minimum secret key length, consistent with use_app_sessions_builder.
MIN_SECRET_KEY_LENGTH = 32

# Default token lifetimes (seconds).
DEFAULT_RESET_MAX_AGE = 60 * 60  # 1 hour
DEFAULT_VERIFY_MAX_AGE = 60 * 60 * 24  # 24 hours

_PASSWORD_RESET_SALT = "z8ter.password-reset"  # noqa: S105 - salt, not a secret
_EMAIL_VERIFY_SALT = "z8ter.email-verify"  # noqa: S105 - salt, not a secret


class TokenManager:
    """Mint and verify purpose-scoped, time-limited signed tokens.

    Args:
        secret_key: Server-side signing key (>= 32 chars). Typically the
            same APP_SESSION_KEY used elsewhere.

    Raises:
        ValueError: If the secret key is missing or too short.

    """

    def __init__(self, secret_key: str) -> None:
        """Validate the secret key and prepare per-purpose serializers."""
        if not secret_key:
            raise ValueError("Z8ter: secret key is required for TokenManager.")
        if len(secret_key) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"Z8ter: TokenManager secret key must be at least "
                f"{MIN_SECRET_KEY_LENGTH} characters. Generate with: "
                "python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        self._secret_key = secret_key

    def _serializer(self, salt: str) -> URLSafeTimedSerializer:
        """Return a serializer scoped to a purpose salt."""
        return URLSafeTimedSerializer(self._secret_key, salt=salt)

    # -------- Generic API --------

    def generate(self, purpose: str, payload: Any) -> str:
        """Mint a signed token for an arbitrary purpose.

        Args:
            purpose: Namespace string; verification must use the same value.
            payload: JSON-serializable payload (str, dict, list, ...).

        Returns:
            URL-safe token string.

        """
        return self._serializer(f"z8ter.{purpose}").dumps(payload)

    def verify(self, purpose: str, token: str, *, max_age: int) -> Any | None:
        """Verify a token minted by `generate` with the same purpose.

        Args:
            purpose: Namespace string used at generation time.
            token: Token string to verify.
            max_age: Maximum allowed age in seconds.

        Returns:
            The original payload, or None if the token is invalid, was
            minted for a different purpose, or has expired.

        """
        try:
            return self._serializer(f"z8ter.{purpose}").loads(
                token, max_age=max_age
            )
        except (BadSignature, SignatureExpired):
            return None

    # -------- Password reset --------

    def generate_password_reset_token(self, user_id: str) -> str:
        """Mint a password-reset token bound to a user id.

        Args:
            user_id: Stable user identifier.

        Returns:
            URL-safe token to embed in an emailed reset link.

        """
        return self._serializer(_PASSWORD_RESET_SALT).dumps({"uid": user_id})

    def verify_password_reset_token(
        self, token: str, *, max_age: int = DEFAULT_RESET_MAX_AGE
    ) -> str | None:
        """Verify a password-reset token.

        Args:
            token: Token from the reset link.
            max_age: Maximum age in seconds (default: 1 hour).

        Returns:
            The user id the token was minted for, or None if invalid/expired.

        Security:
            - After a successful reset, call
              `session_repo.revoke_all_for_user(user_id)` (SEC-014).

        """
        try:
            data = self._serializer(_PASSWORD_RESET_SALT).loads(
                token, max_age=max_age
            )
        except (BadSignature, SignatureExpired):
            return None
        if isinstance(data, dict):
            uid = data.get("uid")
            return uid if isinstance(uid, str) else None
        return None

    # -------- Email verification --------

    def generate_email_verification_token(
        self, user_id: str, email: str
    ) -> str:
        """Mint an email-verification token bound to a user id and address.

        Binding the email means a token becomes useless if the user changes
        their address before clicking the link.

        Args:
            user_id: Stable user identifier.
            email: Address being verified.

        Returns:
            URL-safe token to embed in the verification link.

        """
        return self._serializer(_EMAIL_VERIFY_SALT).dumps(
            {"uid": user_id, "email": email.lower()}
        )

    def verify_email_verification_token(
        self, token: str, *, max_age: int = DEFAULT_VERIFY_MAX_AGE
    ) -> dict[str, str] | None:
        """Verify an email-verification token.

        Args:
            token: Token from the verification link.
            max_age: Maximum age in seconds (default: 24 hours).

        Returns:
            {"uid": ..., "email": ...} or None if invalid/expired.

        Usage:
            data = manager.verify_email_verification_token(token)
            if data and user.email == data["email"]:
                user_repo.update_user(data["uid"], is_verified=True)

        """
        try:
            data = self._serializer(_EMAIL_VERIFY_SALT).loads(
                token, max_age=max_age
            )
        except (BadSignature, SignatureExpired):
            return None
        if (
            isinstance(data, dict)
            and isinstance(data.get("uid"), str)
            and isinstance(data.get("email"), str)
        ):
            return {"uid": data["uid"], "email": data["email"]}
        return None
