# Testing

`z8ter.testing` provides in-memory repositories, an email outbox, and a minimal app builder for tests that can use fakes instead of external databases or email delivery.

## Test Dependencies

Z8ter 0.3.1 requires Starlette `>=1.6,<2`. Its development extra includes pytest, pytest-asyncio, `httpx`, and `httpx2`, including the client dependency used by current Starlette testing support:

```bash
python -m pip install "z8ter[dev]>=0.3.1,<0.4"
python -m pytest
```

Use these commands in your active test environment. Do not retain a Starlette 0.x pin from a 0.3.0 environment when upgrading.

## A Minimal Test App

`create_test_app()` configures application-session cookies with a fixed **test-only** key and, by default, framework error handlers. When both `session_repo` and `user_repo` are provided, it registers those repositories and authentication middleware.

It still uses the application’s route discovery, so run this example from a project where the `endpoints.views` and `endpoints.api` packages are importable. It does **not** enable config, templates, Vite, email, CSRF protection, or background tasks:

```python
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from z8ter.testing import InMemorySessionRepo, InMemoryUserRepo, create_test_app


def test_anonymous_request():
    app = create_test_app(
        session_repo=InMemorySessionRepo(),
        user_repo=InMemoryUserRepo(),
    )

    async def identity(request):
        return JSONResponse({"user": request.state.user})

    app.starlette_app.routes.append(Route("/_test_identity", identity))
    with TestClient(app.starlette_app) as client:
        response = client.get("/_test_identity")
    assert response.status_code == 200
    assert response.json() == {"user": None}
```

Use `TestClient` as a context manager to run lifespan startup and shutdown, particularly when testing background tasks. Add your application's actual login handlers to test a login flow; the helper does not generate login routes or seed users.

## In-Memory Repositories

`InMemorySessionRepo` hashes stored session IDs and checks expiry and revocation. Rotation revokes the preceding session. `InMemoryUserRepo` supports user creation, lookup, password updates, and other methods that mirror the SQLite repository.

The user repository stores the password hash you supply; it does not hash a raw password automatically:

```python
from z8ter.auth.crypto import hash_password
from z8ter.testing import InMemoryUserRepo


def test_user_lookup():
    repo = InMemoryUserRepo()
    user = repo.create_user(
        email="ada@example.com",
        password_hash=hash_password("a test password"),
        name="Ada",
    )
    assert repo.get_user_by_email("ada@example.com")["id"] == user["id"]
    assert "password_hash" not in repo.get_user_by_id(user["id"])
```

Create fresh repositories per test to keep state isolated. These fakes are intended for testing and do not replace production persistence.

## Tests Against Your Project

To test rendered pages, run tests from your real project root so its endpoint packages are importable, select that directory for assets, and explicitly enable the integrations the test needs. For example, in `tests/test_pages.py`:

```python
from pathlib import Path

import z8ter
from starlette.testclient import TestClient
from z8ter.builders.app_builder import AppBuilder


def test_home_page():
    project_dir = Path(__file__).resolve().parents[1]
    previous_dir = z8ter.get_app_dir()
    z8ter.set_app_dir(project_dir)
    try:
        builder = AppBuilder()
        builder.use_config()
        builder.use_templating()
        builder.use_vite()
        builder.use_errors()
        app = builder.build(debug=True)

        with TestClient(app.starlette_app) as client:
            response = client.get("/")
        assert response.status_code == 200
    finally:
        z8ter.set_app_dir(previous_dir)
```

Build the project's browser assets before tests that render Vite script tags:

```bash
npm run build
python -m pytest
```

Choose test secrets, repositories, and providers explicitly when adding authentication, CSRF, email, or other integrations to this builder. Changing the app directory alone does not configure those services.

## Capturing Email

Use `InMemoryEmailProvider` with `EmailService` for a test that sends no external email:

```python
import asyncio

from z8ter.email import EmailService
from z8ter.testing import InMemoryEmailProvider


def test_welcome_email():
    provider = InMemoryEmailProvider()
    email = EmailService(provider, default_from="noreply@example.com")
    asyncio.run(email.send_email(
        to="ada@example.com",
        subject="Welcome!",
        text="Thanks for signing up.",
    ))
    assert provider.outbox[0].to == ["ada@example.com"]
    assert provider.outbox[0].subject == "Welcome!"
```

For request-level email tests, configure the same provider with `builder.use_config()` and `builder.use_email(provider=provider, default_from=...)` before building your app. Await delivery or the relevant task before checking the outbox.
