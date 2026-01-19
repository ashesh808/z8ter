"""Z8ter core application wrapper.

Provides the `Z8ter` class, which wraps a Starlette application and
adds framework-specific state, debug handling, and logging.
"""

from __future__ import annotations

import logging

from starlette.applications import Starlette
from starlette.types import Receive, Scope, Send

logger = logging.getLogger("z8ter")
ALLOWED_MODES = {"dev", "prod", "test"}


class Z8ter:
    """Z8ter application wrapper around Starlette.

    This class holds a reference to the underlying Starlette app, exposes
    its state, and manages framework-level debug/mode settings.

    Args:
        debug: Optional explicit debug flag. If None, defaults to True
            when mode="dev".
        mode: Application mode string (e.g., "dev", "prod", "test"). Defaults
            to "prod" if not set. Used to configure mode-specific behavior.
        starlette_app: The underlying Starlette ASGI application.

    Attributes:
        starlette_app: The wrapped Starlette application instance.
        state: Shortcut to `starlette_app.state`.
        mode: Lowercased mode string (default "prod").
        debug: Boolean indicating whether debug mode is active.
        is_dev: Convenience property, True when mode == "dev".
        is_prod: Convenience property, True when mode == "prod".
        is_test: Convenience property, True when mode == "test".

    Notes:
        - In debug mode, a warning banner is logged at startup.
        - The class is itself ASGI-callable (`__call__` forwards to
          `starlette_app`).

    """

    def __init__(
        self,
        *,
        debug: bool | None = None,
        mode: str | None = None,
        starlette_app: Starlette,
    ) -> None:
        """Initialize Z8ter apps, this should only be done via the App builder."""
        self.starlette_app = starlette_app
        self.mode: str = (mode or "prod").lower()
        if self.mode not in ALLOWED_MODES:
            raise ValueError(
                f"Unknown mode '{self.mode}'. Allowed: {sorted(ALLOWED_MODES)}"
            )
        if debug is None:
            self.debug = self.mode == "dev"
        else:
            self.debug = bool(debug)
        if self.debug:
            logger.warning("[Z8ter] Running in DEBUG mode - do not use in production")

    @property
    def state(self):
        """Access the underlying Starlette app state."""
        return self.starlette_app.state

    @property
    def is_dev(self) -> bool:
        """Return True if running in development mode."""
        return self.mode == "dev"

    @property
    def is_prod(self) -> bool:
        """Return True if running in production mode."""
        return self.mode == "prod"

    @property
    def is_test(self) -> bool:
        """Return True if running in test mode."""
        return self.mode == "test"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward ASGI calls directly to the underlying Starlette app.

        Args:
            scope: The ASGI connection scope.
            receive: Awaitable to receive ASGI events.
            send: Awaitable to send ASGI events.

        Returns:
            None. The ASGI response cycle is handled by Starlette.

        """
        await self.starlette_app(scope, receive, send)
