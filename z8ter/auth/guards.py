"""Auth route guards for Z8ter.

These decorators are applied to view/API handlers to enforce authentication
rules. They integrate with Z8ter's request/response objects and assume that
middleware has already attached `request.state.user` (or left it None).

Provided guards:
- `login_required`: Protects a route so only authenticated users may access it.
  Redirects to login if missing, preserving the requested URL as `?next=...`.
- `skip_if_authenticated`: Inverse guard; used for login/register routes so that
  authenticated users are redirected to the main app instead of re-logging in.

Assumptions:
- A `config` service is registered in `request.app.state.services["config"]`.
  - `LOGIN_PATH`: Path to the login page (e.g., "/login").
  - `APP_PATH`: Path to redirect logged-in users (e.g., "/app" or "/dashboard").
- Middleware is responsible for resolving the current user and setting
  `request.state.user`. By convention, None = not authenticated.

Security notes:
- Always use a safe HTTP status for redirects (303 = "See Other") so POST
  requests don't accidentally get replayed.
- The `next` query parameter is validated using `is_safe_redirect_url` to prevent
  open redirect vulnerabilities.
"""

from functools import wraps
from urllib.parse import quote, unquote

from z8ter.requests import Request
from z8ter.responses import RedirectResponse
from z8ter.security.redirect import get_safe_redirect_url, is_safe_redirect_url


def login_required(handler):
    """Require authentication before accessing a route.

    If `request.state.user` is missing/None, the user is redirected to LOGIN_PATH
    with a `?next=<original>` query parameter so they can be sent back after login.

    Usage:
        @login_required
        async def dashboard(self, request: Request):
            ...

    Returns:
        - RedirectResponse to login if unauthenticated.
        - Otherwise, forwards call to the wrapped handler.

    Security:
        - The `next` parameter is validated to prevent open redirect attacks.
        - Only relative URLs are accepted; absolute URLs are rejected.
    """

    @wraps(handler)
    async def wrapper(self, request: Request, *args, **kwargs):
        config = request.app.state.services["config"]
        login_path = config("LOGIN_PATH")
        user = getattr(request.state, "user", None)

        if not user:
            next_url = request.url.path
            if request.url.query:
                next_url = f"{next_url}?{request.url.query}"
            # Only preserve the next URL if it's safe (relative path)
            if is_safe_redirect_url(next_url):
                redirect_url = f"{login_path}?next={quote(next_url, safe='')}"
            else:
                redirect_url = login_path
            return RedirectResponse(redirect_url, status_code=303)

        return await handler(self, request, *args, **kwargs)

    return wrapper


def get_post_login_redirect(request: Request, fallback: str = "/") -> str:
    """Get the safe redirect URL for post-login redirection.

    Extracts the `next` query parameter and validates it to prevent
    open redirect vulnerabilities.

    Args:
        request: The current request object
        fallback: URL to redirect to if `next` is missing or invalid

    Returns:
        Safe redirect URL (either validated `next` or fallback)

    Usage:
        redirect_url = get_post_login_redirect(request, fallback="/app")
        return RedirectResponse(redirect_url, status_code=303)
    """
    next_url = request.query_params.get("next")
    if next_url:
        # URL-decode the next parameter
        next_url = unquote(next_url)
    return get_safe_redirect_url(next_url, fallback=fallback)


def skip_if_authenticated(handler):
    """Skip certain routes if the user is already authenticated.

    Typical use case: login/register pages. If the user is logged in, redirect
    them away to APP_PATH instead of showing the page.

    Usage:
        @skip_if_authenticated
        async def login(self, request: Request):
            ...

    Returns:
        - RedirectResponse to app path if already authenticated.
        - Otherwise, forwards call to the wrapped handler.

    """

    @wraps(handler)
    async def wrapper(self, request: Request, *args, **kwargs):
        config = request.app.state.services["config"]
        app_path = config("APP_PATH")
        user = getattr(request.state, "user", None)

        if user:
            return RedirectResponse(f"{app_path}", status_code=303)

        return await handler(self, request, *args, **kwargs)

    return wrapper
