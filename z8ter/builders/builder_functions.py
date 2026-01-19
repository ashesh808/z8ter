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

from z8ter.builders.helpers import ensure_services, get_config_value
from z8ter.config import build_config
from z8ter.core import Z8ter
from z8ter.errors import register_exception_handlers
from z8ter.security.csrf import CSRFMiddleware
from z8ter.security.headers import SecurityHeadersMiddleware
from z8ter.security.rate_limit import RateLimitConfig, RateLimitMiddleware
from z8ter.vite import vite_script_tag

if TYPE_CHECKING:
    pass

# Minimum secret key length for security
MIN_SECRET_KEY_LENGTH = 32


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
            f"Z8ter: service '{name}' already registered. Pass replace=True to override."
        )

    services[name] = obj

    # Inject config if service has a set_config method
    # Note: We only support set_config() method, not direct attribute assignment,
    # to avoid overwriting existing data or failing on read-only properties.
    if hasattr(obj, "set_config") and callable(getattr(obj, "set_config")):
        cfg = services.get("config")
        if cfg is None:
            raise RuntimeError(
                f"Z8ter: cannot inject config into '{name}' before use_config()."
            )
        obj.set_config(cfg)


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
        ValueError: If secret key is too short (< 32 characters).

    Notes:
        - Cookie name is fixed to `z8_app_sess`. SameSite=Lax, 7-day max_age.
        - For production, always use a strong, private secret key.

    """
    app = context["app"]
    secret_key = get_config_value(context=context, key="APP_SESSION_KEY")
    secret_key = context.get("secret_key") or secret_key
    if not secret_key:
        raise TypeError("Z8ter: secret key is required for app sessions.")
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise ValueError(
            f"Z8ter: APP_SESSION_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters. "
            "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
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

    Raises:
        ImportError: If z8ter-auth package is not installed.
    """
    try:
        from z8ter.auth.middleware import AuthSessionMiddleware
    except ImportError as e:
        raise ImportError(
            "z8ter-auth is required for authentication. "
            "Install it with: pip install z8ter-auth"
        ) from e

    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_auth_added", False):
        return
    app.starlette_app.add_middleware(AuthSessionMiddleware)
    state._z8_auth_added = True


def use_csrf_builder(context: dict[str, Any]) -> None:
    """Enable CSRF protection middleware.

    Context inputs:
        - secret_key (optional): overrides APP_SESSION_KEY from config.
        - csrf_exempt_paths (optional): list of path prefixes to skip validation.
        - csrf_cookie_secure (optional): set Secure flag on cookie (default: True).

    Raises:
        TypeError: If no secret key can be resolved.

    Notes:
        - CSRF tokens are validated on POST, PUT, DELETE, PATCH requests.
        - Tokens can be submitted via form field 'csrf_token' or header 'X-CSRF-Token'.
        - The token is available in request.state.csrf_token for templates.
    """
    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_csrf_added", False):
        return

    secret_key = get_config_value(context=context, key="APP_SESSION_KEY")
    secret_key = context.get("secret_key") or secret_key
    if not secret_key:
        raise TypeError("Z8ter: secret key is required for CSRF protection.")

    exempt_paths = context.get("csrf_exempt_paths", [])
    cookie_secure = context.get("csrf_cookie_secure", True)

    app.starlette_app.add_middleware(
        CSRFMiddleware,
        secret_key=secret_key,
        exempt_paths=exempt_paths,
        cookie_secure=cookie_secure,
    )
    state._z8_csrf_added = True


def use_rate_limiting_builder(context: dict[str, Any]) -> None:
    """Enable rate limiting middleware.

    Context inputs:
        - rate_limit_requests (optional): requests per minute (default: 60).
        - rate_limit_burst (optional): burst allowance (default: 10).
        - rate_limit_exempt_paths (optional): list of path prefixes to skip.
        - rate_limit_rules (optional): list of RateLimitConfig for path-specific limits.

    Notes:
        - Rate limiting is per-IP address.
        - For production, consider Redis-based rate limiting for distributed systems.
    """
    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_rate_limit_added", False):
        return

    requests_per_minute = context.get("rate_limit_requests", 60)
    burst_size = context.get("rate_limit_burst", 10)
    exempt_paths = context.get("rate_limit_exempt_paths", [])
    rules = context.get("rate_limit_rules", [])

    app.starlette_app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        exempt_paths=exempt_paths,
        rules=rules,
    )
    state._z8_rate_limit_added = True


def use_security_headers_builder(context: dict[str, Any]) -> None:
    """Enable security headers middleware.

    Context inputs:
        - security_enable_hsts (optional): enable HSTS header (default: False).
        - security_hsts_max_age (optional): HSTS max-age in seconds.
        - security_csp (optional): Content-Security-Policy string.
        - security_x_frame_options (optional): X-Frame-Options value (default: "DENY").
        - security_referrer_policy (optional): Referrer-Policy value.
        - security_permissions_policy (optional): Permissions-Policy value.

    Notes:
        - HSTS should only be enabled in production with proper HTTPS.
        - CSP requires careful tuning to avoid breaking functionality.
    """
    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_security_headers_added", False):
        return

    enable_hsts = context.get("security_enable_hsts", False)
    hsts_max_age = context.get("security_hsts_max_age", 31536000)
    csp = context.get("security_csp")
    x_frame_options = context.get("security_x_frame_options", "DENY")
    referrer_policy = context.get(
        "security_referrer_policy", "strict-origin-when-cross-origin"
    )
    permissions_policy = context.get("security_permissions_policy")

    app.starlette_app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,
        hsts_max_age=hsts_max_age,
        content_security_policy=csp,
        x_frame_options=x_frame_options,
        referrer_policy=referrer_policy,
        permissions_policy=permissions_policy,
    )
    state._z8_security_headers_added = True


def use_health_check_builder(context: dict[str, Any]) -> None:
    """Add a health check endpoint at /health.

    Context inputs:
        - health_check_path (optional): path for health endpoint (default: "/health").
        - health_check_include_details (optional): include service status details.

    Notes:
        - Returns JSON: {"status": "healthy", "version": "...", ...}
        - Useful for container orchestration (Docker, Kubernetes).
        - Exempt from rate limiting by default.
    """
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    import z8ter

    app: Z8ter = context["app"]
    state = app.starlette_app.state
    if getattr(state, "_z8_health_added", False):
        return

    path = context.get("health_check_path", "/health")
    include_details = context.get("health_check_include_details", False)

    async def health_check(request):
        response = {
            "status": "healthy",
            "version": z8ter.__version__,
        }

        if include_details:
            # Add service status details
            services = getattr(state, "services", {})
            response["services"] = {
                name: "available" for name in services.keys()
            }

        return JSONResponse(response)

    # Add route to the app
    route = Route(path, health_check, methods=["GET"], name="health_check")
    app.starlette_app.routes.append(route)
    state._z8_health_added = True
