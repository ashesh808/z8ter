# Authentication

Z8ter provides session authentication, Argon2id password helpers, and route guards. Authentication is opt-in: the generated starter does not automatically install login routes, repositories, or authentication middleware.

## Configure repositories and middleware

For a local prototype or tests, use the supplied in-memory repositories:

```python
from z8ter.builders.app_builder import AppBuilder
from z8ter.testing import InMemorySessionRepo, InMemoryUserRepo

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()
builder.use_auth_repos(
    session_repo=InMemorySessionRepo(),
    user_repo=InMemoryUserRepo(),
)
builder.use_authentication()
builder.use_csrf(cookie_secure=False)  # Local HTTP only; use True with HTTPS
app = builder.build(debug=True)
asgi_app = app.starlette_app
```

Provide these settings before using CSRF or the guards:

```dotenv
APP_SESSION_KEY=replace-with-a-generated-private-key-at-least-32-characters
LOGIN_PATH=/login
APP_PATH=/app/dashboard
```

Use persistent repositories for persistent sessions. The built-in SQLite implementations accept a `Database` instance:

```python
from z8ter.database import SQLiteSessionRepo, SQLiteUserRepo

# db is an initialized Database; config is your configuration accessor.
session_repo = SQLiteSessionRepo(db, secret_key=config("APP_SESSION_KEY"))
user_repo = SQLiteUserRepo(db)
```

Initialize SQLite tables before serving requests; see [Configuration](configuration.md). Register these repositories with `use_auth_repos()` before `use_authentication()`.

## Repository contracts are synchronous

Implement the protocols in `z8ter.auth.contracts` with regular `def` methods, not `async def`. Authentication middleware and `SessionManager` call repository methods in a thread pool. Supplying coroutine methods would return coroutine objects instead of the expected records.

`SessionRepo` provides:

- `insert(*, sid_plain, user_id, expires_at, remember, ip, user_agent, rotated_from_sid=None)`
- `revoke(*, sid_plain)`
- `get_user_id(sid_plain)`
- `revoke_all_for_user(user_id)`
- `cleanup_expired()`

Store session IDs hashed, enforce expiry/revocation on lookup, and use timezone-aware UTC expiry timestamps. `UserRepo` requires `get_user_by_id(user_id)`, returning a public user mapping or `None`. Keep password hashes out of that public mapping.

The SQLite and in-memory user repositories also expose synchronous `create_user(email=..., password_hash=..., name=...)`, `get_user_by_email(email)`, and `update_password(user_id, password_hash)`. They generate user IDs themselves. Use a thread pool when calling blocking repository methods directly from an async handler.

## Passwords

```python
from z8ter.auth.crypto import hash_password, needs_rehash, verify_password

stored_hash = hash_password("example-password")
valid = verify_password(stored_hash, "example-password")
if valid and needs_rehash(stored_hash):
    replacement_hash = hash_password("example-password")
    # Persist replacement_hash with your repository.
```

Rehashing is explicit; `verify_password()` does not update stored records. Password policy, account verification, and lockout behavior belong in your application flow.

## Login handler

This example uses the published repositories and `SessionManager` directly. It assumes you have created `templates/pages/login.jinja`, registered a user, and configured the middleware above. The login template should include a hidden `csrf_token` field.

```python
# endpoints/views/login.py
import asyncio
from z8ter.auth.crypto import hash_password, needs_rehash, verify_password
from z8ter.auth.guards import get_post_login_redirect, skip_if_authenticated
from z8ter.auth.sessions import SessionManager
from z8ter.endpoints.view import View
from z8ter.responses import RedirectResponse


class Login(View):
    @skip_if_authenticated
    async def get(self, request):
        return self.render(request, "pages/login.jinja", {})

    @skip_if_authenticated
    async def post(self, request):
        async with request.form() as form:
            email = str(form.get("email", "")).strip()
            password = str(form.get("password", ""))
            remember = form.get("remember") == "on"

        repo = request.app.state.user_repo
        user = await asyncio.to_thread(repo.get_user_by_email, email)
        valid = bool(user and user.get("is_active", True))
        if valid:
            valid = await asyncio.to_thread(
                verify_password, user["password_hash"], password
            )
        if not valid:
            return self.render(request, "pages/login.jinja", {
                "error": "Invalid email or password"
            })

        if needs_rehash(user["password_hash"]):
            new_hash = await asyncio.to_thread(hash_password, password)
            await asyncio.to_thread(repo.update_password, user["id"], new_hash)

        config = request.app.state.services["config"]
        response = RedirectResponse(
            get_post_login_redirect(request, fallback=config("APP_PATH")),
            status_code=303,
        )
        sessions = SessionManager(request.app.state.session_repo)
        sid = await sessions.start_session(user["id"], remember=remember)
        await sessions.set_session_cookie(
            response, sid, remember=remember, secure=True
        )
        return response
```

The example sets an HTTPS-only cookie. For local HTTP development, use `secure=False` deliberately. Add rate limiting and account-lockout checks for your application's login flow; see [Security](security.md). A `manage_sessions` service is not created by the framework.

### Session lifecycle

All four `SessionManager` operations are async, including cookie mutations:

```python
from z8ter.auth.sessions import SessionManager

async def finish_login(response, session_repo, user_id):
    sessions = SessionManager(session_repo)
    ttl = 30 * 24 * 60 * 60
    sid = await sessions.start_session(user_id, remember=True, ttl=ttl)
    await sessions.set_session_cookie(
        response, sid, secure=True, remember=True, ttl=ttl
    )
    return response
```

The default session TTL is seven days. `remember=True` makes the cookie persistent; it does not automatically extend the server-side TTL. Pass the same chosen TTL to both methods. The cookie is named `z8_auth_sid`, with HttpOnly, SameSite=Lax, and path `/`.

### Logout

```python
# endpoints/api/auth.py
from z8ter.auth.sessions import SessionManager
from z8ter.endpoints.api import API
from z8ter.responses import JSONResponse


class Auth(API):
    @API.endpoint("POST", "/logout")
    async def logout(self, request):
        sessions = SessionManager(request.app.state.session_repo)
        sid = request.cookies.get(sessions.cookie_name)
        if sid:
            await sessions.revoke_session(sid)
        response = JSONResponse({"ok": True})
        await sessions.clear_session_cookie(response)
        return response
```

Send the CSRF token with this POST when CSRF protection is enabled. Clearing a browser cookie alone does not revoke the stored session.

## Guards and current user

`AuthSessionMiddleware` sets `request.state.user` to a user mapping or `None`. Missing, expired, revoked, or unresolvable sessions are treated as anonymous.

```python
from z8ter.auth.guards import login_required
from z8ter.endpoints.view import View


class Dashboard(View):
    @login_required
    async def get(self, request):
        return self.render(request, "pages/dashboard.jinja", {
            "user": request.state.user
        })
```

`login_required` returns a 303 redirect to `LOGIN_PATH`, preserving a validated local return URL. `skip_if_authenticated` redirects authenticated users to `APP_PATH`. For APIs that should return JSON 401 instead, check `request.state.user` in the handler and return the desired response. Roles and account verification are not enforced automatically.

For post-login redirects, use `get_post_login_redirect()` instead of trusting a raw `next` query parameter.

## Application sessions are separate

`builder.use_app_sessions()` installs signed client-side application sessions under `z8_app_sess`; handlers access `request.session`. These are not the server-side authentication sessions described above. Data is signed, not encrypted. The builder uses a seven-day age and SameSite=Lax; it does not expose all Starlette cookie options. For custom secure-cookie settings, configure Starlette's `SessionMiddleware` explicitly instead of installing both variants.

## Further reading

- [Security](security.md): CSRF, lockouts, signed reset tokens, audit events
- [Testing](testing.md): in-memory repositories and clients
- [Background Tasks](background-tasks.md): expired-session cleanup
