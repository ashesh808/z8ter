"""Builder step definitions and utilities for assembling a Z8ter app.

This module provides:
  - `BuilderStep`: a small spec describing a build operation.
  - Helper functions to publish services and query config from the shared context.
  - Concrete builder functions (`use_*_builder`) that mutate the app/context.

Conventions:
  - Each builder receives a single `context: dict[str, Any]` and returns None.
  - Shared services live in `context["services"]` and mirror to
    `app.starlette_app.state.services`.
  - Steps should be idempotent when feasible and validate dependencies
    explicitly (see `AppBuilder` for orchestration).

Security:
  - `use_app_sessions_builder` requires a non-empty secret key.
  - URL helpers injected into templates must not be used to build external
    redirects without validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.datastructures import URLPath
from starlette.middleware.sessions import SessionMiddleware

from z8ter.auth.middleware import AuthSessionMiddleware
from z8ter.builders.helpers import ensure_services, get_config_value
from z8ter.config import build_config
from z8ter.core import Z8ter
from z8ter.errors import register_exception_handlers
from z8ter.vite import vite_script_tag

if TYPE_CHECKING:
    pass


def use_service_builder(context: dict[str, Any]) -> None:
    """Register an object as a named service.

    Services are stored in both `context["services"]` and `app.state.services`.
    The key is derived from the object's class name (lowercased, trailing
    underscores stripped).

    Required context:
        - app: Z8ter instance
        - obj: service instance to publish
        - replace (optional): bool

    Raises:
        RuntimeError: If a service with the same key exists and `replace=False`.

    """
    app: Z8ter = context["app"]
    obj = context["obj"]
    name = (context.get("name") or obj.__class__.__name__).rstrip("_").lower()
    replace: bool = bool(context.get("replace", False))
    services = context.setdefault("services", {})
    state = app.starlette_app.state
    if not hasattr(state, "services"):
        state.services = services
    else:
        services = state.services

    if name in services and not replace:
        raise RuntimeError(
            f"Z8ter: service '{name}' already registered.Pass replace=True to override."
        )

    services[name] = obj
    needs_config = hasattr(obj, "set_config") or hasattr(obj, "config")
    if needs_config:
        cfg = services.get("config")
        if cfg is None:
            raise RuntimeError(
                f"Z8ter: cannot inject config into '{name}' before use_config()."
            )
        if hasattr(obj, "set_config"):
            obj.set_config(cfg)
        elif hasattr(obj, "config"):
            obj.config = cfg


def use_config_builder(context: dict[str, Any]) -> None:
    """Load configuration and publish a `config` accessor service.

    Context inputs:
        - envfile (optional): str, path to .env file. Defaults to ".env".

    Side effects:
        - Sets `context["config"]`.
        - Publishes `services["config"]`.
    """
    envfile = context.get("envfile", ".env")
    config = build_config(env_file=envfile)
    context["config"] = config
    services = ensure_services(context)
    services["config"] = config


def use_templating_builder(context: dict[str, Any]) -> None:
    """Initialize Jinja templating and inject convenience globals.

    Injected globals:
        - `url_for(name, filename=None, **params)`: wraps Starlette's
          `url_path_for`, mapping `filename` to `path` for static routes.

    Side effects:
        - Sets `context["templates"]`.
        - Publishes `services["templates"]`.
    """
    import z8ter

    app: Z8ter = context["app"]
    templates = z8ter.get_templates()

    def _url_for(name: str, filename: str | None = None, **params: Any) -> str:
        if filename is not None:
            params["path"] = filename
        path: URLPath = app.starlette_app.url_path_for(name, **params)
        return str(path)

    templates.env.globals["url_for"] = _url_for
    context["templates"] = templates
    services = ensure_services(context)
    services["templates"] = templates


def use_vite_builder(context: dict[str, Any]) -> None:
    """Expose Vite helper(s) to templates.

    Requirements:
        - `use_templating_builder` must have been applied.

    Injected globals:
        - `vite_script_tag(entry: str) -> Markup`: emits script tags for Vite
          dev server or built assets.

    Raises:
        RuntimeError: If templating has not been initialized.

    """
    templates = context.get("templates")
    if not templates:
        raise RuntimeError(
            "Z8ter: 'vite' requires 'templating'. "
            "Call use_templating() before use_vite()."
        )
    templates.env.globals["vite_script_tag"] = vite_script_tag


def use_errors_builder(context: dict[str, Any]) -> None:
    """Register framework exception handlers.

    Side effects:
        - Binds handlers on the underlying Starlette app for a consistent UX.
    """
    app: Z8ter = context["app"]
    register_exception_handlers(app)


def publish_auth_repos_builder(context: dict[str, Any]) -> None:
    """Publish authentication repositories to app state and services.

    Required context:
        - app: Z8ter instance
        - session_repo: object with methods insert/revoke/get_user_id
        - user_repo: object with method get_user_by_id

    Raises:
        RuntimeError: If required methods are missing on either repo.

    Side effects:
        - Sets `app.state.session_repo` and `app.state.user_repo`.
        - Publishes both repos into `services`.

    """
    app = context["app"]
    services = context.setdefault("services", {})
    session_repo = context["session_repo"]
    user_repo = context["user_repo"]

    for name, repo, methods in [
        ("session_repo", session_repo, ["insert", "revoke", "get_user_id"]),
        ("user_repo", user_repo, ["get_user_by_id"]),
    ]:
        for m in methods:
            if not hasattr(repo, m):
                raise RuntimeError(
                    f"Z8ter: {name} missing required method '{m}'. "
                    f"Provided object: {repo.__class__.__name__}"
                )

    app.starlette_app.state.session_repo = session_repo
    app.starlette_app.state.user_repo = user_repo
    services["session_repo"] = session_repo
    services["user_repo"] = user_repo


def use_app_sessions_builder(context: dict[str, Any]) -> None:
    """Enable application (non-auth) session cookies via Starlette middleware.

    Context inputs:
        - secret_key (optional): overrides APP_SESSION_KEY from config.
        - config (optional): callable or mapping providing APP_SESSION_KEY.

    Raises:
        TypeError: If no secret key can be resolved.

    Notes:
        - Cookie name is fixed to `z8_app_sess`. SameSite=Lax, 7-day max_age.
        - For production, always use a strong, private secret key.

    """
    app = context["app"]
    secret_key = get_config_value(context=context, key="APP_SESSION_KEY")
    secret_key = context.get("secret_key") or secret_key
    if not secret_key:
        raise TypeError("Z8ter: secret key is required for app sessions.")
    app.starlette_app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="z8_app_sess",
        max_age=60 * 60 * 24 * 7,
        same_site="lax",
    )


def use_authentication_builder(context: dict[str, Any]) -> None:
    """Attach authentication session middleware once.

    Guarded by a private sentinel to avoid double-insertion.
    """
    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_auth_added", False):
        return
    app.starlette_app.add_middleware(AuthSessionMiddleware)
    state._z8_auth_added = True
