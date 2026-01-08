# Authentication

Z8ter provides a flexible, protocol-based authentication system with session management, password hashing, and route guards.

## Overview

The auth system consists of:

- **Session Management**: Secure session creation, storage, and cookies
- **Password Hashing**: Argon2id hashing with automatic rehashing
- **Middleware**: Automatic user loading from session cookies
- **Route Guards**: Decorators to protect views and endpoints

## Quick Setup

### 1. Configure the Builder

```python
from z8ter.builders.app_builder import AppBuilder
from app.identity.adapter.session_repo import InMemorySessionRepo
from app.identity.adapter.user_repo import InMemoryUserRepo

builder = AppBuilder()
builder.use_config(".env")
builder.use_templating()
builder.use_vite()

# Add authentication
builder.use_auth_repos(
    session_repo=InMemorySessionRepo(),
    user_repo=InMemoryUserRepo()
)
builder.use_authentication()
builder.use_app_sessions()  # For non-auth session data
builder.use_errors()

app = builder.build(debug=True)
```

### 2. Environment Variables

```env
# .env
SECRET_KEY=your-secret-key-at-least-32-characters
LOGIN_PATH=/login
APP_PATH=/app/dashboard
```

## Repository Protocols

Z8ter uses protocols (interfaces) for session and user storage, allowing you to implement any backend.

### SessionRepo Protocol

```python
from typing import Protocol
from datetime import datetime


class SessionRepo(Protocol):
    async def insert(
        self,
        sid_plain: str,
        user_id: str,
        expires_at: datetime,
        remember: bool,
        ip: str,
        user_agent: str,
        rotated_from_sid: str | None = None
    ) -> None:
        """Store a new session.

        IMPORTANT: Hash `sid_plain` before storing!
        """
        ...

    async def revoke(self, sid_plain: str) -> bool:
        """Revoke a session by ID. Returns True if found and revoked."""
        ...

    async def get_user_id(self, sid_plain: str) -> str | None:
        """Look up user_id from session. Returns None if not found or expired."""
        ...
```

### UserRepo Protocol

```python
from typing import Protocol


class UserRepo(Protocol):
    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Fetch user by ID. Returns dict with at least {"id": ...}."""
        ...
```

## Implementing Repositories

### In-Memory Session Repository

```python
# app/identity/adapter/session_repo.py
import hashlib
from datetime import datetime


class InMemorySessionRepo:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def _hash_sid(self, sid_plain: str) -> str:
        return hashlib.sha256(sid_plain.encode()).hexdigest()

    async def insert(
        self,
        sid_plain: str,
        user_id: str,
        expires_at: datetime,
        remember: bool,
        ip: str,
        user_agent: str,
        rotated_from_sid: str | None = None
    ) -> None:
        sid_hash = self._hash_sid(sid_plain)
        self._sessions[sid_hash] = {
            "user_id": user_id,
            "expires_at": expires_at,
            "remember": remember,
            "ip": ip,
            "user_agent": user_agent,
        }

    async def revoke(self, sid_plain: str) -> bool:
        sid_hash = self._hash_sid(sid_plain)
        if sid_hash in self._sessions:
            del self._sessions[sid_hash]
            return True
        return False

    async def get_user_id(self, sid_plain: str) -> str | None:
        sid_hash = self._hash_sid(sid_plain)
        session = self._sessions.get(sid_hash)

        if not session:
            return None

        if datetime.now() > session["expires_at"]:
            del self._sessions[sid_hash]
            return None

        return session["user_id"]
```

### In-Memory User Repository

```python
# app/identity/adapter/user_repo.py

class InMemoryUserRepo:
    def __init__(self):
        self._users: dict[str, dict] = {}

    async def get_user_by_id(self, user_id: str) -> dict | None:
        return self._users.get(user_id)

    async def create_user(self, user_id: str, email: str, password_hash: str) -> dict:
        user = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
        }
        self._users[user_id] = user
        return user

    async def get_user_by_email(self, email: str) -> dict | None:
        for user in self._users.values():
            if user.get("email") == email:
                return user
        return None
```

### Database Repository (Example with SQLAlchemy)

```python
# app/identity/adapter/session_repo.py
import hashlib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete


class DatabaseSessionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _hash_sid(self, sid: str) -> str:
        return hashlib.sha256(sid.encode()).hexdigest()

    async def insert(self, sid_plain: str, user_id: str, expires_at: datetime, **kwargs):
        session = SessionModel(
            sid_hash=self._hash_sid(sid_plain),
            user_id=user_id,
            expires_at=expires_at,
            **kwargs
        )
        self.db.add(session)
        await self.db.commit()

    async def revoke(self, sid_plain: str) -> bool:
        result = await self.db.execute(
            delete(SessionModel).where(
                SessionModel.sid_hash == self._hash_sid(sid_plain)
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_user_id(self, sid_plain: str) -> str | None:
        result = await self.db.execute(
            select(SessionModel).where(
                SessionModel.sid_hash == self._hash_sid(sid_plain),
                SessionModel.expires_at > datetime.now()
            )
        )
        session = result.scalar_one_or_none()
        return session.user_id if session else None
```

## Password Hashing

Z8ter uses Argon2id for secure password hashing:

```python
from z8ter.auth.crypto import hash_password, verify_password, needs_rehash

# Hash a password
password_hash = hash_password("user-password")

# Verify a password
is_valid = verify_password(password_hash, "user-password")

# Check if rehashing is needed (after algorithm updates)
if needs_rehash(password_hash):
    new_hash = hash_password("user-password")
    # Update stored hash
```

## Session Management

### SessionManager

```python
from z8ter.auth.sessions import SessionManager

# Create manager with your session repo
session_manager = SessionManager(session_repo)

# Start a new session
sid = await session_manager.start_session(
    user_id="user-123",
    remember=True,  # Long-lived session
    ip="127.0.0.1",
    user_agent="Mozilla/5.0...",
    ttl=86400 * 30  # 30 days
)

# Set session cookie
session_manager.set_session_cookie(
    response,
    sid,
    secure=True,  # HTTPS only
    remember=True,
    ttl=86400 * 30
)

# Revoke a session
await session_manager.revoke_session(sid)

# Clear session cookie
session_manager.clear_session_cookie(response)
```

## Login Flow

### Login View

```python
# endpoints/views/login.py
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import Response, RedirectResponse
from z8ter.auth.guards import skip_if_authenticated
from z8ter.auth.crypto import verify_password, needs_rehash


class Login(View):
    @skip_if_authenticated
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/login.jinja")

    @skip_if_authenticated
    async def post(self, request: Request) -> Response:
        form = await request.form()
        email = form.get("email", "")
        password = form.get("password", "")
        remember = form.get("remember") == "on"

        # Get services
        services = request.app.state.services
        user_repo = services["user_repo"]
        manage_sessions = services["manage_sessions"]
        config = services["config"]

        # Find user
        user = await user_repo.get_user_by_email(email)
        if not user:
            return self.render(request, "pages/login.jinja", {
                "error": "Invalid email or password"
            })

        # Verify password
        if not verify_password(user["password_hash"], password):
            return self.render(request, "pages/login.jinja", {
                "error": "Invalid email or password"
            })

        # Rehash if needed
        if needs_rehash(user["password_hash"]):
            new_hash = hash_password(password)
            await user_repo.update_password_hash(user["id"], new_hash)

        # Create session
        response = RedirectResponse(
            url=request.query_params.get("next", config("APP_PATH")),
            status_code=303
        )

        await manage_sessions.login(
            response=response,
            user_id=user["id"],
            remember=remember,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
        )

        return response
```

### Logout Endpoint

```python
# endpoints/api/auth.py
from z8ter.endpoints.api import API
from z8ter.requests import Request
from z8ter.responses import JSONResponse


class Auth(API):
    @API.endpoint("POST", "/logout")
    async def logout(self, request: Request):
        services = request.app.state.services
        manage_sessions = services["manage_sessions"]

        response = JSONResponse({"ok": True})
        await manage_sessions.logout(request, response)

        return response
```

## Route Guards

### Protecting Views

```python
from z8ter.endpoints.view import View
from z8ter.auth.guards import login_required, skip_if_authenticated


class Dashboard(View):
    @login_required
    async def get(self, request: Request) -> Response:
        user = request.state.user  # Guaranteed to exist
        return self.render(request, "pages/dashboard.jinja", {
            "user": user
        })


class Login(View):
    @skip_if_authenticated  # Redirect logged-in users away
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/login.jinja")
```

### Custom Guards

```python
from functools import wraps
from z8ter.responses import RedirectResponse, JSONResponse


def admin_required(func):
    """Require admin role"""
    @wraps(func)
    async def wrapper(self, request):
        user = getattr(request.state, "user", None)

        if not user:
            return RedirectResponse(url="/login")

        if user.get("role") != "admin":
            return RedirectResponse(url="/unauthorized")

        return await func(self, request)
    return wrapper


def api_auth_required(func):
    """Require authentication for API endpoints"""
    @wraps(func)
    async def wrapper(self, request):
        user = getattr(request.state, "user", None)

        if not user:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Authentication required"}
            }, status_code=401)

        return await func(self, request)
    return wrapper
```

## Auth Middleware

The `AuthSessionMiddleware` automatically loads users from session cookies:

```python
# How it works internally:
async def dispatch(self, request, call_next):
    # 1. Read session cookie
    sid = request.cookies.get("z8_auth_sid")

    if sid:
        # 2. Look up session → get user_id
        user_id = await session_repo.get_user_id(sid)

        if user_id:
            # 3. Fetch user
            user = await user_repo.get_user_by_id(user_id)
            request.state.user = user

    if not hasattr(request.state, "user"):
        request.state.user = None

    return await call_next(request)
```

## Accessing the Current User

### In Views

```python
class Profile(View):
    @login_required
    async def get(self, request: Request) -> Response:
        user = request.state.user
        return self.render(request, "pages/profile.jinja", {
            "user": user
        })
```

### In APIs

```python
class Users(API):
    @API.endpoint("GET", "/me")
    async def get_current_user(self, request: Request):
        user = request.state.user

        if not user:
            return JSONResponse({
                "ok": False,
                "error": {"message": "Not authenticated"}
            }, status_code=401)

        return JSONResponse({
            "ok": True,
            "data": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name")
            }
        })
```

### In Templates

```jinja
{% if request.state.user %}
    <span>Welcome, {{ request.state.user.name }}!</span>
    <a href="/logout">Logout</a>
{% else %}
    <a href="/login">Login</a>
{% endif %}
```

## Registration Flow

```python
# endpoints/views/register.py
from z8ter.endpoints.view import View
from z8ter.auth.guards import skip_if_authenticated
from z8ter.auth.crypto import hash_password
import uuid


class Register(View):
    @skip_if_authenticated
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/register.jinja")

    @skip_if_authenticated
    async def post(self, request: Request) -> Response:
        form = await request.form()
        email = form.get("email", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")

        errors = {}

        # Validation
        if not email:
            errors["email"] = "Email is required"
        if len(password) < 8:
            errors["password"] = "Password must be at least 8 characters"
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match"

        if errors:
            return self.render(request, "pages/register.jinja", {
                "errors": errors,
                "email": email
            })

        # Check if user exists
        services = request.app.state.services
        user_repo = services["user_repo"]

        existing = await user_repo.get_user_by_email(email)
        if existing:
            return self.render(request, "pages/register.jinja", {
                "errors": {"email": "Email already registered"},
                "email": email
            })

        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        await user_repo.create_user(
            user_id=user_id,
            email=email,
            password_hash=password_hash
        )

        # Auto-login after registration
        manage_sessions = services["manage_sessions"]
        config = services["config"]

        response = RedirectResponse(
            url=config("APP_PATH"),
            status_code=303
        )

        await manage_sessions.login(
            response=response,
            user_id=user_id,
            remember=False,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
        )

        return response
```

## Security Best Practices

1. **Always hash session IDs** before storing them
2. **Use HTTPS** in production (`secure=True` for cookies)
3. **Set appropriate TTLs** for sessions (shorter for sensitive apps)
4. **Rotate sessions** on privilege changes
5. **Clear sessions** on password change
6. **Rate limit** login attempts
7. **Use strong passwords** (enforce minimum requirements)
8. **Log security events** (failed logins, session creation/revocation)

## Next Steps

- [Configuration](configuration.md) - Environment and settings
- [CLI Reference](cli.md) - Command-line tools
- [Views & Pages](views.md) - Server-rendered pages
