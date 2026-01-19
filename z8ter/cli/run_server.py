# z8ter/cli/run_server.py
"""Run a Z8ter app via Uvicorn.

This module exposes `run_server`, which starts a Uvicorn process in one of four
modes:

- dev  : local development (reload on; loop/watch set by Uvicorn).
- prod : production-ish (bind 127.0.0.1; reload off). For containerized
         environments, use WAN mode or set host explicitly.
- LAN  : bind to the current machine's LAN IP for same-network devices.
- WAN  : bind to 0.0.0.0 for external access (reload follows dev/prod logic).

Notes:
- The CLI sets the app directory to `z8ter.BASE_DIR` so imports work.
- We pass `factory=True` and point to the configured app factory.
- Logging uses `z8ter.logging_utils.uvicorn_log_config`.
- For Docker/containers, use mode="WAN" or set host="0.0.0.0" explicitly.

Environment variables:
- Z8TER_APP_FACTORY: Override the app factory path (default: "main:app_builder.build")

"""

import logging
import os
import socket

import uvicorn

import z8ter
from z8ter.logging_utils import uvicorn_log_config

logger = logging.getLogger("z8ter.cli")

# Default app factory path - can be overridden via environment variable
DEFAULT_APP_FACTORY = "main:app_builder.build"


def run_server(
    mode: str = "prod",
    host: str = "127.0.0.1",
    port: int = 8080,
    reload: bool | None = None,
    app_factory: str | None = None,
) -> None:
    """Start the Uvicorn server with sensible defaults per mode.

    Args:
        mode: One of {"dev", "prod", "WAN", "LAN"}.
            - "dev": local dev; `reload=True` by default.
            - "prod": production-ish; binds 127.0.0.1 and disables reload.
                      Note: For Docker/containers, use "WAN" mode instead.
            - "LAN": bind to detected LAN IP; `reload` follows dev/prod logic.
            - "WAN": bind 0.0.0.0; `reload` follows dev/prod logic.
        host: Host override (ignored for "prod"/"WAN"/"LAN" where we set it).
        port: TCP port to listen on.
        reload: Force code reload. If None, defaults to True in dev, False in prod.
        app_factory: App factory path (e.g., "main:app_builder.build").
                     Defaults to Z8TER_APP_FACTORY env var or "main:app_builder.build".

    Security:
        - "WAN" binds to 0.0.0.0. Do not expose in untrusted networks
          without a proxy, TLS, and proper hardening.

    Raises:
        RuntimeError: If the app factory path is incorrect (raised by Uvicorn).

    """

    def lan_ip() -> str:
        """Best-effort LAN IP discovery via a UDP 'connect' trick.

        Returns:
            The local IP chosen by the OS routing table.

        Notes:
            - This does not send packets to 8.8.8.8; UDP connect sets a peer and
              lets us query the chosen local socket address.
            - Falls back to closing the socket in a `finally` block to avoid
              leaking file descriptors.

        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    # Resolve app factory path
    if app_factory is None:
        app_factory = os.getenv("Z8TER_APP_FACTORY", DEFAULT_APP_FACTORY)

    is_prod = mode == "prod"
    is_dev = not is_prod
    # If reload not specified, enable in dev-like modes, disable in prod.
    reload = is_dev if reload is None else reload

    # Mode-specific host overrides.
    if mode == "WAN":
        host = "0.0.0.0"
        logger.info("[WAN] Binding to %s:%d (reload=%s)", host, port, reload)
    elif mode == "LAN":
        host = lan_ip()
        logger.info("[LAN] Binding to %s:%d (reload=%s)", host, port, reload)
    elif mode == "prod":
        host = "127.0.0.1"
        reload = False
        logger.info("[PROD] Binding to %s:%d (reload=%s) - use WAN mode for Docker", host, port, reload)
    else:
        logger.info("[DEV] Binding to %s:%d (reload=%s)", host, port, reload)

    # Start Uvicorn with an app factory. Your main.py must expose:
    #   def app_builder() -> AppBuilder: ...
    #   and app_builder.build() must be a callable returning ASGI app.
    try:
        uvicorn.run(
            app_factory,
            factory=True,
            host=host,
            port=port,
            reload=reload,
            app_dir=str(z8ter.BASE_DIR),
            reload_dirs=[str(z8ter.BASE_DIR)],
            log_level="info",
            log_config=uvicorn_log_config(is_dev),
        )
    except KeyboardInterrupt:
        pass
